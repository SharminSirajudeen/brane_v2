"""
BRANE Tool System Pydantic Schemas
Request/Response models for tool access API endpoints
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from enum import Enum
from pydantic import BaseModel, Field, validator, ConfigDict
from uuid import UUID


# Enums (matching SQLAlchemy models)
class ToolCategory(str, Enum):
    FILE_SYSTEM = "file_system"
    NETWORK = "network"
    HARDWARE = "hardware"
    SERVICES = "services"
    SYSTEM = "system"
    DATA_PROCESSING = "data_processing"
    COMMUNICATION = "communication"
    AUTOMATION = "automation"


class PermissionScope(str, Enum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    DELETE = "delete"
    ADMIN = "admin"


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ROLLBACK = "rollback"


# Tool Schemas
class ToolBase(BaseModel):
    """Base tool information"""
    name: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    category: ToolCategory
    tags: List[str] = Field(default_factory=list)
    icon: Optional[str] = None


class ToolCreate(ToolBase):
    """Schema for creating a new tool"""
    provider_class: str = Field(..., description="Python class path for tool provider")
    input_schema: Dict[str, Any] = Field(..., description="JSON Schema for input parameters")
    output_schema: Optional[Dict[str, Any]] = None
    version: str = Field(default="1.0.0")
    privacy_tier: int = Field(default=0, ge=0, le=2)
    requires_confirmation: bool = Field(default=False)
    dangerous: bool = Field(default=False)
    estimated_duration_ms: Optional[int] = None
    max_concurrent_executions: int = Field(default=10, gt=0)
    rate_limit_per_minute: Optional[int] = None
    rate_limit_per_hour: Optional[int] = None

    @validator('input_schema')
    def validate_json_schema(cls, v):
        if '$schema' not in v:
            v['$schema'] = "http://json-schema.org/draft-07/schema#"
        return v


class ToolResponse(ToolBase):
    """Tool response with full details"""
    id: UUID
    version: str
    author: Optional[str]
    privacy_tier: int
    requires_confirmation: bool
    dangerous: bool
    enabled: bool
    deprecated: bool
    created_at: datetime
    updated_at: datetime
    provider_class: str
    input_schema: Dict[str, Any]
    output_schema: Optional[Dict[str, Any]]
    estimated_duration_ms: Optional[int]
    max_concurrent_executions: int
    rate_limit_per_minute: Optional[int]
    rate_limit_per_hour: Optional[int]

    model_config = ConfigDict(from_attributes=True)


class ToolDiscovery(BaseModel):
    """Tool discovery response for Neurons"""
    id: UUID
    name: str
    display_name: str
    description: str
    category: ToolCategory
    tags: List[str]
    icon: Optional[str]
    privacy_tier: int
    requires_confirmation: bool
    available: bool
    permitted: bool = Field(default=False, description="Whether current neuron has permission")
    permission_scopes: List[PermissionScope] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# Permission Schemas
class PermissionRequest(BaseModel):
    """Request permission to use a tool"""
    tool_id: UUID
    neuron_id: UUID
    scopes: List[PermissionScope] = Field(..., min_items=1)
    expires_in_hours: Optional[int] = Field(None, gt=0, description="Permission expiry in hours")
    max_daily_uses: Optional[int] = Field(None, gt=0)
    max_total_uses: Optional[int] = Field(None, gt=0)
    require_confirmation: bool = Field(default=False)
    confirmation_message: Optional[str] = None
    allowed_parameters: Optional[Dict[str, Any]] = None
    denied_parameters: Optional[Dict[str, Any]] = None


class PermissionGrant(BaseModel):
    """Response after granting permission"""
    id: UUID
    tool_id: UUID
    tool_name: str
    neuron_id: UUID
    neuron_name: str
    scopes: List[PermissionScope]
    granted_at: datetime
    expires_at: Optional[datetime]
    max_daily_uses: Optional[int]
    max_total_uses: Optional[int]
    require_confirmation: bool
    active: bool

    model_config = ConfigDict(from_attributes=True)


class PermissionRevoke(BaseModel):
    """Revoke a permission"""
    reason: str = Field(..., min_length=1)


class PermissionStatus(BaseModel):
    """Current status of a permission"""
    id: UUID
    valid: bool
    active: bool
    scopes: List[PermissionScope]
    current_uses: int
    max_daily_uses: Optional[int]
    max_total_uses: Optional[int]
    expires_at: Optional[datetime]
    last_used: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


# Execution Schemas
class ToolExecutionRequest(BaseModel):
    """Request to execute a tool"""
    tool_id: UUID
    neuron_id: UUID
    parameters: Dict[str, Any]
    dry_run: bool = Field(default=False, description="Simulate execution without side effects")
    session_id: Optional[UUID] = Field(None, description="Group related executions")
    memory_context: Optional[Dict[str, Any]] = Field(None, description="L1-L4 memory snapshot")


class ToolExecutionConfirmation(BaseModel):
    """Confirm tool execution (for dangerous operations)"""
    execution_id: UUID
    confirm: bool
    confirmation_code: Optional[str] = Field(None, description="Optional 2FA code")


class ToolExecutionResponse(BaseModel):
    """Tool execution result"""
    id: UUID
    tool_id: UUID
    tool_name: str
    status: ExecutionStatus
    started_at: datetime
    completed_at: Optional[datetime]
    duration_ms: Optional[int]
    input_parameters: Dict[str, Any]
    output_result: Optional[Any]
    error_message: Optional[str]
    requires_confirmation: bool
    confirmation_url: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class ToolExecutionStream(BaseModel):
    """Streaming execution update"""
    execution_id: UUID
    status: ExecutionStatus
    progress: Optional[float] = Field(None, ge=0, le=100)
    message: Optional[str]
    partial_result: Optional[Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Audit and Monitoring
class ExecutionAuditLog(BaseModel):
    """Audit log entry for tool execution"""
    id: UUID
    tool_name: str
    neuron_name: str
    user_id: UUID
    status: ExecutionStatus
    started_at: datetime
    completed_at: Optional[datetime]
    duration_ms: Optional[int]
    input_parameters: Dict[str, Any]
    output_result: Optional[Any]
    error_message: Optional[str]
    cpu_time_ms: Optional[int]
    memory_peak_mb: Optional[int]

    model_config = ConfigDict(from_attributes=True)


class ToolUsageStats(BaseModel):
    """Usage statistics for a tool"""
    tool_id: UUID
    tool_name: str
    total_executions: int
    successful_executions: int
    failed_executions: int
    average_duration_ms: float
    total_cpu_time_ms: int
    total_memory_mb: int
    unique_neurons: int
    unique_users: int
    last_execution: Optional[datetime]
    busiest_hour: Optional[int]

    model_config = ConfigDict(from_attributes=True)


# Batch Operations
class BatchToolExecution(BaseModel):
    """Execute multiple tools in sequence or parallel"""
    executions: List[ToolExecutionRequest]
    mode: str = Field(default="sequential", pattern="^(sequential|parallel)$")
    stop_on_error: bool = Field(default=True)
    max_parallel: int = Field(default=5, gt=0, le=20)


class BatchToolResult(BaseModel):
    """Results from batch tool execution"""
    batch_id: UUID
    total: int
    successful: int
    failed: int
    results: List[ToolExecutionResponse]
    total_duration_ms: int


# Tool Provider Schemas
class ToolProviderRegister(BaseModel):
    """Register a new tool provider plugin"""
    name: str = Field(..., min_length=1, max_length=100)
    module_path: str = Field(..., description="Python module path")
    version: str
    description: Optional[str]
    config_schema: Optional[Dict[str, Any]]
    default_config: Optional[Dict[str, Any]]


class ToolProviderInfo(BaseModel):
    """Tool provider information"""
    id: UUID
    name: str
    module_path: str
    version: str
    description: Optional[str]
    enabled: bool
    trusted: bool
    health_status: Optional[str]
    last_health_check: Optional[datetime]
    error_count: int

    model_config = ConfigDict(from_attributes=True)


# Search and Discovery
class ToolSearchRequest(BaseModel):
    """Search for available tools"""
    query: Optional[str] = Field(None, description="Text search query")
    categories: Optional[List[ToolCategory]] = None
    tags: Optional[List[str]] = None
    privacy_tier_max: Optional[int] = Field(None, ge=0, le=2)
    only_permitted: bool = Field(default=False)
    include_dangerous: bool = Field(default=False)
    limit: int = Field(default=20, gt=0, le=100)
    offset: int = Field(default=0, ge=0)


class ToolSearchResponse(BaseModel):
    """Search results for tools"""
    total: int
    tools: List[ToolDiscovery]
    categories_available: List[ToolCategory]
    suggested_tools: Optional[List[UUID]] = Field(None, description="AI-suggested tools based on context")