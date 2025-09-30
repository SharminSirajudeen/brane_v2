"""Admin API - User management and audit logs"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import logging

from db.database import get_db_session
from db.models import User, AuditLog, UserRole
from api.auth import get_current_user, require_role

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/users")
async def list_users(
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db_session)
):
    """List all users (admin only)"""
    result = await db.execute(select(User))
    users = result.scalars().all()

    return [
        {
            "id": u.id,
            "email": u.email,
            "name": u.name,
            "role": u.role.value,
            "created_at": u.created_at.isoformat()
        }
        for u in users
    ]


@router.get("/audit-logs")
async def list_audit_logs(
    limit: int = 100,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """List audit logs"""
    # Allow users to see their own logs, admins see all
    if user.role == UserRole.ADMIN:
        result = await db.execute(
            select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit)
        )
    else:
        result = await db.execute(
            select(AuditLog)
            .where(AuditLog.user_id == user.id)
            .order_by(AuditLog.timestamp.desc())
            .limit(limit)
        )

    logs = result.scalars().all()

    return [
        {
            "id": log.id,
            "event_type": log.event_type,
            "action": log.action,
            "result": log.result,
            "timestamp": log.timestamp.isoformat()
        }
        for log in logs
    ]
