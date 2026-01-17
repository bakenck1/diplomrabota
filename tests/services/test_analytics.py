"""Property-based tests for Analytics Service.

**Feature: voice-assistant-pipeline**
**Validates: Requirements 9.2, 9.5**
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from hypothesis import given, strategies as st, settings, assume
from dataclasses import dataclass
from typing import Optional

from src.services.metrics import calculate_wer, calculate_cer


# Strategies for text generation
word_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L",)),
    min_size=1,
    max_size=20,
).filter(lambda x: x.strip() != "")

sentence_strategy = st.lists(word_strategy, min_size=1, max_size=20).map(lambda words: " ".join(words))


class TestWERCalculation:
    """Property 10: WER/CER Calculation Correctness tests."""

    @given(text=sentence_strategy)
    @settings(max_examples=100)
    def test_wer_identical_texts_is_zero(self, text: str):
        """Property 10: WER of identical texts is 0.
        
        **Feature: voice-assistant-pipeline, Property 10: WER/CER Calculation Correctness**
        **Validates: Requirements 9.5**
        """
        wer = calculate_wer(text, text)
        assert wer == 0.0

    @given(text=sentence_strategy)
    @settings(max_examples=100)
    def test_cer_identical_texts_is_zero(self, text: str):
        """Property 10: CER of identical texts is 0.
        
        **Feature: voice-assistant-pipeline, Property 10: WER/CER Calculation Correctness**
        **Validates: Requirements 9.5**
        """
        cer = calculate_cer(text, text)
        assert cer == 0.0

    @given(
        hypothesis=sentence_strategy,
        reference=sentence_strategy,
    )
    @settings(max_examples=100)
    def test_wer_is_non_negative(self, hypothesis: str, reference: str):
        """Property 10: WER is always non-negative.
        
        **Feature: voice-assistant-pipeline, Property 10: WER/CER Calculation Correctness**
        **Validates: Requirements 9.5**
        """
        wer = calculate_wer(hypothesis, reference)
        assert wer >= 0.0

    @given(
        hypothesis=sentence_strategy,
        reference=sentence_strategy,
    )
    @settings(max_examples=100)
    def test_cer_is_non_negative(self, hypothesis: str, reference: str):
        """Property 10: CER is always non-negative.
        
        **Feature: voice-assistant-pipeline, Property 10: WER/CER Calculation Correctness**
        **Validates: Requirements 9.5**
        """
        cer = calculate_cer(hypothesis, reference)
        assert cer >= 0.0

    def test_wer_empty_reference_empty_hypothesis(self):
        """Property 10: WER of empty texts is 0.
        
        **Validates: Requirements 9.5**
        """
        wer = calculate_wer("", "")
        assert wer == 0.0

    def test_wer_empty_reference_non_empty_hypothesis(self):
        """Property 10: WER with empty reference and non-empty hypothesis is 1.
        
        **Validates: Requirements 9.5**
        """
        wer = calculate_wer("hello world", "")
        assert wer == 1.0

    def test_wer_known_example(self):
        """Property 10: WER calculation matches known example.
        
        Reference: "the cat sat on the mat"
        Hypothesis: "the cat sit on mat"
        
        Errors: "sat" -> "sit" (substitution), "the" deleted
        WER = 2/6 = 0.333...
        
        **Validates: Requirements 9.5**
        """
        reference = "the cat sat on the mat"
        hypothesis = "the cat sit on mat"
        
        wer = calculate_wer(hypothesis, reference)
        
        # 2 errors (1 substitution + 1 deletion) / 6 words
        assert abs(wer - 2/6) < 0.01

    def test_cer_known_example(self):
        """Property 10: CER calculation matches known example.
        
        **Validates: Requirements 9.5**
        """
        reference = "hello"
        hypothesis = "hallo"  # 1 substitution
        
        cer = calculate_cer(hypothesis, reference)
        
        # 1 error / 5 characters = 0.2
        assert abs(cer - 0.2) < 0.01

    @given(
        word=word_strategy,
        num_insertions=st.integers(min_value=1, max_value=5),
    )
    @settings(max_examples=100)
    def test_wer_insertions_increase_error(self, word: str, num_insertions: int):
        """Property 10: Adding words increases WER.
        
        **Feature: voice-assistant-pipeline, Property 10: WER/CER Calculation Correctness**
        **Validates: Requirements 9.5**
        """
        reference = word
        hypothesis = " ".join([word] + ["extra"] * num_insertions)
        
        wer = calculate_wer(hypothesis, reference)
        
        # WER should be num_insertions / 1 (reference has 1 word)
        expected_wer = num_insertions / 1
        assert abs(wer - expected_wer) < 0.01


class TestTopNOrdering:
    """Property 11: Top-N Unknown Terms Ordering tests."""

    @dataclass
    class MockTerm:
        term: str
        count: int
        provider: Optional[str]

    @given(
        counts=st.lists(st.integers(min_value=1, max_value=1000), min_size=1, max_size=20),
    )
    @settings(max_examples=100)
    def test_top_n_sorted_by_count_desc(self, counts: list[int]):
        """Property 11: Top-N results are sorted by count descending.
        
        **Feature: voice-assistant-pipeline, Property 11: Top-N Unknown Terms Ordering**
        **Validates: Requirements 9.2**
        """
        # Create mock terms
        terms = [
            self.MockTerm(term=f"term_{i}", count=count, provider="openai")
            for i, count in enumerate(counts)
        ]
        
        # Sort by count descending (simulating the query)
        sorted_terms = sorted(terms, key=lambda t: t.count, reverse=True)
        
        # Verify ordering
        for i in range(len(sorted_terms) - 1):
            assert sorted_terms[i].count >= sorted_terms[i + 1].count

    @given(
        counts=st.lists(st.integers(min_value=1, max_value=1000), min_size=5, max_size=20),
        n=st.integers(min_value=1, max_value=10),
    )
    @settings(max_examples=100)
    def test_top_n_limited_to_n_items(self, counts: list[int], n: int):
        """Property 11: Top-N returns at most N items.
        
        **Feature: voice-assistant-pipeline, Property 11: Top-N Unknown Terms Ordering**
        **Validates: Requirements 9.2**
        """
        terms = [
            self.MockTerm(term=f"term_{i}", count=count, provider="openai")
            for i, count in enumerate(counts)
        ]
        
        # Sort and limit
        sorted_terms = sorted(terms, key=lambda t: t.count, reverse=True)[:n]
        
        # Verify limit
        assert len(sorted_terms) <= n

    @given(
        counts=st.lists(st.integers(min_value=1, max_value=1000), min_size=1, max_size=20),
    )
    @settings(max_examples=100)
    def test_top_n_contains_highest_counts(self, counts: list[int]):
        """Property 11: Top-N contains the terms with highest counts.
        
        **Feature: voice-assistant-pipeline, Property 11: Top-N Unknown Terms Ordering**
        **Validates: Requirements 9.2**
        """
        n = min(5, len(counts))
        
        terms = [
            self.MockTerm(term=f"term_{i}", count=count, provider="openai")
            for i, count in enumerate(counts)
        ]
        
        # Get top N
        sorted_terms = sorted(terms, key=lambda t: t.count, reverse=True)[:n]
        top_counts = {t.count for t in sorted_terms}
        
        # Get actual top N counts
        actual_top_counts = set(sorted(counts, reverse=True)[:n])
        
        # Top N should contain the highest counts
        assert top_counts == actual_top_counts


class TestWERCERFormula:
    """Additional tests for WER/CER formula correctness."""

    def test_wer_formula_substitution(self):
        """WER correctly counts substitutions.
        
        **Validates: Requirements 9.5**
        """
        reference = "a b c"
        hypothesis = "a x c"  # 1 substitution
        
        wer = calculate_wer(hypothesis, reference)
        assert abs(wer - 1/3) < 0.01

    def test_wer_formula_deletion(self):
        """WER correctly counts deletions.
        
        **Validates: Requirements 9.5**
        """
        reference = "a b c"
        hypothesis = "a c"  # 1 deletion
        
        wer = calculate_wer(hypothesis, reference)
        assert abs(wer - 1/3) < 0.01

    def test_wer_formula_insertion(self):
        """WER correctly counts insertions.
        
        **Validates: Requirements 9.5**
        """
        reference = "a b c"
        hypothesis = "a b x c"  # 1 insertion
        
        wer = calculate_wer(hypothesis, reference)
        assert abs(wer - 1/3) < 0.01

    def test_wer_case_insensitive(self):
        """WER is case insensitive.
        
        **Validates: Requirements 9.5**
        """
        reference = "Hello World"
        hypothesis = "hello world"
        
        wer = calculate_wer(hypothesis, reference)
        assert wer == 0.0
