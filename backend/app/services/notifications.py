"""Avisos para a profissional fora do painel (e-mail).

Avisos: o de alerta (abaixo), o de pedido para a profissional
(`notify_human_request`: a pessoa pediu para falar com ela, ou a SelenIA
levou um pedido com `avisar_profissional`) e os de pedido de horário.

A Marília pediu para saber na hora, sem precisar estar com o painel
aberto. O e-mail sai da conta do produto (`settings.smtp_*`) para o
endereço que cada profissional configura (`Professional.alert_email`).

Duas decisões:

- **Nenhum conteúdo da conversa no e-mail.** Só o tipo do alerta, o
  horário e o canal. O e-mail sai do sistema e fica guardado no provedor
  dela, fora do alcance da cifra e da retenção de 90 dias; o trecho e a
  conversa ficam no painel.
- **O resultado entra na trilha do alerta.** Enviado vira `notified`;
  qualquer falha (sem endereço, sem SMTP, erro no envio) vira
  `notify_failed`. Um alerta que não chegou à profissional não pode
  passar despercebido.

O envio roda depois da resposta ao contato (tarefa em segundo plano):
um servidor de e-mail lento não pode atrasar a mensagem de emergência.

**Em consulta, os pedidos esperam** (decisão do Pedro, 03/11/2026). Com
a profissional em consulta (botão ou Google Agenda, ver
`services/availability.py`), os e-mails de pedido (falar com ela,
horário especial, pagamento, valor, pedido de sessão, troca,
cancelamento) não saem na hora: ficam marcados em
`Professional.held_notices_since`. Quando a consulta acaba,
`send_held_notices` manda **um e-mail só**, com quantas pessoas aguardam
e por quê. Os alertas de segurança (emergência, dúvida sobre segurança,
recusa do bot) nunca esperam.
"""

import logging
import smtplib
from email.message import EmailMessage
from zoneinfo import ZoneInfo

from app import models
from app.config import settings
from app.database import SessionLocal
from app.models import AlertEventType, AlertLevel, AwaitingReason
from app.services import availability, calendar

logger = logging.getLogger(__name__)

_BRASILIA = ZoneInfo("America/Sao_Paulo")

# Assunto e explicação de cada nível, em linguagem da profissional.
_LEVEL_TEXT = {
    AlertLevel.EMERGENCY: (
        "[SelenIA] EMERGÊNCIA: possível risco à vida",
        "A triagem identificou um possível risco à vida. A pessoa recebeu a "
        "mensagem fixa de emergência (SAMU 192, CVV 188) e a SelenIA parou de "
        "responder nessa conversa até você liberar pelo painel.",
    ),
    AlertLevel.POSSIBLE_RISK: (
        "[SelenIA] Alerta: dúvida sobre segurança",
        "A triagem encontrou uma referência a morte ou risco com intenção "
        "incerta. A SelenIA continua a conversa normalmente; vale você olhar.",
    ),
    AlertLevel.BOT_REFUSED: (
        "[SelenIA] Uma pessoa quer falar com você",
        "A pessoa disse que não quer conversar com um bot. A SelenIA parou de "
        "responder nessa conversa e avisou que você responde pessoalmente.",
    ),
}

_CHANNEL_TEXT = {"whatsapp": "WhatsApp", "simulator": "simulador do painel"}


def build_email(alert: models.SafetyAlert, professional: models.Professional) -> EmailMessage:
    subject, explanation = _LEVEL_TEXT[alert.level]
    return _compose(professional, subject, explanation, alert.created_at, alert.conversation.contact.channel)


def _compose(professional, subject, explanation, when, channel) -> EmailMessage:
    when = when.astimezone(_BRASILIA).strftime("%d/%m/%Y às %H:%M")
    channel = _CHANNEL_TEXT.get(channel, channel)

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_from or settings.smtp_user
    message["To"] = professional.alert_email
    message.set_content(
        f"Olá, {professional.name}.\n\n"
        f"{explanation}\n\n"
        f"Quando: {when} (horário de Brasília)\n"
        f"Canal: {channel}\n\n"
        f"Abra o painel para ver a conversa: {settings.frontend_url}\n\n"
        "Por segurança, este e-mail não traz o conteúdo da conversa.\n"
        "— SelenIA"
    )
    return message


def _send(message: EmailMessage) -> None:
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
        smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(message)


def _hold_if_in_session(db, professional: models.Professional, happened_at) -> bool:
    """Em consulta: guarda o aviso para o resumo e devolve True.

    `held_notices_since` fica com o horário do pedido mais antigo
    guardado, para o resumo encontrar todos eles.
    """
    if not availability.current(professional).in_session:
        return False
    happened_at = happened_at or models._now()
    if professional.held_notices_since is None or happened_at < professional.held_notices_since:
        professional.held_notices_since = happened_at
        db.commit()
    logger.info("aviso guardado até o fim da consulta")
    return True


def notify_alert(alert_id: str) -> None:
    """Envia o e-mail do alerta e registra o resultado na trilha.

    Roda como tarefa em segundo plano, então abre a própria sessão do
    banco e nunca deixa exceção escapar.
    """
    db = SessionLocal()
    try:
        alert = db.get(models.SafetyAlert, alert_id)
        if alert is None or alert.level not in _LEVEL_TEXT:
            return
        professional = alert.conversation.professional

        failure = None
        if not professional.alert_email:
            failure = "sem e-mail de alerta configurado"
        elif not settings.smtp_host:
            failure = "envio de e-mail não configurado (SMTP)"
        else:
            try:
                _send(build_email(alert, professional))
            except Exception as exc:
                # Sem conteúdo da conversa no log: só o tipo do erro.
                logger.exception("falha ao enviar e-mail do alerta %s", alert_id)
                failure = f"erro no envio: {type(exc).__name__}"

        db.add(
            models.SafetyAlertEvent(
                alert_id=alert.id,
                event_type=AlertEventType.NOTIFY_FAILED if failure else AlertEventType.NOTIFIED,
                actor="system",
                note=failure or f"e-mail para {professional.alert_email}",
            )
        )
        db.commit()
    except Exception:
        logger.exception("falha ao registrar o aviso do alerta %s", alert_id)
    finally:
        db.close()


HUMAN_REQUEST_SUBJECT = "[SelenIA] Uma pessoa pediu para falar com você"
HUMAN_REQUEST_TEXT = (
    "Uma pessoa pediu para falar com você. A SelenIA avisou que você responde "
    "por este canal, e a conversa está marcada como \"Aguardando você\" no painel."
)
# Pedidos que a SelenIA leva com `avisar_profissional`. Só o tipo do
# pedido, nunca o que a pessoa escreveu. A SelenIA continua respondendo
# nessas conversas.
ASSISTANT_REQUEST_SUBJECT = "[SelenIA] Uma pessoa aguarda uma resposta sua"
ASSISTANT_REQUEST_TEXT = {
    AwaitingReason.SPECIAL_HOURS: "Uma pessoa pediu um horário fora do seu horário de atendimento.",
    AwaitingReason.PAYMENT: "Uma pessoa perguntou sobre uma forma de pagamento que não está no seu perfil.",
    AwaitingReason.PRICE: (
        "Uma pessoa pediu uma exceção no valor (desconto ou outro preço), ou perguntou um valor que "
        "não está no seu perfil."
    ),
    AwaitingReason.OTHER: "Uma pessoa fez uma pergunta que só você pode responder.",
}
ASSISTANT_REQUEST_FOOTER = (
    " A SelenIA disse que ia perguntar a você, e a conversa está marcada como "
    "\"Aguardando você\" no painel. Ela continua tirando as outras dúvidas da pessoa."
)


def request_email_text(reason: str | None) -> tuple[str, str]:
    """Assunto e texto do e-mail de pedido, conforme o motivo."""
    if reason in ASSISTANT_REQUEST_TEXT:
        return ASSISTANT_REQUEST_SUBJECT, ASSISTANT_REQUEST_TEXT[reason] + ASSISTANT_REQUEST_FOOTER
    return HUMAN_REQUEST_SUBJECT, HUMAN_REQUEST_TEXT


def notify_human_request(conversation_id: str) -> None:
    """E-mail quando a pessoa pede para falar com a profissional.

    Mesmas regras do e-mail de alerta (sem conteúdo da conversa, em
    segundo plano), mas sem trilha de auditoria: não é alerta de
    segurança. Uma falha só vai para o log. Sai uma vez por pedido: o
    chamador só agenda quando a conversa ainda não estava aguardando.
    Decisão do Pedro em 27/09/2026.
    """
    db = SessionLocal()
    try:
        conversation = db.get(models.Conversation, conversation_id)
        if conversation is None:
            return
        professional = conversation.professional
        if not professional.alert_email or not settings.smtp_host:
            logger.warning("pedido para falar com a profissional sem e-mail enviado (sem endereço ou SMTP)")
            return
        if _hold_if_in_session(db, professional, conversation.awaiting_reply_since):
            return
        subject, text = request_email_text(conversation.awaiting_reason)
        _send(
            _compose(
                professional,
                subject,
                text,
                conversation.awaiting_reply_since or models._now(),
                conversation.contact.channel,
            )
        )
    except Exception:
        logger.exception("falha ao enviar o aviso de pedido da conversa %s", conversation_id)
    finally:
        db.close()


APPOINTMENT_REQUEST_SUBJECT = "[SelenIA] Um horário aguarda sua confirmação"
APPOINTMENT_REQUEST_TEXT = (
    "Uma pessoa pediu uma sessão e a SelenIA reservou o horário provisoriamente na "
    "sua agenda: {slot}. Confirme ou recuse na tela Agenda do painel. Sem decisão "
    "em 24 horas ou até a hora da sessão, o horário é liberado."
)
RESCHEDULE_REQUEST_SUBJECT = "[SelenIA] Um pedido de troca de horário aguarda você"
RESCHEDULE_REQUEST_TEXT = (
    "Uma pessoa pediu para trocar a sessão dela, e a SelenIA reservou o novo horário provisoriamente: "
    "{slot}. A sessão antiga continua marcada até você decidir. Confirme ou recuse na tela Agenda do "
    "painel. Sem decisão em 24 horas ou até a hora da sessão, o novo horário é liberado e a sessão antiga continua."
)
CANCEL_REQUEST_SUBJECT = "[SelenIA] Um pedido de cancelamento aguarda você"
CANCEL_REQUEST_TEXT = (
    "Uma pessoa pediu para cancelar a sessão de {slot}. A sessão continua marcada até você confirmar "
    "o cancelamento na tela Agenda do painel."
)
APPOINTMENT_EXPIRED_SUBJECT = "[SelenIA] Um horário provisório foi liberado"
APPOINTMENT_EXPIRED_TEXT = (
    "O pedido de sessão para {slot} venceu sem confirmação, e a SelenIA tirou "
    "o horário provisório da sua agenda. {contact} A conversa está no painel."
)
EXPIRED_CONTACT_TOLD = "A pessoa foi avisada pela conversa."
EXPIRED_CONTACT_NOT_TOLD = "A pessoa não pôde ser avisada."


def _notify_appointment(appointment_id: str, subject: str, text: str, when_field: str, hold: bool = True) -> None:
    """E-mail sobre um pedido de horário. Leva o dia e a hora pedidos, mas
    não o nome da pessoa nem o conteúdo da conversa. Falha só vai para o log.

    Com `hold`, em consulta o e-mail fica para o resumo do fim da consulta."""
    db = SessionLocal()
    try:
        appointment = db.get(models.Appointment, appointment_id)
        if appointment is None:
            return
        professional = appointment.professional
        if not professional.alert_email or not settings.smtp_host:
            logger.warning("aviso de pedido de horário sem e-mail enviado (sem endereço ou SMTP)")
            return
        if hold and _hold_if_in_session(db, professional, getattr(appointment, when_field)):
            return
        _send(
            _compose(
                professional,
                subject,
                text.format(slot=calendar.format_slot(appointment.starts_at)),
                getattr(appointment, when_field) or models._now(),
                appointment.conversation.contact.channel,
            )
        )
    except Exception:
        logger.exception("falha ao enviar o aviso do pedido de horário %s", appointment_id)
    finally:
        db.close()


def notify_appointment_request(appointment_id: str) -> None:
    """Pedido novo, de troca ou de cancelamento: o e-mail diz qual."""
    db = SessionLocal()
    try:
        appointment = db.get(models.Appointment, appointment_id)
        kind = None
        urgent = False
        if appointment is not None:
            kind = "cancel" if appointment.cancel_requested_at else "reschedule" if appointment.replaces_id else None
            # Pedido em cima da hora (só cliente especial chega aqui) não
            # espera o resumo do fim da consulta: venceria antes dele.
            urgent = appointment.starts_at - models._now() < calendar.MIN_NOTICE
    finally:
        db.close()
    if kind == "cancel":
        _notify_appointment(appointment_id, CANCEL_REQUEST_SUBJECT, CANCEL_REQUEST_TEXT, "cancel_requested_at")
    elif kind == "reschedule":
        _notify_appointment(
            appointment_id, RESCHEDULE_REQUEST_SUBJECT, RESCHEDULE_REQUEST_TEXT, "created_at", hold=not urgent
        )
    else:
        _notify_appointment(
            appointment_id, APPOINTMENT_REQUEST_SUBJECT, APPOINTMENT_REQUEST_TEXT, "created_at", hold=not urgent
        )


def notify_appointment_expired(appointment_id: str) -> None:
    # Não é pedido de ninguém, é aviso do sistema: sai na hora.
    db = SessionLocal()
    try:
        appointment = db.get(models.Appointment, appointment_id)
        told = appointment is not None and appointment.contact_notified
    finally:
        db.close()
    contact = EXPIRED_CONTACT_TOLD if told else EXPIRED_CONTACT_NOT_TOLD
    # `{slot}` continua para `_notify_appointment` preencher.
    text = APPOINTMENT_EXPIRED_TEXT.replace("{contact}", contact)
    _notify_appointment(appointment_id, APPOINTMENT_EXPIRED_SUBJECT, text, "decided_at", hold=False)


# ---------------------------------------------------------------------------
# Resumo do fim da consulta
# ---------------------------------------------------------------------------

# Uma linha por tipo de pedido. Só o tipo, nunca o que a pessoa escreveu.
HELD_REASON_TEXT = {
    AwaitingReason.WANTS_PROFESSIONAL: "pediu para falar com você",
    AwaitingReason.REFUSES_BOT: "não quis conversar com o bot e aguarda você",
    AwaitingReason.SPECIAL_HOURS: "pediu um horário fora do seu atendimento",
    AwaitingReason.PAYMENT: "perguntou sobre uma forma de pagamento que não está no seu perfil",
    AwaitingReason.PRICE: "pediu uma exceção no valor ou perguntou um valor que não está no seu perfil",
    AwaitingReason.OTHER: "fez uma pergunta que só você pode responder",
}
HELD_APPOINTMENT_TEXT = {
    "new": "pediu uma sessão (horário reservado provisoriamente, confirme na tela Agenda)",
    "reschedule": "pediu para trocar de horário (confirme na tela Agenda)",
    "cancel": "pediu para cancelar uma sessão (confirme na tela Agenda)",
}


def held_summary(db, professional: models.Professional) -> tuple[int, list[tuple[str, int]]]:
    """Quantas pessoas aguardam desde o primeiro aviso guardado, e as linhas
    do e-mail (texto, quantidade). Conta só o que ainda está pendente: se
    ela já respondeu pelo painel durante a consulta, não entra."""
    since = professional.held_notices_since
    people: set[str] = set()
    counts: dict[str, int] = {}

    waiting = (
        db.query(models.Conversation)
        .filter(models.Conversation.professional_id == professional.id)
        .filter(models.Conversation.awaiting_reply_since >= since)
    )
    for conversation in waiting:
        people.add(conversation.id)
        text = HELD_REASON_TEXT.get(conversation.awaiting_reason, HELD_REASON_TEXT[AwaitingReason.OTHER])
        counts[text] = counts.get(text, 0) + 1

    requests = (
        db.query(models.Appointment)
        .filter(models.Appointment.professional_id == professional.id)
        .filter(models.Appointment.conversation_id.isnot(None))
    )
    for appointment in requests:
        if appointment.cancel_requested_at is not None and appointment.cancel_requested_at >= since:
            kind = "cancel"
        elif appointment.status == models.AppointmentStatus.TENTATIVE and appointment.created_at >= since:
            kind = "reschedule" if appointment.replaces_id else "new"
        else:
            continue
        people.add(appointment.conversation_id)
        text = HELD_APPOINTMENT_TEXT[kind]
        counts[text] = counts.get(text, 0) + 1

    return len(people), sorted(counts.items(), key=lambda item: -item[1])


def build_held_email(professional: models.Professional, people: int, lines: list[tuple[str, int]]) -> EmailMessage:
    if people == 1:
        subject = "[SelenIA] Enquanto você atendia, uma pessoa ficou aguardando você"
    else:
        subject = f"[SelenIA] Enquanto você atendia, {people} pessoas ficaram aguardando você"
    since = professional.held_notices_since.astimezone(_BRASILIA).strftime("%d/%m/%Y às %H:%M")
    items = "\n".join(f"- {n} {'pessoa' if n == 1 else 'pessoas'}: {text}" for text, n in lines)

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_from or settings.smtp_user
    message["To"] = professional.alert_email
    message.set_content(
        f"Olá, {professional.name}.\n\n"
        "Você estava em consulta, então a SelenIA guardou estes avisos para não te interromper. "
        "Eles continuam pendentes:\n\n"
        f"{items}\n\n"
        f"Desde: {since} (horário de Brasília)\n\n"
        f"Abra o painel para ver as conversas: {settings.frontend_url}\n\n"
        "Alertas de segurança não esperam o fim da consulta: esses saem na hora.\n"
        "Por segurança, este e-mail não traz o conteúdo das conversas.\n"
        "— SelenIA"
    )
    return message


def send_held_notices() -> None:
    """Manda o resumo de quem terminou a consulta. Roda a cada minuto
    (`main.py`). Se o envio falhar, tenta de novo no minuto seguinte."""
    db = SessionLocal()
    try:
        pending = db.query(models.Professional).filter(models.Professional.held_notices_since.isnot(None)).all()
        for professional in pending:
            if availability.current(professional).in_session:
                continue
            people, lines = held_summary(db, professional)
            if people and professional.alert_email and settings.smtp_host:
                try:
                    _send(build_held_email(professional, people, lines))
                except Exception:
                    logger.exception("falha ao enviar o resumo do fim da consulta")
                    continue
            elif people:
                logger.warning("resumo do fim da consulta sem e-mail enviado (sem endereço ou SMTP)")
            professional.held_notices_since = None
            db.commit()
    finally:
        db.close()
