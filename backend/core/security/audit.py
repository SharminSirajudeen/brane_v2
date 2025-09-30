"""
Audit Logging - HIPAA/GDPR Compliant
Immutable logs with cryptographic signatures
"""

import hashlib
import hmac
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import logging

from db.models import AuditLog
from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def compute_signature(event_data: dict) -> str:
    """
    Compute SHA-256 HMAC signature for audit log entry.
    This ensures log immutability - any tampering will be detected.
    """
    # Create canonical string from event data
    canonical = (
        f"{event_data['timestamp']}|"
        f"{event_data['event_type']}|"
        f"{event_data['action']}|"
        f"{event_data['user_id']}|"
        f"{event_data['result']}"
    )

    # Compute HMAC
    signature = hmac.new(
        settings.ENCRYPTION_KEY.encode(),
        canonical.encode(),
        hashlib.sha256
    ).hexdigest()

    return signature


async def log_audit_event(
    db: AsyncSession,
    event_type: str,
    action: str,
    result: str,
    user_id: Optional[str] = None,
    neuron_id: Optional[str] = None,
    resource: Optional[str] = None,
    details: Optional[dict] = None,
    error_message: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> AuditLog:
    """
    Create immutable audit log entry.

    Args:
        event_type: Category (auth, chat, config_change, data_access, etc.)
        action: Specific action (login, send_message, update_neuron, etc.)
        result: Outcome (success, failure)
        user_id: User who performed action
        neuron_id: Neuron involved (if applicable)
        resource: Resource affected (document_id, config_id, etc.)
        details: Additional context (JSON)
        error_message: Error details (if result=failure)
        ip_address: Client IP
        user_agent: Client user agent

    Returns:
        Created AuditLog instance
    """
    from datetime import datetime

    timestamp = datetime.utcnow()

    # Prepare event data for signature
    event_data = {
        "timestamp": timestamp.isoformat(),
        "event_type": event_type,
        "action": action,
        "user_id": user_id or "system",
        "result": result
    }

    # Compute cryptographic signature
    signature = compute_signature(event_data)

    # Create audit log entry
    audit_log = AuditLog(
        user_id=user_id,
        neuron_id=neuron_id,
        event_type=event_type,
        action=action,
        resource=resource,
        result=result,
        error_message=error_message,
        details=details or {},
        ip_address=ip_address,
        user_agent=user_agent,
        signature=signature,
        timestamp=timestamp
    )

    db.add(audit_log)
    await db.commit()
    await db.refresh(audit_log)

    logger.info(f"Audit log: {event_type}/{action} - {result}")

    return audit_log


async def verify_audit_log(audit_log: AuditLog) -> bool:
    """
    Verify audit log entry hasn't been tampered with.

    Returns:
        True if signature is valid, False otherwise
    """
    event_data = {
        "timestamp": audit_log.timestamp.isoformat(),
        "event_type": audit_log.event_type,
        "action": audit_log.action,
        "user_id": audit_log.user_id or "system",
        "result": audit_log.result
    }

    expected_signature = compute_signature(event_data)
    return hmac.compare_digest(expected_signature, audit_log.signature)
