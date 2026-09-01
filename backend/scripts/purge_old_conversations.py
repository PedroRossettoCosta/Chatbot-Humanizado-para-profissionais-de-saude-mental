"""Aplica a política de retenção de dados (LGPD): remove conversas mais
antigas que DATA_RETENTION_DAYS (definido no .env). Rode manualmente
quando quiser aplicar a limpeza — não é agendado automaticamente.

Uso (de dentro de backend/, com o venv ativado):
    python scripts/purge_old_conversations.py
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import models  # noqa: E402
from app.config import settings  # noqa: E402
from app.database import SessionLocal  # noqa: E402


def main():
    cutoff = datetime.utcnow() - timedelta(days=settings.data_retention_days)
    db = SessionLocal()
    try:
        old_conversations = db.query(models.Conversation).filter(models.Conversation.created_at < cutoff).all()
        for conversation in old_conversations:
            db.delete(conversation)
        db.commit()
        print(
            f"Removidas {len(old_conversations)} conversa(s) com mais de "
            f"{settings.data_retention_days} dias (antes de {cutoff.isoformat()})."
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
