from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ProfessionalCreate(BaseModel):
    slug: str = Field(min_length=3, max_length=64, pattern=r"^[a-z0-9-]+$")
    name: str
    voice_tone: Optional[str] = None


class ProfessionalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    slug: str
    name: str
    voice_tone: Optional[str] = None
    created_at: datetime


class ProfessionalUpdate(BaseModel):
    name: Optional[str] = None
    voice_tone: Optional[str] = None


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    content_type: Optional[str] = None
    chunk_count: int
    uploaded_at: datetime


class ChatRequest(BaseModel):
    professional_slug: str
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    sources: list[str] = []
    disclaimer: Optional[str] = None
