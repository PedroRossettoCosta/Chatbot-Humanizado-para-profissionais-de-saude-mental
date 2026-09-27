"""Webhook do WhatsApp: a porta por onde a Meta entrega as mensagens.

- `GET`: o desafio que a Meta faz uma vez, ao cadastrar o endereço.
- `POST`: cada mensagem. Confere a assinatura, responde "recebi" na
  hora (a Meta reenvia se demorar) e processa depois, em segundo plano
  (`services/whatsapp_inbox.py`).

Estas são as únicas rotas que passam pelo túnel público
(`PUBLIC_WEBHOOK_HOST`, ver `main.py`). Não usam login: quem prova a
origem é a assinatura da Meta.
"""

import hmac
import json
import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from app.config import settings
from app.services import whatsapp, whatsapp_inbox

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.get("/whatsapp", response_class=PlainTextResponse)
def verify(
    mode: str | None = Query(default=None, alias="hub.mode"),
    token: str | None = Query(default=None, alias="hub.verify_token"),
    challenge: str | None = Query(default=None, alias="hub.challenge"),
):
    expected = settings.whatsapp_verify_token
    if mode == "subscribe" and expected and token and hmac.compare_digest(token, expected):
        return challenge or ""
    raise HTTPException(status_code=403, detail="Token de verificação inválido")


@router.post("/whatsapp")
async def receive(request: Request, background_tasks: BackgroundTasks):
    body = await request.body()
    if not whatsapp.valid_signature(body, request.headers.get("x-hub-signature-256")):
        logger.warning("chamada do webhook com assinatura inválida ou sem segredo configurado")
        raise HTTPException(status_code=401, detail="Assinatura inválida")
    try:
        payload = json.loads(body)
    except ValueError:
        raise HTTPException(status_code=400, detail="Corpo inválido")
    events = whatsapp.parse(payload)
    if events:
        background_tasks.add_task(whatsapp_inbox.handle, events)
    return {"status": "ok"}
