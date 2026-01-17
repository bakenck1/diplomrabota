"""Voice API endpoints.

Validates: Requirements 11.1, 11.2, 11.3, 11.4, 11.5
"""

import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth import get_current_user, get_optional_user
from src.api.schemas import (
    SessionCreateRequest,
    SessionResponse,
    TranscribeResponse,
    ConfirmRequest,
    ConfirmResponse,
    RespondRequest,
    RespondResponse,
)
from src.models.database import get_db
from src.models.entities import User
from src.services.voice_session import VoiceSessionService

router = APIRouter(prefix="/api/voice", tags=["voice"])


@router.post("/session", response_model=SessionResponse)
async def create_session(
    request: SessionCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Create a new voice session.
    
    Validates: Requirements 11.1
    """
    service = VoiceSessionService(db)
    
    # Use demo user if not authenticated
    user_id = current_user.id if current_user else "00000000-0000-0000-0000-000000000001"
    
    conversation = await service.create_session(
        user_id=user_id,
        device_info=request.device_info,
    )
    return SessionResponse(session_id=conversation.id)


@router.post("/upload/{session_id}", response_model=TranscribeResponse)
async def upload_and_transcribe(
    session_id: uuid.UUID,
    audio: Annotated[UploadFile, File(description="Audio file (WAV, MP3)")],
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Upload audio and get transcription.
    
    Validates: Requirements 11.2, 11.3
    """
    # Validate file type
    allowed_types = ["audio/wav", "audio/mpeg", "audio/mp3", "audio/webm", "audio/ogg"]
    if audio.content_type and audio.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid audio format. Allowed: {allowed_types}",
        )

    # Read audio content
    audio_content = await audio.read()
    
    if len(audio_content) < 500:  # Reduced minimum
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audio too short.",
        )

    # Use demo user if not authenticated
    user_id = current_user.id if current_user else "00000000-0000-0000-0000-000000000001"

    service = VoiceSessionService(db)
    
    try:
        result = await service.process_audio(
            session_id=str(session_id),
            audio=audio_content,
            user_id=user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    return TranscribeResponse(
        turn_id=result.turn_id,
        raw_transcript=result.raw_transcript,
        normalized_transcript=result.normalized_transcript,
        confidence=result.confidence,
        stt_latency_ms=result.stt_latency_ms,
    )


@router.post("/transcribe/{session_id}", response_model=TranscribeResponse)
async def transcribe(
    session_id: uuid.UUID,
    audio: Annotated[UploadFile, File(description="Audio file")],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Transcribe audio (alias for upload).
    
    Validates: Requirements 11.3
    """
    return await upload_and_transcribe(session_id, audio, current_user, db)


@router.post("/confirm/{session_id}", response_model=ConfirmResponse)
async def confirm_transcript(
    session_id: uuid.UUID,
    request: ConfirmRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Confirm or correct transcript.
    
    Validates: Requirements 11.5
    """
    service = VoiceSessionService(db)
    
    try:
        await service.confirm_transcript(
            session_id=session_id,
            turn_id=request.turn_id,
            confirmed=request.confirmed,
            correction=request.correction,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    return ConfirmResponse(success=True)


@router.post("/respond/{session_id}", response_model=RespondResponse)
async def generate_response(
    session_id: uuid.UUID,
    request: RespondRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Generate TTS response.
    
    Validates: Requirements 11.4
    """
    service = VoiceSessionService(db)
    
    try:
        result = await service.generate_response(
            session_id=session_id,
            turn_id=request.turn_id,
            assistant_text=request.assistant_text,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    return RespondResponse(
        assistant_text=result.assistant_text,
        audio_url=result.audio_url,
        tts_latency_ms=result.tts_latency_ms,
    )


@router.post("/end/{session_id}")
async def end_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """End voice session."""
    service = VoiceSessionService(db)
    await service.end_session(session_id)
    return {"success": True}
