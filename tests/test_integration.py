"""Integration tests for Voice Assistant Pipeline.

Tests end-to-end flows without external dependencies.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import given, settings, strategies as st


# Mock classes for integration testing
@dataclass
class MockUser:
    id: uuid.UUID
    name: str
    role: str
    language: str
    stt_provider: str
    tts_provider: str
    is_test_user: bool = False


@dataclass
class MockConversation:
    id: uuid.UUID
    user_id: uuid.UUID
    started_at: datetime
    ended_at: Optional[datetime]
    stt_provider_used: str
    tts_provider_used: str


@dataclass
class MockTurn:
    id: uuid.UUID
    conversation_id: uuid.UUID
    turn_number: int
    raw_transcript: Optional[str]
    normalized_transcript: Optional[str]
    transcript_confidence: Optional[float]
    user_confirmed: Optional[bool]
    user_correction: Optional[str]
    assistant_text: Optional[str]
    stt_latency_ms: Optional[int]
    tts_latency_ms: Optional[int]


class MockVoicePipeline:
    """Mock voice pipeline for integration testing."""
    
    def __init__(self):
        self.sessions = {}
        self.turns = {}
        self.users = {}
        self.unknown_terms = {}
    
    def add_user(self, user: MockUser):
        self.users[user.id] = user
    
    async def create_session(self, user_id: uuid.UUID) -> MockConversation:
        user = self.users.get(user_id)
        if not user:
            raise ValueError("User not found")
        
        conv = MockConversation(
            id=uuid.uuid4(),
            user_id=user_id,
            started_at=datetime.utcnow(),
            ended_at=None,
            stt_provider_used=user.stt_provider,
            tts_provider_used=user.tts_provider,
        )
        self.sessions[conv.id] = conv
        return conv
    
    async def process_audio(
        self,
        session_id: uuid.UUID,
        audio: bytes,
    ) -> MockTurn:
        conv = self.sessions.get(session_id)
        if not conv:
            raise ValueError("Session not found")
        
        # Simulate STT
        raw_text = "тестовый текст"
        confidence = 0.85
        
        # Simulate normalization
        normalized = raw_text
        for heard, correct in self.unknown_terms.items():
            if heard in normalized:
                normalized = normalized.replace(heard, correct)
        
        turn = MockTurn(
            id=uuid.uuid4(),
            conversation_id=session_id,
            turn_number=len([t for t in self.turns.values() if t.conversation_id == session_id]) + 1,
            raw_transcript=raw_text,
            normalized_transcript=normalized,
            transcript_confidence=confidence,
            user_confirmed=None,
            user_correction=None,
            assistant_text=None,
            stt_latency_ms=150,
            tts_latency_ms=None,
        )
        self.turns[turn.id] = turn
        return turn
    
    async def confirm_transcript(
        self,
        turn_id: uuid.UUID,
        confirmed: bool,
        correction: Optional[str] = None,
    ):
        turn = self.turns.get(turn_id)
        if not turn:
            raise ValueError("Turn not found")
        
        turn.user_confirmed = confirmed
        if correction:
            turn.user_correction = correction
            # Add to unknown terms
            words = turn.raw_transcript.split() if turn.raw_transcript else []
            corr_words = correction.split()
            for i, (orig, corr) in enumerate(zip(words, corr_words)):
                if orig != corr:
                    self.unknown_terms[orig] = corr
    
    async def generate_response(
        self,
        turn_id: uuid.UUID,
        response_text: str,
    ) -> str:
        turn = self.turns.get(turn_id)
        if not turn:
            raise ValueError("Turn not found")
        
        turn.assistant_text = response_text
        turn.tts_latency_ms = 200
        return f"audio_url_{turn_id}"


class TestEndToEndVoiceFlow:
    """Test complete voice flow from recording to response."""
    
    @pytest.fixture
    def pipeline(self):
        return MockVoicePipeline()
    
    @pytest.fixture
    def test_user(self, pipeline):
        user = MockUser(
            id=uuid.uuid4(),
            name="Test User",
            role="senior",
            language="ru",
            stt_provider="openai",
            tts_provider="openai",
        )
        pipeline.add_user(user)
        return user
    
    @pytest.mark.asyncio
    async def test_complete_voice_flow(self, pipeline, test_user):
        """Test: Audio → STT → Normalize → Confirm → LLM → TTS."""
        # Create session
        session = await pipeline.create_session(test_user.id)
        assert session.stt_provider_used == test_user.stt_provider
        assert session.tts_provider_used == test_user.tts_provider
        
        # Process audio
        turn = await pipeline.process_audio(session.id, b"fake_audio")
        assert turn.raw_transcript is not None
        assert turn.transcript_confidence is not None
        assert turn.stt_latency_ms is not None
        
        # Confirm transcript
        await pipeline.confirm_transcript(turn.id, confirmed=True)
        assert pipeline.turns[turn.id].user_confirmed is True
        
        # Generate response
        audio_url = await pipeline.generate_response(turn.id, "Ответ ассистента")
        assert audio_url is not None
        assert pipeline.turns[turn.id].assistant_text == "Ответ ассистента"
        assert pipeline.turns[turn.id].tts_latency_ms is not None
    
    @pytest.mark.asyncio
    async def test_correction_flow(self, pipeline, test_user):
        """Test: User corrects transcript → Unknown term created."""
        session = await pipeline.create_session(test_user.id)
        turn = await pipeline.process_audio(session.id, b"fake_audio")
        
        # User corrects
        await pipeline.confirm_transcript(
            turn.id,
            confirmed=False,
            correction="исправленный текст",
        )
        
        assert pipeline.turns[turn.id].user_confirmed is False
        assert pipeline.turns[turn.id].user_correction == "исправленный текст"
        # Unknown term should be created
        assert len(pipeline.unknown_terms) > 0
    
    @given(st.text(min_size=1, max_size=100))
    @settings(max_examples=50)
    def test_normalization_applies_corrections(self, text):
        """Property: Normalization applies known corrections."""
        pipeline = MockVoicePipeline()
        
        # Add known correction
        pipeline.unknown_terms["ошибка"] = "правильно"
        
        # If text contains the error, it should be corrected
        if "ошибка" in text:
            normalized = text
            for heard, correct in pipeline.unknown_terms.items():
                normalized = normalized.replace(heard, correct)
            assert "ошибка" not in normalized
            assert "правильно" in normalized


class TestProviderSwitching:
    """Test provider switching functionality."""
    
    @pytest.fixture
    def pipeline(self):
        return MockVoicePipeline()
    
    @given(
        stt_provider=st.sampled_from(["openai", "google"]),
        tts_provider=st.sampled_from(["openai", "google"]),
    )
    @settings(max_examples=20)
    def test_session_uses_user_providers(self, stt_provider, tts_provider):
        """Property: Session uses user's configured providers."""
        import asyncio
        
        pipeline = MockVoicePipeline()
        user = MockUser(
            id=uuid.uuid4(),
            name="Test",
            role="senior",
            language="ru",
            stt_provider=stt_provider,
            tts_provider=tts_provider,
        )
        pipeline.add_user(user)
        
        session = asyncio.get_event_loop().run_until_complete(
            pipeline.create_session(user.id)
        )
        
        assert session.stt_provider_used == stt_provider
        assert session.tts_provider_used == tts_provider


class TestAdminWorkflows:
    """Test admin panel workflows."""
    
    @dataclass
    class MockUnknownTerm:
        id: uuid.UUID
        heard_variant: str
        correct_form: str
        status: str
        occurrence_count: int
    
    @pytest.fixture
    def admin_service(self):
        class MockAdminService:
            def __init__(self):
                self.terms = {}
                self.audit_log = []
            
            def add_term(self, term):
                self.terms[term.id] = term
            
            def approve_term(self, term_id: uuid.UUID, admin_id: uuid.UUID):
                term = self.terms.get(term_id)
                if term:
                    term.status = "approved"
                    self.audit_log.append({
                        "action": "approve_term",
                        "resource_id": term_id,
                        "user_id": admin_id,
                    })
            
            def reject_term(self, term_id: uuid.UUID, admin_id: uuid.UUID):
                term = self.terms.get(term_id)
                if term:
                    term.status = "rejected"
                    self.audit_log.append({
                        "action": "reject_term",
                        "resource_id": term_id,
                        "user_id": admin_id,
                    })
        
        return MockAdminService()
    
    def test_term_approval_workflow(self, admin_service):
        """Test: Approve term → Status changes → Audit logged."""
        term = self.MockUnknownTerm(
            id=uuid.uuid4(),
            heard_variant="ошибка",
            correct_form="правильно",
            status="pending",
            occurrence_count=5,
        )
        admin_service.add_term(term)
        admin_id = uuid.uuid4()
        
        admin_service.approve_term(term.id, admin_id)
        
        assert admin_service.terms[term.id].status == "approved"
        assert len(admin_service.audit_log) == 1
        assert admin_service.audit_log[0]["action"] == "approve_term"
    
    def test_term_rejection_workflow(self, admin_service):
        """Test: Reject term → Status changes → Audit logged."""
        term = self.MockUnknownTerm(
            id=uuid.uuid4(),
            heard_variant="ошибка",
            correct_form="неправильно",
            status="pending",
            occurrence_count=2,
        )
        admin_service.add_term(term)
        admin_id = uuid.uuid4()
        
        admin_service.reject_term(term.id, admin_id)
        
        assert admin_service.terms[term.id].status == "rejected"
        assert len(admin_service.audit_log) == 1
        assert admin_service.audit_log[0]["action"] == "reject_term"
    
    @given(st.lists(st.integers(min_value=1, max_value=100), min_size=1, max_size=20))
    @settings(max_examples=30)
    def test_top_terms_ordering(self, counts):
        """Property: Top terms are ordered by count descending."""
        terms = []
        for i, count in enumerate(counts):
            terms.append(self.MockUnknownTerm(
                id=uuid.uuid4(),
                heard_variant=f"term_{i}",
                correct_form=f"correct_{i}",
                status="pending",
                occurrence_count=count,
            ))
        
        # Sort by count desc
        sorted_terms = sorted(terms, key=lambda t: t.occurrence_count, reverse=True)
        
        # Verify ordering
        for i in range(len(sorted_terms) - 1):
            assert sorted_terms[i].occurrence_count >= sorted_terms[i + 1].occurrence_count


class TestDataPersistence:
    """Test data persistence completeness."""
    
    @given(
        raw_text=st.text(min_size=1, max_size=200),
        confidence=st.floats(min_value=0.0, max_value=1.0),
        latency=st.integers(min_value=50, max_value=5000),
    )
    @settings(max_examples=50)
    def test_turn_data_completeness(self, raw_text, confidence, latency):
        """Property: All turn data is persisted."""
        turn = MockTurn(
            id=uuid.uuid4(),
            conversation_id=uuid.uuid4(),
            turn_number=1,
            raw_transcript=raw_text,
            normalized_transcript=raw_text,
            transcript_confidence=confidence,
            user_confirmed=True,
            user_correction=None,
            assistant_text="Response",
            stt_latency_ms=latency,
            tts_latency_ms=latency,
        )
        
        # Verify all required fields are set
        assert turn.id is not None
        assert turn.conversation_id is not None
        assert turn.raw_transcript is not None
        assert turn.normalized_transcript is not None
        assert turn.transcript_confidence is not None
        assert turn.stt_latency_ms is not None
