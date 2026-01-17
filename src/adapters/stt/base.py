"""Base STT Adapter interface and data classes."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal, Optional


@dataclass
class STTWord:
    """Individual word with timing and confidence."""

    word: str
    start: float  # seconds
    end: float  # seconds
    confidence: float


@dataclass
class STTResult:
    """Result from STT transcription."""

    text: str
    confidence: float
    words: list[STTWord] = field(default_factory=list)
    language: str = "ru"
    latency_ms: int = 0


class STTAdapter(ABC):
    """Abstract base class for Speech-to-Text adapters.
    
    All STT providers must implement this interface.
    Validates: Requirements 12.1
    """

    @abstractmethod
    async def transcribe(
        self,
        audio: bytes,
        language: Literal["ru", "kk"] = "ru",
        hints: Optional[list[str]] = None,
    ) -> STTResult:
        """Transcribe audio to text.
        
        Args:
            audio: Audio data as bytes (WAV, MP3, or other supported format)
            language: Language code ('ru' for Russian, 'kk' for Kazakh)
            hints: Optional list of words/phrases to improve recognition
            
        Returns:
            STTResult with transcribed text, confidence, and word-level details
            
        Raises:
            STTError: If transcription fails
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the name of this STT provider."""
        pass


class STTError(Exception):
    """Base exception for STT errors."""

    def __init__(self, message: str, provider: str, details: Optional[dict] = None):
        self.message = message
        self.provider = provider
        self.details = details or {}
        super().__init__(f"[{provider}] {message}")


class STTTimeoutError(STTError):
    """Raised when STT request times out."""

    pass


class STTInvalidAudioError(STTError):
    """Raised when audio format is invalid."""

    pass


class STTRateLimitError(STTError):
    """Raised when rate limit is exceeded."""

    pass
