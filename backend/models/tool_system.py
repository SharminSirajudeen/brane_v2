"""
BRANE Tool System Database Models
Enables Neurons to interact with digital and physical world through secure tool access
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
import json
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, JSON,
    ForeignKey, Float, CheckConstraint, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.dialects.postgresql import UUID
import uuid

from backend.database import Base


class ToolCategory(str, Enum):
    """Tool categories for organization and discovery"""
    FILE_SYSTEM = "file_system"
    NETWORK = "network"
    HARDWARE = "hardware"
    SERVICES = "services"
    SYSTEM = "system"
    DATA_PROCESSING = "data_processing"
    COMMUNICATION = "communication"
    AUTOMATION = "automation"


class PermissionScope(str, Enum):
    """Granular permission scopes"""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    DELETE = "delete"
    ADMIN = "admin"


class ExecutionStatus(str, Enum):
    """Tool execution status tracking"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ROLLBACK = "rollback"


class Tool(Base):
    """Tool registry - defines available tools and their capabilities"""
    __tablename__ = "tools"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True, index=True)
    display_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(50), nullable=False, index=True)

    # Tool metadata
    version = Column(String(20), nullable=False, default="1.0.0")
    author = Column(String(100))
    icon = Column(String(200))  # Icon URL or emoji
    tags = Column(JSON, default=list)  # For search and discovery

    # Technical specifications
    provider_class = Column(String(200), nullable=False)  # Python class path
    input_schema = Column(JSON, nullable=False)  # JSON Schema for parameters
    output_schema = Column(JSON)  # Expected output format

    # Privacy and security
    privacy_tier = Column(Integer, default=0, nullable=False)  # 0=local, 1=private, 2=public
    requires_confirmation = Column(Boolean, default=False)
    dangerous = Column(Boolean, default=False)  # Requires extra confirmation

    # Resource requirements
    estimated_duration_ms = Column(Integer)  # Expected execution time
    memory_requirement_mb = Column(Integer)
    cpu_intensive = Column(Boolean, default=False)

    # Capabilities and limits
    max_concurrent_executions = Column(Integer, default=10)
    rate_limit_per_minute = Column(Integer)
    rate_limit_per_hour = Column(Integer)

    # Status
    enabled = Column(Boolean, default=True, nullable=False)
    deprecated = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    permissions = relationship("ToolPermission", back_populates="tool", cascade="all, delete-orphan")
    executions = relationship("ToolExecution", back_populates="tool")

    __table_args__ = (
        CheckConstraint('privacy_tier >= 0 AND privacy_tier <= 2'),
        Index('idx_tool_category_enabled', 'category', 'enabled'),
    )

    @validates('input_schema')
    def validate_input_schema(self, key, value):
        """Ensure input_schema is valid JSON Schema"""
        if not isinstance(value, dict):
            raise ValueError("input_schema must be a dictionary")
        if '$schema' not in value:
            value['$schema'] = "http://json-schema.org/draft-07/schema#"
        return value

    @hybrid_property
    def is_available(self):
        """Check if tool is currently available for use"""
        return self.enabled and not self.deprecated


class ToolPermission(Base):
    """User-granted permissions for Neurons to use specific tools"""
    __tablename__ = "tool_permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    neuron_id = Column(UUID(as_uuid=True), ForeignKey("neurons.id"), nullable=False)
    tool_id = Column(UUID(as_uuid=True), ForeignKey("tools.id"), nullable=False)

    # Permission details
    scopes = Column(JSON, nullable=False)  # List of PermissionScope values
    granted_at = Column(DateTime, default=datetime.utcnow)
    granted_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))

    # Constraints
    expires_at = Column(DateTime)
    max_daily_uses = Column(Integer)
    max_total_uses = Column(Integer)
    current_uses = Column(Integer, default=0)

    # Advanced permissions
    allowed_parameters = Column(JSON)  # Whitelist specific parameter values
    denied_parameters = Column(JSON)  # Blacklist specific parameter values
    require_confirmation = Column(Boolean, default=False)
    confirmation_message = Column(Text)

    # Delegation
    can_delegate = Column(Boolean, default=False)
    parent_permission_id = Column(UUID(as_uuid=True), ForeignKey("tool_permissions.id"))

    # Status
    active = Column(Boolean, default=True)
    revoked_at = Column(DateTime)
    revoked_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    revocation_reason = Column(Text)

    # Relationships
    tool = relationship("Tool", back_populates="permissions")
    user = relationship("User", foreign_keys=[user_id])
    neuron = relationship("Neuron")
    executions = relationship("ToolExecution", back_populates="permission")
    parent = relationship("ToolPermission", remote_side=[id])

    __table_args__ = (
        UniqueConstraint('user_id', 'neuron_id', 'tool_id', name='unique_user_neuron_tool'),
        Index('idx_permission_active', 'active', 'neuron_id'),
    )

    @hybrid_property
    def is_valid(self):
        """Check if permission is currently valid"""
        if not self.active or self.revoked_at:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        if self.max_total_uses and self.current_uses >= self.max_total_uses:
            return False
        return True


class ToolExecution(Base):
    """Audit log and execution history for tool usage"""
    __tablename__ = "tool_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tool_id = Column(UUID(as_uuid=True), ForeignKey("tools.id"), nullable=False)
    permission_id = Column(UUID(as_uuid=True), ForeignKey("tool_permissions.id"), nullable=False)
    neuron_id = Column(UUID(as_uuid=True), ForeignKey("neurons.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Execution context
    session_id = Column(UUID(as_uuid=True), index=True)  # Group related executions
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"))
    memory_context = Column(JSON)  # L1-L4 memory snapshot

    # Input/Output
    input_parameters = Column(JSON, nullable=False)
    output_result = Column(JSON)
    error_message = Column(Text)

    # Execution details
    status = Column(String(20), nullable=False, default=ExecutionStatus.PENDING)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    duration_ms = Column(Integer)

    # Resource usage
    cpu_time_ms = Column(Integer)
    memory_peak_mb = Column(Integer)
    network_bytes = Column(Integer)

    # Safety and validation
    dry_run = Column(Boolean, default=False)
    sandbox_id = Column(String(100))  # Docker container or VM ID
    validation_errors = Column(JSON)
    rollback_available = Column(Boolean, default=False)
    rollback_data = Column(JSON)

    # User interaction
    required_confirmation = Column(Boolean, default=False)
    confirmed_at = Column(DateTime)
    confirmed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))

    # Relationships
    tool = relationship("Tool", back_populates="executions")
    permission = relationship("ToolPermission", back_populates="executions")
    neuron = relationship("Neuron")
    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index('idx_execution_status', 'status', 'neuron_id'),
        Index('idx_execution_session', 'session_id', 'started_at'),
    )

    @hybrid_property
    def execution_time(self):
        """Calculate execution duration"""
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


class ToolProvider(Base):
    """Plugin-based tool providers for dynamic tool loading"""
    __tablename__ = "tool_providers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)
    module_path = Column(String(200), nullable=False)  # Python module path

    # Provider metadata
    version = Column(String(20), nullable=False)
    description = Column(Text)
    author = Column(String(100))
    website = Column(String(200))

    # Configuration
    config_schema = Column(JSON)  # JSON Schema for provider config
    default_config = Column(JSON)
    user_config = Column(JSON)  # User-specific overrides

    # Security
    signature = Column(Text)  # Digital signature for verification
    checksum = Column(String(64))  # SHA256 hash
    trusted = Column(Boolean, default=False)

    # Status
    enabled = Column(Boolean, default=True)
    last_health_check = Column(DateTime)
    health_status = Column(String(20))
    error_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_provider_enabled', 'enabled', 'trusted'),
    )


class ToolRateLimit(Base):
    """Rate limiting tracking per user/neuron/tool combination"""
    __tablename__ = "tool_rate_limits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    neuron_id = Column(UUID(as_uuid=True), ForeignKey("neurons.id"), nullable=False)
    tool_id = Column(UUID(as_uuid=True), ForeignKey("tools.id"), nullable=False)

    # Time windows
    minute_window = Column(DateTime, nullable=False)
    hour_window = Column(DateTime, nullable=False)
    day_window = Column(DateTime, nullable=False)

    # Counters
    minute_count = Column(Integer, default=0)
    hour_count = Column(Integer, default=0)
    day_count = Column(Integer, default=0)

    # Last execution
    last_execution = Column(DateTime)
    consecutive_failures = Column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint('neuron_id', 'tool_id', name='unique_neuron_tool_limit'),
        Index('idx_rate_limit_window', 'minute_window', 'neuron_id'),
    )