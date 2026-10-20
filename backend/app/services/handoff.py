"""Handoff: passar a conversa do bot para a profissional e de volta.

Quatro caminhos levam a conversa para a profissional (estado `human`,
bot em silêncio):

1. ela assume pelo painel (`take_over`);
2. ela responde pelo painel (`send_professional_message`): quem escreve
   assume, para o bot e a profissional não falarem ao mesmo tempo;
3. o contato **recusa falar com um bot** ("não quero falar com robô",
   "quero falar com uma pessoa de verdade"): mensagem fixa de
   compreensão, bot parado e alerta para a profissional, esteja ela em
   consulta ou não. Sem números de emergência: não é risco;
4. o contato pede para falar **com a profissional** ("quero falar com o
   Pedro"), com o botão "Em consulta" desligado.

Com o botão "Em consulta" ligado, o pedido do caminho 4 não muda o
estado: a SelenIA avisa que a profissional está em atendimento e oferece
ajuda. Quem recusou o bot não recebe essa oferta de ajuda, porque acabou
de dizer que não quer.

Nos caminhos 3 e 4 a conversa fica "Aguardando você"
(`awaiting_reply_since`) no inbox até a profissional responder ou
devolver a conversa ao bot (decisão do Pedro em 27/09/2026).

Há ainda um quinto jeito de a conversa ficar aguardando, sem parar o
bot: a própria SelenIA avisa a profissional pela ferramenta
`avisar_profissional` (`ask_professional`), quando a pessoa pede algo
que só ela decide (horário fora do expediente, forma de pagamento,
desconto). Antes disso a SelenIA dizia "vou perguntar a ela" e nada
chegava à profissional (teste de 18/10/2026; decisão do Pedro em 19/10).
O motivo fica em `awaiting_reason`, para o painel e o e-mail dizerem o
tipo do pedido sem repetir a conversa.

Só ela devolve a conversa ao bot (`release`), inclusive depois de uma
emergência (decisão da Marília em 23/09: não há retomada automática).

Os textos daqui são fixos e iguais para todas as profissionais, como o
texto de emergência: o bot não improvisa nada sobre a agenda dela.
"""

import re
from datetime import timedelta
from enum import StrEnum

from sqlalchemy.orm import Session

from app import models
from app.models import AlertEventType, AlertLevel, AwaitingReason, ConversationState, MessageRole, SentBy
from app.services import conversations
from app.services.triage import normalize

# Forma neutra de gênero ("{name}" e não "ela"), porque vale para
# qualquer profissional.
HANDOFF_MESSAGE = (
    "Claro! Vou avisar {name}, e a resposta chega por aqui assim que possível."
)
IN_SESSION_MESSAGE = (
    "{name} está em atendimento agora e responde assim que terminar. "
    "Enquanto isso, posso te ajudar com alguma dúvida?"
)
BOT_REFUSED_MESSAGE = (
    "Entendo, e tudo bem preferir conversar com uma pessoa. Vou parar por "
    "aqui e avisar {name}, que responde pessoalmente por este canal assim "
    "que possível."
)
BOT_REFUSED_IN_SESSION_MESSAGE = (
    "Entendo, e tudo bem preferir conversar com uma pessoa. Vou parar por "
    "aqui e avisar {name}, que está em atendimento agora e responde "
    "pessoalmente por este canal assim que terminar."
)


class HumanRequest(StrEnum):
    REFUSES_BOT = "refuses_bot"  # não quer falar com o bot
    WANTS_PROFESSIONAL = "wants_professional"  # quer falar com a profissional


_RECUSA_BOT = [
    # "não quero falar com robô", "não gosto de conversar com IA"
    r"\bnao (quero|gosto de|gostaria de|vou) (falar|conversar) com (robo|bot|maquina|ia|inteligencia artificial"
    r"|assistente virtual|computador)\b",
    # Tolerante a erro de digitação ("nao quero flaar co um robo", "n quero
    # fala c bot"): "não quero" e "robô" a até quatro palavras de distância.
    # "ia" fica de fora aqui porque também é verbo ("não quero ir, ia chover").
    r"\b(nao|n|naum) (quero|gosto|gostaria|vou|curto)\b(?: \S+){0,4} (robo|robos|robozinho|bot|bots|chatbot|maquina)\b",
    # "quero falar com uma pessoa", "prefiro alguém de verdade", "atendente humano"
    r"\b(falar|conversar|atendimento|atendido|atendida) (diretamente |direto )?(com|por) (a |o |uma |um )?"
    r"(pessoa|humano|humana|atendente|alguem de verdade|gente de verdade|pessoa de verdade|pessoa real)\b",
    # "quero falar com ele, não um robô", "quero a Marília, não uma IA".
    # O artigo logo depois do "não" é o que separa da pergunta "você não é
    # um robô?" e deixa "ia" entrar sem confundir com o verbo.
    r"\bnao (um|uma) (robo|bot|chatbot|maquina|ia|inteligencia artificial|assistente virtual)\b",
    r"\b(odeio|detesto|chega de|cansei de) (falar com )?(robo|bot|maquina|ia)\b",
    r"\b(me passa|me transfere|me encaminha) (pra|para) (uma pessoa|alguem|um humano|um atendente)\b",
]
_PEDIDO_PROFISSIONAL = [
    # "tem como conversar com a psicóloga?"
    r"\b(falar|conversar|atendimento|contato) (diretamente |direto )?com (a |o )?"
    r"(psicologa|psicologo|psicanalista|terapeuta|profissional|doutora|doutor|dra|dr)\b",
    # "quero falar com ela", "posso falar direto com ele?"
    r"\b(quero|queria|prefiro|preferia|posso|gostaria de|da pra|tem como|preciso) (falar|conversar) "
    r"(diretamente |direto )?com (ela|ele)\b",
    # "me passa pra ela"
    r"\b(me passa|me transfere|me encaminha) (pra|para) (ela|ele|a doutora|o doutor)\b",
]
_RECUSA_BOT_COMPILADA = [re.compile(p) for p in _RECUSA_BOT]
_PEDIDO_PROFISSIONAL_COMPILADO = [re.compile(p) for p in _PEDIDO_PROFISSIONAL]


def classify_request(text: str, professional: models.Professional) -> HumanRequest | None:
    """O contato recusou o bot, pediu a profissional, ou nenhum dos dois?

    Regras e não modelo: é barato, previsível e fácil de explicar. Perguntar
    "você é humana?" não conta, porque a SelenIA responde isso sozinha. A
    recusa é verificada primeiro: "não quero falar com robô, quero falar
    com o Pedro" é recusa.
    """
    texto = normalize(text)
    if any(p.search(texto) for p in _RECUSA_BOT_COMPILADA):
        return HumanRequest.REFUSES_BOT
    if any(p.search(texto) for p in _PEDIDO_PROFISSIONAL_COMPILADO):
        return HumanRequest.WANTS_PROFESSIONAL
    primeiro_nome = normalize(professional.name).split(" ")[0] if professional.name else ""
    if primeiro_nome:
        pelo_nome = rf"\b(falar|conversar) (diretamente |direto )?com (a |o )?{re.escape(primeiro_nome)}\b"
        if re.search(pelo_nome, texto):
            return HumanRequest.WANTS_PROFESSIONAL
    return None


def handle_human_request(
    db: Session,
    professional: models.Professional,
    conversation: models.Conversation,
    user_message: models.Message,
    request: HumanRequest,
) -> tuple[str, models.SafetyAlert | None]:
    """Responde ao pedido. Devolve o texto enviado ao contato e o alerta, se houver."""
    in_session = professional.is_in_session
    alert = None
    if request == HumanRequest.REFUSES_BOT:
        template = BOT_REFUSED_IN_SESSION_MESSAGE if in_session else BOT_REFUSED_MESSAGE
        alert = conversations.raise_safety_alert(
            db,
            conversation,
            user_message,
            AlertLevel.BOT_REFUSED,
            trigger="handoff:recusa_bot",
            excerpt=user_message.content[:500],
        )
        conversation.state = ConversationState.HUMAN
        reason = AwaitingReason.REFUSES_BOT
    elif in_session:
        template = IN_SESSION_MESSAGE
        reason = AwaitingReason.WANTS_PROFESSIONAL
    else:
        template = HANDOFF_MESSAGE
        conversation.state = ConversationState.HUMAN
        reason = AwaitingReason.WANTS_PROFESSIONAL
    if conversation.awaiting_reply_since is None:
        conversation.awaiting_reply_since = models._now()
    # A recusa do bot é o motivo mais forte: não é trocada por um pedido.
    if conversation.awaiting_reason != AwaitingReason.REFUSES_BOT:
        conversation.awaiting_reason = reason
    reply = template.format(name=professional.name)
    conversations.record_message(db, conversation, MessageRole.ASSISTANT, reply, sent_by=SentBy.SYSTEM)
    return reply, alert


# Motivos que a SelenIA pode passar pela ferramenta `avisar_profissional`.
ASSISTANT_REASONS = (
    AwaitingReason.SPECIAL_HOURS,
    AwaitingReason.PAYMENT,
    AwaitingReason.PRICE,
    AwaitingReason.WANTS_PROFESSIONAL,
    AwaitingReason.OTHER,
)


def ask_professional(
    db: Session, professional: models.Professional, conversation: models.Conversation, reason: str
) -> tuple[str, bool]:
    """A SelenIA avisa a profissional. Devolve o texto da ferramenta e se
    o e-mail deve sair.

    A conversa fica "Aguardando você", mas o bot continua respondendo: a
    pessoa pode seguir tirando dúvidas enquanto a profissional não
    responde. O e-mail sai uma vez por pedido, como no caminho 4: se a
    conversa já estava aguardando, a profissional já foi avisada.
    """
    if reason not in ASSISTANT_REASONS:
        reason = AwaitingReason.OTHER
    name = professional.name
    if conversation.awaiting_reply_since is not None:
        if conversation.awaiting_reason is None:
            conversation.awaiting_reason = reason
            db.commit()
        return (
            f"{name} já tinha recebido um aviso desta conversa e ainda não respondeu; o novo pedido fica "
            f"junto. Diga que o pedido está com {name} e que a resposta vem por esta conversa, sem prometer "
            "prazo. Não aceite nem recuse o pedido.",
            False,
        )
    conversation.awaiting_reply_since = models._now()
    conversation.awaiting_reason = reason
    db.commit()
    return (
        f"Aviso enviado: {name} recebeu um e-mail e a conversa ficou marcada no painel. Diga que você "
        f"avisou {name} e que a resposta vem por esta conversa, sem prometer prazo. Não aceite nem recuse "
        "o pedido.",
        True,
    )


def take_over(db: Session, conversation: models.Conversation) -> None:
    """A profissional assume. Em emergência, a conversa continua em espera."""
    if conversation.state == ConversationState.ACTIVE:
        conversation.state = ConversationState.HUMAN
        db.commit()


def release(db: Session, conversation: models.Conversation) -> None:
    """Devolve a conversa ao bot.

    Se ela estava em espera de emergência, a liberação entra na trilha de
    auditoria de cada alerta da conversa: fica registrado quando e por
    quem o bot voltou a falar depois de um disparo.
    """
    if conversation.state == ConversationState.EMERGENCY_HOLD:
        for alert in conversation.alerts:
            db.add(
                models.SafetyAlertEvent(
                    alert_id=alert.id,
                    event_type=AlertEventType.BOT_RELEASED,
                    actor=conversation.professional_id,
                )
            )
    conversation.state = ConversationState.ACTIVE
    conversation.needs_attention = False
    conversation.awaiting_reply_since = None
    conversation.awaiting_reason = None
    db.commit()


class ReplyWindowClosed(Exception):
    """Passaram 24h desde a última mensagem do contato (regra da Meta)."""


def send_professional_message(
    db: Session, conversation: models.Conversation, content: str, external_id: str | None = None
) -> models.Message:
    """Mensagem escrita pela profissional no painel. Quem escreve, assume."""
    if not conversations.reply_window_open(conversation):
        raise ReplyWindowClosed()
    if conversation.state == ConversationState.ACTIVE:
        conversation.state = ConversationState.HUMAN
    conversation.needs_attention = False
    conversation.awaiting_reply_since = None
    conversation.awaiting_reason = None
    return conversations.record_message(
        db, conversation, MessageRole.ASSISTANT, content, sent_by=SentBy.PROFESSIONAL, external_id=external_id
    )


def start_session(db: Session, professional: models.Professional, minutes: int | None) -> None:
    now = models._now()
    professional.in_session_since = now
    professional.in_session_until = now + timedelta(minutes=minutes) if minutes else None
    db.commit()


def end_session(db: Session, professional: models.Professional) -> None:
    professional.in_session_since = None
    professional.in_session_until = None
    db.commit()
