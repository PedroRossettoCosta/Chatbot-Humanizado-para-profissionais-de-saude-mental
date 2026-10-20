"""Conversa com a API do WhatsApp (Cloud API da Meta).

Só o que é específico do canal: conferir a assinatura do webhook, ler o
formato que a Meta manda e enviar mensagens. A lógica do atendimento
(triagem, resposta, handoff) fica em `services/pipeline.py`, igual para
o simulador e o WhatsApp.

Nada de conteúdo de mensagem nos logs: só tipos, ids e códigos de erro.
"""

import hashlib
import hmac
import logging
from dataclasses import dataclass

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_GRAPH = "https://graph.facebook.com"
_TIMEOUT = 15.0


class SendError(Exception):
    """A Meta não aceitou a mensagem (ou não respondeu)."""


# ---------------------------------------------------------------------------
# Entrada (webhook)
# ---------------------------------------------------------------------------


def valid_signature(body: bytes, header: str | None) -> bool:
    """Confere o `X-Hub-Signature-256` que a Meta manda em cada chamada.

    É um HMAC-SHA256 do corpo cru com o segredo do app. Sem segredo
    configurado, nada passa: um webhook sem conferência deixaria qualquer
    pessoa injetar mensagens (inclusive uma falsa emergência).
    """
    if not settings.whatsapp_app_secret or not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(settings.whatsapp_app_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.removeprefix("sha256="))


@dataclass(frozen=True)
class Inbound:
    """Uma mensagem recebida, já sem o formato da Meta."""

    phone_number_id: str  # nosso número que recebeu (qual profissional)
    sender: str  # quem mandou: o wa_id (número) do contato
    message_id: str  # o `wamid`, único: serve para descartar reenvios
    type: str  # text, audio, image...
    text: str | None  # só em mensagens de texto
    profile_name: str | None
    # Foto, áudio ou documento: a referência para buscar o arquivo na Meta.
    media_id: str | None = None
    mime_type: str | None = None
    filename: str | None = None


# Tipos que o painel mostra (foto, áudio, documento). Vídeo e figurinha
# continuam só como etiqueta.
MEDIA_TYPES = ("image", "audio", "document")


def parse(payload: dict) -> list[Inbound]:
    """Extrai as mensagens de uma chamada do webhook.

    Avisos de entregue e lido (`statuses`) e reações são ignorados no
    MVP (decisão de 27/09/2026).
    """
    found = []
    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            value = change.get("value") or {}
            if change.get("field") != "messages":
                continue
            phone_number_id = (value.get("metadata") or {}).get("phone_number_id")
            names = {
                c.get("wa_id"): (c.get("profile") or {}).get("name") for c in value.get("contacts") or []
            }
            for message in value.get("messages") or []:
                kind = message.get("type") or "unknown"
                sender = message.get("from")
                if not phone_number_id or not sender or not message.get("id") or kind == "reaction":
                    continue
                media = (message.get(kind) or {}) if kind in MEDIA_TYPES else {}
                found.append(
                    Inbound(
                        phone_number_id=phone_number_id,
                        sender=sender,
                        message_id=message["id"],
                        type=kind,
                        text=(message.get("text") or {}).get("body") if kind == "text" else None,
                        profile_name=names.get(sender),
                        media_id=media.get("id"),
                        mime_type=media.get("mime_type"),
                        filename=media.get("filename"),
                    )
                )
    return found


# ---------------------------------------------------------------------------
# Mídia recebida (foto, áudio, documento)
# ---------------------------------------------------------------------------


class MediaUnavailable(Exception):
    """A Meta não entregou o arquivo (expirou, foi apagado ou falhou)."""


def _download(url: str) -> bytes:
    """Baixa o arquivo do endereço temporário da Meta (substituída nos testes)."""
    response = httpx.get(
        url, headers={"Authorization": f"Bearer {settings.whatsapp_access_token}"}, timeout=_TIMEOUT
    )
    if response.status_code >= 400:
        raise MediaUnavailable(f"HTTP {response.status_code}")
    return response.content


def fetch_media(media_id: str) -> tuple[bytes, str | None]:
    """Busca o arquivo na Meta na hora, sem guardar. Devolve o conteúdo e o
    tipo (mime). O endereço que a Meta dá vale só alguns minutos, então é
    pedido de novo a cada vez."""
    try:
        info = _graph("GET", media_id)
    except MetaError as exc:
        raise MediaUnavailable(f"código {exc.code}") from exc
    if not info.get("url"):
        raise MediaUnavailable("sem endereço")
    return _download(info["url"]), info.get("mime_type")


# ---------------------------------------------------------------------------
# Saída
# ---------------------------------------------------------------------------


def _post(phone_number_id: str, body: dict) -> dict:
    """Chamada crua à API (substituída nos testes, ver `conftest.py`)."""
    response = httpx.post(
        f"{_GRAPH}/{settings.whatsapp_api_version}/{phone_number_id}/messages",
        headers={"Authorization": f"Bearer {settings.whatsapp_access_token}"},
        json=body,
        timeout=_TIMEOUT,
    )
    if response.status_code >= 400:
        # O corpo de erro da Meta não traz o texto enviado, só o código.
        error = (response.json() if response.content else {}).get("error", {})
        raise SendError(f"HTTP {response.status_code}, código {error.get('code')}: {error.get('message')}")
    return response.json()


# ---------------------------------------------------------------------------
# Gestão de números (cadastro, código, registro)
# ---------------------------------------------------------------------------


class MetaError(Exception):
    """A Meta recusou uma chamada de gestão de número. `code` é o código
    de erro dela (ex.: 133016), para a tela explicar o que houve."""

    def __init__(self, message: str, code: int | None = None):
        super().__init__(message)
        self.code = code


def _graph(method: str, path: str, body: dict | None = None, params: dict | None = None) -> dict:
    """Chamada crua à Graph API (substituída nos testes, ver `conftest.py`)."""
    try:
        response = httpx.request(
            method,
            f"{_GRAPH}/{settings.whatsapp_api_version}/{path}",
            headers={"Authorization": f"Bearer {settings.whatsapp_access_token}"},
            json=body,
            params=params,
            timeout=_TIMEOUT,
        )
    except httpx.HTTPError as exc:
        raise MetaError(f"sem resposta da Meta: {type(exc).__name__}") from exc
    data = response.json() if response.content else {}
    if response.status_code >= 400:
        error = data.get("error", {})
        # A mensagem amigável da Meta (`error_user_msg`) explica melhor
        # que a técnica quando existe; nenhuma das duas traz conversa.
        message = error.get("error_user_msg") or error.get("message") or f"HTTP {response.status_code}"
        raise MetaError(message, error.get("code"))
    return data


def send_text(phone_number_id: str, to: str, text: str) -> str:
    """Envia texto e devolve o `wamid` da mensagem enviada."""
    try:
        data = _post(
            phone_number_id,
            {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": "text",
                "text": {"preview_url": False, "body": text},
            },
        )
    except httpx.HTTPError as exc:
        raise SendError(f"sem resposta da Meta: {type(exc).__name__}") from exc
    return (data.get("messages") or [{}])[0].get("id", "")


def show_typing(phone_number_id: str, message_id: str) -> None:
    """Marca a mensagem como lida e mostra "digitando…" para a pessoa.

    O indicador some quando a resposta chega (ou em até 25 segundos). É
    só cortesia: se falhar, o atendimento segue.
    """
    try:
        _post(
            phone_number_id,
            {
                "messaging_product": "whatsapp",
                "status": "read",
                "message_id": message_id,
                "typing_indicator": {"type": "text"},
            },
        )
    except Exception as exc:
        logger.warning("não consegui mostrar 'digitando' (%s)", type(exc).__name__)
