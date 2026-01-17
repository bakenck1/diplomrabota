"""Google TTS Adapter using edge-tts (Microsoft Edge TTS).

Uses edge-tts for text-to-speech synthesis (free, fast, high quality).
"""

import asyncio
import io
import time
from typing import Literal, Optional

from src.adapters.tts.base import TTSAdapter, TTSResult, TTSError


class GoogleTTSAdapter(TTSAdapter):
    """TTS adapter using Microsoft Edge TTS (via edge-tts)."""

    PROVIDER_NAME = "google"
    
    # Voice mapping for languages
    VOICES = {
        "ru": "ru-RU-SvetlanaNeural",  # Russian female voice
        "kk": "kk-KZ-AigulNeural",      # Kazakh female voice
    }

    def __init__(self):
        """Initialize TTS adapter."""
        pass
        
    async def synthesize(
        self,
        text: str,
        language: Literal["ru", "kk"] = "ru",
        voice: Optional[str] = None,
        speed: float = 1.0,
    ) -> TTSResult:
        """Synthesize speech using edge-tts."""
        import edge_tts
        
        start_time = time.perf_counter()
        
        try:
            # Select voice
            voice_name = voice or self.VOICES.get(language, self.VOICES["ru"])
            
            # Create communicate object
            communicate = edge_tts.Communicate(text, voice_name)
            
            # Collect audio chunks
            audio_chunks = []
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_chunks.append(chunk["data"])
            
            audio_data = b"".join(audio_chunks)
            
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            
            # Estimate duration (rough: ~150 words per minute)
            word_count = len(text.split())
            duration_ms = int((word_count / 150) * 60 * 1000) or 1000
            
            return TTSResult(
                audio=audio_data,
                format="mp3",  # edge-tts outputs MP3
                duration_ms=duration_ms,
                latency_ms=latency_ms,
            )
            
        except Exception as e:
            raise TTSError(
                message=str(e),
                provider=self.PROVIDER_NAME,
            ) from e

    def get_provider_name(self) -> str:
        return self.PROVIDER_NAME
