"""
HTTP Tool - Make HTTP API calls
"""

import httpx
import json
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin

from .base import DigitalTool, ToolSchema, ToolParameter, ToolCategory, ToolRiskLevel


class HTTPTool(DigitalTool):
    """Tool for making HTTP API calls"""

    def __init__(self):
        schema = ToolSchema(
            name="http_request",
            description="Make HTTP requests to APIs and web services",
            category=ToolCategory.NETWORK,
            risk_level=ToolRiskLevel.MEDIUM,
            parameters=[
                ToolParameter(
                    name="url",
                    type="string",
                    description="Full URL to request",
                    required=True
                ),
                ToolParameter(
                    name="method",
                    type="string",
                    description="HTTP method: GET, POST, PUT, DELETE, PATCH",
                    required=False,
                    default="GET"
                ),
                ToolParameter(
                    name="headers",
                    type="object",
                    description="HTTP headers as key-value pairs",
                    required=False,
                    default={}
                ),
                ToolParameter(
                    name="body",
                    type="object",
                    description="Request body (JSON)",
                    required=False,
                    default=None
                ),
                ToolParameter(
                    name="params",
                    type="object",
                    description="URL query parameters",
                    required=False,
                    default={}
                ),
                ToolParameter(
                    name="timeout",
                    type="number",
                    description="Request timeout in seconds (default: 30)",
                    required=False,
                    default=30
                ),
                ToolParameter(
                    name="auth_token",
                    type="string",
                    description="Bearer token for authentication",
                    required=False,
                    default=None
                )
            ],
            returns={
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "status_code": {"type": "number"},
                    "data": {"type": "any"},
                    "headers": {"type": "object"}
                }
            },
            examples=[
                {
                    "url": "https://api.github.com/repos/python/cpython",
                    "method": "GET"
                },
                {
                    "url": "https://api.example.com/data",
                    "method": "POST",
                    "headers": {"Content-Type": "application/json"},
                    "body": {"key": "value"}
                },
                {
                    "url": "https://api.stripe.com/v1/charges",
                    "method": "GET",
                    "auth_token": "sk_test_..."
                }
            ],
            requires_confirmation=False,  # GET requests are safe
            requires_network=True,
            max_calls_per_minute=60,
            max_data_mb_per_hour=50.0
        )
        super().__init__(schema)
        self._write_methods = ['POST', 'PUT', 'DELETE', 'PATCH']

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute HTTP request"""
        url = kwargs.get("url")
        method = kwargs.get("method", "GET").upper()
        headers = kwargs.get("headers", {})
        body = kwargs.get("body")
        params = kwargs.get("params", {})
        timeout = kwargs.get("timeout", 30)
        auth_token = kwargs.get("auth_token")

        # Add auth token if provided
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                # Make request
                if method == "GET":
                    response = await client.get(url, headers=headers, params=params)
                elif method == "POST":
                    response = await client.post(url, headers=headers, json=body, params=params)
                elif method == "PUT":
                    response = await client.put(url, headers=headers, json=body, params=params)
                elif method == "DELETE":
                    response = await client.delete(url, headers=headers, params=params)
                elif method == "PATCH":
                    response = await client.patch(url, headers=headers, json=body, params=params)
                else:
                    return {
                        "success": False,
                        "error": f"Unsupported HTTP method: {method}",
                        "status_code": 0
                    }

                # Parse response
                try:
                    response_data = response.json()
                except:
                    response_data = response.text

                # Check if request was successful
                success = 200 <= response.status_code < 300

                return {
                    "success": success,
                    "status_code": response.status_code,
                    "data": response_data,
                    "headers": dict(response.headers),
                    "url": str(response.url),
                    "method": method,
                    "elapsed_ms": response.elapsed.total_seconds() * 1000
                }

        except httpx.TimeoutException as e:
            return {
                "success": False,
                "error": f"Request timeout after {timeout}s",
                "status_code": 0
            }
        except httpx.HTTPError as e:
            return {
                "success": False,
                "error": f"HTTP error: {str(e)}",
                "status_code": 0
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Request failed: {str(e)}",
                "status_code": 0
            }

    async def validate_parameters(self, **kwargs) -> bool:
        """Validate HTTP parameters"""
        url = kwargs.get("url")
        method = kwargs.get("method", "GET").upper()

        if not url:
            return False

        # Validate URL format
        if not url.startswith(("http://", "https://")):
            return False

        # Validate method
        valid_methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]
        if method not in valid_methods:
            return False

        return True

    def _is_write_operation(self, method: str) -> bool:
        """Check if method is a write operation"""
        return method.upper() in self._write_methods

    def to_langchain_tool(self):
        """Convert to LangChain tool format"""
        from langchain_core.tools import tool

        @tool
        async def http_request(
            url: str,
            method: str = "GET",
            headers: Optional[Dict[str, str]] = None,
            body: Optional[Dict[str, Any]] = None,
            params: Optional[Dict[str, str]] = None,
            timeout: int = 30,
            auth_token: Optional[str] = None
        ) -> str:
            """Make HTTP request to an API or web service.

            Args:
                url: Full URL to request
                method: HTTP method (GET, POST, PUT, DELETE, PATCH)
                headers: HTTP headers as dictionary
                body: Request body as JSON dictionary
                params: URL query parameters
                timeout: Request timeout in seconds
                auth_token: Bearer token for authentication

            Returns:
                Response data and status
            """
            result = await self.execute(
                url=url,
                method=method,
                headers=headers or {},
                body=body,
                params=params or {},
                timeout=timeout,
                auth_token=auth_token
            )

            if result.get("success"):
                output = f"✓ {method} {url} - {result['status_code']}\n"
                output += f"⏱ {result.get('elapsed_ms', 0):.0f}ms\n\n"

                # Format response data
                data = result.get("data")
                if isinstance(data, dict) or isinstance(data, list):
                    output += f"Response:\n{json.dumps(data, indent=2)}\n"
                else:
                    output += f"Response:\n{data}\n"

                return output
            else:
                return f"✗ {method} {url} failed: {result.get('error', 'Unknown error')}"

        return http_request


# Example usage
async def example_usage():
    """Example of using HTTP tool"""
    http_tool = HTTPTool()

    # GET request
    result = await http_tool.execute(
        url="https://api.github.com/repos/python/cpython",
        method="GET"
    )
    print("GitHub repo:", result)

    # POST request with auth
    result = await http_tool.execute(
        url="https://api.example.com/data",
        method="POST",
        headers={"Content-Type": "application/json"},
        body={"name": "test", "value": 123},
        auth_token="your-api-token"
    )
    print("POST result:", result)

    # GET with query params
    result = await http_tool.execute(
        url="https://api.example.com/search",
        method="GET",
        params={"q": "python", "limit": 10}
    )
    print("Search result:", result)
