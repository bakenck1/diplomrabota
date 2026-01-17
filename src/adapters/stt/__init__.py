# STT Adapters
from src.adapters.stt.base import STTAdapter, STTResult, STTWord

__all__ = [
    "STTAdapter",
    "STTResult",
    "STTWord",
]

# Lazy imports for adapters with external dependencies
def get_openai_adapter():
    from src.adapters.stt.openai_adapter import OpenAISTTAdapter
    return OpenAISTTAdapter

def get_google_adapter():
    from src.adapters.stt.google_adapter import GoogleSTTAdapter
    return GoogleSTTAdapter
