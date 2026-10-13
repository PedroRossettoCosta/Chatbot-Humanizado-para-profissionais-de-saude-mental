"""Alertas no painel: situação, trilha de auditoria, visto e revisado.

O alerta nunca muda depois de criado (`models.SafetyAlert`). Tudo o que
acontece com ele depois vira um evento acrescentado
(`SafetyAlertEvent`): o e-mail que saiu ou falhou, a primeira vez que a
profissional abriu, a revisão e a liberação da SelenIA. A situação
("novo" ou "revisado") é derivada dessa trilha, não guardada.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from app import models
from app.models import AlertEventType, AlertLevel


class AlreadyReviewed(Exception):
    pass


# Qual regra ou camada disparou, em linguagem da profissional.
_TRIGGER_TEXT = {
    "camada1:suicidio": "Regra fixa: ideação suicida",
    "camada1:automutilacao": "Regra fixa: automutilação",
    "camada1:tentativa_em_andamento": "Regra fixa: tentativa em andamento",
    "camada1:sem_seguranca": "Regra fixa: sem condições de se manter em segurança",
    "camada1:violencia_perigo_imediato": "Regra fixa: violência ou perigo imediato",
    "camada1:desejo_de_morrer": "Regra fixa: desejo de morrer",
    "camada2:falha": "A análise do modelo falhou; na dúvida, virou alerta (falha fechada)",
    "handoff:recusa_bot": "A pessoa disse que não quer conversar com a SelenIA",
}

# O que a SelenIA fez na hora, pelo nível. Vem do fluxo do código
# (`routers/chat.py`), que é o mesmo para todo alerta daquele nível.
_ACTION_TEXT = {
    AlertLevel.EMERGENCY: (
        "Mensagem fixa de emergência enviada e SelenIA pausada",
        "A pessoa recebeu os contatos do SAMU 192 e do CVV 188. A SelenIA não responde nesta conversa até você liberar.",
    ),
    AlertLevel.POSSIBLE_RISK: (
        "A SelenIA seguiu a conversa",
        "Na dúvida sobre segurança, a conversa continua normalmente e o aviso vai para você olhar.",
    ),
    AlertLevel.BOT_REFUSED: (
        "Mensagem fixa de compreensão enviada e SelenIA parada",
        "A SelenIA avisou que você responde pessoalmente e parou de responder nesta conversa.",
    ),
}

_EVENT_TEXT = {
    AlertEventType.NOTIFIED: "E-mail de aviso enviado",
    AlertEventType.NOTIFY_FAILED: "O e-mail de aviso não saiu",
    AlertEventType.VIEWED: "Você abriu o alerta",
    AlertEventType.REVIEWED: "Marcado como revisado",
    AlertEventType.BOT_RELEASED: "SelenIA liberada para responder",
}


def trigger_text(trigger: str | None) -> str | None:
    if trigger is None:
        return None
    if trigger.endswith(":juntas"):
        # A frase de risco veio quebrada em mensagens seguidas.
        base = trigger_text(trigger.removesuffix(":juntas"))
        return f"{base} (frase quebrada em mensagens seguidas)"
    if trigger in _TRIGGER_TEXT:
        return _TRIGGER_TEXT[trigger]
    if trigger.startswith("camada2:"):
        return "Análise do modelo (camada 2), lendo a conversa"
    return trigger


def reviewed_event(alert: models.SafetyAlert) -> models.SafetyAlertEvent | None:
    return next((e for e in alert.events if e.event_type == AlertEventType.REVIEWED), None)


def timeline(alert: models.SafetyAlert) -> list[dict]:
    """A trilha em ordem, com textos para a tela.

    As duas primeiras linhas vêm do próprio alerta (disparo e o que a
    SelenIA fez); as outras, dos eventos gravados.
    """
    title, detail = _ACTION_TEXT.get(alert.level, (None, None))
    items = [
        {
            "kind": "created",
            "title": "Pedido registrado" if alert.level == AlertLevel.BOT_REFUSED else "Alerta criado pela triagem",
            "detail": trigger_text(alert.trigger),
            "at": alert.created_at,
            "actor": "system",
        }
    ]
    if title:
        items.append({"kind": "action", "title": title, "detail": detail, "at": alert.created_at, "actor": "system"})
    for event in alert.events:
        items.append(
            {
                "kind": event.event_type,
                "title": _EVENT_TEXT.get(event.event_type, event.event_type),
                "detail": event.note,
                "at": event.created_at,
                "actor": "system" if event.actor == "system" else "professional",
            }
        )
    return items


def mark_viewed(db: Session, alert: models.SafetyAlert) -> None:
    """Registra a primeira vez que a profissional abre o alerta.

    Só a primeira: o que importa para a auditoria é quanto tempo o
    alerta levou para ser visto.
    """
    if any(e.event_type == AlertEventType.VIEWED for e in alert.events):
        return
    db.add(models.SafetyAlertEvent(alert_id=alert.id, event_type=AlertEventType.VIEWED, actor=alert.professional_id))
    db.commit()
    db.refresh(alert)


def mark_reviewed(db: Session, alert: models.SafetyAlert, note: str | None) -> None:
    if reviewed_event(alert):
        raise AlreadyReviewed()
    db.add(
        models.SafetyAlertEvent(
            alert_id=alert.id,
            event_type=AlertEventType.REVIEWED,
            actor=alert.professional_id,
            note=(note or "").strip() or None,
        )
    )
    db.commit()
    db.refresh(alert)


def reviewed_at(alert: models.SafetyAlert) -> datetime | None:
    event = reviewed_event(alert)
    return event.created_at if event else None
