"""Property-based tests for STT Adapters.

**Feature: voice-assistant-pipeline, Property 18: Adapter Interface Compliance**
**Validates: Requirements 12.1, 12.2**
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from hypothesis import given, strategies as st, settings
from dataclasses import fields

# Import only base classes (no external dependencies)
from src.adapters.stt.base import STTAdapter, STTResult, STTWord


class TestSTTResultSchema:
    """Test that STTResult conforms to the expected schema."""

    @given(
        text=st.text(min_size=0, max_size=1000),
        confidence=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        language=st.sampled_from(["ru", "kk"]),
        latency_ms=st.integers(min_value=0, max_value=100000),
    )
    @settings(max_examples=100)
    def test_stt_result_contains_required_fields(
        self, text: str, confidence: float, language: str, latency_ms: int
    ):
        """Property 18: For any STT result, it must contain text, confidence, and latency_ms.
        
        **Feature: voice-assistant-pipeline, Property 18: Adapter Interface Compliance**
        **Validates: Requirements 12.1**
        """
        result = STTResult(
            text=text,
            confidence=confidence,
            language=language,
            latency_ms=latency_ms,
        )

        # Verify required fields exist and have correct types
        assert isinstance(result.text, str)
        assert isinstance(result.confidence, (int, float))
        assert 0.0 <= result.confidence <= 1.0
        assert isinstance(result.latency_ms, int)
        assert result.latency_ms >= 0
        assert isinstance(result.language, str)
        assert result.language in ["ru", "kk"]

    @given(
        word=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"))),
        start=st.floats(min_value=0.0, max_value=1000.0, allow_nan=False),
        end=st.floats(min_value=0.0, max_value=1000.0, allow_nan=False),
        confidence=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    )
    @settings(max_examples=100)
    def test_stt_word_contains_required_fields(
        self, word: str, start: float, end: float, confidence: float
    ):
        """Property 18: For any STT word, it must contain word, start, end, confidence.
        
        **Feature: voice-assistant-pipeline, Property 18: Adapter Interface Compliance**
        **Validates: Requirements 12.1**
        """
        stt_word = STTWord(
            word=word,
            start=start,
            end=end,
            confidence=confidence,
        )

        assert isinstance(stt_word.word, str)
        assert len(stt_word.word) > 0
        assert isinstance(stt_word.start, float)
        assert isinstance(stt_word.end, float)
        assert isinstance(stt_word.confidence, float)
        assert 0.0 <= stt_word.confidence <= 1.0

    @given(
        text=st.text(min_size=0, max_size=500),
        confidence=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        num_words=st.integers(min_value=0, max_value=20),
    )
    @settings(max_examples=100)
    def test_stt_result_words_list_is_valid(
        self, text: str, confidence: float, num_words: int
    ):
        """Property 18: STTResult.words must be a list of STTWord objects.
        
        **Feature: voice-assistant-pipeline, Property 18: Adapter Interface Compliance**
        **Validates: Requirements 12.1**
        """
        words = [
            STTWord(word=f"word{i}", start=float(i), end=float(i + 1), confidence=0.9)
            for i in range(num_words)
        ]

        result = STTResult(
            text=text,
            confidence=confidence,
            words=words,
            language="ru",
            latency_ms=100,
        )

        assert isinstance(result.words, list)
        assert len(result.words) == num_words
        for w in result.words:
            assert isinstance(w, STTWord)


class TestSTTAdapterInterface:
    """Test that STT adapters implement the required interface."""

    def test_stt_adapter_is_abstract(self):
        """STTAdapter should be abstract and not instantiable directly."""
        with pytest.raises(TypeError):
            STTAdapter()

    def test_stt_adapter_has_required_methods(self):
        """STTAdapter must define transcribe and get_provider_name methods."""
        assert hasattr(STTAdapter, "transcribe")
        assert hasattr(STTAdapter, "get_provider_name")
        assert callable(getattr(STTAdapter, "transcribe", None))
        assert callable(getattr(STTAdapter, "get_provider_name", None))


class TestSTTResultDataclass:
    """Test STTResult dataclass structure."""

    def test_stt_result_has_all_required_fields(self):
        """STTResult must have text, confidence, words, language, latency_ms fields."""
        field_names = {f.name for f in fields(STTResult)}
        required_fields = {"text", "confidence", "words", "language", "latency_ms"}
        
        assert required_fields.issubset(field_names), (
            f"Missing fields: {required_fields - field_names}"
        )

    def test_stt_word_has_all_required_fields(self):
        """STTWord must have word, start, end, confidence fields."""
        field_names = {f.name for f in fields(STTWord)}
        required_fields = {"word", "start", "end", "confidence"}
        
        assert required_fields.issubset(field_names), (
            f"Missing fields: {required_fields - field_names}"
        )
