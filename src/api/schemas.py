"""Pydantic schemas for API requests and responses."""

import uuid
from datetime import datetime
from typing import Literal, Optional, List

from pydantic import BaseModel, Field


# Auth schemas
class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    """User creation request."""
    name: str = Field(..., min_length=1, max_length=255)
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=6)
    role: Literal["senior", "admin"] = "senior"
    language: Literal["ru", "kk"] = "ru"
    stt_provider: Literal["openai", "google"] = "openai"
    tts_provider: Literal["openai", "google"] = "openai"


class UserResponse(BaseModel):
    """User response."""
    id: uuid.UUID
    name: str
    email: str
    role: str
    language: str
    stt_provider: str
    tts_provider: str
    is_test_user: bool
    created_at: datetime
    last_active_at: Optional[datetime]

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """User update request."""
    name: Optional[str] = None
    stt_provider: Optional[Literal["openai", "google"]] = None
    tts_provider: Optional[Literal["openai", "google"]] = None
    language: Optional[Literal["ru", "kk"]] = None
    is_test_user: Optional[bool] = None


# Voice session schemas
class SessionCreateRequest(BaseModel):
    """Create voice session request."""
    device_info: Optional[dict] = None


class SessionResponse(BaseModel):
    """Voice session response."""
    session_id: uuid.UUID


class TranscribeResponse(BaseModel):
    """Transcription response."""
    turn_id: uuid.UUID
    raw_transcript: str
    normalized_transcript: str
    confidence: float
    stt_latency_ms: int


class ConfirmRequest(BaseModel):
    """Confirm/correct transcript request."""
    turn_id: uuid.UUID
    confirmed: bool
    correction: Optional[str] = None


class ConfirmResponse(BaseModel):
    """Confirm response."""
    success: bool


class RespondRequest(BaseModel):
    """Generate response request."""
    turn_id: uuid.UUID
    assistant_text: str


class RespondResponse(BaseModel):
    """Response generation result."""
    assistant_text: str
    audio_url: str
    tts_latency_ms: int


# Admin schemas
class ConversationFilter(BaseModel):
    """Conversation filter parameters."""
    user_id: Optional[uuid.UUID] = None
    provider: Optional[Literal["openai", "google"]] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    low_confidence: Optional[bool] = None
    has_corrections: Optional[bool] = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class ConversationSummary(BaseModel):
    """Conversation summary for list view."""
    id: uuid.UUID
    user_id: uuid.UUID
    user_name: str
    started_at: datetime
    ended_at: Optional[datetime]
    stt_provider_used: str
    tts_provider_used: str
    turn_count: int

    class Config:
        from_attributes = True


class TurnResponse(BaseModel):
    """Turn details response."""
    id: uuid.UUID
    turn_number: int
    timestamp: datetime
    audio_input_url: Optional[str]
    raw_transcript: Optional[str]
    normalized_transcript: Optional[str]
    transcript_confidence: Optional[float]
    stt_latency_ms: Optional[int]
    user_confirmed: Optional[bool]
    user_correction: Optional[str]
    assistant_text: Optional[str]
    audio_output_url: Optional[str]
    tts_latency_ms: Optional[int]
    low_confidence: bool

    class Config:
        from_attributes = True


class ConversationDetails(BaseModel):
    """Full conversation details."""
    id: uuid.UUID
    user_id: uuid.UUID
    started_at: datetime
    ended_at: Optional[datetime]
    stt_provider_used: str
    tts_provider_used: str
    turns: list[TurnResponse]

    class Config:
        from_attributes = True


# Unknown terms schemas
class UnknownTermResponse(BaseModel):
    """Unknown term response."""
    id: uuid.UUID
    language: str
    heard_variant: str
    correct_form: str
    context_examples: list[str]
    provider_where_seen: Optional[str]
    occurrence_count: int
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UnknownTermCreate(BaseModel):
    """Create unknown term request."""
    language: Literal["ru", "kk"]
    heard_variant: str = Field(..., min_length=1, max_length=255)
    correct_form: str = Field(..., min_length=1, max_length=255)
    context_examples: list[str] = []


class UnknownTermApprove(BaseModel):
    """Approve unknown term request."""
    correct_form: str = Field(..., min_length=1, max_length=255)


# Error schemas
class ErrorResponse(BaseModel):
    """API error response."""
    code: str
    message: str
    details: Optional[dict] = None
    request_id: Optional[str] = None


# Comparison Analysis schemas

class MetricResponse(BaseModel):
    """Metric for a specific STT algorithm."""
    algorithm_name: str
    confidence_score: float
    processing_time_ms: int
    created_at: datetime

    class Config:
        from_attributes = True


class SpeechRecordResponse(BaseModel):
    """Speech record response with metrics."""
    id: uuid.UUID
    user_id: uuid.UUID
    audio_url: Optional[str]
    recognized_text_ru: Optional[str]
    recognized_text_kz: Optional[str]
    created_at: datetime
    metrics: List[MetricResponse]

    class Config:
        from_attributes = True


class ComparisonStatsResponse(BaseModel):
    """Aggregated stats for comparison."""
    total_records: int
    avg_confidence_by_provider: dict[str, float]
    avg_latency_by_provider: dict[str, float]
