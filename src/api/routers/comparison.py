"""API Endpoints for comparative analysis."""

from typing import List, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth import get_current_user
from src.api.schemas import (
    ComparisonStatsResponse,
    SpeechRecordResponse,
)
from src.models.database import get_db
from src.models.entities import User
from src.services.comparison import ComparisonService
from src.services.storage import StorageService

router = APIRouter(prefix="/api/speech", tags=["comparison"])


@router.post("/process", response_model=SpeechRecordResponse)
async def process_speech(
    language: Literal["ru", "kk"] = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Process audio for comparative analysis.

    Uploads audio, runs it through all configured STT providers,
    and returns comparative metrics.
    """
    if not file.content_type.startswith("audio/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only audio files are allowed.",
        )

    # Read audio content
    content = await file.read()

    storage = StorageService()
    service = ComparisonService(db, storage)

    try:
        record = await service.process_audio(
            user_id=current_user.id,
            audio_content=content,
            language=language,
            content_type=file.content_type,
        )
        return record
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Processing failed: {str(e)}",
        )


@router.get("/history", response_model=List[SpeechRecordResponse])
async def get_history(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get processed speech history for the current user."""
    storage = StorageService()
    service = ComparisonService(db, storage)

    records = await service.get_history(current_user.id, limit, offset)
    return records


@router.get("/metrics", response_model=ComparisonStatsResponse)
async def get_metrics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get aggregated metrics for comparative analysis.

    Returns total records and average confidence/latency per provider.
    Accessible by all users (or could be restricted to admin).
    """
    storage = StorageService()
    service = ComparisonService(db, storage)

    stats = await service.get_metrics_stats()
    return stats
