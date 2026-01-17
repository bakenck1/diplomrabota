"""Base TTS Adapter interface and data classes."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal, Optional


@dataclass
class TTSResult:
    """Result from TTS synthesis."""

    audio: bytes
    format: Literal["mp3", "wav", "ogg"]
    duration_ms: int
    latency_ms: int


class TTSAdapter(ABC):
    """Abstract base class for Text-to-Speech adapters.
    
    All TTS providers must implement this interface.
    Validates: Requirements 12.2
    """

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        language: Literal["ru", "kk"] = "ru",
        voice: Optional[str] = None,
        speed: float = 1.0,
    ) -> TTSResult:
        """Synthesize text to speech.
        
        Args:
            text: Text to synthesize
            language: Language code ('ru' for Russian, 'kk' for Kazakh)
            voice: Optional voice identifier
            speed: Speech speed multiplier (0.5 to 2.0)
            
        Returns:
            TTSResult with audio data and metadata
            
        Raises:
            TTSError: If synthesis fails
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the name of this TTS provider."""
        pass


class TTSError(Exception):
    """Base exception for TTS errors."""

    def __init__(self, message: str, provider: str, details: Optional[dict] = None):
        self.message = message
        self.provider = provider
        self.details = details or {}
        super().__init__(f"[{provider}] {message}")


class TTSTimeoutError(TTSError):
    """Raised when TTS request times out."""

    pass


class TTSTextTooLongError(TTSError):
    """Raised when text exceeds maximum length."""

    pass


class TTSRateLimitError(TTSError):
    """Raised when rate limit is exceeded."""

    pass
