"""Aplica a política de retenção de dados (LGPD).

Remove conversas cuja última mensagem é mais antiga que
DATA_RETENTION_DAYS (definido no .env), junto com as mensagens delas.
Rode manualmente quando quiser aplicar a limpeza — não é agendado
automaticamente nesta fase do projeto.

O corte usa a **última atividade**, não a data de criação: uma conversa
que continuou ativa por meses não deve ser apagada só porque começou há
muito tempo.

Os alertas de segurança daquela conversa são apagados junto. Isso não
conflita com a regra de que a profissional não pode apagar um alerta
(RNF05): ela continua sem esse poder, e a exclusão aqui é automática,
por tempo, como manda a política de retenção.

Uso (de dentro de backend/, com o venv ativado):
    python scripts/purge_old_conversations.py
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import models  # noqa: E402
from app.config import settings  # noqa: E402
from app.database import SessionLocal  # noqa: E402


def main():
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.data_retention_days)
    db = SessionLocal()
    try:
        old_conversations = (
            db.query(models.Conversation).filter(models.Conversation.last_message_at < cutoff).all()
        )
        for conversation in old_conversations:
            db.delete(conversation)
        db.commit()
        print(
            f"Removidas {len(old_conversations)} conversa(s) sem atividade há mais de "
            f"{settings.data_retention_days} dias (antes de {cutoff.isoformat()})."
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
