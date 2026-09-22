"""Criptografia dos dados sensíveis em repouso (LGPD).

Dois mecanismos, com propósitos diferentes:

- `encrypt` / `decrypt`: cifram o conteúdo (Fernet, simétrico). O mesmo
  texto gera cifras diferentes a cada chamada, então é seguro, mas não
  dá para buscar no banco por um valor cifrado.
- `blind_index`: gera uma impressão digital determinística do valor
  (HMAC-SHA256 com a mesma chave secreta). O mesmo telefone sempre gera
  o mesmo índice, então dá para procurar por ele, mas o índice não
  permite recuperar o número original.

Exemplo: o telefone do paciente é guardado cifrado (para exibir no
painel) e indexado (para achar a conversa quando ele manda mensagem de
novo).
"""

import hashlib
import hmac

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

_fernet = Fernet(settings.data_encryption_key) if settings.data_encryption_key else None

# Chave separada da de cifragem, derivada da mesma origem: usar a mesma
# chave para dois propósitos distintos é má prática em criptografia.
_index_key = (
    hashlib.sha256(b"blind-index|" + settings.data_encryption_key.encode("utf-8")).digest()
    if settings.data_encryption_key
    else None
)


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


def blind_index(value: str) -> str:
    """Impressão digital determinística, para buscar sem descriptografar.

    Usa HMAC em vez de um hash simples porque o espaço de telefones é
    pequeno o bastante para ser varrido por força bruta: sem a chave
    secreta, não dá para montar essa tabela.
    """
    if not _index_key:
        raise RuntimeError("DATA_ENCRYPTION_KEY não configurada no .env")
    return hmac.new(_index_key, value.encode("utf-8"), hashlib.sha256).hexdigest()
