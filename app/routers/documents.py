from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.services import rag, text_extraction

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


@router.post("/upload", response_model=schemas.DocumentOut, status_code=201)
async def upload_document(
    professional_slug: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    professional = db.query(models.Professional).filter_by(slug=professional_slug).first()
    if not professional:
        raise HTTPException(status_code=404, detail="Profissional não encontrado")

    extension = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Formato não suportado: {extension or file.filename}")

    content = await file.read()
    text = text_extraction.extract_text(file.filename, content)
    chunks = text_extraction.chunk_text(text)

    document = models.Document(
        professional_id=professional.id,
        filename=file.filename,
        content_type=file.content_type,
        chunk_count=len(chunks),
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    rag.add_chunks(professional.slug, document.id, document.filename, chunks)

    return document
