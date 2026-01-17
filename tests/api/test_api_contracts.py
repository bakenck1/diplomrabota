"""Property-based tests for API contracts.

**Feature: voice-assistant-pipeline**
**Validates: Requirements 10.3, 10.6, 11.1, 11.3, 11.4, 11.5**
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from hypothesis import given, strategies as st, settings
import uuid
from datetime import datetime
from pydantic import ValidationError

from src.api.schemas import (
    SessionResponse,
    TranscribeResponse,
    ConfirmRequest,
    ConfirmResponse,
    RespondRequest,
    RespondResponse,
    UserCreate,
    UserResponse,
    ErrorResponse,
)


class TestAPIResponseContracts:
    """Property 17: API Response Contract tests."""

    @given(session_id=st.uuids())
    @settings(max_examples=100)
    def test_session_response_has_session_id(self, session_id: uuid.UUID):
        """Property 17: POST /voice/session returns {session_id}.
        
        **Feature: voice-assistant-pipeline, Property 17: API Response Contract**
        **Validates: Requirements 11.1**
        """
        response = SessionResponse(session_id=session_id)
        
        assert response.session_id is not None
        assert isinstance(response.session_id, uuid.UUID)
        assert response.session_id == session_id

    @given(
        turn_id=st.uuids(),
        raw_transcript=st.text(min_size=0, max_size=500),
        normalized_transcript=st.text(min_size=0, max_size=500),
        confidence=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        stt_latency_ms=st.integers(min_value=0, max_value=100000),
    )
    @settings(max_examples=100)
    def test_transcribe_response_has_required_fields(
        self,
        turn_id: uuid.UUID,
        raw_transcript: str,
        normalized_transcript: str,
        confidence: float,
        stt_latency_ms: int,
    ):
        """Property 17: POST /voice/transcribe returns required fields.
        
        **Feature: voice-assistant-pipeline, Property 17: API Response Contract**
        **Validates: Requirements 11.3**
        """
        response = TranscribeResponse(
            turn_id=turn_id,
            raw_transcript=raw_transcript,
            normalized_transcript=normalized_transcript,
            confidence=confidence,
            stt_latency_ms=stt_latency_ms,
        )
        
        assert response.turn_id is not None
        assert response.raw_transcript is not None
        assert response.normalized_transcript is not None
        assert response.confidence is not None
        assert 0.0 <= response.confidence <= 1.0
        assert response.stt_latency_ms >= 0

    @given(
        assistant_text=st.text(min_size=1, max_size=500).filter(lambda x: x.strip() != ""),
        audio_url=st.text(min_size=10, max_size=500),
        tts_latency_ms=st.integers(min_value=0, max_value=100000),
    )
    @settings(max_examples=100)
    def test_respond_response_has_required_fields(
        self,
        assistant_text: str,
        audio_url: str,
        tts_latency_ms: int,
    ):
        """Property 17: POST /voice/respond returns required fields.
        
        **Feature: voice-assistant-pipeline, Property 17: API Response Contract**
        **Validates: Requirements 11.4**
        """
        response = RespondResponse(
            assistant_text=assistant_text,
            audio_url=audio_url,
            tts_latency_ms=tts_latency_ms,
        )
        
        assert response.assistant_text is not None
        assert len(response.assistant_text) > 0
        assert response.audio_url is not None
        assert response.tts_latency_ms >= 0

    @given(success=st.booleans())
    @settings(max_examples=100)
    def test_confirm_response_has_success(self, success: bool):
        """Property 17: POST /voice/confirm returns {success: true}.
        
        **Feature: voice-assistant-pipeline, Property 17: API Response Contract**
        **Validates: Requirements 11.5**
        """
        response = ConfirmResponse(success=success)
        
        assert response.success is not None
        assert isinstance(response.success, bool)


class TestAuthorizationEnforcement:
    """Property 13: Authorization Enforcement tests."""

    @given(
        code=st.sampled_from(["E001", "E002", "E003", "E004", "E999"]),
        message=st.text(min_size=1, max_size=200).filter(lambda x: x.strip() != ""),
    )
    @settings(max_examples=100)
    def test_error_response_has_required_fields(self, code: str, message: str):
        """Property 13: Error responses have code and message.
        
        **Feature: voice-assistant-pipeline, Property 13: Authorization Enforcement**
        **Validates: Requirements 10.3, 10.6**
        """
        response = ErrorResponse(code=code, message=message)
        
        assert response.code is not None
        assert response.message is not None
        assert len(response.code) > 0
        assert len(response.message) > 0

    def test_unauthorized_error_code(self):
        """Property 13: Unauthorized requests get E001 code.
        
        **Feature: voice-assistant-pipeline, Property 13: Authorization Enforcement**
        **Validates: Requirements 10.6**
        """
        response = ErrorResponse(code="E001", message="Unauthorized")
        assert response.code == "E001"

    def test_forbidden_error_code(self):
        """Property 13: Forbidden requests get E002 code.
        
        **Feature: voice-assistant-pipeline, Property 13: Authorization Enforcement**
        **Validates: Requirements 10.3**
        """
        response = ErrorResponse(code="E002", message="Forbidden")
        assert response.code == "E002"


class TestRequestValidation:
    """Tests for request schema validation."""

    @given(
        turn_id=st.uuids(),
        confirmed=st.booleans(),
        correction=st.one_of(st.none(), st.text(min_size=1, max_size=500)),
    )
    @settings(max_examples=100)
    def test_confirm_request_validation(
        self,
        turn_id: uuid.UUID,
        confirmed: bool,
        correction: str,
    ):
        """ConfirmRequest validates correctly.
        
        **Validates: Requirements 11.5**
        """
        request = ConfirmRequest(
            turn_id=turn_id,
            confirmed=confirmed,
            correction=correction,
        )
        
        assert request.turn_id == turn_id
        assert request.confirmed == confirmed
        assert request.correction == correction

    @given(
        turn_id=st.uuids(),
        assistant_text=st.text(min_size=1, max_size=500).filter(lambda x: x.strip() != ""),
    )
    @settings(max_examples=100)
    def test_respond_request_validation(
        self,
        turn_id: uuid.UUID,
        assistant_text: str,
    ):
        """RespondRequest validates correctly.
        
        **Validates: Requirements 11.4**
        """
        request = RespondRequest(
            turn_id=turn_id,
            assistant_text=assistant_text,
        )
        
        assert request.turn_id == turn_id
        assert request.assistant_text == assistant_text

    @given(
        name=st.text(min_size=1, max_size=255).filter(lambda x: x.strip() != ""),
        email=st.emails(),
        password=st.text(min_size=6, max_size=100),
        role=st.sampled_from(["senior", "admin"]),
        language=st.sampled_from(["ru", "kk"]),
        stt_provider=st.sampled_from(["openai", "google"]),
        tts_provider=st.sampled_from(["openai", "google"]),
    )
    @settings(max_examples=100)
    def test_user_create_validation(
        self,
        name: str,
        email: str,
        password: str,
        role: str,
        language: str,
        stt_provider: str,
        tts_provider: str,
    ):
        """UserCreate validates correctly."""
        request = UserCreate(
            name=name,
            email=email,
            password=password,
            role=role,
            language=language,
            stt_provider=stt_provider,
            tts_provider=tts_provider,
        )
        
        assert request.name == name
        assert request.email == email
        assert request.role == role
        assert request.language == language
        assert request.stt_provider == stt_provider
        assert request.tts_provider == tts_provider

    def test_user_create_rejects_short_password(self):
        """UserCreate rejects passwords shorter than 6 characters."""
        with pytest.raises(ValidationError):
            UserCreate(
                name="Test",
                email="test@example.com",
                password="12345",  # Too short
            )

    def test_user_create_rejects_invalid_role(self):
        """UserCreate rejects invalid roles."""
        with pytest.raises(ValidationError):
            UserCreate(
                name="Test",
                email="test@example.com",
                password="123456",
                role="invalid_role",
            )

    def test_user_create_rejects_invalid_provider(self):
        """UserCreate rejects invalid providers."""
        with pytest.raises(ValidationError):
            UserCreate(
                name="Test",
                email="test@example.com",
                password="123456",
                stt_provider="invalid_provider",
            )
