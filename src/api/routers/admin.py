"""Admin API endpoints.

Validates: Requirements 6.1-6.4, 7.1-7.5, 8.1-8.5
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.auth import get_current_admin
from src.api.schemas import (
    UserResponse,
    UserUpdate,
    ConversationFilter,
    ConversationSummary,
    ConversationDetails,
    TurnResponse,
    UnknownTermResponse,
    UnknownTermCreate,
    UnknownTermApprove,
)
from src.models.database import get_db
from src.models.entities import User, Conversation, Turn
from src.models.entities_ext import UnknownTerm, AuditLog
from src.services.normalization import NormalizationService

router = APIRouter(prefix="/api/admin", tags=["admin"])


# User management endpoints
@router.get("/users", response_model=list[UserResponse])
async def list_users(
    role: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all users with optional role filter.
    
    Validates: Requirements 6.1
    """
    query = select(User)
    if role:
        query = query.where(User.role == role)
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    # Log action
    await _log_action(db, current_admin.id, "list_users", "user", None)
    
    return [UserResponse.model_validate(u) for u in users]


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: uuid.UUID,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get user details.
    
    Validates: Requirements 6.2
    """
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    await _log_action(db, current_admin.id, "view_user", "user", user_id)
    
    return UserResponse.model_validate(user)


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    request: UserUpdate,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update user settings (provider, language).
    
    Validates: Requirements 6.3
    """
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Update fields
    if request.name is not None:
        user.name = request.name
    if request.stt_provider is not None:
        user.stt_provider = request.stt_provider
    if request.tts_provider is not None:
        user.tts_provider = request.tts_provider
    if request.language is not None:
        user.language = request.language
    if request.is_test_user is not None:
        user.is_test_user = request.is_test_user
    
    await db.flush()
    await _log_action(db, current_admin.id, "update_user", "user", user_id, request.model_dump(exclude_none=True))
    
    return UserResponse.model_validate(user)


# Conversation endpoints
@router.get("/conversations", response_model=list[ConversationSummary])
async def list_conversations(
    user_id: Optional[uuid.UUID] = None,
    provider: Optional[str] = None,
    low_confidence: Optional[bool] = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """List conversations with filters.
    
    Validates: Requirements 7.1, 7.4
    """
    query = select(Conversation).options(selectinload(Conversation.user))
    
    if user_id:
        query = query.where(Conversation.user_id == user_id)
    if provider:
        query = query.where(Conversation.stt_provider_used == provider)
    
    query = query.order_by(Conversation.started_at.desc()).offset(offset).limit(limit)
    
    result = await db.execute(query)
    conversations = result.scalars().all()
    
    # Get turn counts
    summaries = []
    for conv in conversations:
        turn_count_query = select(func.count(Turn.id)).where(Turn.conversation_id == conv.id)
        turn_count_result = await db.execute(turn_count_query)
        turn_count = turn_count_result.scalar()
        
        summaries.append(ConversationSummary(
            id=conv.id,
            user_id=conv.user_id,
            user_name=conv.user.name,
            started_at=conv.started_at,
            ended_at=conv.ended_at,
            stt_provider_used=conv.stt_provider_used,
            tts_provider_used=conv.tts_provider_used,
            turn_count=turn_count,
        ))
    
    await _log_action(db, current_admin.id, "list_conversations", "conversation", None)
    
    return summaries


@router.get("/conversations/{conversation_id}", response_model=ConversationDetails)
async def get_conversation(
    conversation_id: uuid.UUID,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get conversation details with all turns.
    
    Validates: Requirements 7.2, 7.3
    """
    query = select(Conversation).where(Conversation.id == conversation_id).options(
        selectinload(Conversation.turns)
    )
    result = await db.execute(query)
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    
    await _log_action(db, current_admin.id, "view_conversation", "conversation", conversation_id)
    
    return ConversationDetails(
        id=conversation.id,
        user_id=conversation.user_id,
        started_at=conversation.started_at,
        ended_at=conversation.ended_at,
        stt_provider_used=conversation.stt_provider_used,
        tts_provider_used=conversation.tts_provider_used,
        turns=[TurnResponse.model_validate(t) for t in sorted(conversation.turns, key=lambda x: x.turn_number)],
    )


# Unknown terms endpoints
@router.get("/unknown-terms", response_model=list[UnknownTermResponse])
async def list_unknown_terms(
    status_filter: Optional[str] = Query(None, alias="status"),
    language: Optional[str] = None,
    provider: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """List unknown terms with filters.
    
    Validates: Requirements 8.1, 8.2
    """
    query = select(UnknownTerm)
    
    if status_filter:
        query = query.where(UnknownTerm.status == status_filter)
    if language:
        query = query.where(UnknownTerm.language == language)
    if provider:
        query = query.where(UnknownTerm.provider_where_seen == provider)
    
    query = query.order_by(UnknownTerm.occurrence_count.desc()).offset(offset).limit(limit)
    
    result = await db.execute(query)
    terms = result.scalars().all()
    
    return [UnknownTermResponse.model_validate(t) for t in terms]


@router.post("/unknown-terms", response_model=UnknownTermResponse)
async def create_unknown_term(
    request: UnknownTermCreate,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new unknown term manually.
    
    Validates: Requirements 8.5
    """
    # Check if term exists
    query = select(UnknownTerm).where(
        UnknownTerm.language == request.language,
        UnknownTerm.heard_variant == request.heard_variant.lower(),
    )
    result = await db.execute(query)
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Term already exists",
        )
    
    term = UnknownTerm(
        id=uuid.uuid4(),
        language=request.language,
        heard_variant=request.heard_variant.lower(),
        correct_form=request.correct_form,
        context_examples=request.context_examples,
        status="approved",  # Manual entries are auto-approved
        approved_by=current_admin.id,
    )
    db.add(term)
    await db.flush()
    
    await _log_action(db, current_admin.id, "create_term", "unknown_term", term.id)
    
    return UnknownTermResponse.model_validate(term)


@router.patch("/unknown-terms/{term_id}/approve", response_model=UnknownTermResponse)
async def approve_term(
    term_id: uuid.UUID,
    request: UnknownTermApprove,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Approve an unknown term.
    
    Validates: Requirements 8.3
    """
    service = NormalizationService(db)
    
    try:
        term = await service.approve_term(term_id, request.correct_form, current_admin.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    
    await _log_action(db, current_admin.id, "approve_term", "unknown_term", term_id)
    
    return UnknownTermResponse.model_validate(term)


@router.patch("/unknown-terms/{term_id}/reject", response_model=UnknownTermResponse)
async def reject_term(
    term_id: uuid.UUID,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Reject an unknown term.
    
    Validates: Requirements 8.4
    """
    service = NormalizationService(db)
    
    try:
        term = await service.reject_term(term_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    
    await _log_action(db, current_admin.id, "reject_term", "unknown_term", term_id)
    
    return UnknownTermResponse.model_validate(term)


# Analytics endpoint
@router.get("/analytics")
async def get_analytics(
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get analytics data for dashboard.
    
    Validates: Requirements 9.1, 9.2, 9.3
    """
    # Get metrics by provider
    metrics = []
    for provider in ["openai", "google"]:
        # Count requests
        count_query = (
            select(func.count(Turn.id))
            .join(Conversation, Turn.conversation_id == Conversation.id)
            .where(Conversation.stt_provider_used == provider)
        )
        count_result = await db.execute(count_query)
        total_requests = count_result.scalar() or 0
        
        if total_requests > 0:
            # Get averages
            avg_query = (
                select(
                    func.avg(Turn.transcript_confidence),
                    func.avg(Turn.stt_latency_ms),
                    func.avg(Turn.tts_latency_ms),
                    func.count(Turn.user_correction),
                )
                .join(Conversation, Turn.conversation_id == Conversation.id)
                .where(Conversation.stt_provider_used == provider)
            )
            avg_result = await db.execute(avg_query)
            row = avg_result.one()
            
            metrics.append({
                "provider": provider,
                "total_requests": total_requests,
                "avg_confidence": float(row[0] or 0),
                "avg_stt_latency_ms": int(row[1] or 0),
                "avg_tts_latency_ms": int(row[2] or 0),
                "correction_rate": (row[3] or 0) / total_requests if total_requests > 0 else 0,
            })
    
    # Get top unknown terms
    terms_query = (
        select(UnknownTerm)
        .where(UnknownTerm.status == "pending")
        .order_by(UnknownTerm.occurrence_count.desc())
        .limit(10)
    )
    terms_result = await db.execute(terms_query)
    terms = terms_result.scalars().all()
    
    top_terms = [{"term": t.heard_variant, "count": t.occurrence_count} for t in terms]
    
    await _log_action(db, current_admin.id, "view_analytics", "analytics", None)
    
    return {"metrics": metrics, "top_unknown_terms": top_terms}


async def _log_action(
    db: AsyncSession,
    user_id: uuid.UUID,
    action: str,
    resource_type: str,
    resource_id: Optional[uuid.UUID],
    details: Optional[dict] = None,
):
    """Log admin action to audit log.
    
    Validates: Requirements 10.4
    """
    log = AuditLog(
        id=uuid.uuid4(),
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
    )
    db.add(log)
    await db.flush()
