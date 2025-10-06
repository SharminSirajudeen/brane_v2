"""
LLM Tools Bridge - Connect BRANE tools to any LLM provider
Converts BRANE tools → OpenAI/Anthropic/Gemini function calling format

This makes Neurons work with:
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude 3.5)
- Google (Gemini)
- Any LiteLLM-supported model
"""

from typing import List, Dict, Any, Optional
from tools.base import BaseTool, ToolParameter


def tool_to_openai_function(tool: BaseTool) -> Dict[str, Any]:
    """
    Convert BRANE tool to OpenAI function calling format.

    OpenAI format:
    {
        "type": "function",
        "function": {
            "name": "tool_name",
            "description": "What it does",
            "parameters": { JSON Schema }
        }
    }
    """
    properties = {}
    required = []

    for param in tool.schema.parameters:
        # Convert parameter to JSON Schema
        properties[param.name] = {
            "type": param.type,
            "description": param.description
        }

        if param.default is not None:
            properties[param.name]["default"] = param.default

        if param.validation:
            properties[param.name].update(param.validation)

        if param.required:
            required.append(param.name)

    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.schema.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }
    }


def tool_to_anthropic_function(tool: BaseTool) -> Dict[str, Any]:
    """
    Convert BRANE tool to Anthropic Claude function calling format.

    Anthropic format (similar to OpenAI):
    {
        "name": "tool_name",
        "description": "What it does",
        "input_schema": { JSON Schema }
    }
    """
    properties = {}
    required = []

    for param in tool.schema.parameters:
        properties[param.name] = {
            "type": param.type,
            "description": param.description
        }

        if param.validation:
            properties[param.name].update(param.validation)

        if param.required:
            required.append(param.name)

    return {
        "name": tool.name,
        "description": tool.schema.description,
        "input_schema": {
            "type": "object",
            "properties": properties,
            "required": required
        }
    }


def tool_to_gemini_function(tool: BaseTool) -> Dict[str, Any]:
    """
    Convert BRANE tool to Google Gemini function calling format.

    Gemini format:
    {
        "name": "tool_name",
        "description": "What it does",
        "parameters": { JSON Schema }
    }
    """
    properties = {}
    required = []

    for param in tool.schema.parameters:
        properties[param.name] = {
            "type": param.type,
            "description": param.description
        }

        if param.required:
            required.append(param.name)

    return {
        "name": tool.name,
        "description": tool.schema.description,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required
        }
    }


def tools_to_llm_format(tools: List[BaseTool], provider: str = "openai") -> List[Dict[str, Any]]:
    """
    Convert list of BRANE tools to LLM-specific format.

    Args:
        tools: List of BRANE tools
        provider: LLM provider ("openai", "anthropic", "gemini", "auto")

    Returns:
        List of function definitions in provider's format
    """
    converter_map = {
        "openai": tool_to_openai_function,
        "anthropic": tool_to_anthropic_function,
        "claude": tool_to_anthropic_function,  # Alias
        "gemini": tool_to_gemini_function,
        "google": tool_to_gemini_function,  # Alias
    }

    converter = converter_map.get(provider.lower(), tool_to_openai_function)
    return [converter(tool) for tool in tools]


async def execute_tool_call(
    tool_name: str,
    arguments: Dict[str, Any],
    available_tools: List[BaseTool],
    neuron_id: str
) -> Dict[str, Any]:
    """
    Execute a tool call from LLM response.

    Args:
        tool_name: Name of tool to execute
        arguments: Tool parameters from LLM
        available_tools: List of tools available to this neuron
        neuron_id: ID of neuron making the call

    Returns:
        Tool execution result
    """
    # Find the tool
    tool = next((t for t in available_tools if t.name == tool_name), None)

    if not tool:
        return {
            "success": False,
            "error": f"Tool '{tool_name}' not found or not authorized for this neuron"
        }

    # Validate parameters
    try:
        is_valid = await tool.validate_parameters(**arguments)
        if not is_valid:
            return {
                "success": False,
                "error": "Invalid parameters for tool"
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"Parameter validation failed: {str(e)}"
        }

    # Execute tool
    try:
        result = await tool.execute(**arguments)
        return result
    except Exception as e:
        return {
            "success": False,
            "error": f"Tool execution failed: {str(e)}"
        }


class NeuronToolExecutor:
    """
    Manages tool execution for a specific Neuron.
    Handles LLM function calling responses and executes tools.
    """

    def __init__(self, neuron_id: str, available_tools: List[BaseTool]):
        self.neuron_id = neuron_id
        self.available_tools = available_tools
        self._execution_history = []

    def get_tools_for_llm(self, provider: str = "openai") -> List[Dict[str, Any]]:
        """Get tools in LLM-specific format"""
        return tools_to_llm_format(self.available_tools, provider)

    async def process_llm_response(self, llm_response: Dict[str, Any], provider: str = "openai") -> Optional[Dict[str, Any]]:
        """
        Process LLM response and execute any tool calls.

        Args:
            llm_response: Response from LLM (OpenAI/Anthropic/Gemini format)
            provider: LLM provider to determine response format

        Returns:
            Tool execution result if tool was called, None otherwise
        """
        if provider == "openai":
            return await self._process_openai_response(llm_response)
        elif provider in ["anthropic", "claude"]:
            return await self._process_anthropic_response(llm_response)
        elif provider in ["gemini", "google"]:
            return await self._process_gemini_response(llm_response)
        else:
            # Try OpenAI format as default
            return await self._process_openai_response(llm_response)

    async def _process_openai_response(self, response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process OpenAI format response"""
        # OpenAI puts tool calls in message.tool_calls
        message = response.get("choices", [{}])[0].get("message", {})
        tool_calls = message.get("tool_calls", [])

        if not tool_calls:
            return None

        # Execute first tool call (can extend to handle multiple)
        tool_call = tool_calls[0]
        function = tool_call.get("function", {})

        tool_name = function.get("name")
        arguments = json.loads(function.get("arguments", "{}"))

        result = await execute_tool_call(
            tool_name=tool_name,
            arguments=arguments,
            available_tools=self.available_tools,
            neuron_id=self.neuron_id
        )

        self._execution_history.append({
            "tool": tool_name,
            "arguments": arguments,
            "result": result
        })

        return result

    async def _process_anthropic_response(self, response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process Anthropic Claude format response"""
        # Claude puts tool use in content blocks
        content = response.get("content", [])

        for block in content:
            if block.get("type") == "tool_use":
                tool_name = block.get("name")
                arguments = block.get("input", {})

                result = await execute_tool_call(
                    tool_name=tool_name,
                    arguments=arguments,
                    available_tools=self.available_tools,
                    neuron_id=self.neuron_id
                )

                self._execution_history.append({
                    "tool": tool_name,
                    "arguments": arguments,
                    "result": result
                })

                return result

        return None

    async def _process_gemini_response(self, response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process Google Gemini format response"""
        # Gemini format similar to OpenAI
        function_call = response.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("function_call")

        if not function_call:
            return None

        tool_name = function_call.get("name")
        arguments = function_call.get("args", {})

        result = await execute_tool_call(
            tool_name=tool_name,
            arguments=arguments,
            available_tools=self.available_tools,
            neuron_id=self.neuron_id
        )

        self._execution_history.append({
            "tool": tool_name,
            "arguments": arguments,
            "result": result
        })

        return result

    def get_execution_history(self) -> List[Dict[str, Any]]:
        """Get history of tool executions"""
        return self._execution_history
