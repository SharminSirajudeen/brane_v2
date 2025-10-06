"""
MCP Adapter - Integrate Model Context Protocol servers with BRANE
"""

import logging
from typing import List, Dict, Any, Optional
from langchain_mcp_adapters import MCPClient

logger = logging.getLogger(__name__)


class MCPToolAdapter:
    """Adapter for integrating MCP servers as LangChain tools"""

    def __init__(self):
        self.client: Optional[MCPClient] = None
        self.connected_servers: Dict[str, str] = {}

    async def initialize(self, server_configs: List[Dict[str, Any]]):
        """Initialize MCP client and connect to servers

        Args:
            server_configs: List of server configurations
                Example: [
                    {
                        "name": "filesystem",
                        "command": "npx",
                        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/directory"]
                    },
                    {
                        "name": "fetch",
                        "command": "uvx",
                        "args": ["mcp-server-fetch"]
                    }
                ]
        """
        try:
            # Create MCP client
            self.client = MCPClient()

            # Connect to each server
            for config in server_configs:
                server_name = config.get("name")
                command = config.get("command")
                args = config.get("args", [])

                logger.info(f"Connecting to MCP server: {server_name}")

                # Connect to server
                await self.client.connect_to_server(
                    server_name=server_name,
                    command=command,
                    args=args
                )

                self.connected_servers[server_name] = f"{command} {' '.join(args)}"
                logger.info(f"✅ Connected to MCP server: {server_name}")

            logger.info(f"MCP adapter initialized with {len(self.connected_servers)} servers")

        except Exception as e:
            logger.error(f"Failed to initialize MCP adapter: {e}")
            raise

    async def get_tools(self) -> List:
        """Get all tools from connected MCP servers as LangChain tools

        Returns:
            List of LangChain-compatible tools
        """
        if not self.client:
            logger.warning("MCP client not initialized")
            return []

        try:
            # Get tools from all connected servers
            tools = await self.client.get_tools()
            logger.info(f"Loaded {len(tools)} tools from MCP servers")
            return tools

        except Exception as e:
            logger.error(f"Failed to get MCP tools: {e}")
            return []

    async def get_tools_by_server(self, server_name: str) -> List:
        """Get tools from a specific MCP server

        Args:
            server_name: Name of the server

        Returns:
            List of LangChain-compatible tools from that server
        """
        if not self.client:
            logger.warning("MCP client not initialized")
            return []

        try:
            tools = await self.client.get_tools(server_name=server_name)
            logger.info(f"Loaded {len(tools)} tools from MCP server: {server_name}")
            return tools

        except Exception as e:
            logger.error(f"Failed to get tools from {server_name}: {e}")
            return []

    def get_server_info(self) -> Dict[str, Any]:
        """Get information about connected MCP servers

        Returns:
            Dictionary with server names and connection info
        """
        return {
            "connected_servers": self.connected_servers,
            "server_count": len(self.connected_servers),
            "status": "connected" if self.client else "not_initialized"
        }

    async def close(self):
        """Close all MCP server connections"""
        if self.client:
            try:
                await self.client.close()
                logger.info("MCP client closed")
            except Exception as e:
                logger.error(f"Error closing MCP client: {e}")


# Default MCP server configurations
DEFAULT_MCP_SERVERS = [
    {
        "name": "filesystem",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp/brane"]
        # Note: Restricts filesystem access to /tmp/brane for security
    },
    {
        "name": "fetch",
        "command": "uvx",
        "args": ["mcp-server-fetch"]
        # HTTP/fetch operations
    }
]


# Singleton instance
_mcp_adapter: Optional[MCPToolAdapter] = None


async def get_mcp_adapter() -> MCPToolAdapter:
    """Get or create MCP adapter singleton"""
    global _mcp_adapter

    if _mcp_adapter is None:
        _mcp_adapter = MCPToolAdapter()
        # Note: Servers are initialized on-demand when first requested

    return _mcp_adapter


async def initialize_mcp_servers(server_configs: Optional[List[Dict[str, Any]]] = None):
    """Initialize MCP servers with given configurations

    Args:
        server_configs: List of server configurations (uses defaults if None)
    """
    adapter = await get_mcp_adapter()
    configs = server_configs or DEFAULT_MCP_SERVERS
    await adapter.initialize(configs)
    return adapter
