"""OpenAI TTS Adapter implementation."""

import time
from typing import Literal, Optional

from openai import AsyncOpenAI, APIError, APITimeoutError, RateLimitError

from src.adapters.tts.base import (
    TTSAdapter,
    TTSResult,
    TTSError,
    TTSTimeoutError,
    TTSTextTooLongError,
    TTSRateLimitError,
)
from src.config import get_settings


class OpenAITTSAdapter(TTSAdapter):
    """OpenAI TTS API adapter for Text-to-Speech.
    
    Validates: Requirements 3.2, 12.2
    """

    PROVIDER_NAME = "openai"
    MAX_TEXT_LENGTH = 4096
    
    # Available voices
    VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
    DEFAULT_VOICE = "nova"  # Good for Russian

    def __init__(self, api_key: Optional[str] = None):
        """Initialize OpenAI TTS adapter.
        
        Args:
            api_key: OpenAI API key. If not provided, uses settings.
        """
        settings = get_settings()
        self.client = AsyncOpenAI(api_key=api_key or settings.openai_api_key)
        self.timeout = 30.0

    async def synthesize(
        self,
        text: str,
        language: Literal["ru", "kk"] = "ru",
        voice: Optional[str] = None,
        speed: float = 1.0,
    ) -> TTSResult:
        """Synthesize text using OpenAI TTS API.
        
        Args:
            text: Text to synthesize
            language: Language code (used for voice selection hints)
            voice: Voice identifier (alloy, echo, fable, onyx, nova, shimmer)
            speed: Speech speed (0.25 to 4.0)
            
        Returns:
            TTSResult with MP3 audio
        """
        start_time = time.perf_counter()

        # Validate text length
        if len(text) > self.MAX_TEXT_LENGTH:
            raise TTSTextTooLongError(
                message=f"Text exceeds maximum length of {self.MAX_TEXT_LENGTH} characters",
                provider=self.PROVIDER_NAME,
                details={"text_length": len(text), "max_length": self.MAX_TEXT_LENGTH},
            )

        # Select voice
        selected_voice = voice if voice in self.VOICES else self.DEFAULT_VOICE

        # Clamp speed to valid range
        speed = max(0.25, min(4.0, speed))

        try:
            response = await self.client.audio.speech.create(
                model="tts-1",
                voice=selected_voice,
                input=text,
                speed=speed,
                response_format="mp3",
            )

            # Read audio content
            audio_content = response.content

            latency_ms = int((time.perf_counter() - start_time) * 1000)

            # Estimate duration (rough estimate based on text length and speed)
            # Average speaking rate: ~150 words per minute
            word_count = len(text.split())
            estimated_duration_ms = int((word_count / 150) * 60 * 1000 / speed)

            return TTSResult(
                audio=audio_content,
                format="mp3",
                duration_ms=estimated_duration_ms,
                latency_ms=latency_ms,
            )

        except APITimeoutError as e:
            raise TTSTimeoutError(
                message="Request timed out",
                provider=self.PROVIDER_NAME,
                details={"timeout": self.timeout},
            ) from e

        except RateLimitError as e:
            raise TTSRateLimitError(
                message="Rate limit exceeded",
                provider=self.PROVIDER_NAME,
                details={"error": str(e)},
            ) from e

        except APIError as e:
            raise TTSError(
                message=str(e),
                provider=self.PROVIDER_NAME,
                details={"status_code": getattr(e, "status_code", None)},
            ) from e

    def get_provider_name(self) -> str:
        """Get provider name."""
        return self.PROVIDER_NAME
