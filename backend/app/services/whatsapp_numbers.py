"""Conectar o número de WhatsApp da profissional pelo painel.

Os passos são os da Cloud API da Meta, na conta do WhatsApp Business
(WABA) do produto (`WHATSAPP_BUSINESS_ACCOUNT_ID`):

1. **Cadastrar** o número na WABA (`POST /{waba}/phone_numbers`), com o
   nome que vai aparecer no WhatsApp. Se o número já estiver lá (outra
   tentativa), reaproveita em vez de cadastrar de novo.
2. **Pedir o código** por SMS ou ligação (`request_code`).
3. **Verificar** o código que a profissional digitou (`verify_code`).
4. **Registrar** o número na Cloud API (`register`), com um PIN de 6
   dígitos da verificação em duas etapas, gerado aqui e guardado cifrado.

Só depois do registro o número vira `whatsapp_phone_number_id` e as
mensagens começam a chegar à profissional (o app já está inscrito na
WABA, então o webhook recebe os números novos sem configurar nada).

Depois de conectado, a profissional pode **trocar o nome** que aparece
(`rename`: a Meta analisa e, aprovado, o número é registrado de novo em
`apply_name`) ou **desconectar** o número para pôr outro (`disconnect`).

Limites da Meta que a tela precisa respeitar (planejamento, 26/09/2026):
conta sem verificação de empresa tem no máximo 2 números; registro, no
máximo 10 vezes por número em 72 horas (o 11º bloqueia por mais 72
horas); apagar um número só pelo WhatsApp Manager; o número não pode
estar em uso em nenhum WhatsApp.

Nada de PIN nem de código nos logs.
"""

import re
import secrets
from datetime import timedelta

from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.services import crypto, whatsapp

# Para antes do limite da Meta (10): a margem cobre um registro feito
# fora do painel, que não fica contado aqui.
REGISTER_LIMIT = 8
REGISTER_WINDOW = timedelta(hours=72)

STEP_CODE_SENT = "code_sent"
STEP_VERIFIED = "verified"

# Códigos de erro da Meta com explicação própria na tela. Os demais
# aparecem com a mensagem da Meta e o código, para dar para pesquisar.
ALREADY_VERIFIED = 136024
REGISTER_RATE_LIMIT = 133016
PIN_MISMATCH = 133005
NOT_VERIFIED_AT_META = (
    "A Meta ainda não considera este número verificado. Peça um novo código por SMS ou ligação e digite o "
    "código para tentar de novo."
)
FRIENDLY = {
    REGISTER_RATE_LIMIT: "Este número passou do limite de registros da Meta e ficou bloqueado por 72 horas.",
    PIN_MISMATCH: "Este número já tem verificação em duas etapas com outro PIN. Desative a verificação em duas "
    "etapas dele no WhatsApp Manager e tente de novo.",
}


class NumberError(Exception):
    """Algo que a profissional precisa saber para seguir. `status` é o
    código HTTP que a rota devolve."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def normalize_br(number: str) -> tuple[str, str]:
    """"(21) 95952-4339" → ("55", "21959524339"). Só números do Brasil:
    DDD + 8 ou 9 dígitos, com ou sem o +55 na frente."""
    number = (number or "").strip()
    if number.startswith("+") and not number.removeprefix("+").lstrip().startswith("55"):
        raise NumberError("Por enquanto, só números do Brasil (+55).")
    digits = re.sub(r"\D", "", number)
    if digits.startswith("55") and len(digits) in (12, 13):
        digits = digits[2:]
    if len(digits) not in (10, 11) or digits[0] == "0":
        raise NumberError("Digite o número com DDD, por exemplo (21) 95952-4339.")
    return "55", digits


def format_br(national: str) -> str:
    """"21959524339" → "+55 21 95952-4339"."""
    ddd, rest = national[:2], national[2:]
    return f"+55 {ddd} {rest[:-4]}-{rest[-4:]}"


def _same_number(display_phone_number: str, national: str) -> bool:
    """A Meta mostra "+55 21 95952-4339"; compara só os dígitos. Aceita
    também a forma sem o nono dígito, que alguns números antigos têm."""
    digits = re.sub(r"\D", "", display_phone_number or "")
    if digits.startswith("55"):
        digits = digits[2:]
    return digits == national or (digits[:2] == national[:2] and digits[-8:] == national[-8:])


def _meta_error(exc: whatsapp.MetaError) -> NumberError:
    message = FRIENDLY.get(exc.code) or f"A Meta recusou: {exc} (código {exc.code})."
    return NumberError(message, status=502)


def _waba() -> str:
    if not settings.whatsapp_business_account_id or not settings.whatsapp_access_token:
        raise NumberError("A conexão com o WhatsApp não está configurada no servidor.", status=503)
    return settings.whatsapp_business_account_id


def _taken_by_other(db: Session, professional: models.Professional, phone_number_id: str) -> bool:
    other = (
        db.query(models.Professional)
        .filter(models.Professional.id != professional.id)
        .filter(
            (models.Professional.whatsapp_phone_number_id == phone_number_id)
            | (models.Professional.whatsapp_pending_id == phone_number_id)
        )
        .first()
    )
    return other is not None


def _find_in_waba(waba: str, national: str) -> dict | None:
    data = whatsapp._graph(
        "GET",
        f"{waba}/phone_numbers",
        params={"fields": "id,display_phone_number,verified_name,code_verification_status", "limit": 100},
    )
    for number in data.get("data") or []:
        if _same_number(number.get("display_phone_number", ""), national):
            return number
    return None


def _request_code(phone_number_id: str, method: str) -> bool:
    """Pede o código. Devolve False se a Meta disser que o número já está
    verificado (aí não há código a esperar)."""
    try:
        whatsapp._graph(
            "POST", f"{phone_number_id}/request_code", body={"code_method": method, "language": "pt_BR"}
        )
    except whatsapp.MetaError as exc:
        if exc.code == ALREADY_VERIFIED:
            return False
        raise _meta_error(exc) from exc
    return True


def start(
    db: Session, professional: models.Professional, number: str, display_name: str, method: str = "SMS"
) -> None:
    """Passos 1 e 2: cadastra (ou reaproveita) o número e pede o código."""
    waba = _waba()
    if professional.whatsapp_phone_number_id:
        raise NumberError("Você já tem um número conectado.", status=409)
    display_name = (display_name or "").strip()
    if not 3 <= len(display_name) <= 100:
        raise NumberError("Informe o nome que vai aparecer no WhatsApp (3 a 100 caracteres).")
    cc, national = normalize_br(number)

    try:
        existing = _find_in_waba(waba, national)
        if existing:
            phone_number_id = existing["id"]
            verified = existing.get("code_verification_status") == "VERIFIED"
            display = existing.get("display_phone_number") or format_br(national)
            verified_name = existing.get("verified_name") or display_name
        else:
            created = whatsapp._graph(
                "POST",
                f"{waba}/phone_numbers",
                body={"cc": cc, "phone_number": national, "verified_name": display_name},
            )
            phone_number_id = created["id"]
            verified, display, verified_name = False, format_br(national), display_name
    except whatsapp.MetaError as exc:
        raise _meta_error(exc) from exc

    if _taken_by_other(db, professional, phone_number_id):
        raise NumberError("Este número já está ligado a outra conta da SelenIA.", status=409)

    if not verified:
        verified = not _request_code(phone_number_id, method)
    professional.whatsapp_pending_id = phone_number_id
    professional.whatsapp_display_number = display
    professional.whatsapp_verified_name = verified_name
    professional.whatsapp_setup_step = STEP_VERIFIED if verified else STEP_CODE_SENT
    db.commit()


def resend_code(db: Session, professional: models.Professional, method: str = "SMS") -> None:
    if not professional.whatsapp_pending_id or professional.whatsapp_setup_step != STEP_CODE_SENT:
        raise NumberError("Não há código para reenviar.", status=409)
    _waba()
    if not _request_code(professional.whatsapp_pending_id, method):
        professional.whatsapp_setup_step = STEP_VERIFIED
        db.commit()


def verify(db: Session, professional: models.Professional, code: str) -> None:
    """Passo 3 e, se der certo, o passo 4."""
    if not professional.whatsapp_pending_id or professional.whatsapp_setup_step != STEP_CODE_SENT:
        raise NumberError("Comece pela etapa do número.", status=409)
    _waba()
    code = re.sub(r"\D", "", code or "")
    if len(code) != 6:
        raise NumberError("O código tem 6 números.")
    try:
        whatsapp._graph("POST", f"{professional.whatsapp_pending_id}/verify_code", body={"code": code})
    except whatsapp.MetaError as exc:
        if exc.code != ALREADY_VERIFIED:
            raise NumberError(
                f"O código não foi aceito. Confira o SMS ou peça outro código. (Meta: {exc}, código {exc.code})",
                status=400,
            ) from exc
    professional.whatsapp_setup_step = STEP_VERIFIED
    db.commit()
    register(db, professional)


def registrations_in_window(db: Session, phone_number_id: str) -> int:
    since = models._now() - REGISTER_WINDOW
    return (
        db.query(models.WhatsAppRegisterAttempt)
        .filter(models.WhatsAppRegisterAttempt.phone_number_id == phone_number_id)
        .filter(models.WhatsAppRegisterAttempt.created_at >= since)
        .count()
    )


def _verification_status(phone_number_id: str) -> str | None:
    """Como a Meta vê a verificação do número; None se não deu para perguntar."""
    try:
        meta = whatsapp._graph("GET", phone_number_id, params={"fields": "code_verification_status"})
    except whatsapp.MetaError:
        return None
    return meta.get("code_verification_status")


def _check_register_limit(db: Session, phone_number_id: str) -> None:
    if registrations_in_window(db, phone_number_id) >= REGISTER_LIMIT:
        raise NumberError(
            "Este número já foi registrado muitas vezes nas últimas 72 horas. Espere antes de tentar de novo, "
            "para a Meta não bloquear o número.",
            status=429,
        )


def _register_call(db: Session, professional: models.Professional, phone_number_id: str) -> None:
    """`POST /register` com o PIN da profissional, contando a tentativa."""
    if not professional.whatsapp_pin:
        professional.whatsapp_pin = crypto.encrypt(f"{secrets.randbelow(10**6):06d}")
    pin = crypto.decrypt(professional.whatsapp_pin)
    try:
        whatsapp._graph("POST", f"{phone_number_id}/register", body={"messaging_product": "whatsapp", "pin": pin})
    except whatsapp.MetaError as exc:
        db.add(
            models.WhatsAppRegisterAttempt(
                professional_id=professional.id, phone_number_id=phone_number_id, ok=False, error_code=str(exc.code)
            )
        )
        db.commit()
        raise
    db.add(models.WhatsAppRegisterAttempt(professional_id=professional.id, phone_number_id=phone_number_id, ok=True))


def register(db: Session, professional: models.Professional) -> None:
    """Passo 4: registra o número na Cloud API e liga à profissional."""
    phone_number_id = professional.whatsapp_pending_id
    if not phone_number_id or professional.whatsapp_setup_step != STEP_VERIFIED:
        raise NumberError("Verifique o número antes de registrar.", status=409)
    _waba()
    _check_register_limit(db, phone_number_id)
    if _taken_by_other(db, professional, phone_number_id):
        raise NumberError("Este número já está ligado a outra conta da SelenIA.", status=409)
    try:
        _register_call(db, professional, phone_number_id)
    except whatsapp.MetaError as exc:
        # A tela pode estar em "verificado" sem a Meta concordar (caso real
        # de 19/10/2026: o registro voltou "número não verificado por SMS ou
        # voz"). Aí volta para a etapa do código, em vez de ficar presa
        # num botão de registrar que nunca funciona.
        if _verification_status(phone_number_id) not in (None, "VERIFIED"):
            professional.whatsapp_setup_step = STEP_CODE_SENT
            db.commit()
            raise NumberError(NOT_VERIFIED_AT_META, status=409) from exc
        raise _meta_error(exc) from exc

    professional.whatsapp_phone_number_id = phone_number_id
    professional.whatsapp_pending_id = None
    professional.whatsapp_setup_step = None
    db.commit()


def cancel(db: Session, professional: models.Professional) -> None:
    """Desiste da conexão em andamento (para trocar o número digitado).

    O número continua cadastrado na conta da Meta: apagar só pelo
    WhatsApp Manager. Uma nova tentativa com o mesmo número o reaproveita.
    """
    professional.whatsapp_pending_id = None
    professional.whatsapp_setup_step = None
    db.commit()


def rename(db: Session, professional: models.Professional, display_name: str) -> None:
    """Pede à Meta para trocar o nome que aparece no WhatsApp.

    A Meta analisa o nome novo (em geral de 1 a 2 dias); até lá continua
    o antigo. O andamento aparece em `status` (`new_display_name`,
    `new_name_status`).
    """
    phone_number_id = professional.whatsapp_phone_number_id
    if not phone_number_id:
        raise NumberError("Conecte um número antes de trocar o nome.", status=409)
    _waba()
    display_name = (display_name or "").strip()
    if not 3 <= len(display_name) <= 100:
        raise NumberError("Informe o nome que vai aparecer no WhatsApp (3 a 100 caracteres).")
    try:
        whatsapp._graph("POST", phone_number_id, params={"new_display_name": display_name})
    except whatsapp.MetaError as exc:
        raise _meta_error(exc) from exc


def apply_name(db: Session, professional: models.Professional) -> None:
    """Nome novo aprovado: a Meta só passa a mostrá-lo depois de registrar
    o número de novo. Conta no limite de registros, como o primeiro."""
    phone_number_id = professional.whatsapp_phone_number_id
    if not phone_number_id:
        raise NumberError("Conecte um número antes de trocar o nome.", status=409)
    _waba()
    _check_register_limit(db, phone_number_id)
    try:
        _register_call(db, professional, phone_number_id)
    except whatsapp.MetaError as exc:
        raise _meta_error(exc) from exc
    db.commit()


def disconnect(db: Session, professional: models.Professional) -> None:
    """Tira o número da Cloud API (`deregister`) e desliga da profissional,
    para ela conectar outro.

    As conversas antigas ficam. O número continua na conta da Meta e conta
    no limite de números dela: para cadastrar outro numa conta sem
    verificação de empresa, apague o antigo no WhatsApp Manager.
    """
    phone_number_id = professional.whatsapp_phone_number_id
    if not phone_number_id:
        raise NumberError("Não há número conectado.", status=409)
    _waba()
    try:
        whatsapp._graph("POST", f"{phone_number_id}/deregister")
    except whatsapp.MetaError as exc:
        raise _meta_error(exc) from exc
    professional.whatsapp_phone_number_id = None
    professional.whatsapp_display_number = None
    professional.whatsapp_verified_name = None
    db.commit()


def status(db: Session, professional: models.Professional) -> dict:
    """O que a tela mostra. Com número conectado, pergunta à Meta como ele
    está (conectado, nome aprovado, qualidade); se a Meta não responder,
    a tela mostra só o que está guardado aqui."""
    meta = None
    phone_number_id = professional.whatsapp_phone_number_id or professional.whatsapp_pending_id
    if phone_number_id and settings.whatsapp_access_token:
        try:
            meta = whatsapp._graph(
                "GET",
                phone_number_id,
                params={
                    "fields": "display_phone_number,verified_name,status,name_status,code_verification_status,"
                    "new_display_name,new_name_status"
                },
            )
        except whatsapp.MetaError:
            meta = None
    if meta and professional.whatsapp_phone_number_id and not professional.whatsapp_display_number:
        # Número ligado à mão antes desta tela existir (ex.: o do Pedro).
        professional.whatsapp_display_number = meta.get("display_phone_number")
        professional.whatsapp_verified_name = meta.get("verified_name")
        db.commit()
    return {
        "configured": bool(settings.whatsapp_business_account_id and settings.whatsapp_access_token),
        "connected": bool(professional.whatsapp_phone_number_id),
        "step": professional.whatsapp_setup_step,
        "display_number": professional.whatsapp_display_number,
        "verified_name": professional.whatsapp_verified_name,
        "registrations_last_72h": registrations_in_window(db, phone_number_id) if phone_number_id else 0,
        "register_limit": REGISTER_LIMIT,
        "meta_status": (meta or {}).get("status"),
        "name_status": (meta or {}).get("name_status"),
        "new_display_name": (meta or {}).get("new_display_name"),
        "new_name_status": (meta or {}).get("new_name_status"),
    }
