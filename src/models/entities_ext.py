"""Additional SQLAlchemy ORM models - UnknownTerm, STTEvaluation, AuditLog."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.database import Base


class UnknownTerm(Base):
    """Unknown Terms Dictionary for improving STT recognition."""

    __tablename__ = "unknown_terms"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    language: Mapped[str] = mapped_column(String(5), nullable=False)
    heard_variant: Mapped[str] = mapped_column(String(255), nullable=False)
    correct_form: Mapped[str] = mapped_column(String(255), nullable=False)
    context_examples: Mapped[list] = mapped_column(JSON, default=list)
    provider_where_seen: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    approved_by: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)


class STTEvaluation(Base):
    """STT Evaluation with ground truth for WER/CER calculation."""

    __tablename__ = "stt_evaluations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    turn_id: Mapped[str] = mapped_column(String(36), ForeignKey("turns.id"), nullable=False)
    ground_truth_text: Mapped[str] = mapped_column(Text, nullable=False)
    labeled_by: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    label_source: Mapped[str] = mapped_column(String(20), nullable=False)
    wer: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)
    cer: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    """Audit log for tracking admin actions."""

    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
