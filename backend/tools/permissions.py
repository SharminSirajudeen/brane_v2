"""
Permission management for BRANE tools
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from enum import Enum
import json
import hashlib
from pathlib import Path

from pydantic import BaseModel
import jwt


class PermissionScope(Enum):
    """Permission scopes"""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    DELETE = "delete"
    ADMIN = "admin"


class PermissionStatus(Enum):
    """Permission status"""
    PENDING = "pending"
    GRANTED = "granted"
    DENIED = "denied"
    REVOKED = "revoked"
    EXPIRED = "expired"


@dataclass
class ToolPermission:
    """Tool access permission"""
    # Identifiers
    permission_id: str
    tool_id: str
    neuron_id: str
    user_id: str

    # Scope
    allowed_actions: List[PermissionScope]
    resource_patterns: List[str]  # Glob patterns for resource access

    # Time constraints
    granted_at: datetime
    expires_at: Optional[datetime]

    # Security settings
    sandbox_level: int = 2  # 0=none, 1=light, 2=strict
    requires_2fa: bool = False
    requires_user_confirmation: bool = False

    # Usage limits
    max_calls_per_day: int = 1000
    max_data_gb: float = 1.0
    current_usage_calls: int = 0
    current_usage_gb: float = 0.0

    # Audit
    audit_level: str = "full"  # none, basic, full
    status: PermissionStatus = PermissionStatus.GRANTED

    def is_valid(self) -> bool:
        """Check if permission is still valid"""
        if self.status != PermissionStatus.GRANTED:
            return False

        if self.expires_at and datetime.now() > self.expires_at:
            return False

        if self.current_usage_calls >= self.max_calls_per_day:
            return False

        if self.current_usage_gb >= self.max_data_gb:
            return False

        return True

    def allows_action(self, action: str) -> bool:
        """Check if permission allows specific action"""
        try:
            scope = PermissionScope(action)
            return scope in self.allowed_actions
        except ValueError:
            return False

    def allows_resource(self, resource: str) -> bool:
        """Check if permission allows access to resource"""
        from fnmatch import fnmatch

        for pattern in self.resource_patterns:
            if fnmatch(resource, pattern):
                return True
        return False

    def to_token(self, secret: str) -> str:
        """Generate JWT token for this permission"""
        payload = {
            "permission_id": self.permission_id,
            "tool_id": self.tool_id,
            "neuron_id": self.neuron_id,
            "user_id": self.user_id,
            "actions": [a.value for a in self.allowed_actions],
            "resources": self.resource_patterns,
            "exp": self.expires_at.isoformat() if self.expires_at else None
        }
        return jwt.encode(payload, secret, algorithm="HS256")


class PermissionRequest(BaseModel):
    """Request for tool permission"""
    neuron_id: str
    neuron_name: str
    tool_id: str
    tool_name: str
    tool_description: str
    requested_actions: List[str]
    resource_patterns: List[str]
    reason: Optional[str] = None
    duration_hours: int = 24
    risk_level: str = "medium"
    examples: List[str] = []


class PermissionManager:
    """Manages tool permissions for neurons"""

    def __init__(self, db_connection, secret_key: str):
        self.db = db_connection
        self.secret_key = secret_key
        self.pending_requests = {}

    async def request_permission(self,
                                 request: PermissionRequest,
                                 user_id: str) -> Optional[ToolPermission]:
        """Request permission from user"""

        # Generate permission ID
        permission_id = self._generate_permission_id(request)

        # Store pending request
        self.pending_requests[permission_id] = {
            "request": request,
            "user_id": user_id,
            "timestamp": datetime.now()
        }

        # Send notification to user (webhook, websocket, etc.)
        await self._notify_user(user_id, permission_id, request)

        # Wait for user response (with timeout)
        response = await self._wait_for_response(permission_id, timeout=300)

        if response and response["approved"]:
            permission = await self.create_permission(
                permission_id,
                request,
                user_id,
                response.get("modifications", {})
            )
            return permission

        return None

    async def create_permission(self,
                               permission_id: str,
                               request: PermissionRequest,
                               user_id: str,
                               modifications: Dict = None) -> ToolPermission:
        """Create a new permission"""

        # Apply any user modifications
        if modifications:
            if "duration_hours" in modifications:
                request.duration_hours = modifications["duration_hours"]
            if "resource_patterns" in modifications:
                request.resource_patterns = modifications["resource_patterns"]

        # Create permission object
        permission = ToolPermission(
            permission_id=permission_id,
            tool_id=request.tool_id,
            neuron_id=request.neuron_id,
            user_id=user_id,
            allowed_actions=[PermissionScope(a) for a in request.requested_actions],
            resource_patterns=request.resource_patterns,
            granted_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=request.duration_hours),
            requires_user_confirmation=(request.risk_level == "high"),
            sandbox_level=self._get_sandbox_level(request.risk_level)
        )

        # Store in database
        await self._store_permission(permission)

        # Log the grant
        await self._audit_log("permission_granted", permission)

        return permission

    async def verify_permission(self,
                               neuron_id: str,
                               tool_id: str,
                               action: str,
                               resource: str = None) -> bool:
        """Verify if neuron has permission for action"""

        # Get permission from database
        permission = await self._get_permission(neuron_id, tool_id)

        if not permission:
            return False

        if not permission.is_valid():
            return False

        if not permission.allows_action(action):
            return False

        if resource and not permission.allows_resource(resource):
            return False

        # Update usage counters
        await self._update_usage(permission)

        return True

    async def revoke_permission(self,
                               permission_id: str,
                               reason: str = None):
        """Revoke a permission"""

        permission = await self._get_permission_by_id(permission_id)
        if permission:
            permission.status = PermissionStatus.REVOKED
            await self._update_permission(permission)
            await self._audit_log("permission_revoked", {
                "permission_id": permission_id,
                "reason": reason
            })

    def verify_token(self, token: str) -> Optional[Dict]:
        """Verify permission token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    async def get_neuron_permissions(self, neuron_id: str) -> List[ToolPermission]:
        """Get all permissions for a neuron"""
        # Query database for neuron's permissions
        query = "SELECT * FROM tool_permissions WHERE neuron_id = %s AND status = 'granted'"
        results = await self.db.fetch(query, neuron_id)
        return [self._row_to_permission(row) for row in results]

    async def cleanup_expired(self):
        """Clean up expired permissions"""
        query = """
            UPDATE tool_permissions
            SET status = 'expired'
            WHERE expires_at < NOW() AND status = 'granted'
        """
        await self.db.execute(query)

    # Private methods
    def _generate_permission_id(self, request: PermissionRequest) -> str:
        """Generate unique permission ID"""
        data = f"{request.neuron_id}:{request.tool_id}:{datetime.now().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def _get_sandbox_level(self, risk_level: str) -> int:
        """Determine sandbox level based on risk"""
        levels = {
            "low": 0,
            "medium": 1,
            "high": 2,
            "critical": 2
        }
        return levels.get(risk_level, 2)

    async def _notify_user(self, user_id: str, permission_id: str, request: PermissionRequest):
        """Send permission request to user"""
        # Implementation would send via WebSocket, push notification, etc.
        pass

    async def _wait_for_response(self, permission_id: str, timeout: int) -> Optional[Dict]:
        """Wait for user response with timeout"""
        # Implementation would wait for user response
        # For now, auto-approve in development
        return {"approved": True}

    async def _store_permission(self, permission: ToolPermission):
        """Store permission in database"""
        query = """
            INSERT INTO tool_permissions
            (id, neuron_id, user_id, tool_id, allowed_actions,
             resource_patterns, granted_at, expires_at, sandbox_level,
             requires_confirmation, max_calls_per_day, status)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        """
        await self.db.execute(
            query,
            permission.permission_id,
            permission.neuron_id,
            permission.user_id,
            permission.tool_id,
            json.dumps([a.value for a in permission.allowed_actions]),
            json.dumps(permission.resource_patterns),
            permission.granted_at,
            permission.expires_at,
            permission.sandbox_level,
            permission.requires_user_confirmation,
            permission.max_calls_per_day,
            permission.status.value
        )

    async def _get_permission(self, neuron_id: str, tool_id: str) -> Optional[ToolPermission]:
        """Get permission from database"""
        query = """
            SELECT * FROM tool_permissions
            WHERE neuron_id = $1 AND tool_id = $2 AND status = 'granted'
            ORDER BY granted_at DESC
            LIMIT 1
        """
        row = await self.db.fetchrow(query, neuron_id, tool_id)
        return self._row_to_permission(row) if row else None

    async def _update_usage(self, permission: ToolPermission):
        """Update usage counters"""
        permission.current_usage_calls += 1
        query = """
            UPDATE tool_permissions
            SET current_usage_calls = current_usage_calls + 1
            WHERE id = $1
        """
        await self.db.execute(query, permission.permission_id)

    async def _audit_log(self, event: str, data: Any):
        """Write to audit log"""
        # Implementation would write to audit log
        pass

    def _row_to_permission(self, row) -> ToolPermission:
        """Convert database row to permission object"""
        # Implementation would convert database row
        pass