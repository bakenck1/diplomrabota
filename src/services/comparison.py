"""Service for comparative analysis of STT algorithms.

Validates: Requirements 5, 6
"""

import asyncio
import time
import uuid
from datetime import datetime
from typing import List, Literal, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.adapters.stt import get_google_adapter, get_openai_adapter
from src.adapters.stt.base import STTAdapter, STTResult
from src.models.entities import RecognitionMetric, SpeechRecord, User
from src.services.storage import StorageService


class ComparisonService:
    """Service for orchestrating STT comparison."""

    def __init__(self, db: AsyncSession, storage: StorageService):
        self.db = db
        self.storage = storage
        self.adapters: List[STTAdapter] = []
        self._init_adapters()

    def _init_adapters(self):
        """Initialize all available STT adapters."""
        try:
            openai_adapter = get_openai_adapter()()
            self.adapters.append(openai_adapter)
        except Exception as e:
            print(f"Warning: Failed to init OpenAI adapter: {e}")

        try:
            google_adapter = get_google_adapter()()
            self.adapters.append(google_adapter)
        except Exception as e:
            print(f"Warning: Failed to init Google adapter: {e}")

    async def process_audio(
        self,
        user_id: str,
        audio_content: bytes,
        language: Literal["ru", "kk"],
        content_type: str = "audio/wav",
    ) -> SpeechRecord:
        """Process audio with all configured STT providers and save results."""

        # 1. Create SpeechRecord
        record_id = str(uuid.uuid4())

        # 2. Upload audio
        audio_path = await self.storage.upload_research_audio(
            audio_content,
            user_id,
            record_id,
            content_type=content_type
        )
        audio_url = self.storage.generate_signed_url(audio_path)

        # 3. Create initial DB record
        record = SpeechRecord(
            id=record_id,
            user_id=user_id,
            audio_path=audio_path,
            audio_url=audio_url,
            created_at=datetime.utcnow(),
        )
        self.db.add(record)
        await self.db.flush()

        # 4. Run STT in parallel
        results = await asyncio.gather(
            *[self._run_stt(adapter, audio_content, language) for adapter in self.adapters],
            return_exceptions=True
        )

        # 5. Process results
        metrics = []
        primary_transcript = None

        # We need to know which provider is the "primary" one for the User, or just pick one.
        # Since we don't have the user object here, we'll fetch it or just use OpenAI as default primary,
        # or just pick the first successful one.
        # Let's fetch the user to respect their preference if possible, but for comparison it might not matter.
        # Simple approach: If OpenAISTTAdapter is in results, use that. Or just use the first successful one.

        for i, result in enumerate(results):
            adapter = self.adapters[i]
            provider_name = adapter.get_provider_name()

            if isinstance(result, Exception):
                print(f"Error with {provider_name}: {result}")
                # Create a failed metric record? Or just skip?
                # Requirement says "save result", "confidence", "time".
                # If failed, we might want to record it as 0 confidence or error.
                # For now, let's record it with 0 confidence and store error in logs.
                # Or we can create a metric with 0 confidence to show it failed.
                metric = RecognitionMetric(
                    id=str(uuid.uuid4()),
                    speech_record_id=record.id,
                    algorithm_name=provider_name,
                    confidence_score=0.0,
                    processing_time_ms=0,
                )
                metrics.append(metric)
                continue

            # Successful result
            metric = RecognitionMetric(
                id=str(uuid.uuid4()),
                speech_record_id=record.id,
                algorithm_name=provider_name,
                confidence_score=result.confidence,
                processing_time_ms=result.latency_ms,
            )
            metrics.append(metric)

            # Update primary transcript if not set
            if not primary_transcript and result.text:
                primary_transcript = result.text

            # Prefer OpenAI or Google as primary if available (heuristic)
            if result.text and provider_name.lower() == "openai":
                primary_transcript = result.text

        # 6. Update SpeechRecord
        if language == "ru":
            record.recognized_text_ru = primary_transcript
        else:
            record.recognized_text_kz = primary_transcript

        self.db.add_all(metrics)
        await self.db.commit()
        await self.db.refresh(record, attribute_names=["metrics"])

        return record

    async def _run_stt(
        self,
        adapter: STTAdapter,
        audio: bytes,
        language: str
    ) -> STTResult:
        """Run STT with timing."""
        start_time = time.time()
        try:
            result = await adapter.transcribe(audio, language=language)
            # Ensure latency is set
            if result.latency_ms == 0:
                result.latency_ms = int((time.time() - start_time) * 1000)
            return result
        except Exception as e:
            # Re-raise to be caught by gather
            raise e

    async def get_history(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[SpeechRecord]:
        """Get user's speech history."""
        query = (
            select(SpeechRecord)
            .where(SpeechRecord.user_id == user_id)
            .order_by(SpeechRecord.created_at.desc())
            .options(selectinload(SpeechRecord.metrics))
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_metrics_stats(self) -> dict:
        """Get aggregated metrics."""
        # This is a basic aggregation. For production, use SQL aggregation.
        query = select(RecognitionMetric)
        result = await self.db.execute(query)
        metrics = result.scalars().all()

        total_records = len(set(m.speech_record_id for m in metrics))

        provider_stats = {}
        for m in metrics:
            name = m.algorithm_name
            if name not in provider_stats:
                provider_stats[name] = {"confidence_sum": 0.0, "latency_sum": 0, "count": 0}

            provider_stats[name]["confidence_sum"] += float(m.confidence_score)
            provider_stats[name]["latency_sum"] += m.processing_time_ms
            provider_stats[name]["count"] += 1

        avg_confidence = {
            k: v["confidence_sum"] / v["count"] if v["count"] > 0 else 0
            for k, v in provider_stats.items()
        }
        avg_latency = {
            k: v["latency_sum"] / v["count"] if v["count"] > 0 else 0
            for k, v in provider_stats.items()
        }

        return {
            "total_records": total_records,
            "avg_confidence_by_provider": avg_confidence,
            "avg_latency_by_provider": avg_latency,
        }
