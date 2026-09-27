"""O que acontece com cada mensagem que chega pelo WhatsApp.

Ordem, para cada mensagem (`handle`):

1. Descobre a profissional pelo número que recebeu; descarta reenvio
   da Meta (o mesmo `wamid` duas vezes).
2. Mostra "digitando…" para a pessoa.
3. Grava e roda a **triagem na hora** (`pipeline.receive`). Aviso de IA
   e mensagem de emergência saem imediatamente.
4. A resposta normal espera `REPLY_DEBOUNCE_SECONDS` (6 s): se chegar
   outra mensagem nesse tempo, a espera recomeça. Quando a pessoa para,
   as mensagens dela desde a última resposta viram um texto só e a
   MarIA responde uma vez (decisão do Pedro, 27/09/2026). A API do
   WhatsApp não avisa quando a pessoa está digitando, então a espera é
   o único jeito de juntar mensagens quebradas.

Áudio, imagem e outros tipos: ficam registrados na conversa como
"[Áudio]" etc., sem triagem (não há texto), e a pessoa recebe um aviso
fixo de que a MarIA só lê texto.

As esperas ficam na memória do processo: se o backend reiniciar no meio
de uma, aquela resposta não sai (limitação do MVP, que roda local).
"""

import asyncio
import logging
import threading
from collections import defaultdict
from dataclasses import dataclass, field

from starlette.concurrency import run_in_threadpool
from sqlalchemy.exc import IntegrityError

from app import models
from app.config import settings
from app.database import SessionLocal
from app.models import Channel, ConversationState, MessageRole, SentBy
from app.services import conversations, notifications, pipeline, whatsapp

logger = logging.getLogger(__name__)

# Texto fixo, neutro, sem passar pelo modelo. Precisa da aprovação da
# Marília como os outros textos fixos.
UNSUPPORTED_MESSAGE = (
    "Por enquanto só consigo ler mensagens de texto. Pode me escrever o que você precisa?"
)

# Como uma mensagem que não é texto aparece na conversa, no painel.
TYPE_LABELS = {
    "audio": "[Áudio]",
    "image": "[Imagem]",
    "video": "[Vídeo]",
    "document": "[Documento]",
    "sticker": "[Figurinha]",
    "location": "[Localização]",
    "contacts": "[Contato compartilhado]",
}
OTHER_LABEL = "[Mensagem que a MarIA não lê]"
_LABELS = set(TYPE_LABELS.values()) | {OTHER_LABEL}

# Uma pessoa por vez em cada conversa: duas mensagens que chegam juntas
# não são gravadas nem respondidas em paralelo. Trava de thread, porque
# o trabalho (banco, modelo) roda fora do loop assíncrono.
_locks: dict[tuple[str, str], threading.Lock] = defaultdict(threading.Lock)
_locks_guard = threading.Lock()
# Resposta agendada de cada conversa (a espera em andamento).
_pending: dict[str, asyncio.Task] = {}


def _lock_for(key: tuple[str, str]) -> threading.Lock:
    with _locks_guard:
        return _locks[key]


@dataclass
class _Outcome:
    conversation_id: str
    alert_ids: list[str] = field(default_factory=list)
    wants_reply: bool = False
    notify_request: bool = False


def _deliver(phone_number_id: str, to: str, text: str) -> None:
    try:
        whatsapp.send_text(phone_number_id, to, text)
    except whatsapp.SendError as exc:
        # Sem o texto no log. A mensagem já está gravada na conversa.
        logger.error("falha ao enviar pelo WhatsApp: %s", exc)


def receive_now(event: whatsapp.Inbound) -> _Outcome | None:
    """Passos 1 a 3. Roda numa thread (banco e modelo são síncronos)."""
    with _lock_for((event.phone_number_id, event.sender)):
        db = SessionLocal()
        try:
            professional = (
                db.query(models.Professional).filter_by(whatsapp_phone_number_id=event.phone_number_id).first()
            )
            if professional is None:
                logger.warning("mensagem para um número sem profissional (%s)", event.phone_number_id)
                return None
            if db.query(models.Message.id).filter_by(external_id=event.message_id).first():
                return None  # a Meta reenviou

            whatsapp.show_typing(event.phone_number_id, event.message_id)
            is_text = event.type == "text" and bool(event.text and event.text.strip())
            text = event.text if is_text else TYPE_LABELS.get(event.type, OTHER_LABEL)
            try:
                received = pipeline.receive(
                    db,
                    professional,
                    Channel.WHATSAPP,
                    event.sender,
                    text,
                    display_name=event.profile_name,
                    external_message_id=event.message_id,
                    run_triage=is_text,
                )
            except IntegrityError:
                db.rollback()
                return None  # reenvio que chegou ao mesmo tempo

            conversation = received.conversation
            outgoing = list(received.immediate)
            active = conversation.state == ConversationState.ACTIVE
            if not is_text and active:
                conversations.record_message(
                    db, conversation, MessageRole.ASSISTANT, UNSUPPORTED_MESSAGE, sent_by=SentBy.SYSTEM
                )
                outgoing.append(UNSUPPORTED_MESSAGE)
            for text_out in outgoing:
                _deliver(event.phone_number_id, event.sender, text_out)
            return _Outcome(
                conversation_id=conversation.id,
                alert_ids=[received.alert_id] if received.alert_id else [],
                wants_reply=is_text and active and not received.emergency,
            )
        finally:
            db.close()


def reply_now(key: tuple[str, str], conversation_id: str) -> _Outcome | None:
    """Passo 4: responde às mensagens da pessoa desde a última resposta."""
    with _lock_for(key):
        db = SessionLocal()
        try:
            conversation = db.get(models.Conversation, conversation_id)
            if conversation is None:
                return None
            last_out = (
                db.query(models.Message.seq)
                .filter_by(conversation_id=conversation.id, role=MessageRole.ASSISTANT)
                .order_by(models.Message.seq.desc())
                .limit(1)
                .scalar()
            )
            query = db.query(models.Message).filter_by(conversation_id=conversation.id, role=MessageRole.USER)
            if last_out is not None:
                query = query.filter(models.Message.seq > last_out)
            burst = [m.content for m in query.order_by(models.Message.seq) if m.content not in _LABELS]
            if not burst:
                return None

            answer = pipeline.reply(db, conversation.professional, conversation, " ".join(burst))
            if answer.text:
                _deliver(key[0], key[1], answer.text)
            return _Outcome(
                conversation_id=conversation.id,
                alert_ids=[answer.alert_id] if answer.alert_id else [],
                notify_request=answer.notify_request,
            )
        finally:
            db.close()


async def _notify(outcome: _Outcome) -> None:
    for alert_id in outcome.alert_ids:
        await run_in_threadpool(notifications.notify_alert, alert_id)
    if outcome.notify_request:
        await run_in_threadpool(notifications.notify_human_request, outcome.conversation_id)


async def _reply(key: tuple[str, str], conversation_id: str) -> None:
    try:
        outcome = await run_in_threadpool(reply_now, key, conversation_id)
        if outcome:
            await _notify(outcome)
    except Exception:
        logger.exception("falha ao responder a conversa %s", conversation_id)


async def _reply_later(key: tuple[str, str], conversation_id: str) -> None:
    try:
        await asyncio.sleep(settings.reply_debounce_seconds)
    except asyncio.CancelledError:
        return  # chegou outra mensagem: a espera recomeçou
    if _pending.get(conversation_id) is asyncio.current_task():
        del _pending[conversation_id]
    await _reply(key, conversation_id)


def _schedule(key: tuple[str, str], conversation_id: str) -> None:
    previous = _pending.pop(conversation_id, None)
    if previous:
        previous.cancel()
    _pending[conversation_id] = asyncio.get_running_loop().create_task(_reply_later(key, conversation_id))


async def handle(events: list[whatsapp.Inbound]) -> None:
    """Chamado pelo webhook depois de responder "recebi" à Meta."""
    for event in events:
        key = (event.phone_number_id, event.sender)
        try:
            outcome = await run_in_threadpool(receive_now, event)
            if outcome is None:
                continue
            await _notify(outcome)
            if outcome.wants_reply:
                if settings.reply_debounce_seconds > 0:
                    _schedule(key, outcome.conversation_id)
                else:
                    await _reply(key, outcome.conversation_id)
        except Exception:
            logger.exception("falha ao processar a mensagem %s", event.message_id)
