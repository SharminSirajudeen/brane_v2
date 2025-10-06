"""
BRANE Tool System API Routes
FastAPI endpoints for tool discovery, permission management, and execution
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
import json

from backend.database import get_async_session
from backend.models.tool_system import (
    Tool, ToolPermission, ToolExecution, ToolProvider, ToolRateLimit,
    ToolCategory, PermissionScope, ExecutionStatus
)
from backend.schemas.tool_system import (
    ToolCreate, ToolResponse, ToolDiscovery, PermissionRequest,
    PermissionGrant, PermissionRevoke, PermissionStatus,
    ToolExecutionRequest, ToolExecutionConfirmation, ToolExecutionResponse,
    ToolExecutionStream, ExecutionAuditLog, ToolUsageStats,
    BatchToolExecution, BatchToolResult, ToolProviderRegister,
    ToolProviderInfo, ToolSearchRequest, ToolSearchResponse
)
from backend.auth import get_current_user
from backend.services.tool_executor import ToolExecutor
from backend.services.tool_sandbox import ToolSandbox
from backend.services.tool_validator import ToolValidator
from backend.core.memory import MemoryManager
from backend.core.llm_integration import LLMToolMapper

router = APIRouter(prefix="/api/tools", tags=["tools"])

# Initialize services
tool_executor = ToolExecutor()
tool_sandbox = ToolSandbox()
tool_validator = ToolValidator()
memory_manager = MemoryManager()
llm_mapper = LLMToolMapper()


# ============================================================================
# Tool Discovery & Registry
# ============================================================================

@router.get("/discover", response_model=ToolSearchResponse)
async def discover_tools(
    request: ToolSearchRequest = Depends(),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Discover available tools with search, filtering, and AI suggestions
    """
    query = select(Tool).where(Tool.enabled == True, Tool.deprecated == False)

    # Apply filters
    if request.categories:
        query = query.where(Tool.category.in_(request.categories))

    if request.privacy_tier_max is not None:
        query = query.where(Tool.privacy_tier <= request.privacy_tier_max)

    if not request.include_dangerous:
        query = query.where(Tool.dangerous == False)

    if request.tags:
        # PostgreSQL JSON array containment
        query = query.where(Tool.tags.contains(request.tags))

    if request.query:
        # Full-text search on name, display_name, and description
        search_term = f"%{request.query}%"
        query = query.where(
            or_(
                Tool.name.ilike(search_term),
                Tool.display_name.ilike(search_term),
                Tool.description.ilike(search_term)
            )
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Apply pagination
    query = query.offset(request.offset).limit(request.limit)
    result = await db.execute(query)
    tools = result.scalars().all()

    # Check permissions for each tool
    tool_discoveries = []
    for tool in tools:
        # Check if user has permission for this tool
        perm_query = select(ToolPermission).where(
            and_(
                ToolPermission.tool_id == tool.id,
                ToolPermission.user_id == current_user["id"],
                ToolPermission.active == True
            )
        )
        perm_result = await db.execute(perm_query)
        permission = perm_result.scalar_one_or_none()

        discovery = ToolDiscovery(
            id=tool.id,
            name=tool.name,
            display_name=tool.display_name,
            description=tool.description,
            category=tool.category,
            tags=tool.tags or [],
            icon=tool.icon,
            privacy_tier=tool.privacy_tier,
            requires_confirmation=tool.requires_confirmation,
            available=tool.is_available,
            permitted=permission is not None,
            permission_scopes=permission.scopes if permission else []
        )
        tool_discoveries.append(discovery)

    # Get AI suggestions based on user context
    suggested_tools = None
    if request.query:
        suggested_tools = await llm_mapper.suggest_tools(
            query=request.query,
            user_context=await memory_manager.get_user_context(current_user["id"]),
            available_tools=tool_discoveries
        )

    return ToolSearchResponse(
        total=total,
        tools=tool_discoveries,
        categories_available=list(ToolCategory),
        suggested_tools=suggested_tools
    )


@router.post("/register", response_model=ToolResponse)
async def register_tool(
    tool: ToolCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Register a new tool in the system (admin only)
    """
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")

    # Validate tool schema
    validation_errors = tool_validator.validate_tool_schema(tool.input_schema)
    if validation_errors:
        raise HTTPException(status_code=400, detail=f"Invalid input schema: {validation_errors}")

    # Create tool
    db_tool = Tool(
        **tool.model_dump(),
        author=current_user.get("email")
    )
    db.add(db_tool)
    await db.commit()
    await db.refresh(db_tool)

    return ToolResponse.model_validate(db_tool)


@router.get("/{tool_id}", response_model=ToolResponse)
async def get_tool(
    tool_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get detailed information about a specific tool
    """
    query = select(Tool).where(Tool.id == tool_id)
    result = await db.execute(query)
    tool = result.scalar_one_or_none()

    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    return ToolResponse.model_validate(tool)


# ============================================================================
# Permission Management
# ============================================================================

@router.post("/permissions/grant", response_model=PermissionGrant)
async def grant_permission(
    request: PermissionRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Grant permission for a Neuron to use a specific tool
    """
    # Verify tool exists
    tool = await db.get(Tool, request.tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    # Check if permission already exists
    existing = await db.execute(
        select(ToolPermission).where(
            and_(
                ToolPermission.user_id == current_user["id"],
                ToolPermission.neuron_id == request.neuron_id,
                ToolPermission.tool_id == request.tool_id,
                ToolPermission.active == True
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Permission already exists")

    # Calculate expiry
    expires_at = None
    if request.expires_in_hours:
        expires_at = datetime.utcnow() + timedelta(hours=request.expires_in_hours)

    # Create permission
    permission = ToolPermission(
        user_id=current_user["id"],
        neuron_id=request.neuron_id,
        tool_id=request.tool_id,
        scopes=request.scopes,
        granted_by=current_user["id"],
        expires_at=expires_at,
        max_daily_uses=request.max_daily_uses,
        max_total_uses=request.max_total_uses,
        require_confirmation=request.require_confirmation,
        confirmation_message=request.confirmation_message,
        allowed_parameters=request.allowed_parameters,
        denied_parameters=request.denied_parameters
    )
    db.add(permission)
    await db.commit()
    await db.refresh(permission)

    # Get neuron name (assuming Neuron model exists)
    neuron_name = "Neuron"  # Replace with actual neuron lookup

    return PermissionGrant(
        id=permission.id,
        tool_id=tool.id,
        tool_name=tool.display_name,
        neuron_id=request.neuron_id,
        neuron_name=neuron_name,
        scopes=permission.scopes,
        granted_at=permission.granted_at,
        expires_at=permission.expires_at,
        max_daily_uses=permission.max_daily_uses,
        max_total_uses=permission.max_total_uses,
        require_confirmation=permission.require_confirmation,
        active=permission.active
    )


@router.delete("/permissions/{permission_id}")
async def revoke_permission(
    permission_id: UUID,
    revoke_request: PermissionRevoke,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Revoke a tool permission
    """
    permission = await db.get(ToolPermission, permission_id)
    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")

    if permission.user_id != current_user["id"] and not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Not authorized to revoke this permission")

    permission.active = False
    permission.revoked_at = datetime.utcnow()
    permission.revoked_by = current_user["id"]
    permission.revocation_reason = revoke_request.reason

    await db.commit()
    return {"message": "Permission revoked successfully"}


@router.get("/permissions/status/{permission_id}", response_model=PermissionStatus)
async def get_permission_status(
    permission_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Check the current status of a permission
    """
    permission = await db.get(ToolPermission, permission_id)
    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")

    # Get last execution
    last_exec_query = select(ToolExecution.started_at).where(
        ToolExecution.permission_id == permission_id
    ).order_by(ToolExecution.started_at.desc()).limit(1)
    last_used = await db.scalar(last_exec_query)

    return PermissionStatus(
        id=permission.id,
        valid=permission.is_valid,
        active=permission.active,
        scopes=permission.scopes,
        current_uses=permission.current_uses,
        max_daily_uses=permission.max_daily_uses,
        max_total_uses=permission.max_total_uses,
        expires_at=permission.expires_at,
        last_used=last_used
    )


# ============================================================================
# Tool Execution
# ============================================================================

@router.post("/execute", response_model=ToolExecutionResponse)
async def execute_tool(
    request: ToolExecutionRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Execute a tool with proper validation, sandboxing, and auditing
    """
    # Verify permission
    perm_query = select(ToolPermission).where(
        and_(
            ToolPermission.user_id == current_user["id"],
            ToolPermission.neuron_id == request.neuron_id,
            ToolPermission.tool_id == request.tool_id,
            ToolPermission.active == True
        )
    )
    perm_result = await db.execute(perm_query)
    permission = perm_result.scalar_one_or_none()

    if not permission or not permission.is_valid:
        raise HTTPException(status_code=403, detail="Valid permission not found")

    # Check if EXECUTE scope is granted
    if PermissionScope.EXECUTE not in permission.scopes:
        raise HTTPException(status_code=403, detail="Execute permission not granted")

    # Get tool
    tool = await db.get(Tool, request.tool_id)
    if not tool or not tool.is_available:
        raise HTTPException(status_code=404, detail="Tool not available")

    # Check rate limits
    if not await check_rate_limit(db, request.neuron_id, request.tool_id, tool):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    # Validate parameters
    validation_errors = tool_validator.validate_parameters(
        tool.input_schema,
        request.parameters,
        permission.allowed_parameters,
        permission.denied_parameters
    )
    if validation_errors:
        raise HTTPException(status_code=400, detail=f"Invalid parameters: {validation_errors}")

    # Create execution record
    execution = ToolExecution(
        tool_id=request.tool_id,
        permission_id=permission.id,
        neuron_id=request.neuron_id,
        user_id=current_user["id"],
        session_id=request.session_id,
        memory_context=request.memory_context,
        input_parameters=request.parameters,
        dry_run=request.dry_run,
        status=ExecutionStatus.PENDING,
        required_confirmation=tool.requires_confirmation or permission.require_confirmation
    )
    db.add(execution)
    await db.commit()
    await db.refresh(execution)

    # Check if confirmation required
    if execution.required_confirmation and not request.dry_run:
        return ToolExecutionResponse(
            id=execution.id,
            tool_id=tool.id,
            tool_name=tool.display_name,
            status=ExecutionStatus.PENDING,
            started_at=execution.started_at,
            completed_at=None,
            duration_ms=None,
            input_parameters=execution.input_parameters,
            output_result=None,
            error_message=None,
            requires_confirmation=True,
            confirmation_url=f"/api/tools/confirm/{execution.id}"
        )

    # Execute in background
    background_tasks.add_task(
        execute_tool_async,
        execution.id,
        tool,
        permission,
        request.dry_run
    )

    return ToolExecutionResponse(
        id=execution.id,
        tool_id=tool.id,
        tool_name=tool.display_name,
        status=ExecutionStatus.RUNNING,
        started_at=execution.started_at,
        completed_at=None,
        duration_ms=None,
        input_parameters=execution.input_parameters,
        output_result=None,
        error_message=None,
        requires_confirmation=False,
        confirmation_url=None
    )


async def execute_tool_async(
    execution_id: UUID,
    tool: Tool,
    permission: ToolPermission,
    dry_run: bool
):
    """
    Background task for tool execution
    """
    async with get_async_session() as db:
        execution = await db.get(ToolExecution, execution_id)

        try:
            # Update status to running
            execution.status = ExecutionStatus.RUNNING
            await db.commit()

            # Create sandbox environment
            sandbox_id = None
            if tool.privacy_tier > 0 and not dry_run:
                sandbox_id = await tool_sandbox.create_sandbox(
                    tool_id=tool.id,
                    memory_limit_mb=tool.memory_requirement_mb,
                    cpu_limit=1.0 if tool.cpu_intensive else 0.5
                )
                execution.sandbox_id = sandbox_id

            # Execute tool
            result = await tool_executor.execute(
                tool=tool,
                parameters=execution.input_parameters,
                sandbox_id=sandbox_id,
                dry_run=dry_run
            )

            # Update execution record
            execution.status = ExecutionStatus.SUCCESS
            execution.output_result = result.output
            execution.completed_at = datetime.utcnow()
            execution.duration_ms = int(result.duration * 1000)
            execution.cpu_time_ms = result.cpu_time
            execution.memory_peak_mb = result.memory_peak

            # Update permission usage count
            permission.current_uses += 1

        except Exception as e:
            execution.status = ExecutionStatus.FAILED
            execution.error_message = str(e)
            execution.completed_at = datetime.utcnow()

        finally:
            # Cleanup sandbox
            if execution.sandbox_id:
                await tool_sandbox.destroy_sandbox(execution.sandbox_id)

            await db.commit()


@router.post("/confirm/{execution_id}", response_model=ToolExecutionResponse)
async def confirm_execution(
    execution_id: UUID,
    confirmation: ToolExecutionConfirmation,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Confirm a tool execution that requires user approval
    """
    execution = await db.get(ToolExecution, execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    if execution.user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    if not execution.required_confirmation:
        raise HTTPException(status_code=400, detail="Confirmation not required")

    if execution.status != ExecutionStatus.PENDING:
        raise HTTPException(status_code=400, detail="Execution already processed")

    if not confirmation.confirm:
        execution.status = ExecutionStatus.CANCELLED
        await db.commit()
        return ToolExecutionResponse.model_validate(execution)

    # Get tool and permission
    tool = await db.get(Tool, execution.tool_id)
    permission = await db.get(ToolPermission, execution.permission_id)

    # Mark as confirmed
    execution.confirmed_at = datetime.utcnow()
    execution.confirmed_by = current_user["id"]
    await db.commit()

    # Execute in background
    background_tasks.add_task(
        execute_tool_async,
        execution.id,
        tool,
        permission,
        execution.dry_run
    )

    execution.status = ExecutionStatus.RUNNING
    return ToolExecutionResponse.model_validate(execution)


# ============================================================================
# Streaming Execution (WebSocket)
# ============================================================================

@router.websocket("/execute/stream/{execution_id}")
async def stream_execution(
    websocket: WebSocket,
    execution_id: UUID,
    db: AsyncSession = Depends(get_async_session)
):
    """
    WebSocket endpoint for streaming tool execution updates
    """
    await websocket.accept()

    try:
        while True:
            # Get execution status
            execution = await db.get(ToolExecution, execution_id)
            if not execution:
                await websocket.send_json({
                    "error": "Execution not found"
                })
                break

            # Send update
            update = ToolExecutionStream(
                execution_id=execution.id,
                status=execution.status,
                progress=calculate_progress(execution),
                message=get_status_message(execution),
                partial_result=execution.output_result
            )
            await websocket.send_json(update.model_dump_json())

            # Check if complete
            if execution.status in [ExecutionStatus.SUCCESS, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED]:
                break

            # Wait before next update
            await asyncio.sleep(0.5)

    except WebSocketDisconnect:
        pass
    finally:
        await websocket.close()


# ============================================================================
# Helper Functions
# ============================================================================

async def check_rate_limit(
    db: AsyncSession,
    neuron_id: UUID,
    tool_id: UUID,
    tool: Tool
) -> bool:
    """
    Check if execution is within rate limits
    """
    now = datetime.utcnow()

    # Get or create rate limit record
    rate_limit = await db.execute(
        select(ToolRateLimit).where(
            and_(
                ToolRateLimit.neuron_id == neuron_id,
                ToolRateLimit.tool_id == tool_id
            )
        )
    )
    rate_limit = rate_limit.scalar_one_or_none()

    if not rate_limit:
        rate_limit = ToolRateLimit(
            neuron_id=neuron_id,
            tool_id=tool_id,
            minute_window=now,
            hour_window=now,
            day_window=now
        )
        db.add(rate_limit)

    # Reset windows if needed
    if (now - rate_limit.minute_window).total_seconds() > 60:
        rate_limit.minute_window = now
        rate_limit.minute_count = 0

    if (now - rate_limit.hour_window).total_seconds() > 3600:
        rate_limit.hour_window = now
        rate_limit.hour_count = 0

    if (now - rate_limit.day_window).total_seconds() > 86400:
        rate_limit.day_window = now
        rate_limit.day_count = 0

    # Check limits
    if tool.rate_limit_per_minute and rate_limit.minute_count >= tool.rate_limit_per_minute:
        return False

    if tool.rate_limit_per_hour and rate_limit.hour_count >= tool.rate_limit_per_hour:
        return False

    # Update counts
    rate_limit.minute_count += 1
    rate_limit.hour_count += 1
    rate_limit.day_count += 1
    rate_limit.last_execution = now

    await db.commit()
    return True


def calculate_progress(execution: ToolExecution) -> float:
    """Calculate execution progress percentage"""
    if execution.status == ExecutionStatus.PENDING:
        return 0.0
    elif execution.status == ExecutionStatus.RUNNING:
        if execution.duration_ms and execution.tool.estimated_duration_ms:
            return min(execution.duration_ms / execution.tool.estimated_duration_ms * 100, 99)
        return 50.0
    elif execution.status in [ExecutionStatus.SUCCESS, ExecutionStatus.FAILED]:
        return 100.0
    return 0.0


def get_status_message(execution: ToolExecution) -> str:
    """Generate human-readable status message"""
    status_messages = {
        ExecutionStatus.PENDING: "Waiting to start...",
        ExecutionStatus.RUNNING: "Executing tool...",
        ExecutionStatus.SUCCESS: "Execution completed successfully",
        ExecutionStatus.FAILED: f"Execution failed: {execution.error_message}",
        ExecutionStatus.CANCELLED: "Execution cancelled by user",
        ExecutionStatus.ROLLBACK: "Rolling back changes..."
    }
    return status_messages.get(execution.status, "Unknown status")