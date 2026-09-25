from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services import guidelines


class VoiceExample(BaseModel):
    good: str = ""
    bad: str = ""


class _AssistantProfile(BaseModel):
    """Campos do perfil que a profissional preenche para calibrar a MarIA."""

    audience_description: Optional[str] = None
    service_info: Optional[str] = None
    voice_examples: Optional[dict[str, VoiceExample]] = None
    extra_never_say: Optional[list[str]] = Field(default=None, max_length=30)

    @field_validator("voice_examples")
    @classmethod
    def only_known_questions(cls, value):
        if value is None:
            return value
        unknown = set(value) - guidelines.VOICE_QUESTION_KEYS
        if unknown:
            raise ValueError(f"Pergunta desconhecida: {', '.join(sorted(unknown))}")
        return value

    @field_validator("extra_never_say")
    @classmethod
    def drop_blank_items(cls, value):
        if value is None:
            return value
        return [item.strip() for item in value if item and item.strip()]


class ProfessionalCreate(_AssistantProfile):
    slug: str = Field(min_length=3, max_length=64, pattern=r"^[a-z0-9-]+$")
    name: str
    voice_tone: Optional[str] = None


class ProfessionalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    slug: str
    name: str
    voice_tone: Optional[str] = None
    audience_description: Optional[str] = None
    service_info: Optional[str] = None
    voice_examples: Optional[dict[str, VoiceExample]] = None
    extra_never_say: Optional[list[str]] = None
    # Botão "Em consulta". `in_session_until` nulo com `in_session`
    # verdadeiro = ligado até ela desligar.
    in_session: bool = Field(validation_alias="is_in_session")
    in_session_until: Optional[datetime] = None
    created_at: datetime


class InSessionStart(BaseModel):
    # Nulo = até ela desligar. O teto evita ligar "por um dia inteiro" sem querer.
    minutes: Optional[int] = Field(default=None, ge=5, le=240)


class ProfessionalUpdate(_AssistantProfile):
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
    conversation_id: str
    state: str
    # Nulo quando o bot fica em silêncio (profissional no controle ou
    # conversa em espera depois de um alerta).
    reply: Optional[str] = None
    sources: list[str] = []
    disclaimer: Optional[str] = None


class VoiceQuestion(BaseModel):
    key: str
    question: str


class AssistantGuidelines(BaseModel):
    """Regras fixas do produto, exibidas no painel (só leitura)."""

    assistant_name: str
    voice_questions: list[VoiceQuestion]
    never_say: list[str]


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role: str
    content: str
    sent_by: Optional[str] = None
    created_at: datetime


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    state: str
    needs_attention: bool
    messages: list[MessageOut] = []


class ProfessionalMessage(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
