# TTS Adapters
from src.adapters.tts.base import TTSAdapter, TTSResult

__all__ = [
    "TTSAdapter",
    "TTSResult",
]

# Lazy imports for adapters with external dependencies
def get_openai_adapter():
    from src.adapters.tts.openai_adapter import OpenAITTSAdapter
    return OpenAITTSAdapter

def get_google_adapter():
    from src.adapters.tts.google_adapter import GoogleTTSAdapter
    return GoogleTTSAdapter
