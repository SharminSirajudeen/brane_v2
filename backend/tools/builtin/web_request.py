"""
Web Request Tool - Call any API, webhook, or HTTP endpoint
Users love this: "Check if my website is up", "Call Slack webhook", "Get weather data"
"""

import aiohttp
import json
from typing import Optional, Dict, Any
from ..base import DigitalTool, ToolSchema, ToolParameter, ToolCategory, ToolRiskLevel


class WebRequestTool(DigitalTool):
    """
    Make HTTP requests to any API or webhook.
    Perfect for: API calls, webhooks, health checks, data fetching.
    """

    def __init__(self):
        schema = ToolSchema(
            name="web_request",
            description="Make HTTP requests to any URL. Perfect for checking website status, calling APIs, sending webhooks, fetching data.",
            category=ToolCategory.NETWORK,
            risk_level=ToolRiskLevel.LOW,  # Read-only by default
            parameters=[
                ToolParameter(
                    name="url",
                    type="string",
                    description="Full URL to request (e.g., 'https://api.example.com/data')",
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
                    description="HTTP headers as JSON object",
                    required=False
                ),
                ToolParameter(
                    name="body",
                    type="object",
                    description="Request body for POST/PUT/PATCH (will be JSON-encoded)",
                    required=False
                ),
                ToolParameter(
                    name="timeout",
                    type="number",
                    description="Request timeout in seconds (default: 30)",
                    required=False,
                    default=30
                )
            ],
            returns={"type": "object", "description": "HTTP response with status, headers, and body"},
            requires_network=True,
            max_calls_per_minute=30,  # Reasonable rate limit
        )
        super().__init__(schema)

    async def validate_parameters(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict] = None,
        body: Optional[Dict] = None,
        timeout: int = 30,
        **kwargs
    ) -> bool:
        """Validate parameters"""
        # Basic URL validation
        if not url.startswith(('http://', 'https://')):
            return False

        # Valid HTTP methods
        valid_methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']
        if method.upper() not in valid_methods:
            return False

        # Timeout range
        if timeout < 1 or timeout > 300:  # Max 5 minutes
            return False

        return True

    async def execute(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict] = None,
        body: Optional[Dict] = None,
        timeout: int = 30,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute HTTP request"""
        method = method.upper()
        headers = headers or {}

        # Default headers
        if 'User-Agent' not in headers:
            headers['User-Agent'] = 'BRANE-Agent/1.0'

        try:
            async with aiohttp.ClientSession() as session:
                request_kwargs = {
                    'url': url,
                    'headers': headers,
                    'timeout': aiohttp.ClientTimeout(total=timeout)
                }

                # Add body for methods that support it
                if method in ['POST', 'PUT', 'PATCH'] and body:
                    request_kwargs['json'] = body

                async with session.request(method, **request_kwargs) as response:
                    # Try to parse as JSON, fall back to text
                    try:
                        response_body = await response.json()
                        body_type = "json"
                    except:
                        response_body = await response.text()
                        body_type = "text"

                    return {
                        "success": True,
                        "status_code": response.status,
                        "status_ok": 200 <= response.status < 300,
                        "headers": dict(response.headers),
                        "body": response_body,
                        "body_type": body_type,
                        "url": str(response.url)
                    }

        except aiohttp.ClientError as e:
            return {
                "success": False,
                "error": f"HTTP request failed: {str(e)}",
                "error_type": "connection_error"
            }
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": f"Request timed out after {timeout} seconds",
                "error_type": "timeout"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "error_type": "unknown"
            }
