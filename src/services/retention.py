"""Retention Policy Service for cleaning up old audio files.

Validates: Requirements 10.5
"""

import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.entities import Turn
from src.services.storage import StorageService
from src.config import get_settings

logger = logging.getLogger(__name__)


class RetentionPolicyService:
    """Service for enforcing data retention policies.
    
    Validates: Requirements 10.5
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.storage = StorageService()

    async def cleanup_old_audio(self) -> dict:
        """Delete audio files older than retention period.
        
        Returns:
            Summary of cleanup operation
            
        Validates: Requirements 10.5
        """
        retention_days = self.settings.audio_retention_days
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        # Find turns with old audio
        query = select(Turn).where(
            Turn.timestamp < cutoff_date,
            Turn.audio_input_url.isnot(None),
        )
        
        result = await self.db.execute(query)
        turns = result.scalars().all()
        
        deleted_count = 0
        errors = []
        
        for turn in turns:
            try:
                # Delete input audio
                if turn.audio_input_url:
                    await self.storage.delete_audio(turn.audio_input_url)
                    turn.audio_input_url = None
                
                # Delete output audio
                if turn.audio_output_url:
                    await self.storage.delete_audio(turn.audio_output_url)
                    turn.audio_output_url = None
                
                deleted_count += 1
                
            except Exception as e:
                logger.error(f"Failed to delete audio for turn {turn.id}: {e}")
                errors.append({"turn_id": str(turn.id), "error": str(e)})
        
        await self.db.flush()
        
        return {
            "deleted_count": deleted_count,
            "retention_days": retention_days,
            "cutoff_date": cutoff_date.isoformat(),
            "errors": errors,
        }

    async def get_storage_stats(self) -> dict:
        """Get storage usage statistics.
        
        Returns:
            Storage statistics
        """
        # Count turns with audio
        query_with_audio = select(Turn).where(Turn.audio_input_url.isnot(None))
        result = await self.db.execute(query_with_audio)
        turns_with_audio = len(result.scalars().all())
        
        # Count total turns
        query_total = select(Turn)
        result = await self.db.execute(query_total)
        total_turns = len(result.scalars().all())
        
        return {
            "total_turns": total_turns,
            "turns_with_audio": turns_with_audio,
            "retention_days": self.settings.audio_retention_days,
        }


async def run_retention_cleanup(db: AsyncSession) -> dict:
    """Run retention cleanup as a background task.
    
    Args:
        db: Database session
        
    Returns:
        Cleanup summary
    """
    service = RetentionPolicyService(db)
    return await service.cleanup_old_audio()
