"""SQLAlchemy ORM models for Voice Assistant Pipeline."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.models.database import Base


# Use String for UUID compatibility with SQLite
def uuid_column(**kwargs):
    """Create UUID column compatible with both PostgreSQL and SQLite."""
    return mapped_column(String(36), **kwargs)


class User(Base):
    """User model - supports both senior users and admins."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="senior")
    language: Mapped[str] = mapped_column(String(5), nullable=False, default="ru")
    stt_provider: Mapped[str] = mapped_column(String(20), nullable=False, default="openai")
    tts_provider: Mapped[str] = mapped_column(String(20), nullable=False, default="openai")
    is_test_user: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_active_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Conversation(Base):
    """Conversation/Session model."""

    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    stt_provider_used: Mapped[str] = mapped_column(String(20), nullable=False)
    tts_provider_used: Mapped[str] = mapped_column(String(20), nullable=False)
    device_info: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="conversations")
    turns: Mapped[list["Turn"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )


class Turn(Base):
    """Turn model - each step in a conversation."""

    __tablename__ = "turns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id: Mapped[str] = mapped_column(String(36), ForeignKey("conversations.id"), nullable=False)
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Input
    audio_input_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    audio_input_duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # STT Result
    raw_transcript: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    normalized_transcript: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    transcript_confidence: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)
    stt_latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    stt_words: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # User Confirmation
    user_confirmed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    user_correction: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # LLM Response
    llm_prompt_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    assistant_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    llm_latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # TTS Response
    audio_output_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    audio_output_duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tts_latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Flags
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    low_confidence: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    conversation: Mapped["Conversation"] = relationship(back_populates="turns")
