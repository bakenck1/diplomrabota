"""Voice Session Service - main pipeline orchestration.

Validates: Requirements 3.4, 3.5, 5.1, 5.2, 5.3, 5.4, 11.1
"""

import uuid
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.stt.base import STTAdapter, STTResult
from src.adapters.tts.base import TTSAdapter, TTSResult
from src.models.entities import User, Conversation, Turn
from src.services.normalization import NormalizationService, NormalizationResult
from src.services.storage import StorageService
from src.config import get_settings


@dataclass
class ProcessAudioResult:
    """Result of processing audio input."""

    turn_id: str
    raw_transcript: str
    normalized_transcript: str
    confidence: float
    stt_latency_ms: int


@dataclass
class GenerateResponseResult:
    """Result of generating assistant response."""

    assistant_text: str
    audio_url: str
    tts_latency_ms: int


class AdapterFactory:
    """Factory for creating STT/TTS adapters based on provider name.
    
    Validates: Requirements 3.4, 3.5, 3.6
    """

    @staticmethod
    def get_stt_adapter(provider: Literal["openai", "google"]) -> STTAdapter:
        """Get STT adapter for provider.
        
        Args:
            provider: Provider name
            
        Returns:
            STT adapter instance
        """
        if provider == "openai":
            from src.adapters.stt.openai_adapter import OpenAISTTAdapter
            return OpenAISTTAdapter()
        elif provider == "google":
            from src.adapters.stt.google_adapter import GoogleSTTAdapter
            return GoogleSTTAdapter()
        else:
            raise ValueError(f"Unknown STT provider: {provider}")

    @staticmethod
    def get_tts_adapter(provider: Literal["openai", "google"]) -> TTSAdapter:
        """Get TTS adapter for provider.
        
        Args:
            provider: Provider name
            
        Returns:
            TTS adapter instance
        """
        if provider == "openai":
            from src.adapters.tts.openai_adapter import OpenAITTSAdapter
            return OpenAITTSAdapter()
        elif provider == "google":
            from src.adapters.tts.google_adapter import GoogleTTSAdapter
            return GoogleTTSAdapter()
        else:
            raise ValueError(f"Unknown TTS provider: {provider}")


class VoiceSessionService:
    """Service for managing voice sessions and processing pipeline.
    
    Validates: Requirements 3.4, 3.5, 5.1, 5.2, 5.3, 5.4, 11.1
    """

    def __init__(self, db: AsyncSession):
        """Initialize voice session service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.settings = get_settings()
        self.storage = StorageService()
        self._normalization_service: Optional[NormalizationService] = None

    @property
    def normalization(self) -> NormalizationService:
        """Get normalization service (lazy init)."""
        if self._normalization_service is None:
            self._normalization_service = NormalizationService(self.db)
        return self._normalization_service

    async def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        query = select(User).where(User.id == str(user_id))
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_session(
        self,
        user_id: str,
        device_info: Optional[dict] = None,
    ) -> Conversation:
        """Create a new voice session.
        
        Args:
            user_id: User ID
            device_info: Optional device information
            
        Returns:
            Created conversation
            
        Validates: Requirements 11.1
        """
        user = await self.get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        conversation = Conversation(
            id=str(uuid.uuid4()),
            user_id=str(user_id),
            stt_provider_used=user.stt_provider,
            tts_provider_used=user.tts_provider,
            device_info=device_info,
        )
        self.db.add(conversation)
        await self.db.flush()

        # Update user last active
        user.last_active_at = datetime.utcnow()
        await self.db.flush()

        return conversation

    async def process_audio(
        self,
        session_id: str,
        audio: bytes,
        user_id: str,
    ) -> ProcessAudioResult:
        """Process audio input through STT and normalization.
        
        Args:
            session_id: Conversation/session ID
            audio: Audio data as bytes
            user_id: User ID
            
        Returns:
            ProcessAudioResult with transcripts and confidence
            
        Validates: Requirements 3.4, 5.1, 5.2
        """
        # Get user settings
        user = await self.get_user(str(user_id))
        if not user:
            raise ValueError(f"User {user_id} not found")

        # Get conversation
        query = select(Conversation).where(Conversation.id == str(session_id))
        result = await self.db.execute(query)
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise ValueError(f"Session {session_id} not found")

        # Create turn
        turn_number = await self._get_next_turn_number(str(session_id))
        turn = Turn(
            id=str(uuid.uuid4()),
            conversation_id=str(session_id),
            turn_number=turn_number,
        )
        self.db.add(turn)
        await self.db.flush()

        # Upload audio to storage
        audio_key = await self.storage.upload_audio(
            audio=audio,
            user_id=user_id,
            conversation_id=session_id,
            turn_id=turn.id,
            file_type="input.wav",
        )
        turn.audio_input_url = audio_key

        # Get STT adapter based on user settings
        stt_adapter = AdapterFactory.get_stt_adapter(user.stt_provider)

        # Transcribe audio
        stt_result = await stt_adapter.transcribe(
            audio=audio,
            language=user.language,
        )

        # Normalize transcript
        norm_result = await self.normalization.normalize(
            text=stt_result.text,
            language=user.language,
            stt_confidence=stt_result.confidence,
        )

        # Update turn with results
        turn.raw_transcript = norm_result.raw_transcript
        turn.normalized_transcript = norm_result.normalized_transcript
        turn.transcript_confidence = stt_result.confidence
        turn.stt_latency_ms = stt_result.latency_ms
        turn.stt_words = [
            {"word": w.word, "start": w.start, "end": w.end, "confidence": w.confidence}
            for w in stt_result.words
        ]
        turn.low_confidence = stt_result.confidence < self.settings.normalization_confidence_threshold

        # Create pending unknown terms
        for term in norm_result.unknown_terms_created:
            await self.normalization.create_pending_term(
                heard_variant=term,
                language=user.language,
                context=norm_result.raw_transcript,
                provider=user.stt_provider,
            )

        await self.db.flush()

        return ProcessAudioResult(
            turn_id=turn.id,
            raw_transcript=norm_result.raw_transcript,
            normalized_transcript=norm_result.normalized_transcript,
            confidence=stt_result.confidence,
            stt_latency_ms=stt_result.latency_ms,
        )

    async def confirm_transcript(
        self,
        session_id: str,
        turn_id: str,
        confirmed: bool,
        correction: Optional[str] = None,
    ) -> None:
        """Confirm or correct transcript.
        
        Args:
            session_id: Conversation ID
            turn_id: Turn ID
            confirmed: Whether user confirmed the transcript
            correction: Optional corrected text
            
        Validates: Requirements 2.3, 2.4, 2.6, 5.5
        """
        query = select(Turn).where(Turn.id == str(turn_id), Turn.conversation_id == str(session_id))
        result = await self.db.execute(query)
        turn = result.scalar_one_or_none()
        if not turn:
            raise ValueError(f"Turn {turn_id} not found")

        turn.user_confirmed = confirmed
        
        if correction:
            turn.user_correction = correction
            # Save correction to dictionary
            conv_query = select(Conversation).where(Conversation.id == str(session_id))
            conv_result = await self.db.execute(conv_query)
            conversation = conv_result.scalar_one()
            
            user_query = select(User).where(User.id == str(conversation.user_id))
            user_result = await self.db.execute(user_query)
            user = user_result.scalar_one()

            # Create term from correction
            if turn.raw_transcript and correction != turn.raw_transcript:
                await self.normalization.create_pending_term(
                    heard_variant=turn.raw_transcript,
                    language=user.language,
                    context=correction,
                    provider=conversation.stt_provider_used,
                )

        await self.db.flush()

    async def generate_response(
        self,
        session_id: str,
        turn_id: str,
        assistant_text: str,
    ) -> GenerateResponseResult:
        """Generate TTS response for assistant text.
        
        Args:
            session_id: Conversation ID
            turn_id: Turn ID
            assistant_text: Text to synthesize
            
        Returns:
            GenerateResponseResult with audio URL
            
        Validates: Requirements 3.5, 5.3
        """
        # Get turn
        query = select(Turn).where(Turn.id == str(turn_id), Turn.conversation_id == str(session_id))
        result = await self.db.execute(query)
        turn = result.scalar_one_or_none()
        if not turn:
            raise ValueError(f"Turn {turn_id} not found")

        # Get conversation and user
        conv_query = select(Conversation).where(Conversation.id == str(session_id))
        conv_result = await self.db.execute(conv_query)
        conversation = conv_result.scalar_one()

        user_query = select(User).where(User.id == str(conversation.user_id))
        user_result = await self.db.execute(user_query)
        user = user_result.scalar_one()

        # Get TTS adapter
        tts_adapter = AdapterFactory.get_tts_adapter(user.tts_provider)

        # Synthesize speech
        tts_result = await tts_adapter.synthesize(
            text=assistant_text,
            language=user.language,
        )

        # Upload audio - use format from TTS result
        file_ext = "wav" if tts_result.format == "wav" else "mp3"
        content_type = "audio/wav" if tts_result.format == "wav" else "audio/mpeg"
        audio_key = await self.storage.upload_audio(
            audio=tts_result.audio,
            user_id=user.id,
            conversation_id=session_id,
            turn_id=turn_id,
            file_type=f"output.{file_ext}",
            content_type=content_type,
        )

        # Update turn
        turn.assistant_text = assistant_text
        turn.audio_output_url = audio_key
        turn.audio_output_duration_ms = tts_result.duration_ms
        turn.tts_latency_ms = tts_result.latency_ms

        await self.db.flush()

        # Generate signed URL
        audio_url = self.storage.generate_signed_url(audio_key)

        return GenerateResponseResult(
            assistant_text=assistant_text,
            audio_url=audio_url,
            tts_latency_ms=tts_result.latency_ms,
        )

    async def end_session(self, session_id: str) -> None:
        """End a voice session.
        
        Args:
            session_id: Conversation ID
        """
        query = select(Conversation).where(Conversation.id == str(session_id))
        result = await self.db.execute(query)
        conversation = result.scalar_one_or_none()
        if conversation:
            conversation.ended_at = datetime.utcnow()
            await self.db.flush()

    async def _get_next_turn_number(self, session_id: str) -> int:
        """Get next turn number for session."""
        query = select(Turn).where(Turn.conversation_id == str(session_id))
        result = await self.db.execute(query)
        turns = result.scalars().all()
        return len(turns) + 1
