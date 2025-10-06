"""
Shell Command Tool - Execute safe system commands
Users love this: "Run npm install", "Check Docker containers", "Git status"
"""

import asyncio
import shlex
from typing import Optional, List
from ..base import DigitalTool, ToolSchema, ToolParameter, ToolCategory, ToolRiskLevel


class ShellTool(DigitalTool):
    """
    Execute safe shell commands with whitelist protection.
    Perfect for: npm/pip installs, git operations, docker commands, system checks.
    """

    # Safe commands allowed by default (extensible via config)
    DEFAULT_SAFE_COMMANDS = [
        "ls", "cat", "echo", "pwd", "whoami", "hostname", "date",
        "git", "npm", "pip", "python", "node", "docker", "kubectl",
        "curl", "wget", "ping", "dig", "nslookup",
        "grep", "find", "wc", "head", "tail", "sort", "uniq"
    ]

    # Dangerous patterns to block
    DANGEROUS_PATTERNS = [
        "rm -rf", "mkfs", "dd if=", ">>/etc/", "chmod 777",
        "curl | sh", "wget | sh", "eval", "exec", "|sh",
        "sudo", "su -", "passwd"
    ]

    def __init__(self, allowed_commands: Optional[List[str]] = None, cwd: str = "."):
        schema = ToolSchema(
            name="shell",
            description="Execute safe shell commands. Supports git, npm, docker, and other common development tools. Dangerous commands are blocked for safety.",
            category=ToolCategory.CODE_EXEC,
            risk_level=ToolRiskLevel.HIGH,  # Requires approval by default
            parameters=[
                ToolParameter(
                    name="command",
                    type="string",
                    description="Shell command to execute (e.g., 'git status', 'npm install', 'docker ps')",
                    required=True
                ),
                ToolParameter(
                    name="timeout",
                    type="number",
                    description="Command timeout in seconds (default: 60)",
                    required=False,
                    default=60
                )
            ],
            returns={"type": "object", "description": "Command output with stdout, stderr, and exit code"},
            requires_confirmation=True,  # Always ask before running commands
        )
        super().__init__(schema)
        self.allowed_commands = allowed_commands or self.DEFAULT_SAFE_COMMANDS
        self.cwd = cwd

    def _is_safe_command(self, command: str) -> tuple[bool, Optional[str]]:
        """
        Check if command is safe to execute.
        Returns: (is_safe, reason_if_not_safe)
        """
        # Check for dangerous patterns
        command_lower = command.lower()
        for pattern in self.DANGEROUS_PATTERNS:
            if pattern in command_lower:
                return False, f"Blocked dangerous pattern: '{pattern}'"

        # Extract base command (first word)
        try:
            parts = shlex.split(command)
            if not parts:
                return False, "Empty command"

            base_command = parts[0]

            # Check if base command is in allowed list
            if base_command not in self.allowed_commands:
                return False, f"Command '{base_command}' is not in allowed list"

            return True, None

        except ValueError as e:
            return False, f"Invalid command syntax: {str(e)}"

    async def validate_parameters(self, command: str, timeout: int = 60, **kwargs) -> bool:
        """Validate parameters"""
        if not command or not command.strip():
            return False

        if timeout < 1 or timeout > 300:  # Max 5 minutes
            return False

        is_safe, reason = self._is_safe_command(command)
        return is_safe

    async def execute(self, command: str, timeout: int = 60, **kwargs):
        """Execute shell command safely"""
        # Final safety check
        is_safe, reason = self._is_safe_command(command)
        if not is_safe:
            return {
                "success": False,
                "error": f"Safety check failed: {reason}",
                "command": command
            }

        try:
            # Execute command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.cwd
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )

                return {
                    "success": process.returncode == 0,
                    "exit_code": process.returncode,
                    "stdout": stdout.decode('utf-8', errors='replace'),
                    "stderr": stderr.decode('utf-8', errors='replace'),
                    "command": command,
                    "cwd": self.cwd
                }

            except asyncio.TimeoutError:
                # Kill the process if it times out
                process.kill()
                await process.wait()

                return {
                    "success": False,
                    "error": f"Command timed out after {timeout} seconds",
                    "command": command,
                    "timeout": timeout
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"Execution failed: {str(e)}",
                "command": command
            }


# Convenience factory for common use cases
def create_dev_shell_tool(workspace_path: str = ".") -> ShellTool:
    """Create shell tool configured for development workflows"""
    return ShellTool(
        allowed_commands=ShellTool.DEFAULT_SAFE_COMMANDS + [
            "yarn", "pnpm", "poetry", "cargo", "go", "make",
            "pytest", "jest", "mocha", "phpunit",
            "terraform", "ansible", "helm"
        ],
        cwd=workspace_path
    )
