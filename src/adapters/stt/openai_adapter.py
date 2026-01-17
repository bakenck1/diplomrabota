"""OpenAI Whisper STT Adapter implementation."""

import io
import time
from typing import Literal, Optional

from openai import AsyncOpenAI, APIError, APITimeoutError, RateLimitError

from src.adapters.stt.base import (
    STTAdapter,
    STTResult,
    STTWord,
    STTError,
    STTTimeoutError,
    STTInvalidAudioError,
    STTRateLimitError,
)
from src.config import get_settings


class OpenAISTTAdapter(STTAdapter):
    """OpenAI Whisper API adapter for Speech-to-Text.
    
    Validates: Requirements 3.1, 12.1
    """

    PROVIDER_NAME = "openai"
    SUPPORTED_FORMATS = ["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"]

    def __init__(self, api_key: Optional[str] = None):
        """Initialize OpenAI STT adapter.
        
        Args:
            api_key: OpenAI API key. If not provided, uses settings.
        """
        settings = get_settings()
        self.client = AsyncOpenAI(api_key=api_key or settings.openai_api_key)
        self.timeout = 30.0

    async def transcribe(
        self,
        audio: bytes,
        language: Literal["ru", "kk"] = "ru",
        hints: Optional[list[str]] = None,
    ) -> STTResult:
        """Transcribe audio using OpenAI Whisper API.
        
        Args:
            audio: Audio data as bytes
            language: Language code ('ru' or 'kk')
            hints: Optional prompt hints for better recognition
            
        Returns:
            STTResult with transcription
        """
        start_time = time.perf_counter()

        # Prepare prompt from hints
        prompt = " ".join(hints) if hints else None

        # Create file-like object for API
        audio_file = io.BytesIO(audio)
        audio_file.name = "audio.wav"

        try:
            # Use verbose_json for word-level timestamps
            response = await self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=language,
                prompt=prompt,
                response_format="verbose_json",
                timestamp_granularities=["word"],
            )

            latency_ms = int((time.perf_counter() - start_time) * 1000)

            # Parse word-level data if available
            words: list[STTWord] = []
            if hasattr(response, "words") and response.words:
                for w in response.words:
                    words.append(
                        STTWord(
                            word=w.word,
                            start=w.start,
                            end=w.end,
                            confidence=1.0,  # Whisper doesn't provide per-word confidence
                        )
                    )

            # Calculate overall confidence (Whisper doesn't provide this directly)
            # Use a heuristic based on response quality
            confidence = self._estimate_confidence(response)

            return STTResult(
                text=response.text.strip(),
                confidence=confidence,
                words=words,
                language=language,
                latency_ms=latency_ms,
            )

        except APITimeoutError as e:
            raise STTTimeoutError(
                message="Request timed out",
                provider=self.PROVIDER_NAME,
                details={"timeout": self.timeout},
            ) from e

        except RateLimitError as e:
            raise STTRateLimitError(
                message="Rate limit exceeded",
                provider=self.PROVIDER_NAME,
                details={"error": str(e)},
            ) from e

        except APIError as e:
            if "Invalid file format" in str(e):
                raise STTInvalidAudioError(
                    message=f"Invalid audio format. Supported: {self.SUPPORTED_FORMATS}",
                    provider=self.PROVIDER_NAME,
                ) from e
            raise STTError(
                message=str(e),
                provider=self.PROVIDER_NAME,
                details={"status_code": getattr(e, "status_code", None)},
            ) from e

    def _estimate_confidence(self, response) -> float:
        """Estimate confidence score from Whisper response.
        
        Whisper doesn't provide confidence directly, so we use heuristics:
        - Check if no_speech_prob is available
        - Default to high confidence for successful transcriptions
        """
        if hasattr(response, "segments") and response.segments:
            # Average no_speech_prob across segments (lower is better)
            no_speech_probs = [
                s.no_speech_prob
                for s in response.segments
                if hasattr(s, "no_speech_prob")
            ]
            if no_speech_probs:
                avg_no_speech = sum(no_speech_probs) / len(no_speech_probs)
                return max(0.0, min(1.0, 1.0 - avg_no_speech))

        # Default confidence for successful transcription
        return 0.85

    def get_provider_name(self) -> str:
        """Get provider name."""
        return self.PROVIDER_NAME
