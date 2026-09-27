"""Avisos para a profissional fora do painel (e-mail).

Dois avisos: o de alerta (abaixo) e o de pedido para falar com ela
(`notify_human_request`, no fim do arquivo).

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
"""

import logging
import smtplib
from email.message import EmailMessage
from zoneinfo import ZoneInfo

from app import models
from app.config import settings
from app.database import SessionLocal
from app.models import AlertEventType, AlertLevel

logger = logging.getLogger(__name__)

_BRASILIA = ZoneInfo("America/Sao_Paulo")

# Assunto e explicação de cada nível, em linguagem da profissional.
_LEVEL_TEXT = {
    AlertLevel.EMERGENCY: (
        "[MarIA] EMERGÊNCIA: possível risco à vida",
        "A triagem identificou um possível risco à vida. A pessoa recebeu a "
        "mensagem fixa de emergência (SAMU 192, CVV 188) e a MarIA parou de "
        "responder nessa conversa até você liberar pelo painel.",
    ),
    AlertLevel.POSSIBLE_RISK: (
        "[MarIA] Alerta: dúvida sobre segurança",
        "A triagem encontrou uma referência a morte ou risco com intenção "
        "incerta. A MarIA continua a conversa normalmente; vale você olhar.",
    ),
    AlertLevel.BOT_REFUSED: (
        "[MarIA] Uma pessoa quer falar com você",
        "A pessoa disse que não quer conversar com um bot. A MarIA parou de "
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
        "— MarIA"
    )
    return message


def _send(message: EmailMessage) -> None:
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
        smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(message)


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


HUMAN_REQUEST_SUBJECT = "[MarIA] Uma pessoa pediu para falar com você"
HUMAN_REQUEST_TEXT = (
    "Uma pessoa pediu para falar com você. A MarIA avisou que você responde "
    "por este canal, e a conversa está marcada como \"Aguardando você\" no painel."
)


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
        _send(
            _compose(
                professional,
                HUMAN_REQUEST_SUBJECT,
                HUMAN_REQUEST_TEXT,
                conversation.awaiting_reply_since or models._now(),
                conversation.contact.channel,
            )
        )
    except Exception:
        logger.exception("falha ao enviar o aviso de pedido da conversa %s", conversation_id)
    finally:
        db.close()
