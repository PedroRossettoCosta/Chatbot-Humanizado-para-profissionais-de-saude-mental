"""O caminho de uma mensagem, igual para o simulador e o WhatsApp.

Dividido em duas partes, porque no WhatsApp elas acontecem em momentos
diferentes:

1. `receive`: grava a mensagem e roda a **triagem na hora**. Emergência
   sai daqui, sem esperar nada.
2. `reply`: a resposta normal (handoff ou MarIA). No simulador vem logo
   em seguida; no WhatsApp, depois da espera que junta mensagens
   quebradas (`services/whatsapp_inbox.py`).

Nenhuma das duas envia nada: devolvem o que foi decidido, e quem chamou
entrega pelo canal (resposta HTTP do simulador ou API da Meta).
"""

from dataclasses import dataclass, field
from datetime import timedelta

from sqlalchemy.orm import Session

from app import models
from app.models import AlertLevel, Channel, ConversationState, MessageRole, SentBy
from app.services import appointments, calendar, conversations, guidelines, handoff, llm, rag, triage

HISTORY_LIMIT = 12

# Mensagem quebrada: a camada 1 da triagem junta a mensagem nova com as
# até duas anteriores do contato que chegaram nos últimos 5 minutos.
FRAGMENT_MESSAGES = 3
FRAGMENT_WINDOW = timedelta(minutes=5)

# Primeira mensagem de toda conversa, antes de qualquer resposta do
# modelo. Diz o nome da assistente e que ela é uma IA (o aviso de IA
# nunca sai do fluxo, ver planejamento-mvp-9out.md, seção 8).
AI_DISCLAIMER_TEMPLATE = (
    "Oi! Eu sou a {assistant}, assistente virtual com inteligência artificial "
    "de {name}. Posso tirar suas dúvidas sobre o atendimento. Não sou uma "
    "pessoa e não substituo consulta ou atendimento clínico."
)


@dataclass
class Received:
    conversation: models.Conversation
    message: models.Message
    # Textos fixos a entregar já, nesta ordem (aviso de IA, emergência).
    immediate: list[str] = field(default_factory=list)
    disclaimer: str | None = None
    triage_level: str = "normal"
    alert_id: str | None = None

    @property
    def emergency(self) -> bool:
        return self.triage_level == AlertLevel.EMERGENCY


@dataclass
class Reply:
    text: str | None = None
    handoff: str | None = None
    alert_id: str | None = None
    # Mandar o e-mail "uma pessoa pediu para falar com você".
    notify_request: bool = False
    # Pedido de horário que a MarIA reservou nesta resposta (e-mail para
    # a profissional confirmar).
    appointment_id: str | None = None
    sources: list[str] = field(default_factory=list)


def receive(
    db: Session,
    professional: models.Professional,
    channel: Channel,
    external_id: str,
    text: str,
    *,
    display_name: str | None = None,
    external_message_id: str | None = None,
    run_triage: bool = True,
) -> Received:
    """Grava a mensagem do contato e roda a triagem.

    A triagem roda antes de tudo e em qualquer estado da conversa: mesmo
    com a profissional no controle ou com um alerta anterior, um novo
    sinal de risco sempre é registrado. `run_triage=False` só para o que
    não é texto (áudio, imagem), que a triagem não consegue ler.
    """
    contact = conversations.get_or_create_contact(db, professional, channel, external_id, display_name)
    conversation, is_new = conversations.get_or_create_conversation(db, contact)

    immediate = []
    disclaimer = None
    if is_new:
        disclaimer = AI_DISCLAIMER_TEMPLATE.format(assistant=guidelines.ASSISTANT_NAME, name=professional.name)
        conversations.record_message(db, conversation, MessageRole.ASSISTANT, disclaimer, sent_by=SentBy.SYSTEM)
        immediate.append(disclaimer)

    message = conversations.record_message(
        db, conversation, MessageRole.USER, text, external_id=external_message_id
    )
    result = Received(conversation=conversation, message=message, immediate=immediate, disclaimer=disclaimer)
    if not run_triage:
        return result

    # A camada 2 lê só as últimas mensagens da conversa dentro da mesma
    # janela da camada 1: com o histórico inteiro, uma emergência de meia
    # hora antes fazia um pedido de horário virar emergência (caso real,
    # 30/09/2026, decisão do Pedro).
    history = conversations.recent_history_within(db, conversation, FRAGMENT_MESSAGES, FRAGMENT_WINDOW)
    recent = conversations.recent_contact_texts(db, conversation, FRAGMENT_MESSAGES, FRAGMENT_WINDOW)
    risk = triage.assess(text, history, professional.audience_description, previous=recent[:-1])
    if risk:
        result.triage_level = risk.level
    if risk and risk.level in (AlertLevel.EMERGENCY, AlertLevel.POSSIBLE_RISK):
        alert = conversations.raise_safety_alert(db, conversation, message, risk.level, risk.trigger, risk.excerpt)
        result.alert_id = alert.id
    elif risk and risk.level == AlertLevel.INTENSE_SUFFERING:
        conversations.mark_needs_attention(db, conversation)
    # Na dúvida sobre segurança, a profissional é avisada e a conversa
    # segue normalmente; só a emergência interrompe o fluxo.
    if result.emergency:
        conversations.record_message(
            db, conversation, MessageRole.ASSISTANT, triage.EMERGENCY_MESSAGE, sent_by=SentBy.SYSTEM
        )
        result.immediate.append(triage.EMERGENCY_MESSAGE)
    return result


def _reply_history(db: Session, conversation: models.Conversation) -> list[dict]:
    """Histórico da resposta normal, sem risco antigo.

    A resposta lê as últimas mensagens para não perder o fio da conversa
    (nome, o que já foi perguntado). Mas a mensagem de risco e o texto de
    emergência de mais de `FRAGMENT_WINDOW` atrás ficam de fora: a
    triagem já tratou disso, e com eles a MarIA voltava a falar em
    suicídio num pedido de horário meia hora depois (caso real,
    30/09/2026, decisão do Pedro). Dentro da janela, ficam.
    """
    messages = (
        db.query(models.Message)
        .filter_by(conversation_id=conversation.id)
        .order_by(models.Message.seq.desc())
        .limit(HISTORY_LIMIT)
        .all()
    )
    if not messages:
        return []
    cutoff = messages[0].created_at - FRAGMENT_WINDOW
    risk_ids = {
        alert.message_id
        for alert in conversation.alerts
        if alert.level in (AlertLevel.EMERGENCY, AlertLevel.POSSIBLE_RISK)
    }

    def is_old_risk(message: models.Message) -> bool:
        if message.created_at >= cutoff:
            return False
        return message.id in risk_ids or (
            message.sent_by == SentBy.SYSTEM and message.content == triage.EMERGENCY_MESSAGE
        )

    return [{"role": m.role, "content": m.content} for m in reversed(messages) if not is_old_risk(m)]


def reply(
    db: Session, professional: models.Professional, conversation: models.Conversation, text: str
) -> Reply:
    """A resposta normal a `text` (a mensagem, ou as mensagens juntas).

    Nada sai se a conversa está com a profissional ou em espera de
    emergência: não há retomada automática, só a profissional libera o
    bot de novo, pelo painel (decisão da Marília em 23/09).
    """
    db.refresh(conversation)
    if conversation.state in (ConversationState.HUMAN, ConversationState.EMERGENCY_HOLD):
        return Reply()

    # Recusa do bot ou pedido para falar com a profissional: texto fixo,
    # sem passar pelo modelo. Ver `services/handoff.py` (inclui o botão
    # "Em consulta").
    request = handoff.classify_request(text, professional)
    if request:
        already_awaiting = conversation.awaiting_reply_since is not None
        last_message = (
            db.query(models.Message)
            .filter_by(conversation_id=conversation.id, role=MessageRole.USER)
            .order_by(models.Message.seq.desc())
            .first()
        )
        reply_text, alert = handoff.handle_human_request(db, professional, conversation, last_message, request)
        return Reply(
            text=reply_text,
            handoff=request,
            alert_id=alert.id if alert else None,
            # A recusa do bot já avisa pelo e-mail do alerta; o pedido
            # simples avisa uma vez, até ela responder.
            notify_request=alert is None and not already_awaiting,
        )

    chunks, metadatas = rag.query(professional.slug, text)
    system_prompt = llm.build_system_prompt(professional, chunks)
    history = _reply_history(db, conversation)
    # A agenda só entra como ferramenta quando está pronta; assim o Google
    # só é consultado se a conversa pedir horário.
    booked = []
    tools = {}
    if calendar.is_ready(professional):

        def run_tool(name, tool_input):
            if name == llm.BOOKING_TOOL["name"]:
                booking = appointments.request(
                    db, professional, conversation, tool_input.get("codigo", ""), tool_input.get("nome", "")
                )
                if booking.appointment_id:
                    booked.append(booking.appointment_id)
                return booking.text
            return calendar.describe_for_assistant(
                professional, pending=appointments.pending_note(db, conversation)
            )

        agenda_tools = [llm.AGENDA_TOOL] + ([llm.BOOKING_TOOL] if calendar.can_book(professional) else [])
        tools = dict(tools=agenda_tools, run_tool=run_tool)
    reply_text = llm.generate_reply(system_prompt, history, **tools)
    conversations.record_message(db, conversation, MessageRole.ASSISTANT, reply_text, sent_by=SentBy.BOT)
    sources = sorted({meta["filename"] for meta in metadatas}) if metadatas else []
    return Reply(text=reply_text, sources=sources, appointment_id=booked[-1] if booked else None)
