"""Normalization Service for improving STT transcripts.

Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5
"""

import uuid
from dataclasses import dataclass, field
from typing import Literal, Optional

from Levenshtein import distance as levenshtein_distance
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.entities_ext import UnknownTerm
from src.config import get_settings


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


class NormalizationService:
    """Service for normalizing STT transcripts using dictionary corrections.
    
    Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5
    """

    def __init__(self, db: AsyncSession):
        """Initialize normalization service.
        
        Args:
            db: Database session for loading dictionary
        """
        self.db = db
        self.settings = get_settings()
        self._dictionary: dict[str, dict] = {}  # heard_variant -> {correct_form, ...}
        self._dictionary_loaded = False

    async def load_dictionary(self, language: Literal["ru", "kk"] = "ru") -> None:
        """Load approved terms from database into memory.
        
        Args:
            language: Language to load dictionary for
        """
        query = select(UnknownTerm).where(
            UnknownTerm.status == "approved",
            UnknownTerm.language == language,
        )
        result = await self.db.execute(query)
        terms = result.scalars().all()

        self._dictionary = {}
        for term in terms:
            self._dictionary[term.heard_variant.lower()] = {
                "correct_form": term.correct_form,
                "id": term.id,
            }
        
        self._dictionary_loaded = True

    async def normalize(
        self,
        text: str,
        language: Literal["ru", "kk"] = "ru",
        stt_confidence: float = 1.0,
        context: Optional[str] = None,
    ) -> NormalizationResult:
        """Normalize transcript using dictionary corrections.
        
        Args:
            text: Raw transcript text
            language: Language code
            stt_confidence: STT confidence score (0-1)
            context: Optional context for better matching
            
        Returns:
            NormalizationResult with raw and normalized text
            
        Validates: Requirements 4.1, 4.2, 4.3
        """
        if not self._dictionary_loaded:
            await self.load_dictionary(language)

        raw_transcript = text
        corrections: list[Correction] = []
        unknown_terms_created: list[str] = []

        # Split into words
        words = text.split()
        normalized_words = []

        confidence_threshold = self.settings.normalization_confidence_threshold
        fuzzy_max_distance = self.settings.normalization_fuzzy_max_distance

        for word in words:
            word_lower = word.lower()
            corrected_word = word
            correction_applied = False

            # Try exact match first (always applied)
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
                correction_applied = True

            # Try fuzzy match if confidence is low
            elif stt_confidence < confidence_threshold:
                best_match = self._find_fuzzy_match(word_lower, fuzzy_max_distance)
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
                    correction_applied = True
                else:
                    # Create pending unknown term
                    if len(word) >= 3:  # Only for words with 3+ chars
                        unknown_terms_created.append(word)

            normalized_words.append(corrected_word)

        normalized_transcript = " ".join(normalized_words)

        return NormalizationResult(
            raw_transcript=raw_transcript,
            normalized_transcript=normalized_transcript,
            corrections=corrections,
            unknown_terms_created=unknown_terms_created,
        )

    def _find_fuzzy_match(
        self, word: str, max_distance: int
    ) -> Optional[dict]:
        """Find best fuzzy match in dictionary.
        
        Args:
            word: Word to match
            max_distance: Maximum Levenshtein distance
            
        Returns:
            Match info or None
        """
        best_match = None
        best_distance = max_distance + 1

        for heard_variant, term_info in self._dictionary.items():
            dist = levenshtein_distance(word, heard_variant)
            if dist <= max_distance and dist < best_distance:
                best_distance = dist
                # Confidence decreases with distance
                confidence = 1.0 - (dist / (max_distance + 1))
                best_match = {
                    "correct_form": term_info["correct_form"],
                    "confidence": confidence,
                    "distance": dist,
                }

        return best_match

    async def create_pending_term(
        self,
        heard_variant: str,
        language: Literal["ru", "kk"],
        context: Optional[str] = None,
        provider: Optional[str] = None,
    ) -> UnknownTerm:
        """Create a new pending unknown term.
        
        Args:
            heard_variant: The word as heard by STT
            language: Language code
            context: Optional context (surrounding words)
            provider: STT provider that produced this
            
        Returns:
            Created UnknownTerm
            
        Validates: Requirements 4.5
        """
        # Check if term already exists
        query = select(UnknownTerm).where(
            UnknownTerm.language == language,
            UnknownTerm.heard_variant == heard_variant.lower(),
        )
        result = await self.db.execute(query)
        existing = result.scalar_one_or_none()

        if existing:
            # Increment count
            existing.occurrence_count += 1
            if context and context not in existing.context_examples:
                existing.context_examples = existing.context_examples + [context]
            await self.db.flush()
            return existing

        # Create new term
        term = UnknownTerm(
            id=uuid.uuid4(),
            language=language,
            heard_variant=heard_variant.lower(),
            correct_form=heard_variant,  # Default to same as heard
            context_examples=[context] if context else [],
            provider_where_seen=provider,
            occurrence_count=1,
            status="pending",
        )
        self.db.add(term)
        await self.db.flush()
        return term

    async def approve_term(
        self,
        term_id: uuid.UUID,
        correct_form: str,
        approved_by: uuid.UUID,
    ) -> UnknownTerm:
        """Approve an unknown term with correct form.
        
        Args:
            term_id: Term ID to approve
            correct_form: The correct spelling/form
            approved_by: User ID who approved
            
        Returns:
            Updated UnknownTerm
            
        Validates: Requirements 8.3
        """
        query = select(UnknownTerm).where(UnknownTerm.id == term_id)
        result = await self.db.execute(query)
        term = result.scalar_one_or_none()

        if not term:
            raise ValueError(f"Term {term_id} not found")

        term.correct_form = correct_form
        term.status = "approved"
        term.approved_by = approved_by
        await self.db.flush()

        # Reload dictionary to include new term
        self._dictionary_loaded = False

        return term

    async def reject_term(self, term_id: uuid.UUID) -> UnknownTerm:
        """Reject an unknown term.
        
        Args:
            term_id: Term ID to reject
            
        Returns:
            Updated UnknownTerm
            
        Validates: Requirements 8.4
        """
        query = select(UnknownTerm).where(UnknownTerm.id == term_id)
        result = await self.db.execute(query)
        term = result.scalar_one_or_none()

        if not term:
            raise ValueError(f"Term {term_id} not found")

        term.status = "rejected"
        await self.db.flush()

        return term
