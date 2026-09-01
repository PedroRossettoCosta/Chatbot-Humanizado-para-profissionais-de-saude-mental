import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator

from app.database import Base
from app.services import crypto


def _uuid() -> str:
    return str(uuid.uuid4())


class EncryptedText(TypeDecorator):
    """Texto criptografado em repouso (LGPD) — transparente para o resto do código."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        return crypto.encrypt(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return crypto.decrypt(value)


class Professional(Base):
    __tablename__ = "professionals"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    slug = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    voice_tone = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    documents = relationship("Document", back_populates="professional", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="professional", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    professional_id = Column(UUID(as_uuid=False), ForeignKey("professionals.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=True)
    chunk_count = Column(Integer, default=0)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    professional = relationship("Professional", back_populates="documents")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    professional_id = Column(UUID(as_uuid=False), ForeignKey("professionals.id"), nullable=False)
    session_id = Column(String(128), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    professional = relationship("Professional", back_populates="conversations")
    messages = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at"
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    conversation_id = Column(UUID(as_uuid=False), ForeignKey("conversations.id"), nullable=False)
    role = Column(String(16), nullable=False)
    content = Column(EncryptedText, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")
