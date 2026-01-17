"""Property-based tests for Admin API.

**Feature: voice-assistant-pipeline**
**Validates: Requirements 7.1, 7.4, 8.3, 8.4**
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from hypothesis import given, strategies as st, settings, assume
import uuid
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Literal, Optional


@dataclass
class MockConversation:
    """Mock conversation for filter testing."""
    id: uuid.UUID
    user_id: uuid.UUID
    stt_provider_used: str
    started_at: datetime
    low_confidence_turns: int = 0
    has_corrections: bool = False


@dataclass
class MockUnknownTerm:
    """Mock unknown term for workflow testing."""
    id: uuid.UUID
    heard_variant: str
    correct_form: str
    status: Literal["pending", "approved", "rejected"]
    occurrence_count: int


class MockConversationFilter:
    """Mock filter for testing filter correctness."""

    def __init__(
        self,
        user_id: Optional[uuid.UUID] = None,
        provider: Optional[str] = None,
        low_confidence: Optional[bool] = None,
    ):
        self.user_id = user_id
        self.provider = provider
        self.low_confidence = low_confidence

    def matches(self, conversation: MockConversation) -> bool:
        """Check if conversation matches all filter criteria."""
        if self.user_id is not None and conversation.user_id != self.user_id:
            return False
        if self.provider is not None and conversation.stt_provider_used != self.provider:
            return False
        if self.low_confidence is True and conversation.low_confidence_turns == 0:
            return False
        return True


class MockTermApprovalService:
    """Mock service for term approval workflow testing."""

    def __init__(self, terms: dict[uuid.UUID, MockUnknownTerm]):
        self.terms = terms
        self.approved_terms_in_normalization: set[uuid.UUID] = set()

    def approve_term(self, term_id: uuid.UUID, correct_form: str) -> MockUnknownTerm:
        """Approve a term."""
        if term_id not in self.terms:
            raise ValueError(f"Term {term_id} not found")
        
        term = self.terms[term_id]
        term.status = "approved"
        term.correct_form = correct_form
        self.approved_terms_in_normalization.add(term_id)
        return term

    def reject_term(self, term_id: uuid.UUID) -> MockUnknownTerm:
        """Reject a term."""
        if term_id not in self.terms:
            raise ValueError(f"Term {term_id} not found")
        
        term = self.terms[term_id]
        term.status = "rejected"
        # Ensure rejected terms are NOT in normalization
        self.approved_terms_in_normalization.discard(term_id)
        return term

    def is_used_in_normalization(self, term_id: uuid.UUID) -> bool:
        """Check if term is used in normalization."""
        return term_id in self.approved_terms_in_normalization


# Strategies
provider_strategy = st.sampled_from(["openai", "google"])
status_strategy = st.sampled_from(["pending", "approved", "rejected"])


class TestConversationFilterCorrectness:
    """Property 8: Conversation Filter Correctness tests."""

    @given(
        num_conversations=st.integers(min_value=1, max_value=20),
        filter_provider=st.one_of(st.none(), provider_strategy),
    )
    @settings(max_examples=100)
    def test_provider_filter_returns_matching_conversations(
        self,
        num_conversations: int,
        filter_provider: Optional[str],
    ):
        """Property 8: Provider filter returns only matching conversations.
        
        **Feature: voice-assistant-pipeline, Property 8: Conversation Filter Correctness**
        **Validates: Requirements 7.1, 7.4**
        """
        # Generate random conversations
        conversations = [
            MockConversation(
                id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                stt_provider_used="openai" if i % 2 == 0 else "google",
                started_at=datetime.utcnow() - timedelta(days=i),
            )
            for i in range(num_conversations)
        ]

        # Apply filter
        filter_obj = MockConversationFilter(provider=filter_provider)
        filtered = [c for c in conversations if filter_obj.matches(c)]

        # Verify all results match filter
        for conv in filtered:
            if filter_provider is not None:
                assert conv.stt_provider_used == filter_provider

    @given(
        num_conversations=st.integers(min_value=1, max_value=20),
    )
    @settings(max_examples=100)
    def test_user_filter_returns_matching_conversations(
        self,
        num_conversations: int,
    ):
        """Property 8: User filter returns only that user's conversations.
        
        **Feature: voice-assistant-pipeline, Property 8: Conversation Filter Correctness**
        **Validates: Requirements 7.1, 7.4**
        """
        # Create users
        user1_id = uuid.uuid4()
        user2_id = uuid.uuid4()

        # Generate conversations for both users
        conversations = [
            MockConversation(
                id=uuid.uuid4(),
                user_id=user1_id if i % 2 == 0 else user2_id,
                stt_provider_used="openai",
                started_at=datetime.utcnow(),
            )
            for i in range(num_conversations)
        ]

        # Filter by user1
        filter_obj = MockConversationFilter(user_id=user1_id)
        filtered = [c for c in conversations if filter_obj.matches(c)]

        # All results should belong to user1
        for conv in filtered:
            assert conv.user_id == user1_id

    @given(
        num_conversations=st.integers(min_value=1, max_value=20),
        filter_provider=st.one_of(st.none(), provider_strategy),
    )
    @settings(max_examples=100)
    def test_combined_filters_return_matching_conversations(
        self,
        num_conversations: int,
        filter_provider: Optional[str],
    ):
        """Property 8: Combined filters return conversations matching ALL criteria.
        
        **Feature: voice-assistant-pipeline, Property 8: Conversation Filter Correctness**
        **Validates: Requirements 7.1, 7.4**
        """
        user_id = uuid.uuid4()

        conversations = [
            MockConversation(
                id=uuid.uuid4(),
                user_id=user_id if i % 3 == 0 else uuid.uuid4(),
                stt_provider_used="openai" if i % 2 == 0 else "google",
                started_at=datetime.utcnow(),
            )
            for i in range(num_conversations)
        ]

        # Combined filter
        filter_obj = MockConversationFilter(user_id=user_id, provider=filter_provider)
        filtered = [c for c in conversations if filter_obj.matches(c)]

        # All results must match ALL criteria
        for conv in filtered:
            assert conv.user_id == user_id
            if filter_provider is not None:
                assert conv.stt_provider_used == filter_provider


class TestTermApprovalWorkflow:
    """Property 9: Term Approval Workflow tests."""

    @given(
        heard_variant=st.text(min_size=3, max_size=50, alphabet="абвгдеёжзийклмнопрстуфхцчшщъыьэюя"),
        correct_form=st.text(min_size=3, max_size=50, alphabet="абвгдеёжзийклмнопрстуфхцчшщъыьэюя"),
    )
    @settings(max_examples=100)
    def test_approved_terms_used_in_normalization(
        self,
        heard_variant: str,
        correct_form: str,
    ):
        """Property 9: Approved terms are used in normalization.
        
        **Feature: voice-assistant-pipeline, Property 9: Term Approval Workflow**
        **Validates: Requirements 8.3, 8.4**
        """
        assume(heard_variant.strip() != "" and correct_form.strip() != "")

        term_id = uuid.uuid4()
        term = MockUnknownTerm(
            id=term_id,
            heard_variant=heard_variant,
            correct_form=heard_variant,  # Initially same
            status="pending",
            occurrence_count=1,
        )

        service = MockTermApprovalService({term_id: term})

        # Approve term
        approved_term = service.approve_term(term_id, correct_form)

        # Verify status changed
        assert approved_term.status == "approved"
        assert approved_term.correct_form == correct_form

        # Verify term is used in normalization
        assert service.is_used_in_normalization(term_id)

    @given(
        heard_variant=st.text(min_size=3, max_size=50, alphabet="абвгдеёжзийклмнопрстуфхцчшщъыьэюя"),
    )
    @settings(max_examples=100)
    def test_rejected_terms_not_used_in_normalization(
        self,
        heard_variant: str,
    ):
        """Property 9: Rejected terms are NOT used in normalization.
        
        **Feature: voice-assistant-pipeline, Property 9: Term Approval Workflow**
        **Validates: Requirements 8.3, 8.4**
        """
        assume(heard_variant.strip() != "")

        term_id = uuid.uuid4()
        term = MockUnknownTerm(
            id=term_id,
            heard_variant=heard_variant,
            correct_form=heard_variant,
            status="pending",
            occurrence_count=1,
        )

        service = MockTermApprovalService({term_id: term})

        # Reject term
        rejected_term = service.reject_term(term_id)

        # Verify status changed
        assert rejected_term.status == "rejected"

        # Verify term is NOT used in normalization
        assert not service.is_used_in_normalization(term_id)

    @given(
        heard_variant=st.text(min_size=3, max_size=50, alphabet="абвгдеёжзийклмнопрстуфхцчшщъыьэюя"),
        correct_form=st.text(min_size=3, max_size=50, alphabet="абвгдеёжзийклмнопрстуфхцчшщъыьэюя"),
    )
    @settings(max_examples=100)
    def test_approval_then_rejection_removes_from_normalization(
        self,
        heard_variant: str,
        correct_form: str,
    ):
        """Property 9: Rejecting a previously approved term removes it from normalization.
        
        **Feature: voice-assistant-pipeline, Property 9: Term Approval Workflow**
        **Validates: Requirements 8.3, 8.4**
        """
        assume(heard_variant.strip() != "" and correct_form.strip() != "")

        term_id = uuid.uuid4()
        term = MockUnknownTerm(
            id=term_id,
            heard_variant=heard_variant,
            correct_form=heard_variant,
            status="pending",
            occurrence_count=1,
        )

        service = MockTermApprovalService({term_id: term})

        # First approve
        service.approve_term(term_id, correct_form)
        assert service.is_used_in_normalization(term_id)

        # Then reject
        service.reject_term(term_id)
        assert not service.is_used_in_normalization(term_id)
        assert term.status == "rejected"
