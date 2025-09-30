"""
LLM Broker - Model-Agnostic Interface
Supports Ollama, OpenAI, Anthropic, and any LiteLLM-compatible provider
"""

import logging
from typing import AsyncIterator, Dict, List, Optional
import litellm
from litellm import acompletion

logger = logging.getLogger(__name__)


class LLMBroker:
    """
    Universal interface to ANY LLM provider.
    Handles tool calling across different APIs with capability detection.
    """

    def __init__(self, config: Dict):
        """
        Initialize LLM Broker.

        Args:
            config: Model configuration dict
                {
                    "provider": "ollama" | "openai" | "anthropic" | "together" | ...,
                    "model": "llama3.2" | "gpt-4o" | "claude-3-5-sonnet-20241022",
                    "endpoint": "http://localhost:11434" (optional for Ollama),
                    "api_key": "..." (optional, can use env vars),
                    "temperature": 0.7,
                    "top_p": 0.9
                }
        """
        self.provider = config.get("provider", "ollama")
        self.model = config.get("model")
        self.endpoint = config.get("endpoint")
        self.api_key = config.get("api_key")
        self.temperature = config.get("temperature", 0.7)
        self.top_p = config.get("top_p", 0.9)

        # Capability cache
        self.capabilities: Optional[Dict] = None

        # Configure LiteLLM
        litellm.suppress_debug_info = True
        if self.endpoint:
            litellm.api_base = self.endpoint

        logger.info(f"LLM Broker initialized: {self.provider}/{self.model}")

    async def initialize(self):
        """Detect model capabilities (cached)"""
        # TODO: Implement capability detection
        # For now, assume modern capabilities
        self.capabilities = {
            "native_tools": self._supports_native_tools(),
            "streaming": True,
            "vision": False,  # Detect based on model name
            "context_window": self._get_context_window()
        }

        logger.info(f"Model capabilities: {self.capabilities}")

    def _supports_native_tools(self) -> bool:
        """Check if model supports native tool/function calling"""
        # OpenAI, Anthropic, and some others support native tools
        native_providers = ["openai", "anthropic", "together", "groq"]

        return self.provider in native_providers

    def _get_context_window(self) -> int:
        """Get model context window size"""
        # Common context windows
        context_windows = {
            "gpt-4": 8192,
            "gpt-4-turbo": 128000,
            "gpt-4o": 128000,
            "claude-3-5-sonnet": 200000,
            "claude-3-opus": 200000,
            "llama3": 8192,
            "llama3.1": 128000,
            "llama3.2": 128000,
        }

        # Try to match model name
        for key, window in context_windows.items():
            if key in self.model.lower():
                return window

        # Default fallback
        return 4096

    async def stream(
        self,
        prompt: str,
        tools: Optional[List[Dict]] = None,
        max_tokens: int = 2048
    ) -> AsyncIterator[str]:
        """
        Stream LLM response.

        Args:
            prompt: Full prompt (with system, context, user message)
            tools: List of MCP-compatible tool definitions
            max_tokens: Maximum tokens to generate

        Yields:
            Response chunks as they arrive
        """
        try:
            # Build messages
            messages = [{"role": "user", "content": prompt}]

            # Prepare LiteLLM call args
            call_args = {
                "model": self._get_litellm_model(),
                "messages": messages,
                "temperature": self.temperature,
                "top_p": self.top_p,
                "max_tokens": max_tokens,
                "stream": True
            }

            # Add API key if provided
            if self.api_key:
                call_args["api_key"] = self.api_key

            # Add tools if supported and provided
            if tools and self.capabilities.get("native_tools"):
                call_args["tools"] = self._convert_tools_to_provider_format(tools)
            elif tools:
                # Fallback: inject tools in prompt (ReAct style)
                logger.debug("Model doesn't support native tools, using prompt engineering")
                prompt_with_tools = self._inject_tools_in_prompt(prompt, tools)
                messages[0]["content"] = prompt_with_tools

            # Stream response
            response = await acompletion(**call_args)

            async for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"LLM streaming error: {e}")
            raise

    def _get_litellm_model(self) -> str:
        """
        Convert provider/model to LiteLLM format.

        Examples:
            ollama/llama3.2
            gpt-4o
            anthropic/claude-3-5-sonnet-20241022
        """
        if self.provider == "ollama":
            return f"ollama/{self.model}"
        elif self.provider == "openai":
            return self.model
        elif self.provider == "anthropic":
            return f"anthropic/{self.model}"
        elif self.provider == "together":
            return f"together_ai/{self.model}"
        else:
            # Let LiteLLM handle it
            return f"{self.provider}/{self.model}"

    def _convert_tools_to_provider_format(self, tools: List[Dict]) -> List[Dict]:
        """
        Convert MCP tool format to provider-specific format.
        LiteLLM handles most conversion, but we normalize to OpenAI format.
        """
        # MCP format is similar to OpenAI format
        converted = []

        for tool in tools:
            converted.append({
                "type": "function",
                "function": {
                    "name": tool.get("name"),
                    "description": tool.get("description"),
                    "parameters": tool.get("parameters", {})
                }
            })

        return converted

    def _inject_tools_in_prompt(self, prompt: str, tools: List[Dict]) -> str:
        """
        Inject tools into prompt for models without native tool support.
        Uses ReAct prompting pattern.
        """
        tool_descriptions = []

        for tool in tools:
            tool_desc = (
                f"- {tool['name']}: {tool['description']}\n"
                f"  Parameters: {tool.get('parameters', {})}"
            )
            tool_descriptions.append(tool_desc)

        tools_text = "\n".join(tool_descriptions)

        augmented_prompt = (
            f"{prompt}\n\n"
            f"You have access to the following tools:\n{tools_text}\n\n"
            f"To use a tool, respond in this format:\n"
            f"TOOL: tool_name\n"
            f"ARGS: {{\"param\": \"value\"}}\n\n"
            f"Otherwise, respond normally to the user."
        )

        return augmented_prompt
