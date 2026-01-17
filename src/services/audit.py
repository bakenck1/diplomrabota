"""Audit Log Service for tracking admin actions.

Validates: Requirements 10.4
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.entities_ext import AuditLog


class AuditLogService:
    """Service for logging and querying audit events.
    
    Validates: Requirements 10.4
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_action(
        self,
        user_id: uuid.UUID,
        action: str,
        resource_type: str,
        resource_id: Optional[uuid.UUID] = None,
        details: Optional[dict] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Log an admin action.
        
        Args:
            user_id: ID of user performing action
            action: Action name (e.g., "view_conversation", "approve_term")
            resource_type: Type of resource (e.g., "conversation", "unknown_term")
            resource_id: ID of affected resource
            details: Additional details as JSON
            ip_address: Client IP address
            
        Returns:
            Created AuditLog entry
            
        Validates: Requirements 10.4
        """
        log = AuditLog(
            id=uuid.uuid4(),
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
        )
        self.db.add(log)
        await self.db.flush()
        return log

    async def get_logs(
        self,
        user_id: Optional[uuid.UUID] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        """Query audit logs with filters.
        
        Args:
            user_id: Filter by user
            action: Filter by action type
            resource_type: Filter by resource type
            limit: Max results
            offset: Pagination offset
            
        Returns:
            List of matching AuditLog entries
        """
        query = select(AuditLog)
        
        if user_id:
            query = query.where(AuditLog.user_id == user_id)
        if action:
            query = query.where(AuditLog.action == action)
        if resource_type:
            query = query.where(AuditLog.resource_type == resource_type)
        
        query = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_logs_for_resource(
        self,
        resource_type: str,
        resource_id: uuid.UUID,
    ) -> list[AuditLog]:
        """Get all audit logs for a specific resource.
        
        Args:
            resource_type: Type of resource
            resource_id: Resource ID
            
        Returns:
            List of AuditLog entries for this resource
        """
        query = (
            select(AuditLog)
            .where(
                AuditLog.resource_type == resource_type,
                AuditLog.resource_id == resource_id,
            )
            .order_by(AuditLog.created_at.desc())
        )
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
