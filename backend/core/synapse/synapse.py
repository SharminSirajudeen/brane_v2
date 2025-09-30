"""
Synapse - Plugin/Tool System
MCP-compatible with sandboxed execution
"""

import logging
from typing import Dict, Any, Callable, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class SynapseStatus(str, Enum):
    """Synapse execution status"""
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"


class Synapse:
    """
    MCP-compatible plugin/tool.
    Adapts to model capabilities (native tools vs prompt engineering).
    """

    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        parameters: Dict,
        executor: Callable
    ):
        """
        Initialize Synapse.

        Args:
            id: Unique identifier
            name: Tool name (for LLM)
            description: What the tool does
            parameters: JSON Schema for parameters
            executor: Async function to execute tool
        """
        self.id = id
        self.name = name
        self.description = description
        self.parameters = parameters
        self.executor = executor

        logger.debug(f"Synapse '{self.name}' created")

    def to_mcp_format(self) -> Dict:
        """
        Export as MCP tool definition.
        Compatible with OpenAI, Anthropic, and other providers.
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": self.parameters,
                "required": [
                    param for param, spec in self.parameters.items()
                    if spec.get("required", False)
                ]
            }
        }

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute tool with given parameters.

        Returns:
            {
                "status": "success" | "failure",
                "result": <tool output>,
                "error": <error message if failure>
            }
        """
        try:
            # Validate parameters
            self._validate_params(kwargs)

            # Execute
            result = await self.executor(**kwargs)

            return {
                "status": SynapseStatus.SUCCESS,
                "result": result
            }

        except Exception as e:
            logger.error(f"Synapse '{self.name}' execution error: {e}")
            return {
                "status": SynapseStatus.FAILURE,
                "error": str(e)
            }

    def _validate_params(self, params: Dict):
        """Validate parameters against schema"""
        # TODO: Full JSON Schema validation
        for param_name, param_spec in self.parameters.items():
            if param_spec.get("required") and param_name not in params:
                raise ValueError(f"Missing required parameter: {param_name}")


# Example built-in Synapses

async def web_search_executor(query: str, max_results: int = 5) -> str:
    """
    Web search tool (placeholder - integrate with Brave Search API).
    """
    # TODO: Integrate with Brave Search API or similar
    logger.info(f"Web search: {query} (max_results={max_results})")

    return f"Search results for '{query}': [Placeholder - integrate with search API]"


def create_web_search_synapse() -> Synapse:
    """Create web search Synapse"""
    return Synapse(
        id="web_search",
        name="web_search",
        description="Search the web for current information",
        parameters={
            "query": {
                "type": "string",
                "description": "Search query",
                "required": True
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results",
                "default": 5
            }
        },
        executor=web_search_executor
    )


async def file_read_executor(file_path: str) -> str:
    """
    Read file contents (sandboxed to storage directory).
    """
    import os
    from core.config import get_settings

    settings = get_settings()

    # Security: Only allow reading from storage directory
    allowed_path = os.path.abspath(settings.STORAGE_PATH)
    requested_path = os.path.abspath(file_path)

    if not requested_path.startswith(allowed_path):
        raise PermissionError(f"Access denied: {file_path}")

    with open(requested_path, 'r') as f:
        content = f.read()

    return content


def create_file_read_synapse() -> Synapse:
    """Create file read Synapse"""
    return Synapse(
        id="file_read",
        name="read_file",
        description="Read contents of a file (sandboxed to storage directory)",
        parameters={
            "file_path": {
                "type": "string",
                "description": "Path to file to read",
                "required": True
            }
        },
        executor=file_read_executor
    )


# Medical terminology lookup (example for healthcare)

async def medical_term_executor(term: str) -> str:
    """
    Look up medical terminology.
    TODO: Integrate with UMLS API or local database.
    """
    logger.info(f"Medical term lookup: {term}")

    # Placeholder - integrate with UMLS or medical dictionary
    return f"Definition of '{term}': [Placeholder - integrate with medical terminology database]"


def create_medical_terminology_synapse() -> Synapse:
    """Create medical terminology lookup Synapse"""
    return Synapse(
        id="medical_terminology",
        name="lookup_medical_term",
        description="Look up definition of medical term from UMLS database",
        parameters={
            "term": {
                "type": "string",
                "description": "Medical term to look up",
                "required": True
            }
        },
        executor=medical_term_executor
    )
