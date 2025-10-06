"""
BRANE LLM Tool Integration
Maps LLM function calling to the BRANE tool system for seamless AI-powered execution
"""

import json
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
import asyncio
from uuid import UUID
import litellm
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

from backend.models.tool_system import Tool, ToolPermission, ToolExecution
from backend.services.tool_executor import ToolExecutor
from backend.schemas.tool_system import ToolExecutionRequest, ToolDiscovery
from backend.core.memory import MemoryManager
from backend.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class LLMToolCall:
    """Represents a tool call from an LLM"""
    name: str
    arguments: Dict[str, Any]
    call_id: Optional[str] = None


class LLMToolMapper:
    """
    Maps between LLM function calling formats and BRANE tool system
    Supports OpenAI, Anthropic, and other providers via LiteLLM
    """

    def __init__(self):
        self.executor = ToolExecutor()
        self.memory_manager = MemoryManager()
        self.tool_cache: Dict[str, Tool] = {}

    def tool_to_openai_function(self, tool: Tool) -> Dict[str, Any]:
        """
        Convert BRANE tool to OpenAI function calling format
        """
        # Transform JSON Schema to OpenAI function parameters
        parameters = tool.input_schema.copy()

        # OpenAI expects specific format
        if "properties" not in parameters:
            parameters = {
                "type": "object",
                "properties": parameters,
                "required": []
            }

        return {
            "name": tool.name,
            "description": tool.description,
            "parameters": parameters
        }

    def tool_to_anthropic_tool(self, tool: Tool) -> Dict[str, Any]:
        """
        Convert BRANE tool to Anthropic tool use format
        """
        return {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.input_schema
        }

    def tools_to_litellm_format(self, tools: List[Tool], provider: str) -> List[Dict[str, Any]]:
        """
        Convert BRANE tools to LiteLLM format based on provider
        """
        if provider in ["openai", "azure", "together"]:
            return [self.tool_to_openai_function(tool) for tool in tools]
        elif provider in ["anthropic", "claude"]:
            return [self.tool_to_anthropic_tool(tool) for tool in tools]
        else:
            # Default to OpenAI format
            return [self.tool_to_openai_function(tool) for tool in tools]

    async def get_available_tools_for_neuron(
        self,
        neuron_id: UUID,
        user_id: UUID,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Tool]:
        """
        Get all tools available to a neuron based on permissions and context
        """
        from backend.database import get_async_session
        from sqlalchemy import select, and_

        async with get_async_session() as db:
            # Get all active permissions for this neuron
            query = select(ToolPermission).where(
                and_(
                    ToolPermission.neuron_id == neuron_id,
                    ToolPermission.user_id == user_id,
                    ToolPermission.active == True
                )
            )
            result = await db.execute(query)
            permissions = result.scalars().all()

            # Get corresponding tools
            tool_ids = [p.tool_id for p in permissions if p.is_valid]
            if not tool_ids:
                return []

            tools_query = select(Tool).where(
                and_(
                    Tool.id.in_(tool_ids),
                    Tool.enabled == True,
                    Tool.deprecated == False
                )
            )
            tools_result = await db.execute(tools_query)
            tools = tools_result.scalars().all()

            # Filter based on context if provided
            if context:
                tools = await self._filter_tools_by_context(tools, context)

            return tools

    async def _filter_tools_by_context(
        self,
        tools: List[Tool],
        context: Dict[str, Any]
    ) -> List[Tool]:
        """
        Filter tools based on current context and requirements
        """
        filtered = []

        for tool in tools:
            # Check privacy tier compatibility
            if "privacy_tier" in context:
                if tool.privacy_tier > context["privacy_tier"]:
                    continue

            # Check if tool category matches context needs
            if "required_categories" in context:
                if tool.category not in context["required_categories"]:
                    continue

            # Check if tool is safe for current context
            if context.get("safe_mode", False) and tool.dangerous:
                continue

            filtered.append(tool)

        return filtered

    async def suggest_tools(
        self,
        query: str,
        user_context: Dict[str, Any],
        available_tools: List[ToolDiscovery],
        max_suggestions: int = 5
    ) -> List[UUID]:
        """
        Use LLM to suggest relevant tools based on user query and context
        """
        # Prepare tool descriptions
        tool_descriptions = [
            f"- {tool.display_name} ({tool.category}): {tool.description}"
            for tool in available_tools
        ]

        prompt = f"""
        User Query: {query}

        User Context:
        - Recent activities: {user_context.get('recent_activities', [])}
        - Current project: {user_context.get('current_project', 'Unknown')}

        Available Tools:
        {chr(10).join(tool_descriptions)}

        Based on the user's query and context, suggest the {max_suggestions} most relevant tools.
        Return only the tool names as a JSON array.
        """

        try:
            # Use LiteLLM for flexibility across providers
            response = await litellm.acompletion(
                model="gpt-4o-mini",  # Fast, cheap model for suggestions
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that suggests relevant tools."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )

            suggestions = json.loads(response.choices[0].message.content)
            tool_names = suggestions.get("tools", [])

            # Map names back to UUIDs
            tool_map = {tool.display_name: tool.id for tool in available_tools}
            return [tool_map[name] for name in tool_names if name in tool_map][:max_suggestions]

        except Exception as e:
            logger.error(f"Failed to get tool suggestions: {e}")
            return []

    async def execute_llm_tool_call(
        self,
        tool_call: LLMToolCall,
        neuron_id: UUID,
        user_id: UUID,
        session_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Execute a tool call from an LLM
        """
        from backend.database import get_async_session
        from sqlalchemy import select, and_

        async with get_async_session() as db:
            # Find the tool by name
            tool_query = select(Tool).where(
                and_(
                    Tool.name == tool_call.name,
                    Tool.enabled == True
                )
            )
            tool_result = await db.execute(tool_query)
            tool = tool_result.scalar_one_or_none()

            if not tool:
                return {
                    "error": f"Tool '{tool_call.name}' not found",
                    "call_id": tool_call.call_id
                }

            # Check permission
            perm_query = select(ToolPermission).where(
                and_(
                    ToolPermission.neuron_id == neuron_id,
                    ToolPermission.user_id == user_id,
                    ToolPermission.tool_id == tool.id,
                    ToolPermission.active == True
                )
            )
            perm_result = await db.execute(perm_query)
            permission = perm_result.scalar_one_or_none()

            if not permission or not permission.is_valid:
                return {
                    "error": f"No valid permission for tool '{tool_call.name}'",
                    "call_id": tool_call.call_id
                }

            # Get memory context
            memory_context = await self.memory_manager.get_neuron_context(neuron_id)

            # Create execution request
            execution_request = ToolExecutionRequest(
                tool_id=tool.id,
                neuron_id=neuron_id,
                parameters=tool_call.arguments,
                session_id=session_id,
                memory_context=memory_context
            )

            # Execute the tool
            try:
                result = await self.executor.execute(
                    tool=tool,
                    parameters=tool_call.arguments,
                    dry_run=False
                )

                return {
                    "result": result.output,
                    "call_id": tool_call.call_id,
                    "duration_ms": int(result.duration * 1000),
                    "tool_name": tool.display_name
                }

            except Exception as e:
                logger.error(f"Tool execution failed: {e}")
                return {
                    "error": str(e),
                    "call_id": tool_call.call_id,
                    "tool_name": tool.display_name
                }


class NeuronWithTools:
    """
    Example of a BRANE Neuron that can use tools via LLM function calling
    """

    def __init__(self, neuron_id: UUID, user_id: UUID, model: str = "gpt-4o"):
        self.neuron_id = neuron_id
        self.user_id = user_id
        self.model = model
        self.tool_mapper = LLMToolMapper()
        self.memory_manager = MemoryManager()
        self.session_id = UUID()

    async def process_message(self, message: str) -> str:
        """
        Process a user message with tool access
        """
        # Get available tools
        tools = await self.tool_mapper.get_available_tools_for_neuron(
            self.neuron_id,
            self.user_id
        )

        if not tools:
            # No tools available, process as regular message
            return await self._process_without_tools(message)

        # Convert tools to LLM format
        llm_tools = self.tool_mapper.tools_to_litellm_format(tools, "openai")

        # Get conversation history from memory
        history = await self.memory_manager.get_conversation_history(
            self.neuron_id,
            limit=10
        )

        # Prepare messages
        messages = [
            {"role": "system", "content": self._get_system_prompt()},
            *history,
            {"role": "user", "content": message}
        ]

        try:
            # Call LLM with tools
            response = await litellm.acompletion(
                model=self.model,
                messages=messages,
                tools=llm_tools,
                tool_choice="auto"
            )

            # Check if tools were called
            message = response.choices[0].message

            if hasattr(message, 'tool_calls') and message.tool_calls:
                # Execute tool calls
                tool_results = []
                for tool_call in message.tool_calls:
                    llm_call = LLMToolCall(
                        name=tool_call.function.name,
                        arguments=json.loads(tool_call.function.arguments),
                        call_id=tool_call.id
                    )

                    result = await self.tool_mapper.execute_llm_tool_call(
                        llm_call,
                        self.neuron_id,
                        self.user_id,
                        self.session_id
                    )
                    tool_results.append(result)

                # Send tool results back to LLM
                messages.append(message)
                for result in tool_results:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": result.get("call_id"),
                        "content": json.dumps(result)
                    })

                # Get final response
                final_response = await litellm.acompletion(
                    model=self.model,
                    messages=messages
                )

                return final_response.choices[0].message.content

            else:
                # No tools called, return direct response
                return message.content

        except Exception as e:
            logger.error(f"Failed to process message with tools: {e}")
            return f"I encountered an error: {str(e)}"

    async def _process_without_tools(self, message: str) -> str:
        """
        Process message without tool access
        """
        response = await litellm.acompletion(
            model=self.model,
            messages=[
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": message}
            ]
        )
        return response.choices[0].message.content

    def _get_system_prompt(self) -> str:
        """
        Get the system prompt for the neuron
        """
        return """
        You are a BRANE Neuron - an AI assistant with access to various tools and capabilities.
        You can interact with the digital and physical world through the tools available to you.

        When using tools:
        1. Always check if you have the necessary permissions
        2. Use tools responsibly and safely
        3. Provide clear explanations of what you're doing
        4. Handle errors gracefully
        5. Respect user privacy and security constraints

        Your responses should be helpful, accurate, and transparent about any actions you take.
        """


# Example usage
async def example_usage():
    """
    Example of how the LLM tool integration works
    """
    # Create a neuron with tools
    neuron = NeuronWithTools(
        neuron_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
        user_id=UUID("987fcdeb-51a2-43f1-b671-426614174000"),
        model="gpt-4o"
    )

    # Process a message that might trigger tool use
    response = await neuron.process_message(
        "Can you check the weather and then create a reminder for me to bring an umbrella if it's going to rain?"
    )

    print(response)

    # The neuron will:
    # 1. Identify needed tools (weather API, reminder creation)
    # 2. Check permissions
    # 3. Execute tools with proper parameters
    # 4. Synthesize results into a natural response


if __name__ == "__main__":
    asyncio.run(example_usage())