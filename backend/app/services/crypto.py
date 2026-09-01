from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

_fernet = Fernet(settings.data_encryption_key) if settings.data_encryption_key else None


def encrypt(text: str) -> str:
    if not _fernet:
        raise RuntimeError("DATA_ENCRYPTION_KEY não configurada no .env")
    return _fernet.encrypt(text.encode("utf-8")).decode("utf-8")


def decrypt(token: str) -> str:
    if not _fernet:
        raise RuntimeError("DATA_ENCRYPTION_KEY não configurada no .env")
    try:
        return _fernet.decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        # dado gravado antes da criptografia ser habilitada — devolve como está
        return token
