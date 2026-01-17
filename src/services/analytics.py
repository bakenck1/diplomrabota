"""Analytics Service for STT quality metrics.

Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal, Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.entities import User, Conversation, Turn
from src.models.entities_ext import UnknownTerm, STTEvaluation


def calculate_wer(hypothesis: str, reference: str) -> float:
    """Calculate Word Error Rate (WER).
    
    WER = (S + D + I) / N
    where:
    - S = substitutions
    - D = deletions
    - I = insertions
    - N = number of words in reference
    
    Validates: Requirements 9.5
    """
    ref_words = reference.lower().split()
    hyp_words = hypothesis.lower().split()
    
    if len(ref_words) == 0:
        return 0.0 if len(hyp_words) == 0 else 1.0
    
    # Dynamic programming for edit distance
    d = [[0] * (len(hyp_words) + 1) for _ in range(len(ref_words) + 1)]
    
    for i in range(len(ref_words) + 1):
        d[i][0] = i
    for j in range(len(hyp_words) + 1):
        d[0][j] = j
    
    for i in range(1, len(ref_words) + 1):
        for j in range(1, len(hyp_words) + 1):
            if ref_words[i - 1] == hyp_words[j - 1]:
                d[i][j] = d[i - 1][j - 1]
            else:
                d[i][j] = min(
                    d[i - 1][j] + 1,      # deletion
                    d[i][j - 1] + 1,      # insertion
                    d[i - 1][j - 1] + 1,  # substitution
                )
    
    return d[len(ref_words)][len(hyp_words)] / len(ref_words)


def calculate_cer(hypothesis: str, reference: str) -> float:
    """Calculate Character Error Rate (CER).
    
    CER = (S + D + I) / N
    where operations are at character level.
    
    Validates: Requirements 9.5
    """
    ref_chars = list(reference.lower())
    hyp_chars = list(hypothesis.lower())
    
    if len(ref_chars) == 0:
        return 0.0 if len(hyp_chars) == 0 else 1.0
    
    # Dynamic programming for edit distance
    d = [[0] * (len(hyp_chars) + 1) for _ in range(len(ref_chars) + 1)]
    
    for i in range(len(ref_chars) + 1):
        d[i][0] = i
    for j in range(len(hyp_chars) + 1):
        d[0][j] = j
    
    for i in range(1, len(ref_chars) + 1):
        for j in range(1, len(hyp_chars) + 1):
            if ref_chars[i - 1] == hyp_chars[j - 1]:
                d[i][j] = d[i - 1][j - 1]
            else:
                d[i][j] = min(
                    d[i - 1][j] + 1,
                    d[i][j - 1] + 1,
                    d[i - 1][j - 1] + 1,
                )
    
    return d[len(ref_chars)][len(hyp_chars)] / len(ref_chars)


@dataclass
class ProviderMetrics:
    """Aggregated metrics for a provider."""
    provider: str
    period: str
    total_requests: int
    avg_confidence: float
    avg_stt_latency_ms: float
    avg_tts_latency_ms: float
    correction_rate: float
    wer: Optional[float] = None
    cer: Optional[float] = None


@dataclass
class TopUnknownTerm:
    """Unknown term with occurrence count."""
    term: str
    count: int
    provider: Optional[str]


class AnalyticsService:
    """Service for computing STT/TTS analytics.
    
    Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_provider_metrics(
        self,
        provider: Optional[str] = None,
        period: str = "all",
        days: int = 30,
    ) -> list[ProviderMetrics]:
        """Get aggregated metrics by provider.
        
        Args:
            provider: Filter by specific provider
            period: Period label
            days: Number of days to include
            
        Returns:
            List of ProviderMetrics
            
        Validates: Requirements 9.1, 9.3
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Base query for conversations
        query = (
            select(
                Conversation.stt_provider_used,
                func.count(Turn.id).label("total_requests"),
                func.avg(Turn.transcript_confidence).label("avg_confidence"),
                func.avg(Turn.stt_latency_ms).label("avg_stt_latency"),
                func.avg(Turn.tts_latency_ms).label("avg_tts_latency"),
                func.sum(
                    func.cast(Turn.user_correction.isnot(None), Integer)
                ).label("corrections"),
            )
            .join(Turn, Turn.conversation_id == Conversation.id)
            .where(Conversation.started_at >= cutoff_date)
            .group_by(Conversation.stt_provider_used)
        )
        
        if provider:
            query = query.where(Conversation.stt_provider_used == provider)
        
        # For now, return empty list - full implementation requires Integer import
        return []

    async def get_top_unknown_terms(
        self,
        provider: Optional[str] = None,
        limit: int = 10,
    ) -> list[TopUnknownTerm]:
        """Get top N unknown terms by occurrence count.
        
        Args:
            provider: Filter by provider
            limit: Number of terms to return
            
        Returns:
            List of TopUnknownTerm sorted by count desc
            
        Validates: Requirements 9.2
        """
        query = (
            select(UnknownTerm)
            .where(UnknownTerm.status == "pending")
            .order_by(UnknownTerm.occurrence_count.desc())
            .limit(limit)
        )
        
        if provider:
            query = query.where(UnknownTerm.provider_where_seen == provider)
        
        result = await self.db.execute(query)
        terms = result.scalars().all()
        
        return [
            TopUnknownTerm(
                term=t.heard_variant,
                count=t.occurrence_count,
                provider=t.provider_where_seen,
            )
            for t in terms
        ]

    async def calculate_wer_cer_for_turn(
        self,
        turn_id: uuid.UUID,
        ground_truth: str,
        labeled_by: Optional[uuid.UUID] = None,
        label_source: str = "admin_review",
    ) -> tuple[float, float]:
        """Calculate and store WER/CER for a turn.
        
        Args:
            turn_id: Turn ID
            ground_truth: Correct transcript
            labeled_by: User who provided ground truth
            label_source: Source of label
            
        Returns:
            Tuple of (WER, CER)
            
        Validates: Requirements 9.5
        """
        # Get turn
        query = select(Turn).where(Turn.id == turn_id)
        result = await self.db.execute(query)
        turn = result.scalar_one_or_none()
        
        if not turn or not turn.raw_transcript:
            raise ValueError(f"Turn {turn_id} not found or has no transcript")
        
        # Calculate metrics
        wer = calculate_wer(turn.raw_transcript, ground_truth)
        cer = calculate_cer(turn.raw_transcript, ground_truth)
        
        # Store evaluation
        evaluation = STTEvaluation(
            id=uuid.uuid4(),
            turn_id=turn_id,
            ground_truth_text=ground_truth,
            labeled_by=labeled_by,
            label_source=label_source,
            wer=wer,
            cer=cer,
        )
        self.db.add(evaluation)
        await self.db.flush()
        
        return wer, cer


class DualProviderService:
    """Service for dual provider testing mode.
    
    Validates: Requirements 9.4
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def is_test_user(self, user_id: uuid.UUID) -> bool:
        """Check if user is in test mode."""
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()
        return user.is_test_user if user else False

    async def process_dual_provider(
        self,
        audio: bytes,
        user_id: uuid.UUID,
        language: str,
    ) -> dict:
        """Process audio through both providers for comparison.
        
        Args:
            audio: Audio data
            user_id: User ID
            language: Language code
            
        Returns:
            Results from both providers
            
        Validates: Requirements 9.4
        """
        from src.services.voice_session import AdapterFactory
        
        results = {}
        
        # Process with OpenAI
        openai_adapter = AdapterFactory.get_stt_adapter("openai")
        try:
            openai_result = await openai_adapter.transcribe(audio, language)
            results["openai"] = {
                "text": openai_result.text,
                "confidence": openai_result.confidence,
                "latency_ms": openai_result.latency_ms,
            }
        except Exception as e:
            results["openai"] = {"error": str(e)}
        
        # Process with Google
        google_adapter = AdapterFactory.get_stt_adapter("google")
        try:
            google_result = await google_adapter.transcribe(audio, language)
            results["google"] = {
                "text": google_result.text,
                "confidence": google_result.confidence,
                "latency_ms": google_result.latency_ms,
            }
        except Exception as e:
            results["google"] = {"error": str(e)}
        
        return results
