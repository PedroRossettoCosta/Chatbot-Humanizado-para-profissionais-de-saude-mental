"""Grava os tokens de cada chamada ao modelo (`models.LlmUsage`).

O `llm.py` anota o uso de cada chamada dentro de `llm.collect_usage()`;
o caminho da mensagem (`services/pipeline.py`) grava o que foi anotado,
ligado à profissional e à conversa. Só números: o texto nunca passa por
aqui. O resumo de custo sai por `scripts/custo.py`.
"""

import logging

from sqlalchemy.orm import Session

from app import models

logger = logging.getLogger(__name__)


def record(db: Session, conversation: models.Conversation, entries: list[dict]) -> None:
    """Grava as chamadas anotadas. Uma falha aqui nunca derruba a
    resposta nem a triagem: o custo é medida, não parte do atendimento."""
    if not entries:
        return
    try:
        for entry in entries:
            db.add(
                models.LlmUsage(
                    professional_id=conversation.professional_id, conversation_id=conversation.id, **entry
                )
            )
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("falha ao gravar o uso de tokens")
