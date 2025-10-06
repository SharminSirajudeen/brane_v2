"""
Base classes for BRANE tools
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ToolCategory(Enum):
    """Tool categories"""
    # Digital World
    FILE_SYSTEM = "file_system"
    NETWORK = "network"
    DATABASE = "database"
    CODE_EXEC = "code_execution"
    BROWSER = "browser"
    CLOUD = "cloud"
    DEV_TOOLS = "dev_tools"

    # Physical World
    SMART_HOME = "smart_home"
    GPIO = "gpio"
    USB = "usb"
    BLUETOOTH = "bluetooth"
    ROBOTICS = "robotics"
    IOT = "iot"
    MEDIA = "media"

    # AI/ML
    MCP = "mcp"
    LANGCHAIN = "langchain"
    CUSTOM = "custom"


class ToolRiskLevel(Enum):
    """Risk levels for tools"""
    LOW = "low"       # Read-only operations
    MEDIUM = "medium" # Write operations, reversible
    HIGH = "high"     # System changes, physical world
    CRITICAL = "critical" # Irreversible, safety-critical


class ToolParameter(BaseModel):
    """Tool parameter definition"""
    name: str
    type: str  # "string", "number", "boolean", "object", "array"
    description: str
    required: bool = True
    default: Optional[Any] = None
    validation: Optional[Dict[str, Any]] = None


class ToolSchema(BaseModel):
    """Tool interface schema"""
    name: str
    description: str
    category: ToolCategory
    risk_level: ToolRiskLevel
    parameters: List[ToolParameter]
    returns: Dict[str, Any]
    examples: List[Dict[str, Any]] = []

    # Capabilities
    requires_confirmation: bool = False
    supports_streaming: bool = False
    is_reversible: bool = True

    # Resource requirements
    requires_network: bool = False
    requires_filesystem: bool = False
    requires_hardware: bool = False

    # Rate limits
    max_calls_per_minute: int = 60
    max_calls_per_hour: int = 1000
    max_data_mb_per_hour: float = 100.0


class BaseTool(ABC):
    """Abstract base class for all tools"""

    def __init__(self, schema: ToolSchema):
        self.schema = schema
        self.name = schema.name
        self.category = schema.category
        self.risk_level = schema.risk_level
        self._execution_count = 0
        self._last_execution = None

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """Execute the tool with given parameters"""
        pass

    @abstractmethod
    async def validate_parameters(self, **kwargs) -> bool:
        """Validate input parameters"""
        pass

    async def pre_execute(self, **kwargs):
        """Hook called before execution"""
        self._execution_count += 1
        self._last_execution = datetime.now()

    async def post_execute(self, result: Any, **kwargs):
        """Hook called after execution"""
        pass

    def to_dict(self) -> Dict[str, Any]:
        """Convert tool to dictionary"""
        return {
            "name": self.name,
            "description": self.schema.description,
            "category": self.category.value,
            "risk_level": self.risk_level.value,
            "parameters": [p.dict() for p in self.schema.parameters],
            "requires_confirmation": self.schema.requires_confirmation
        }

    def to_langchain_tool(self):
        """Convert to LangChain tool format"""
        from langchain.tools import Tool

        async def wrapper(**kwargs):
            await self.pre_execute(**kwargs)
            result = await self.execute(**kwargs)
            await self.post_execute(result, **kwargs)
            return result

        return Tool(
            name=self.name,
            description=self.schema.description,
            func=wrapper
        )

    def to_mcp_tool(self):
        """Convert to MCP tool format"""
        # This would integrate with fastmcp
        pass


class DigitalTool(BaseTool):
    """Base class for digital world tools"""

    def __init__(self, schema: ToolSchema):
        super().__init__(schema)
        self.sandbox_level = 1  # Default sandboxing for digital tools

    async def check_rate_limit(self, neuron_id: str) -> bool:
        """Check if rate limit exceeded"""
        # Implementation would check Redis/cache
        return True

    async def log_execution(self, neuron_id: str, args: Dict, result: Any):
        """Log tool execution"""
        # Implementation would write to audit log
        pass


class PhysicalTool(BaseTool):
    """Base class for physical world tools"""

    def __init__(self, schema: ToolSchema, device_config: Dict[str, Any]):
        super().__init__(schema)
        self.device_config = device_config
        self.sandbox_level = 2  # Strict sandboxing for physical tools
        self.safety_checks = self._get_safety_checks()

    def _get_safety_checks(self) -> List[str]:
        """Get required safety checks"""
        return [
            "user_presence_verification",
            "rate_limiting",
            "reversibility_check",
            "emergency_stop",
            "physical_bounds_check"
        ]

    async def verify_safety(self, **kwargs) -> bool:
        """Verify safety before physical action"""
        for check in self.safety_checks:
            if not await self._run_safety_check(check, kwargs):
                return False
        return True

    async def _run_safety_check(self, check: str, kwargs: Dict) -> bool:
        """Run individual safety check"""
        # Implementation would run actual safety verifications
        return True

    async def emergency_stop(self):
        """Emergency stop for physical device"""
        # Implementation would immediately halt physical operations
        pass


class CompositeTool(BaseTool):
    """Tool that combines multiple other tools"""

    def __init__(self, schema: ToolSchema, sub_tools: List[BaseTool]):
        super().__init__(schema)
        self.sub_tools = sub_tools

    async def execute(self, **kwargs) -> Any:
        """Execute composite tool by orchestrating sub-tools"""
        results = {}
        for tool in self.sub_tools:
            tool_args = kwargs.get(tool.name, {})
            results[tool.name] = await tool.execute(**tool_args)
        return results

    async def validate_parameters(self, **kwargs) -> bool:
        """Validate parameters for all sub-tools"""
        for tool in self.sub_tools:
            tool_args = kwargs.get(tool.name, {})
            if not await tool.validate_parameters(**tool_args):
                return False
        return True