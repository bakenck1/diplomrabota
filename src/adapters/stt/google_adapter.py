"""Google STT Adapter - Mock mode for demo.

In production, use Google Cloud Speech-to-Text with service account.
"""

import time
from typing import Literal, Optional

from src.adapters.stt.base import (
    STTAdapter,
    STTResult,
    STTWord,
    STTError,
)
from src.config import get_settings


class GoogleSTTAdapter(STTAdapter):
    """Google STT adapter - Demo/Mock mode."""

    PROVIDER_NAME = "google"

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Google STT adapter."""
        settings = get_settings()
        self.api_key = api_key or settings.google_api_key
        
    async def transcribe(
        self,
        audio: bytes,
        language: Literal["ru", "kk"] = "ru",
        hints: Optional[list[str]] = None,
    ) -> STTResult:
        """Transcribe audio - Demo mode returns placeholder text."""
        start_time = time.perf_counter()
        
        # Demo mode - return placeholder based on audio length
        audio_duration_sec = len(audio) / (16000 * 2)  # Assuming 16kHz, 16-bit
        
        if audio_duration_sec < 1:
            text = "Привет"
        elif audio_duration_sec < 3:
            text = "Привет, как дела?"
        else:
            text = "Здравствуйте, я хотел бы узнать информацию."
        
        latency_ms = int((time.perf_counter() - start_time) * 1000) + 100  # Simulate latency
        
        return STTResult(
            text=text,
            confidence=0.92,
            words=[
                STTWord(word=w, start=i*0.3, end=(i+1)*0.3, confidence=0.9)
                for i, w in enumerate(text.split())
            ],
            language=language,
            latency_ms=latency_ms,
        )

    def get_provider_name(self) -> str:
        return self.PROVIDER_NAME
