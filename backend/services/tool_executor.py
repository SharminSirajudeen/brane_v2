"""
BRANE Tool Executor Service
Handles the execution of tools with proper sandboxing, validation, and monitoring
"""

import asyncio
import importlib
import inspect
import time
import tracemalloc
import psutil
from typing import Any, Dict, Optional, Type, Callable
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import json
import subprocess
import aiohttp
import aiofiles
from pathlib import Path

from backend.models.tool_system import Tool, ToolCategory
from backend.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ExecutionResult:
    """Result of tool execution"""
    output: Any
    duration: float  # seconds
    cpu_time: Optional[int] = None  # milliseconds
    memory_peak: Optional[int] = None  # MB
    stdout: Optional[str] = None
    stderr: Optional[str] = None


class ToolExecutor:
    """
    Main executor for all tool types with built-in safety and monitoring
    """

    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.tool_providers: Dict[str, Type[BaseToolProvider]] = {}
        self._load_builtin_providers()

    def _load_builtin_providers(self):
        """Load built-in tool providers"""
        self.tool_providers = {
            ToolCategory.FILE_SYSTEM: FileSystemProvider,
            ToolCategory.NETWORK: NetworkProvider,
            ToolCategory.SYSTEM: SystemProvider,
            ToolCategory.DATA_PROCESSING: DataProcessingProvider,
        }

    async def execute(
        self,
        tool: Tool,
        parameters: Dict[str, Any],
        sandbox_id: Optional[str] = None,
        dry_run: bool = False,
        timeout: Optional[int] = None
    ) -> ExecutionResult:
        """
        Execute a tool with proper monitoring and safety measures
        """
        start_time = time.time()
        tracemalloc.start()
        process = psutil.Process()
        cpu_start = process.cpu_times()

        try:
            # Get provider
            provider = self._get_provider(tool)

            # Set timeout (use tool's estimate or default)
            if timeout is None:
                timeout = (tool.estimated_duration_ms or 30000) / 1000  # Convert to seconds

            # Execute based on privacy tier
            if tool.privacy_tier == 0:  # Local execution
                result = await self._execute_local(
                    provider, tool, parameters, dry_run, timeout
                )
            elif tool.privacy_tier == 1:  # Private cloud
                result = await self._execute_sandboxed(
                    provider, tool, parameters, sandbox_id, dry_run, timeout
                )
            else:  # Public API
                result = await self._execute_remote(
                    provider, tool, parameters, dry_run, timeout
                )

            # Calculate metrics
            duration = time.time() - start_time
            current, peak = tracemalloc.get_traced_memory()
            memory_peak_mb = peak / 1024 / 1024
            cpu_end = process.cpu_times()
            cpu_time_ms = int((cpu_end.user - cpu_start.user + cpu_end.system - cpu_start.system) * 1000)

            tracemalloc.stop()

            return ExecutionResult(
                output=result,
                duration=duration,
                cpu_time=cpu_time_ms,
                memory_peak=int(memory_peak_mb)
            )

        except asyncio.TimeoutError:
            raise Exception(f"Tool execution timed out after {timeout} seconds")
        except Exception as e:
            logger.error(f"Tool execution failed: {str(e)}")
            raise
        finally:
            tracemalloc.stop()

    def _get_provider(self, tool: Tool) -> 'BaseToolProvider':
        """Get the appropriate provider for a tool"""
        # Try to load custom provider first
        if tool.provider_class:
            try:
                module_path, class_name = tool.provider_class.rsplit('.', 1)
                module = importlib.import_module(module_path)
                provider_class = getattr(module, class_name)
                return provider_class()
            except Exception as e:
                logger.warning(f"Failed to load custom provider: {e}")

        # Fall back to built-in provider
        category = ToolCategory(tool.category)
        provider_class = self.tool_providers.get(category)
        if not provider_class:
            raise ValueError(f"No provider found for category: {category}")

        return provider_class()

    async def _execute_local(
        self,
        provider: 'BaseToolProvider',
        tool: Tool,
        parameters: Dict[str, Any],
        dry_run: bool,
        timeout: float
    ) -> Any:
        """Execute tool locally with timeout"""
        if dry_run:
            return provider.dry_run(tool, parameters)

        # Run in thread pool with timeout
        future = self.executor.submit(provider.execute, tool, parameters)
        try:
            return await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(None, future.result),
                timeout=timeout
            )
        except TimeoutError:
            future.cancel()
            raise

    async def _execute_sandboxed(
        self,
        provider: 'BaseToolProvider',
        tool: Tool,
        parameters: Dict[str, Any],
        sandbox_id: str,
        dry_run: bool,
        timeout: float
    ) -> Any:
        """Execute tool in sandbox environment (Docker container)"""
        if dry_run:
            return provider.dry_run(tool, parameters)

        # Serialize parameters
        params_json = json.dumps(parameters)

        # Execute in Docker container
        cmd = [
            "docker", "exec", sandbox_id,
            "python", "-c",
            f"""
import json
import sys
sys.path.append('/app')
from {tool.provider_class.rsplit('.', 1)[0]} import {tool.provider_class.rsplit('.', 1)[1]}
provider = {tool.provider_class.rsplit('.', 1)[1]}()
params = json.loads('{params_json}')
result = provider.execute(None, params)
print(json.dumps(result))
"""
        ]

        try:
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(
                result.communicate(),
                timeout=timeout
            )

            if result.returncode != 0:
                raise Exception(f"Sandbox execution failed: {stderr.decode()}")

            return json.loads(stdout.decode())

        except asyncio.TimeoutError:
            # Kill the process
            result.terminate()
            await result.wait()
            raise

    async def _execute_remote(
        self,
        provider: 'BaseToolProvider',
        tool: Tool,
        parameters: Dict[str, Any],
        dry_run: bool,
        timeout: float
    ) -> Any:
        """Execute tool via remote API"""
        if dry_run:
            return provider.dry_run(tool, parameters)

        # This would call an external API endpoint
        # For now, we'll use the local execution
        return await self._execute_local(provider, tool, parameters, dry_run, timeout)


# ============================================================================
# Base Tool Provider
# ============================================================================

class BaseToolProvider:
    """Base class for all tool providers"""

    def execute(self, tool: Tool, parameters: Dict[str, Any]) -> Any:
        """Execute the tool with given parameters"""
        raise NotImplementedError

    def dry_run(self, tool: Tool, parameters: Dict[str, Any]) -> Any:
        """Simulate execution without side effects"""
        return {
            "dry_run": True,
            "tool": tool.name,
            "parameters": parameters,
            "expected_result": "Simulated execution successful"
        }

    def validate(self, tool: Tool, parameters: Dict[str, Any]) -> bool:
        """Validate parameters before execution"""
        return True


# ============================================================================
# Built-in Tool Providers
# ============================================================================

class FileSystemProvider(BaseToolProvider):
    """Provider for file system operations"""

    def execute(self, tool: Tool, parameters: Dict[str, Any]) -> Any:
        """Execute file system operations"""
        operation = parameters.get("operation")

        if operation == "read_file":
            return self._read_file(parameters)
        elif operation == "write_file":
            return self._write_file(parameters)
        elif operation == "list_directory":
            return self._list_directory(parameters)
        elif operation == "create_directory":
            return self._create_directory(parameters)
        elif operation == "delete_file":
            return self._delete_file(parameters)
        else:
            raise ValueError(f"Unknown operation: {operation}")

    def _read_file(self, params: Dict[str, Any]) -> str:
        """Read file contents"""
        path = Path(params["path"])
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        # Security check - prevent path traversal
        if ".." in str(path):
            raise ValueError("Path traversal not allowed")

        with open(path, 'r', encoding='utf-8') as f:
            return f.read()

    def _write_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Write content to file"""
        path = Path(params["path"])
        content = params["content"]

        # Security check
        if ".." in str(path):
            raise ValueError("Path traversal not allowed")

        # Create parent directories if needed
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

        return {
            "path": str(path),
            "size": len(content),
            "created": path.exists()
        }

    def _list_directory(self, params: Dict[str, Any]) -> list:
        """List directory contents"""
        path = Path(params.get("path", "."))
        if not path.is_dir():
            raise ValueError(f"Not a directory: {path}")

        return [
            {
                "name": item.name,
                "type": "directory" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else None,
                "modified": item.stat().st_mtime
            }
            for item in path.iterdir()
        ]

    def _create_directory(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create directory"""
        path = Path(params["path"])
        path.mkdir(parents=params.get("parents", True), exist_ok=params.get("exist_ok", True))
        return {"path": str(path), "created": path.exists()}

    def _delete_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Delete file or directory"""
        path = Path(params["path"])
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            import shutil
            shutil.rmtree(path)
        return {"path": str(path), "deleted": not path.exists()}


class NetworkProvider(BaseToolProvider):
    """Provider for network operations"""

    async def execute(self, tool: Tool, parameters: Dict[str, Any]) -> Any:
        """Execute network operations"""
        operation = parameters.get("operation")

        if operation == "http_request":
            return await self._http_request(parameters)
        elif operation == "download_file":
            return await self._download_file(parameters)
        elif operation == "webhook":
            return await self._send_webhook(parameters)
        else:
            raise ValueError(f"Unknown operation: {operation}")

    async def _http_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make HTTP request"""
        async with aiohttp.ClientSession() as session:
            method = params.get("method", "GET")
            url = params["url"]
            headers = params.get("headers", {})
            data = params.get("data")
            json_data = params.get("json")

            async with session.request(
                method=method,
                url=url,
                headers=headers,
                data=data,
                json=json_data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                return {
                    "status": response.status,
                    "headers": dict(response.headers),
                    "body": await response.text(),
                    "json": await response.json() if response.content_type == 'application/json' else None
                }

    async def _download_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Download file from URL"""
        url = params["url"]
        dest = Path(params["destination"])

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()

                dest.parent.mkdir(parents=True, exist_ok=True)
                async with aiofiles.open(dest, 'wb') as f:
                    async for chunk in response.content.iter_chunked(8192):
                        await f.write(chunk)

        return {
            "url": url,
            "destination": str(dest),
            "size": dest.stat().st_size,
            "success": True
        }

    async def _send_webhook(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send webhook notification"""
        url = params["url"]
        payload = params["payload"]

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                return {
                    "status": response.status,
                    "response": await response.text(),
                    "success": response.status < 400
                }


class SystemProvider(BaseToolProvider):
    """Provider for system operations"""

    def execute(self, tool: Tool, parameters: Dict[str, Any]) -> Any:
        """Execute system operations"""
        operation = parameters.get("operation")

        if operation == "run_command":
            return self._run_command(parameters)
        elif operation == "get_system_info":
            return self._get_system_info()
        elif operation == "manage_process":
            return self._manage_process(parameters)
        else:
            raise ValueError(f"Unknown operation: {operation}")

    def _run_command(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Run shell command (with restrictions)"""
        command = params["command"]

        # Security: whitelist safe commands
        safe_commands = ["ls", "pwd", "echo", "date", "whoami", "df", "free"]
        cmd_parts = command.split()
        if cmd_parts[0] not in safe_commands:
            raise ValueError(f"Command '{cmd_parts[0]}' not allowed")

        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )

        return {
            "command": command,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }

    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        return {
            "platform": {
                "system": psutil.os.name,
                "release": psutil.os.uname().release,
                "version": psutil.os.uname().version,
            },
            "cpu": {
                "count": psutil.cpu_count(),
                "percent": psutil.cpu_percent(interval=1),
                "freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
            },
            "memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "percent": psutil.virtual_memory().percent
            },
            "disk": {
                "total": psutil.disk_usage('/').total,
                "free": psutil.disk_usage('/').free,
                "percent": psutil.disk_usage('/').percent
            }
        }

    def _manage_process(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Manage system process"""
        action = params["action"]
        pid = params.get("pid")

        if action == "list":
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            return {"processes": processes[:20]}  # Limit to 20 processes

        elif action == "kill" and pid:
            try:
                proc = psutil.Process(pid)
                proc.terminate()
                return {"pid": pid, "terminated": True}
            except psutil.NoSuchProcess:
                return {"pid": pid, "error": "Process not found"}

        return {"error": "Invalid action or missing parameters"}


class DataProcessingProvider(BaseToolProvider):
    """Provider for data processing operations"""

    def execute(self, tool: Tool, parameters: Dict[str, Any]) -> Any:
        """Execute data processing operations"""
        operation = parameters.get("operation")

        if operation == "transform_json":
            return self._transform_json(parameters)
        elif operation == "validate_schema":
            return self._validate_schema(parameters)
        elif operation == "extract_data":
            return self._extract_data(parameters)
        else:
            raise ValueError(f"Unknown operation: {operation}")

    def _transform_json(self, params: Dict[str, Any]) -> Any:
        """Transform JSON data using jq-like operations"""
        import jq
        data = params["data"]
        expression = params["expression"]

        try:
            result = jq.compile(expression).input(data).first()
            return result
        except Exception as e:
            raise ValueError(f"JSON transformation failed: {e}")

    def _validate_schema(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate data against JSON schema"""
        import jsonschema
        data = params["data"]
        schema = params["schema"]

        try:
            jsonschema.validate(data, schema)
            return {"valid": True, "errors": []}
        except jsonschema.ValidationError as e:
            return {"valid": False, "errors": [str(e)]}

    def _extract_data(self, params: Dict[str, Any]) -> Any:
        """Extract data using regex or patterns"""
        import re
        text = params["text"]
        pattern = params["pattern"]

        matches = re.findall(pattern, text)
        return {"matches": matches, "count": len(matches)}