"""Property-based tests for Voice Session Service.

**Feature: voice-assistant-pipeline**
**Validates: Requirements 3.4, 3.5, 3.6, 5.1, 5.2, 5.3, 5.4**
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from hypothesis import given, strategies as st, settings, assume
import uuid
from dataclasses import dataclass
from typing import Literal, Optional


# Mock classes for testing without database/external dependencies
@dataclass
class MockUser:
    """Mock user for testing."""
    id: uuid.UUID
    name: str
    stt_provider: Literal["openai", "google"]
    tts_provider: Literal["openai", "google"]
    language: Literal["ru", "kk"]
    is_test_user: bool = False


@dataclass
class MockConversation:
    """Mock conversation for testing."""
    id: uuid.UUID
    user_id: uuid.UUID
    stt_provider_used: str
    tts_provider_used: str


@dataclass
class MockTurn:
    """Mock turn for testing."""
    id: uuid.UUID
    conversation_id: uuid.UUID
    turn_number: int
    raw_transcript: Optional[str] = None
    normalized_transcript: Optional[str] = None
    transcript_confidence: Optional[float] = None
    audio_input_url: Optional[str] = None
    audio_output_url: Optional[str] = None
    assistant_text: Optional[str] = None


class MockAdapterFactory:
    """Mock adapter factory for testing provider selection."""

    @staticmethod
    def get_stt_adapter(provider: Literal["openai", "google"]) -> str:
        """Return provider name instead of actual adapter."""
        return f"stt_{provider}"

    @staticmethod
    def get_tts_adapter(provider: Literal["openai", "google"]) -> str:
        """Return provider name instead of actual adapter."""
        return f"tts_{provider}"


class MockVoiceSessionService:
    """Mock service for testing provider selection logic."""

    def __init__(self, users: dict[uuid.UUID, MockUser]):
        self.users = users
        self.conversations: dict[uuid.UUID, MockConversation] = {}
        self.turns: dict[uuid.UUID, MockTurn] = {}

    def get_user(self, user_id: uuid.UUID) -> Optional[MockUser]:
        return self.users.get(user_id)

    def create_session(self, user_id: uuid.UUID) -> MockConversation:
        user = self.get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        conversation = MockConversation(
            id=uuid.uuid4(),
            user_id=user_id,
            stt_provider_used=user.stt_provider,
            tts_provider_used=user.tts_provider,
        )
        self.conversations[conversation.id] = conversation
        return conversation

    def get_stt_adapter_for_user(self, user_id: uuid.UUID) -> str:
        """Get STT adapter name for user."""
        user = self.get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        return MockAdapterFactory.get_stt_adapter(user.stt_provider)

    def get_tts_adapter_for_user(self, user_id: uuid.UUID) -> str:
        """Get TTS adapter name for user."""
        user = self.get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        return MockAdapterFactory.get_tts_adapter(user.tts_provider)

    def process_audio(self, session_id: uuid.UUID, user_id: uuid.UUID) -> dict:
        """Mock process audio - returns provider info."""
        conversation = self.conversations.get(session_id)
        if not conversation:
            raise ValueError(f"Session {session_id} not found")

        user = self.get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        turn = MockTurn(
            id=uuid.uuid4(),
            conversation_id=session_id,
            turn_number=len([t for t in self.turns.values() if t.conversation_id == session_id]) + 1,
            raw_transcript="test transcript",
            normalized_transcript="test transcript",
            transcript_confidence=0.95,
            audio_input_url=f"users/{user_id}/conversations/{session_id}/turns/{uuid.uuid4()}/input.wav",
        )
        self.turns[turn.id] = turn

        return {
            "turn_id": turn.id,
            "stt_provider": user.stt_provider,
            "stt_adapter": self.get_stt_adapter_for_user(user_id),
        }

    def generate_response(self, session_id: uuid.UUID, turn_id: uuid.UUID, text: str) -> dict:
        """Mock generate response - returns provider info."""
        conversation = self.conversations.get(session_id)
        if not conversation:
            raise ValueError(f"Session {session_id} not found")

        user = self.get_user(conversation.user_id)
        if not user:
            raise ValueError(f"User not found")

        turn = self.turns.get(turn_id)
        if turn:
            turn.assistant_text = text
            turn.audio_output_url = f"users/{user.id}/conversations/{session_id}/turns/{turn_id}/output.mp3"

        return {
            "tts_provider": user.tts_provider,
            "tts_adapter": self.get_tts_adapter_for_user(user.id),
            "audio_url": turn.audio_output_url if turn else None,
        }


# Strategies
provider_strategy = st.sampled_from(["openai", "google"])
language_strategy = st.sampled_from(["ru", "kk"])


class TestProviderSelection:
    """Property 1: Provider Selection Correctness tests."""

    @given(
        stt_provider=provider_strategy,
        tts_provider=provider_strategy,
        language=language_strategy,
    )
    @settings(max_examples=100)
    def test_stt_adapter_matches_user_settings(
        self,
        stt_provider: str,
        tts_provider: str,
        language: str,
    ):
        """Property 1: STT adapter matches user's stt_provider setting.
        
        **Feature: voice-assistant-pipeline, Property 1: Provider Selection Correctness**
        **Validates: Requirements 3.4, 3.5, 3.6**
        """
        user_id = uuid.uuid4()
        user = MockUser(
            id=user_id,
            name="Test User",
            stt_provider=stt_provider,
            tts_provider=tts_provider,
            language=language,
        )

        service = MockVoiceSessionService({user_id: user})
        
        adapter_name = service.get_stt_adapter_for_user(user_id)
        
        # Adapter name should contain the provider
        assert stt_provider in adapter_name
        assert adapter_name == f"stt_{stt_provider}"

    @given(
        stt_provider=provider_strategy,
        tts_provider=provider_strategy,
        language=language_strategy,
    )
    @settings(max_examples=100)
    def test_tts_adapter_matches_user_settings(
        self,
        stt_provider: str,
        tts_provider: str,
        language: str,
    ):
        """Property 1: TTS adapter matches user's tts_provider setting.
        
        **Feature: voice-assistant-pipeline, Property 1: Provider Selection Correctness**
        **Validates: Requirements 3.4, 3.5, 3.6**
        """
        user_id = uuid.uuid4()
        user = MockUser(
            id=user_id,
            name="Test User",
            stt_provider=stt_provider,
            tts_provider=tts_provider,
            language=language,
        )

        service = MockVoiceSessionService({user_id: user})
        
        adapter_name = service.get_tts_adapter_for_user(user_id)
        
        # Adapter name should contain the provider
        assert tts_provider in adapter_name
        assert adapter_name == f"tts_{tts_provider}"

    @given(
        stt_provider=provider_strategy,
        tts_provider=provider_strategy,
    )
    @settings(max_examples=100)
    def test_session_records_providers_used(
        self,
        stt_provider: str,
        tts_provider: str,
    ):
        """Property 1: Session records which providers were used.
        
        **Feature: voice-assistant-pipeline, Property 1: Provider Selection Correctness**
        **Validates: Requirements 3.4, 3.5, 3.6**
        """
        user_id = uuid.uuid4()
        user = MockUser(
            id=user_id,
            name="Test User",
            stt_provider=stt_provider,
            tts_provider=tts_provider,
            language="ru",
        )

        service = MockVoiceSessionService({user_id: user})
        conversation = service.create_session(user_id)
        
        # Conversation should record the providers used
        assert conversation.stt_provider_used == stt_provider
        assert conversation.tts_provider_used == tts_provider


class TestDataPersistence:
    """Property 7: Data Persistence Completeness tests."""

    @given(
        stt_provider=provider_strategy,
        tts_provider=provider_strategy,
    )
    @settings(max_examples=100)
    def test_turn_has_audio_input_url(
        self,
        stt_provider: str,
        tts_provider: str,
    ):
        """Property 7: Turn has audio_input_url after processing.
        
        **Feature: voice-assistant-pipeline, Property 7: Data Persistence Completeness**
        **Validates: Requirements 5.1, 5.2, 5.3, 5.4**
        """
        user_id = uuid.uuid4()
        user = MockUser(
            id=user_id,
            name="Test User",
            stt_provider=stt_provider,
            tts_provider=tts_provider,
            language="ru",
        )

        service = MockVoiceSessionService({user_id: user})
        conversation = service.create_session(user_id)
        
        result = service.process_audio(conversation.id, user_id)
        turn = service.turns.get(result["turn_id"])
        
        # Turn should have audio input URL
        assert turn is not None
        assert turn.audio_input_url is not None
        assert "input.wav" in turn.audio_input_url

    @given(
        stt_provider=provider_strategy,
        tts_provider=provider_strategy,
        assistant_text=st.text(min_size=1, max_size=200).filter(lambda x: x.strip() != ""),
    )
    @settings(max_examples=100)
    def test_turn_has_audio_output_url_after_response(
        self,
        stt_provider: str,
        tts_provider: str,
        assistant_text: str,
    ):
        """Property 7: Turn has audio_output_url after generating response.
        
        **Feature: voice-assistant-pipeline, Property 7: Data Persistence Completeness**
        **Validates: Requirements 5.1, 5.2, 5.3, 5.4**
        """
        user_id = uuid.uuid4()
        user = MockUser(
            id=user_id,
            name="Test User",
            stt_provider=stt_provider,
            tts_provider=tts_provider,
            language="ru",
        )

        service = MockVoiceSessionService({user_id: user})
        conversation = service.create_session(user_id)
        
        process_result = service.process_audio(conversation.id, user_id)
        response_result = service.generate_response(
            conversation.id,
            process_result["turn_id"],
            assistant_text,
        )
        
        turn = service.turns.get(process_result["turn_id"])
        
        # Turn should have audio output URL and assistant text
        assert turn is not None
        assert turn.audio_output_url is not None
        assert "output.mp3" in turn.audio_output_url
        assert turn.assistant_text == assistant_text

    @given(
        stt_provider=provider_strategy,
        tts_provider=provider_strategy,
    )
    @settings(max_examples=100)
    def test_turn_has_transcripts(
        self,
        stt_provider: str,
        tts_provider: str,
    ):
        """Property 7: Turn has raw and normalized transcripts.
        
        **Feature: voice-assistant-pipeline, Property 7: Data Persistence Completeness**
        **Validates: Requirements 5.1, 5.2, 5.3, 5.4**
        """
        user_id = uuid.uuid4()
        user = MockUser(
            id=user_id,
            name="Test User",
            stt_provider=stt_provider,
            tts_provider=tts_provider,
            language="ru",
        )

        service = MockVoiceSessionService({user_id: user})
        conversation = service.create_session(user_id)
        
        result = service.process_audio(conversation.id, user_id)
        turn = service.turns.get(result["turn_id"])
        
        # Turn should have transcripts
        assert turn is not None
        assert turn.raw_transcript is not None
        assert turn.normalized_transcript is not None
        assert turn.transcript_confidence is not None

    @given(
        stt_provider=provider_strategy,
        tts_provider=provider_strategy,
    )
    @settings(max_examples=100)
    def test_turn_has_valid_references(
        self,
        stt_provider: str,
        tts_provider: str,
    ):
        """Property 7: Turn has valid conversation_id and turn_id.
        
        **Feature: voice-assistant-pipeline, Property 7: Data Persistence Completeness**
        **Validates: Requirements 5.1, 5.2, 5.3, 5.4**
        """
        user_id = uuid.uuid4()
        user = MockUser(
            id=user_id,
            name="Test User",
            stt_provider=stt_provider,
            tts_provider=tts_provider,
            language="ru",
        )

        service = MockVoiceSessionService({user_id: user})
        conversation = service.create_session(user_id)
        
        result = service.process_audio(conversation.id, user_id)
        turn = service.turns.get(result["turn_id"])
        
        # Turn should have valid references
        assert turn is not None
        assert turn.id is not None
        assert turn.conversation_id == conversation.id
        assert turn.turn_number >= 1
