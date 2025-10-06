"""
LLM Abstraction Layer for BRANE Neurons
Provides transparent support for multiple LLM providers
"""

import os
import json
import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator
from enum import Enum
from abc import ABC, abstractmethod
import aiohttp
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

class LLMProvider(Enum):
    """Supported LLM providers"""
    OLLAMA = "ollama"
    VLLM = "vllm"
    LLAMACPP = "llamacpp"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LITELLM = "litellm"
    LOCAL = "local"

class ModelCapability(Enum):
    """Model capabilities"""
    FUNCTION_CALLING = "function_calling"
    STREAMING = "streaming"
    VISION = "vision"
    EMBEDDINGS = "embeddings"
    LONG_CONTEXT = "long_context"  # >32k tokens
    JSON_MODE = "json_mode"

class LLMConfig(BaseModel):
    """LLM configuration"""
    provider: LLMProvider
    model: str
    api_base: Optional[str] = None
    api_key: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2000
    top_p: float = 0.9
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    timeout: int = 120
    retry_attempts: int = 3
    streaming: bool = False

class Message(BaseModel):
    """Chat message"""
    role: str  # 'system', 'user', 'assistant', 'function'
    content: str
    name: Optional[str] = None  # For function messages
    function_call: Optional[Dict] = None  # For assistant function calls

class Function(BaseModel):
    """Function definition for function calling"""
    name: str
    description: str
    parameters: Dict[str, Any]

class LLMResponse(BaseModel):
    """LLM response"""
    content: str
    function_call: Optional[Dict] = None
    finish_reason: str = "stop"
    usage: Optional[Dict[str, int]] = None

# Base LLM Provider
class BaseLLMProvider(ABC):
    """Base class for LLM providers"""

    def __init__(self, config: LLMConfig):
        self.config = config

    @abstractmethod
    async def complete(
        self,
        messages: List[Message],
        functions: Optional[List[Function]] = None
    ) -> LLMResponse:
        """Generate completion"""
        pass

    @abstractmethod
    async def stream(
        self,
        messages: List[Message],
        functions: Optional[List[Function]] = None
    ) -> AsyncGenerator[str, None]:
        """Stream completion"""
        pass

    @abstractmethod
    def get_capabilities(self) -> List[ModelCapability]:
        """Get model capabilities"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if provider is available"""
        pass

# Ollama Provider
class OllamaProvider(BaseLLMProvider):
    """Ollama provider implementation"""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.api_base = config.api_base or "http://localhost:11434"

    async def complete(
        self,
        messages: List[Message],
        functions: Optional[List[Function]] = None
    ) -> LLMResponse:
        """Generate completion using Ollama"""

        # Convert messages to Ollama format
        ollama_messages = []
        for msg in messages:
            ollama_messages.append({
                "role": msg.role,
                "content": msg.content
            })

        # Handle function calling for supported models
        if functions and self._supports_functions():
            return await self._complete_with_functions(ollama_messages, functions)

        # Standard completion
        url = f"{self.api_base}/api/chat"
        payload = {
            "model": self.config.model,
            "messages": ollama_messages,
            "options": {
                "temperature": self.config.temperature,
                "top_p": self.config.top_p,
                "num_predict": self.config.max_tokens
            },
            "stream": False
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=self.config.timeout)) as response:
                if response.status == 200:
                    data = await response.json()
                    return LLMResponse(
                        content=data["message"]["content"],
                        usage={
                            "prompt_tokens": data.get("prompt_eval_count", 0),
                            "completion_tokens": data.get("eval_count", 0),
                            "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
                        }
                    )
                else:
                    error = await response.text()
                    raise Exception(f"Ollama error: {error}")

    async def _complete_with_functions(
        self,
        messages: List[Dict],
        functions: List[Function]
    ) -> LLMResponse:
        """Handle function calling for Ollama"""

        # Only Llama 3.1+ and Mistral Large support native function calling
        if "llama3.1" in self.config.model.lower() or "llama3.2" in self.config.model.lower():
            # Use native function calling
            tools = []
            for func in functions:
                tools.append({
                    "type": "function",
                    "function": {
                        "name": func.name,
                        "description": func.description,
                        "parameters": func.parameters
                    }
                })

            url = f"{self.api_base}/api/chat"
            payload = {
                "model": self.config.model,
                "messages": messages,
                "tools": tools,
                "options": {
                    "temperature": self.config.temperature,
                    "top_p": self.config.top_p
                },
                "stream": False
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=self.config.timeout)) as response:
                    if response.status == 200:
                        data = await response.json()
                        message = data["message"]

                        # Check for function call
                        if message.get("tool_calls"):
                            tool_call = message["tool_calls"][0]
                            return LLMResponse(
                                content="",
                                function_call={
                                    "name": tool_call["function"]["name"],
                                    "arguments": json.dumps(tool_call["function"]["arguments"])
                                }
                            )
                        else:
                            return LLMResponse(content=message["content"])
                    else:
                        error = await response.text()
                        raise Exception(f"Ollama error: {error}")
        else:
            # Fall back to ReAct pattern
            return await self._complete_with_react(messages, functions)

    async def _complete_with_react(
        self,
        messages: List[Dict],
        functions: List[Function]
    ) -> LLMResponse:
        """Use ReAct pattern for models without native function calling"""

        # Build ReAct prompt
        tools_description = self._build_react_prompt(functions)

        # Modify system message to include ReAct instructions
        if messages and messages[0]["role"] == "system":
            messages[0]["content"] += f"\n\n{tools_description}"
        else:
            messages.insert(0, {
                "role": "system",
                "content": tools_description
            })

        # Get completion
        url = f"{self.api_base}/api/chat"
        payload = {
            "model": self.config.model,
            "messages": messages,
            "options": {
                "temperature": self.config.temperature,
                "stop": ["Observation:", "Final Answer:"]
            },
            "stream": False
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=self.config.timeout)) as response:
                if response.status == 200:
                    data = await response.json()
                    content = data["message"]["content"]

                    # Parse ReAct format
                    if "Action:" in content and "Action Input:" in content:
                        import re
                        action_match = re.search(r"Action: (.+)", content)
                        input_match = re.search(r"Action Input: (.+)", content)

                        if action_match and input_match:
                            return LLMResponse(
                                content="",
                                function_call={
                                    "name": action_match.group(1).strip(),
                                    "arguments": input_match.group(1).strip()
                                }
                            )

                    return LLMResponse(content=content)
                else:
                    error = await response.text()
                    raise Exception(f"Ollama error: {error}")

    def _build_react_prompt(self, functions: List[Function]) -> str:
        """Build ReAct prompt"""
        tools = []
        for func in functions:
            params = ", ".join(func.parameters.get("properties", {}).keys())
            tools.append(f"- {func.name}({params}): {func.description}")

        return f"""You have access to the following tools:
{chr(10).join(tools)}

Use this format:
Thought: reasoning about what to do
Action: tool_name
Action Input: {{"param": "value"}}
Observation: [tool result will be provided]
... (repeat as needed)
Thought: I have the final answer
Final Answer: [your response]"""

    async def stream(
        self,
        messages: List[Message],
        functions: Optional[List[Function]] = None
    ) -> AsyncGenerator[str, None]:
        """Stream completion from Ollama"""

        ollama_messages = [{"role": msg.role, "content": msg.content} for msg in messages]

        url = f"{self.api_base}/api/chat"
        payload = {
            "model": self.config.model,
            "messages": ollama_messages,
            "options": {
                "temperature": self.config.temperature,
                "top_p": self.config.top_p
            },
            "stream": True
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                async for line in response.content:
                    if line:
                        try:
                            data = json.loads(line)
                            if data.get("message", {}).get("content"):
                                yield data["message"]["content"]
                        except json.JSONDecodeError:
                            continue

    def get_capabilities(self) -> List[ModelCapability]:
        """Get Ollama model capabilities"""
        capabilities = [ModelCapability.STREAMING]

        model_lower = self.config.model.lower()

        if "llama3.1" in model_lower or "llama3.2" in model_lower:
            capabilities.append(ModelCapability.FUNCTION_CALLING)

        if "llava" in model_lower or "bakllava" in model_lower:
            capabilities.append(ModelCapability.VISION)

        if any(x in model_lower for x in ["70b", "65b", "34b"]):
            capabilities.append(ModelCapability.LONG_CONTEXT)

        return capabilities

    async def health_check(self) -> bool:
        """Check if Ollama is available"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_base}/api/tags", timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        data = await response.json()
                        models = [m["name"] for m in data.get("models", [])]
                        return self.config.model in models
            return False
        except:
            return False

    def _supports_functions(self) -> bool:
        """Check if model supports function calling"""
        return ModelCapability.FUNCTION_CALLING in self.get_capabilities()

# vLLM Provider
class VLLMProvider(BaseLLMProvider):
    """vLLM provider implementation"""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.api_base = config.api_base or "http://localhost:8000"

    async def complete(
        self,
        messages: List[Message],
        functions: Optional[List[Function]] = None
    ) -> LLMResponse:
        """Generate completion using vLLM"""

        # vLLM uses OpenAI-compatible API
        url = f"{self.api_base}/v1/chat/completions"

        # Convert messages
        openai_messages = []
        for msg in messages:
            message = {"role": msg.role, "content": msg.content}
            if msg.name:
                message["name"] = msg.name
            openai_messages.append(message)

        payload = {
            "model": self.config.model,
            "messages": openai_messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "top_p": self.config.top_p
        }

        # Add functions if supported
        if functions and self._supports_functions():
            payload["functions"] = [
                {
                    "name": func.name,
                    "description": func.description,
                    "parameters": func.parameters
                }
                for func in functions
            ]

        async with aiohttp.ClientSession() as session:
            headers = {}
            if self.config.api_key:
                headers["Authorization"] = f"Bearer {self.config.api_key}"

            async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=self.config.timeout)) as response:
                if response.status == 200:
                    data = await response.json()
                    choice = data["choices"][0]
                    message = choice["message"]

                    return LLMResponse(
                        content=message.get("content", ""),
                        function_call=message.get("function_call"),
                        finish_reason=choice.get("finish_reason", "stop"),
                        usage=data.get("usage")
                    )
                else:
                    error = await response.text()
                    raise Exception(f"vLLM error: {error}")

    async def stream(
        self,
        messages: List[Message],
        functions: Optional[List[Function]] = None
    ) -> AsyncGenerator[str, None]:
        """Stream completion from vLLM"""

        url = f"{self.api_base}/v1/chat/completions"

        openai_messages = [{"role": msg.role, "content": msg.content} for msg in messages]

        payload = {
            "model": self.config.model,
            "messages": openai_messages,
            "temperature": self.config.temperature,
            "stream": True
        }

        async with aiohttp.ClientSession() as session:
            headers = {}
            if self.config.api_key:
                headers["Authorization"] = f"Bearer {self.config.api_key}"

            async with session.post(url, json=payload, headers=headers) as response:
                async for line in response.content:
                    if line and line.startswith(b"data: "):
                        try:
                            data = json.loads(line[6:])
                            if data.get("choices", [{}])[0].get("delta", {}).get("content"):
                                yield data["choices"][0]["delta"]["content"]
                        except:
                            continue

    def get_capabilities(self) -> List[ModelCapability]:
        """Get vLLM model capabilities"""
        return [
            ModelCapability.STREAMING,
            ModelCapability.LONG_CONTEXT,
            ModelCapability.JSON_MODE
        ]

    async def health_check(self) -> bool:
        """Check if vLLM is available"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_base}/v1/models", timeout=aiohttp.ClientTimeout(total=5)) as response:
                    return response.status == 200
        except:
            return False

    def _supports_functions(self) -> bool:
        """Check if model supports function calling"""
        # vLLM supports function calling for compatible models
        model_lower = self.config.model.lower()
        return any(x in model_lower for x in ["llama-3", "mistral", "mixtral"])

# LiteLLM Provider (Universal)
class LiteLLMProvider(BaseLLMProvider):
    """LiteLLM provider - supports 100+ LLM providers"""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        try:
            import litellm
            self.litellm = litellm
            # Configure LiteLLM
            if config.api_key:
                os.environ["OPENAI_API_KEY"] = config.api_key
        except ImportError:
            raise Exception("LiteLLM not installed. Run: pip install litellm")

    async def complete(
        self,
        messages: List[Message],
        functions: Optional[List[Function]] = None
    ) -> LLMResponse:
        """Generate completion using LiteLLM"""

        # Convert messages
        litellm_messages = []
        for msg in messages:
            message = {"role": msg.role, "content": msg.content}
            if msg.name:
                message["name"] = msg.name
            if msg.function_call:
                message["function_call"] = msg.function_call
            litellm_messages.append(message)

        kwargs = {
            "model": self.config.model,
            "messages": litellm_messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "top_p": self.config.top_p,
            "frequency_penalty": self.config.frequency_penalty,
            "presence_penalty": self.config.presence_penalty
        }

        # Add functions if provided
        if functions:
            kwargs["functions"] = [
                {
                    "name": func.name,
                    "description": func.description,
                    "parameters": func.parameters
                }
                for func in functions
            ]

        # Add API base if custom endpoint
        if self.config.api_base:
            kwargs["api_base"] = self.config.api_base

        try:
            # Use async completion
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                self.litellm.completion,
                **kwargs
            )

            choice = response.choices[0]
            return LLMResponse(
                content=choice.message.content or "",
                function_call=choice.message.function_call if hasattr(choice.message, 'function_call') else None,
                finish_reason=choice.finish_reason,
                usage=response.usage._asdict() if response.usage else None
            )
        except Exception as e:
            logger.error(f"LiteLLM error: {e}")
            raise

    async def stream(
        self,
        messages: List[Message],
        functions: Optional[List[Function]] = None
    ) -> AsyncGenerator[str, None]:
        """Stream completion from LiteLLM"""

        litellm_messages = [{"role": msg.role, "content": msg.content} for msg in messages]

        kwargs = {
            "model": self.config.model,
            "messages": litellm_messages,
            "temperature": self.config.temperature,
            "stream": True
        }

        if self.config.api_base:
            kwargs["api_base"] = self.config.api_base

        # LiteLLM streaming
        response = self.litellm.completion(**kwargs)

        for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def get_capabilities(self) -> List[ModelCapability]:
        """Get LiteLLM model capabilities"""
        # LiteLLM supports most capabilities depending on the model
        capabilities = [ModelCapability.STREAMING]

        model_lower = self.config.model.lower()

        if any(x in model_lower for x in ["gpt", "claude", "llama-3", "mistral"]):
            capabilities.append(ModelCapability.FUNCTION_CALLING)

        if "gpt-4" in model_lower or "claude" in model_lower:
            capabilities.append(ModelCapability.VISION)
            capabilities.append(ModelCapability.LONG_CONTEXT)

        if "gpt" in model_lower:
            capabilities.append(ModelCapability.JSON_MODE)

        return capabilities

    async def health_check(self) -> bool:
        """Check if LiteLLM can reach the provider"""
        try:
            # Try a minimal completion
            await self.complete([Message(role="user", content="test")], None)
            return True
        except:
            return False

# LLM Router
class LLMRouter:
    """Routes requests to appropriate LLM provider"""

    def __init__(self, preferred_provider: Optional[LLMProvider] = None):
        self.preferred_provider = preferred_provider
        self.providers: Dict[LLMProvider, BaseLLMProvider] = {}
        self.provider_health: Dict[LLMProvider, bool] = {}

    def register_provider(self, provider: LLMProvider, instance: BaseLLMProvider):
        """Register a provider"""
        self.providers[provider] = instance
        self.provider_health[provider] = False

    async def initialize(self):
        """Initialize and health check all providers"""
        health_checks = []
        for provider, instance in self.providers.items():
            health_checks.append(self._check_provider_health(provider, instance))

        await asyncio.gather(*health_checks)

    async def _check_provider_health(self, provider: LLMProvider, instance: BaseLLMProvider):
        """Check health of a provider"""
        try:
            self.provider_health[provider] = await instance.health_check()
            if self.provider_health[provider]:
                logger.info(f"Provider {provider.value} is healthy")
            else:
                logger.warning(f"Provider {provider.value} is unhealthy")
        except Exception as e:
            logger.error(f"Health check failed for {provider.value}: {e}")
            self.provider_health[provider] = False

    async def complete(
        self,
        messages: List[Message],
        functions: Optional[List[Function]] = None,
        required_capabilities: Optional[List[ModelCapability]] = None
    ) -> LLMResponse:
        """Route completion request to best available provider"""

        # Try preferred provider first
        if self.preferred_provider and self.provider_health.get(self.preferred_provider):
            provider = self.providers[self.preferred_provider]

            # Check capabilities
            if not required_capabilities or all(
                cap in provider.get_capabilities() for cap in required_capabilities
            ):
                try:
                    return await provider.complete(messages, functions)
                except Exception as e:
                    logger.warning(f"Preferred provider failed: {e}")

        # Try other healthy providers
        for provider_type, is_healthy in self.provider_health.items():
            if is_healthy and provider_type != self.preferred_provider:
                provider = self.providers[provider_type]

                # Check capabilities
                if required_capabilities and not all(
                    cap in provider.get_capabilities() for cap in required_capabilities
                ):
                    continue

                try:
                    return await provider.complete(messages, functions)
                except Exception as e:
                    logger.warning(f"Provider {provider_type.value} failed: {e}")
                    self.provider_health[provider_type] = False

        raise Exception("No healthy LLM providers available")

    async def stream(
        self,
        messages: List[Message],
        functions: Optional[List[Function]] = None
    ) -> AsyncGenerator[str, None]:
        """Stream from best available provider"""

        # Similar logic to complete but for streaming
        if self.preferred_provider and self.provider_health.get(self.preferred_provider):
            provider = self.providers[self.preferred_provider]
            if ModelCapability.STREAMING in provider.get_capabilities():
                async for chunk in provider.stream(messages, functions):
                    yield chunk
                return

        # Fallback to other providers
        for provider_type, is_healthy in self.provider_health.items():
            if is_healthy:
                provider = self.providers[provider_type]
                if ModelCapability.STREAMING in provider.get_capabilities():
                    async for chunk in provider.stream(messages, functions):
                        yield chunk
                    return

        raise Exception("No streaming-capable LLM providers available")

# Factory function
async def create_llm_router(config: Dict[str, Any]) -> LLMRouter:
    """Create and initialize LLM router"""

    router = LLMRouter(
        preferred_provider=LLMProvider(config.get("preferred_provider", "ollama"))
    )

    # Register Ollama if available
    if config.get("ollama", {}).get("enabled", True):
        ollama_config = LLMConfig(
            provider=LLMProvider.OLLAMA,
            model=config["ollama"].get("model", "llama3.1:8b"),
            api_base=config["ollama"].get("api_base", "http://localhost:11434")
        )
        router.register_provider(LLMProvider.OLLAMA, OllamaProvider(ollama_config))

    # Register vLLM if available
    if config.get("vllm", {}).get("enabled", False):
        vllm_config = LLMConfig(
            provider=LLMProvider.VLLM,
            model=config["vllm"].get("model", "meta-llama/Llama-3-8b"),
            api_base=config["vllm"].get("api_base", "http://localhost:8000")
        )
        router.register_provider(LLMProvider.VLLM, VLLMProvider(vllm_config))

    # Register LiteLLM as universal fallback
    if config.get("litellm", {}).get("enabled", True):
        litellm_config = LLMConfig(
            provider=LLMProvider.LITELLM,
            model=config["litellm"].get("model", "gpt-3.5-turbo"),
            api_key=config["litellm"].get("api_key")
        )
        router.register_provider(LLMProvider.LITELLM, LiteLLMProvider(litellm_config))

    # Initialize all providers
    await router.initialize()

    return router

# Example usage
async def main():
    """Example usage of LLM abstraction"""

    # Configuration
    config = {
        "preferred_provider": "ollama",
        "ollama": {
            "enabled": True,
            "model": "llama3.1:8b",
            "api_base": "http://localhost:11434"
        },
        "vllm": {
            "enabled": False,
            "model": "meta-llama/Llama-3-8b",
            "api_base": "http://localhost:8000"
        },
        "litellm": {
            "enabled": True,
            "model": "gpt-3.5-turbo",
            "api_key": os.environ.get("OPENAI_API_KEY")
        }
    }

    # Create router
    router = await create_llm_router(config)

    # Example messages
    messages = [
        Message(role="system", content="You are a helpful assistant."),
        Message(role="user", content="What is the capital of France?")
    ]

    # Example functions
    functions = [
        Function(
            name="get_weather",
            description="Get weather for a location",
            parameters={
                "type": "object",
                "properties": {
                    "location": {"type": "string"}
                },
                "required": ["location"]
            }
        )
    ]

    # Complete without functions
    response = await router.complete(messages)
    print(f"Response: {response.content}")

    # Complete with functions (will use ReAct if not supported)
    response_with_functions = await router.complete(messages, functions)
    if response_with_functions.function_call:
        print(f"Function call: {response_with_functions.function_call}")
    else:
        print(f"Response: {response_with_functions.content}")

    # Stream response
    print("Streaming response:")
    async for chunk in router.stream(messages):
        print(chunk, end="", flush=True)

if __name__ == "__main__":
    asyncio.run(main())