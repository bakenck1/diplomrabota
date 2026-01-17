"""Tests for comparison service."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.stt.base import STTAdapter, STTResult
from src.models.entities import RecognitionMetric, SpeechRecord
from src.services.comparison import ComparisonService
from src.services.storage import StorageService


class MockSTTAdapter(STTAdapter):
    def __init__(self, provider_name: str, result_text: str = "text"):
        self.provider_name = provider_name
        self.result_text = result_text

    def get_provider_name(self) -> str:
        return self.provider_name

    async def transcribe(self, audio: bytes, language: str = "ru", hints=None) -> STTResult:
        return STTResult(
            text=self.result_text,
            confidence=0.9,
            latency_ms=100,
            language=language
        )


@pytest.mark.asyncio
async def test_comparison_service_process_audio():
    # Setup mocks
    mock_db = MagicMock(spec=AsyncSession)
    mock_db.add = MagicMock()
    mock_db.add_all = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.flush = AsyncMock()
    mock_db.refresh = AsyncMock()

    mock_storage = MagicMock(spec=StorageService)
    mock_storage.upload_research_audio = AsyncMock(return_value="path/to/audio.wav")
    mock_storage.generate_signed_url = MagicMock(return_value="http://url/audio.wav")

    # Patch adapters
    with patch("src.services.comparison.get_openai_adapter") as mock_get_openai, \
         patch("src.services.comparison.get_google_adapter") as mock_get_google:

        # Configure mock adapters to return our MockSTTAdapter class
        # Note: The service instantiates the class returned by get_adapter()
        # So we need mock_get_adapter() -> returns Class -> Class() returns instance

        mock_openai_class = MagicMock(return_value=MockSTTAdapter("openai", "openai text"))
        mock_google_class = MagicMock(return_value=MockSTTAdapter("google", "google text"))

        mock_get_openai.return_value = mock_openai_class
        mock_get_google.return_value = mock_google_class

        # Initialize service
        service = ComparisonService(mock_db, mock_storage)

        # Test input
        user_id = str(uuid.uuid4())
        audio_content = b"fake audio"
        language = "ru"

        # Run process
        record = await service.process_audio(user_id, audio_content, language)

        # Verification

        # 1. Check storage upload
        mock_storage.upload_research_audio.assert_called_once()

        # 2. Check DB interactions
        # Should add SpeechRecord and Metrics
        assert mock_db.add.called
        assert mock_db.add_all.called
        assert mock_db.commit.called

        # 3. Check Record fields
        assert record.user_id == user_id
        assert record.audio_path == "path/to/audio.wav"
        assert record.recognized_text_ru == "openai text"  # Our mock prefers OpenAI

        # 4. Check Metrics
        # access arguments passed to add_all
        metrics = mock_db.add_all.call_args[0][0]
        assert len(metrics) == 2
        provider_names = [m.algorithm_name for m in metrics]
        assert "openai" in provider_names
        assert "google" in provider_names

        for m in metrics:
            assert m.speech_record_id == record.id
            assert m.confidence_score == 0.9
            assert m.processing_time_ms == 100


@pytest.mark.asyncio
async def test_comparison_service_process_audio_kazakh():
    # Setup mocks
    mock_db = MagicMock(spec=AsyncSession)
    mock_db.add = MagicMock()
    mock_db.add_all = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.flush = AsyncMock()
    mock_db.refresh = AsyncMock()

    mock_storage = MagicMock(spec=StorageService)
    mock_storage.upload_research_audio = AsyncMock(return_value="path/to/audio.wav")
    mock_storage.generate_signed_url = MagicMock(return_value="http://url/audio.wav")

    with patch("src.services.comparison.get_openai_adapter") as mock_get_openai, \
         patch("src.services.comparison.get_google_adapter") as mock_get_google:

        mock_openai_class = MagicMock(return_value=MockSTTAdapter("openai", "openai text"))
        mock_google_class = MagicMock(return_value=MockSTTAdapter("google", "google text"))

        mock_get_openai.return_value = mock_openai_class
        mock_get_google.return_value = mock_google_class

        service = ComparisonService(mock_db, mock_storage)

        user_id = str(uuid.uuid4())
        audio_content = b"fake audio"
        language = "kk"  # Kazakh

        record = await service.process_audio(user_id, audio_content, language)

        # Check that kazakh field is populated
        assert record.recognized_text_kz == "openai text"
        assert record.recognized_text_ru is None
