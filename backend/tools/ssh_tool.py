"""
SSH Tool - Execute commands on remote servers via SSH
"""

import paramiko
from typing import Optional, Dict, Any
from io import StringIO

from .base import DigitalTool, ToolSchema, ToolParameter, ToolCategory, ToolRiskLevel


class SSHTool(DigitalTool):
    """Tool for executing commands on remote servers via SSH"""

    def __init__(self):
        schema = ToolSchema(
            name="ssh_execute",
            description="Execute commands on remote servers via SSH",
            category=ToolCategory.NETWORK,
            risk_level=ToolRiskLevel.HIGH,
            parameters=[
                ToolParameter(
                    name="host",
                    type="string",
                    description="SSH server hostname or IP address",
                    required=True
                ),
                ToolParameter(
                    name="command",
                    type="string",
                    description="Command to execute on remote server",
                    required=True
                ),
                ToolParameter(
                    name="username",
                    type="string",
                    description="SSH username",
                    required=False,
                    default=None
                ),
                ToolParameter(
                    name="password",
                    type="string",
                    description="SSH password (use key auth preferred)",
                    required=False,
                    default=None
                ),
                ToolParameter(
                    name="key_path",
                    type="string",
                    description="Path to SSH private key file",
                    required=False,
                    default=None
                ),
                ToolParameter(
                    name="port",
                    type="number",
                    description="SSH port (default: 22)",
                    required=False,
                    default=22
                ),
                ToolParameter(
                    name="timeout",
                    type="number",
                    description="Command timeout in seconds (default: 30)",
                    required=False,
                    default=30
                )
            ],
            returns={
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "stdout": {"type": "string"},
                    "stderr": {"type": "string"},
                    "exit_code": {"type": "number"}
                }
            },
            examples=[
                {
                    "host": "192.168.1.10",
                    "command": "df -h",
                    "username": "admin",
                    "key_path": "~/.ssh/id_rsa"
                },
                {
                    "host": "server.example.com",
                    "command": "systemctl status nginx",
                    "username": "ubuntu"
                }
            ],
            requires_confirmation=True,  # SSH commands require approval
            requires_network=True,
            max_calls_per_minute=20,  # Rate limit SSH calls
            is_reversible=False  # SSH commands can't be auto-reversed
        )
        super().__init__(schema)
        self._dangerous_commands = [
            'rm ', 'del ', 'format ', 'mkfs.', 'dd ',
            'shutdown', 'reboot', 'halt', 'poweroff',
            '> /dev/', 'chmod -R', 'chown -R'
        ]

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute SSH command on remote server"""
        host = kwargs.get("host")
        command = kwargs.get("command")
        username = kwargs.get("username")
        password = kwargs.get("password")
        key_path = kwargs.get("key_path")
        port = kwargs.get("port", 22)
        timeout = kwargs.get("timeout", 30)

        # Check if command is dangerous
        is_dangerous = self._is_dangerous_command(command)

        try:
            # Create SSH client
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # Connect
            connect_kwargs = {
                "hostname": host,
                "port": port,
                "username": username,
                "timeout": timeout
            }

            if key_path:
                # Use SSH key authentication
                connect_kwargs["key_filename"] = key_path
            elif password:
                # Use password authentication
                connect_kwargs["password"] = password
            else:
                # Try agent authentication (user's default keys)
                pass

            ssh.connect(**connect_kwargs)

            # Execute command
            stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)

            # Get results
            stdout_text = stdout.read().decode('utf-8', errors='replace')
            stderr_text = stderr.read().decode('utf-8', errors='replace')
            exit_code = stdout.channel.recv_exit_status()

            # Close connection
            ssh.close()

            return {
                "success": exit_code == 0,
                "stdout": stdout_text,
                "stderr": stderr_text,
                "exit_code": exit_code,
                "host": host,
                "command": command,
                "dangerous": is_dangerous
            }

        except paramiko.AuthenticationException as e:
            return {
                "success": False,
                "error": f"Authentication failed: {str(e)}",
                "stdout": "",
                "stderr": str(e),
                "exit_code": -1
            }
        except paramiko.SSHException as e:
            return {
                "success": False,
                "error": f"SSH error: {str(e)}",
                "stdout": "",
                "stderr": str(e),
                "exit_code": -1
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Execution failed: {str(e)}",
                "stdout": "",
                "stderr": str(e),
                "exit_code": -1
            }

    async def validate_parameters(self, **kwargs) -> bool:
        """Validate SSH parameters"""
        host = kwargs.get("host")
        command = kwargs.get("command")

        if not host or not command:
            return False

        # Must have either username or rely on default
        # (agent auth will work with user's default keys)

        return True

    def _is_dangerous_command(self, command: str) -> bool:
        """Check if command is potentially dangerous"""
        command_lower = command.lower()
        for dangerous in self._dangerous_commands:
            if dangerous in command_lower:
                return True
        return False

    def to_langchain_tool(self):
        """Convert to LangChain tool format"""
        from langchain_core.tools import tool

        @tool
        async def ssh_execute(
            host: str,
            command: str,
            username: Optional[str] = None,
            password: Optional[str] = None,
            key_path: Optional[str] = None,
            port: int = 22,
            timeout: int = 30
        ) -> str:
            """Execute command on remote server via SSH.

            Args:
                host: SSH server hostname or IP
                command: Command to execute
                username: SSH username (optional)
                password: SSH password (optional, prefer key auth)
                key_path: Path to SSH private key (optional)
                port: SSH port (default: 22)
                timeout: Command timeout in seconds (default: 30)

            Returns:
                Command output and status
            """
            result = await self.execute(
                host=host,
                command=command,
                username=username,
                password=password,
                key_path=key_path,
                port=port,
                timeout=timeout
            )

            if result.get("success"):
                output = f"✓ Command succeeded (exit code {result['exit_code']})\n\n"
                if result.get("stdout"):
                    output += f"Output:\n{result['stdout']}\n"
                if result.get("stderr"):
                    output += f"Warnings:\n{result['stderr']}\n"
                return output
            else:
                return f"✗ Command failed: {result.get('error', 'Unknown error')}\n{result.get('stderr', '')}"

        return ssh_execute


# Example usage
async def example_usage():
    """Example of using SSH tool"""
    ssh_tool = SSHTool()

    # Check disk space
    result = await ssh_tool.execute(
        host="192.168.1.10",
        command="df -h",
        username="admin",
        key_path="~/.ssh/id_rsa"
    )
    print("Disk space:", result)

    # Check service status
    result = await ssh_tool.execute(
        host="server.example.com",
        command="systemctl status nginx",
        username="ubuntu"
    )
    print("Service status:", result)
