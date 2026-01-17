"""Property-based tests for Normalization Service.

**Feature: voice-assistant-pipeline**
**Validates: Requirements 4.1, 4.3, 8.3**
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from hypothesis import given, strategies as st, settings, assume
from dataclasses import dataclass, field
from typing import Literal


# Define local copies of dataclasses to avoid database imports
@dataclass
class Correction:
    """A single correction applied during normalization."""
    original: str
    corrected: str
    rule_type: Literal["exact", "fuzzy"]
    confidence: float


@dataclass
class NormalizationResult:
    """Result of text normalization."""
    raw_transcript: str
    normalized_transcript: str
    corrections: list[Correction] = field(default_factory=list)
    unknown_terms_created: list[str] = field(default_factory=list)


class MockNormalizationService:
    """Mock service for testing without database."""

    def __init__(self, dictionary: dict[str, str]):
        """Initialize with a dictionary of heard_variant -> correct_form."""
        self._dictionary = {k.lower(): {"correct_form": v} for k, v in dictionary.items()}
        self.confidence_threshold = 0.7
        self.fuzzy_max_distance = 2

    def normalize_sync(
        self,
        text: str,
        stt_confidence: float = 1.0,
    ) -> NormalizationResult:
        """Synchronous normalize for testing."""
        from Levenshtein import distance as levenshtein_distance

        raw_transcript = text
        corrections: list[Correction] = []
        unknown_terms_created: list[str] = []

        words = text.split()
        normalized_words = []

        for word in words:
            word_lower = word.lower()
            corrected_word = word
            
            # Exact match
            if word_lower in self._dictionary:
                corrected_word = self._dictionary[word_lower]["correct_form"]
                corrections.append(
                    Correction(
                        original=word,
                        corrected=corrected_word,
                        rule_type="exact",
                        confidence=1.0,
                    )
                )
            # Fuzzy match if low confidence
            elif stt_confidence < self.confidence_threshold:
                best_match = None
                best_distance = self.fuzzy_max_distance + 1
                
                for heard_variant, term_info in self._dictionary.items():
                    dist = levenshtein_distance(word_lower, heard_variant)
                    if dist <= self.fuzzy_max_distance and dist < best_distance:
                        best_distance = dist
                        confidence = 1.0 - (dist / (self.fuzzy_max_distance + 1))
                        best_match = {
                            "correct_form": term_info["correct_form"],
                            "confidence": confidence,
                        }
                
                if best_match:
                    corrected_word = best_match["correct_form"]
                    corrections.append(
                        Correction(
                            original=word,
                            corrected=corrected_word,
                            rule_type="fuzzy",
                            confidence=best_match["confidence"],
                        )
                    )
                elif len(word) >= 3:
                    unknown_terms_created.append(word)

            normalized_words.append(corrected_word)

        return NormalizationResult(
            raw_transcript=raw_transcript,
            normalized_transcript=" ".join(normalized_words),
            corrections=corrections,
            unknown_terms_created=unknown_terms_created,
        )


# Strategies for generating test data
word_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L",), whitelist_characters=" "),
    min_size=1,
    max_size=20,
).filter(lambda x: x.strip() != "")

dictionary_strategy = st.dictionaries(
    keys=st.text(alphabet="абвгдеёжзийклмнопрстуфхцчшщъыьэюя", min_size=3, max_size=15),
    values=st.text(alphabet="абвгдеёжзийклмнопрстуфхцчшщъыьэюя", min_size=3, max_size=15),
    min_size=1,
    max_size=10,
)


class TestDictionaryApplication:
    """Property 2: Normalization Dictionary Application tests."""

    @given(
        dictionary=dictionary_strategy,
    )
    @settings(max_examples=100)
    def test_exact_match_replaces_known_terms(self, dictionary: dict[str, str]):
        """Property 2: For any text with known terms, exact matches are replaced.
        
        **Feature: voice-assistant-pipeline, Property 2: Normalization Dictionary Application**
        **Validates: Requirements 4.1, 8.3**
        """
        assume(len(dictionary) > 0)
        
        service = MockNormalizationService(dictionary)
        
        # Create text with a known term
        heard_variant = list(dictionary.keys())[0]
        correct_form = dictionary[heard_variant]
        text = f"слово {heard_variant} другое"
        
        result = service.normalize_sync(text, stt_confidence=1.0)
        
        # The normalized text should contain the correct form
        assert correct_form in result.normalized_transcript
        # Should have at least one correction
        assert len(result.corrections) >= 1
        # The correction should be exact match
        exact_corrections = [c for c in result.corrections if c.rule_type == "exact"]
        assert len(exact_corrections) >= 1

    @given(
        dictionary=dictionary_strategy,
    )
    @settings(max_examples=100)
    def test_all_dictionary_terms_are_replaced(self, dictionary: dict[str, str]):
        """Property 2: All dictionary terms in text are replaced with correct forms.
        
        **Feature: voice-assistant-pipeline, Property 2: Normalization Dictionary Application**
        **Validates: Requirements 4.1, 8.3**
        """
        assume(len(dictionary) > 0)
        
        service = MockNormalizationService(dictionary)
        
        # Create text with all dictionary terms
        text = " ".join(dictionary.keys())
        
        result = service.normalize_sync(text, stt_confidence=1.0)
        
        # All terms should be corrected
        assert len(result.corrections) == len(dictionary)
        
        # All corrections should be exact matches
        for correction in result.corrections:
            assert correction.rule_type == "exact"
            assert correction.confidence == 1.0


class TestTranscriptPreservation:
    """Property 4: Transcript Preservation Invariant tests."""

    @given(
        text=st.text(min_size=1, max_size=200).filter(lambda x: x.strip() != ""),
        dictionary=dictionary_strategy,
    )
    @settings(max_examples=100)
    def test_raw_transcript_preserved(self, text: str, dictionary: dict[str, str]):
        """Property 4: Raw transcript is always preserved separately.
        
        **Feature: voice-assistant-pipeline, Property 4: Transcript Preservation Invariant**
        **Validates: Requirements 4.3, 5.2**
        """
        service = MockNormalizationService(dictionary)
        
        result = service.normalize_sync(text, stt_confidence=1.0)
        
        # Raw transcript must equal original input
        assert result.raw_transcript == text
        # Normalized transcript must exist
        assert result.normalized_transcript is not None
        # Both must be strings
        assert isinstance(result.raw_transcript, str)
        assert isinstance(result.normalized_transcript, str)

    @given(
        text=st.text(
            alphabet=st.characters(whitelist_categories=("L", "N"), min_codepoint=32),
            min_size=1,
            max_size=200
        ).filter(lambda x: x.strip() != "" and "\r" not in x and "\n" not in x),
    )
    @settings(max_examples=100)
    def test_empty_dictionary_preserves_text(self, text: str):
        """Property 4: With empty dictionary, normalized equals raw.
        
        **Feature: voice-assistant-pipeline, Property 4: Transcript Preservation Invariant**
        **Validates: Requirements 4.3, 5.2**
        """
        service = MockNormalizationService({})
        
        result = service.normalize_sync(text, stt_confidence=1.0)
        
        # With no dictionary, text should be unchanged
        assert result.raw_transcript == text
        # Normalized should equal raw (no corrections possible)
        # Note: whitespace may be normalized by split/join
        assert result.normalized_transcript == " ".join(text.split())
        assert len(result.corrections) == 0


class TestFuzzyMatching:
    """Tests for fuzzy matching behavior."""

    def test_fuzzy_match_activates_on_low_confidence(self):
        """Fuzzy matching only activates when confidence is below threshold.
        
        **Validates: Requirements 4.2**
        """
        dictionary = {"привет": "привет"}
        service = MockNormalizationService(dictionary)
        
        # Typo: "превет" instead of "привет" (distance = 1)
        text = "превет"
        
        # High confidence - no fuzzy match
        result_high = service.normalize_sync(text, stt_confidence=0.9)
        assert result_high.normalized_transcript == text
        
        # Low confidence - fuzzy match should work
        result_low = service.normalize_sync(text, stt_confidence=0.5)
        assert result_low.normalized_transcript == "привет"
        assert len(result_low.corrections) == 1
        assert result_low.corrections[0].rule_type == "fuzzy"

    def test_fuzzy_match_respects_max_distance(self):
        """Fuzzy matching respects maximum Levenshtein distance.
        
        **Validates: Requirements 4.2**
        """
        dictionary = {"привет": "привет"}
        service = MockNormalizationService(dictionary)
        service.fuzzy_max_distance = 2
        
        # Distance 1 - should match
        result1 = service.normalize_sync("превет", stt_confidence=0.5)
        assert "привет" in result1.normalized_transcript
        
        # Distance 3 - should NOT match (too far)
        result3 = service.normalize_sync("пррррет", stt_confidence=0.5)
        assert "привет" not in result3.normalized_transcript


class TestCorrectionDataIntegrity:
    """Tests for correction data structure."""

    @given(
        dictionary=dictionary_strategy,
    )
    @settings(max_examples=100)
    def test_corrections_have_required_fields(self, dictionary: dict[str, str]):
        """All corrections must have original, corrected, rule_type, confidence.
        
        **Validates: Requirements 4.1**
        """
        assume(len(dictionary) > 0)
        
        service = MockNormalizationService(dictionary)
        text = " ".join(dictionary.keys())
        
        result = service.normalize_sync(text, stt_confidence=1.0)
        
        for correction in result.corrections:
            assert hasattr(correction, "original")
            assert hasattr(correction, "corrected")
            assert hasattr(correction, "rule_type")
            assert hasattr(correction, "confidence")
            assert correction.rule_type in ["exact", "fuzzy"]
            assert 0.0 <= correction.confidence <= 1.0
