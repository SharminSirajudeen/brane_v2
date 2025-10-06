"""
Tools API - Enable/disable tools for neurons
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from pydantic import BaseModel

from ..tools import SSHTool, HTTPTool, FileSystemTool
from ..core.auth import get_current_user

router = APIRouter()


# Available tools registry
AVAILABLE_TOOLS = {
    "ssh": SSHTool,
    "http": HTTPTool,
    "filesystem": FileSystemTool
}


class ToolInfo(BaseModel):
    """Tool information"""
    name: str
    description: str
    category: str
    risk_level: str
    requires_confirmation: bool
    parameters: List[Dict[str, Any]]


@router.get("/tools", response_model=List[ToolInfo])
async def list_available_tools(
    current_user: dict = Depends(get_current_user)
):
    """Get list of available tools"""
    tools_info = []

    for tool_name, tool_class in AVAILABLE_TOOLS.items():
        tool_instance = tool_class()
        schema = tool_instance.schema

        tools_info.append(ToolInfo(
            name=schema.name,
            description=schema.description,
            category=schema.category.value,
            risk_level=schema.risk_level.value,
            requires_confirmation=schema.requires_confirmation,
            parameters=[p.dict() for p in schema.parameters]
        ))

    return tools_info


@router.get("/tools/{tool_name}")
async def get_tool_details(
    tool_name: str,
    current_user: dict = Depends(get_current_user)
):
    """Get detailed information about a specific tool"""
    if tool_name not in AVAILABLE_TOOLS:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")

    tool_class = AVAILABLE_TOOLS[tool_name]
    tool_instance = tool_class()

    return {
        "name": tool_instance.name,
        "schema": tool_instance.schema.dict(),
        "langchain_compatible": True
    }


async def get_tools_for_llm(neuron_config: Dict[str, Any]) -> List:
    """Get all tools for a neuron (LangChain + MCP)

    This is called by neuron.py when setting up the LLM

    Returns:
        Combined list of LangChain and MCP tools
    """
    tools = []

    # 1. LangChain tools (our custom implementations)
    ssh_tool = SSHTool()
    tools.append(ssh_tool.to_langchain_tool())

    http_tool = HTTPTool()
    tools.append(http_tool.to_langchain_tool())

    fs_tool = FileSystemTool()
    tools.append(fs_tool.to_langchain_tool())

    # 2. MCP tools (battle-tested integrations)
    try:
        from ..tools.mcp_adapter import get_mcp_adapter

        mcp_adapter = await get_mcp_adapter()

        # Initialize if not already done
        if not mcp_adapter.client:
            from ..tools.mcp_adapter import initialize_mcp_servers
            await initialize_mcp_servers()

        # Get MCP tools
        mcp_tools = await mcp_adapter.get_tools()
        tools.extend(mcp_tools)

    except Exception as e:
        # MCP tools are optional - don't fail if unavailable
        import logging
        logging.getLogger(__name__).warning(f"MCP tools not available: {e}")

    return tools
