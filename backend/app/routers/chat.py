import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.services import llm, rag

router = APIRouter(prefix="/chat", tags=["chat"])

HISTORY_LIMIT = 12


@router.post("/simulate", response_model=schemas.ChatResponse)
def simulate_chat(payload: schemas.ChatRequest, db: Session = Depends(get_db)):
    professional = db.query(models.Professional).filter_by(slug=payload.professional_slug).first()
    if not professional:
        raise HTTPException(status_code=404, detail="Profissional não encontrado")

    session_id = payload.session_id or str(uuid.uuid4())
    conversation = (
        db.query(models.Conversation)
        .filter_by(professional_id=professional.id, session_id=session_id)
        .first()
    )
    if not conversation:
        conversation = models.Conversation(professional_id=professional.id, session_id=session_id)
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    db.add(models.Message(conversation_id=conversation.id, role="user", content=payload.message))
    db.commit()

    chunks, metadatas = rag.query(professional.slug, payload.message)
    system_prompt = llm.build_system_prompt(professional.name, professional.voice_tone, chunks)

    recent_messages = (
        db.query(models.Message)
        .filter_by(conversation_id=conversation.id)
        .order_by(models.Message.created_at)
        .all()[-HISTORY_LIMIT:]
    )
    history = [{"role": m.role, "content": m.content} for m in recent_messages]

    reply = llm.generate_reply(system_prompt, history)

    db.add(models.Message(conversation_id=conversation.id, role="assistant", content=reply))
    db.commit()

    sources = sorted({meta["filename"] for meta in metadatas}) if metadatas else []

    return schemas.ChatResponse(session_id=session_id, reply=reply, sources=sources)
