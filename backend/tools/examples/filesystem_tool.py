"""
Example: File System Tool Implementation
"""

import os
import aiofiles
from pathlib import Path
from typing import Optional, List
import hashlib
import json

from ..base import DigitalTool, ToolSchema, ToolParameter, ToolCategory, ToolRiskLevel
from ..permissions import ToolPermission


class FileSystemTool(DigitalTool):
    """Tool for file system operations"""

    def __init__(self):
        schema = ToolSchema(
            name="filesystem",
            description="Read, write, and manage files on the system",
            category=ToolCategory.FILE_SYSTEM,
            risk_level=ToolRiskLevel.MEDIUM,
            parameters=[
                ToolParameter(
                    name="operation",
                    type="string",
                    description="Operation to perform: read, write, list, delete, move",
                    required=True
                ),
                ToolParameter(
                    name="path",
                    type="string",
                    description="File or directory path",
                    required=True
                ),
                ToolParameter(
                    name="content",
                    type="string",
                    description="Content to write (for write operation)",
                    required=False
                ),
                ToolParameter(
                    name="destination",
                    type="string",
                    description="Destination path (for move operation)",
                    required=False
                )
            ],
            returns={"type": "object", "properties": {"success": {"type": "boolean"}, "data": {"type": "any"}}},
            examples=[
                {"operation": "read", "path": "/home/user/document.txt"},
                {"operation": "write", "path": "/tmp/output.txt", "content": "Hello World"},
                {"operation": "list", "path": "/home/user/documents"}
            ],
            requires_confirmation=False,
            requires_filesystem=True,
            max_calls_per_minute=100
        )
        super().__init__(schema)

    async def execute(self, **kwargs) -> dict:
        """Execute file system operation"""
        operation = kwargs.get("operation")
        path = kwargs.get("path")

        # Validate path (prevent traversal)
        safe_path = self._validate_path(path)

        if operation == "read":
            return await self._read_file(safe_path)
        elif operation == "write":
            content = kwargs.get("content", "")
            return await self._write_file(safe_path, content)
        elif operation == "list":
            return await self._list_directory(safe_path)
        elif operation == "delete":
            return await self._delete_file(safe_path)
        elif operation == "move":
            destination = kwargs.get("destination")
            safe_dest = self._validate_path(destination)
            return await self._move_file(safe_path, safe_dest)
        else:
            raise ValueError(f"Unknown operation: {operation}")

    async def validate_parameters(self, **kwargs) -> bool:
        """Validate input parameters"""
        operation = kwargs.get("operation")
        path = kwargs.get("path")

        if not operation or not path:
            return False

        valid_operations = ["read", "write", "list", "delete", "move"]
        if operation not in valid_operations:
            return False

        if operation == "write" and "content" not in kwargs:
            return False

        if operation == "move" and "destination" not in kwargs:
            return False

        return True

    def _validate_path(self, path_str: str) -> Path:
        """Validate and sanitize file path"""
        # Convert to Path object and resolve
        path = Path(path_str).resolve()

        # Check for path traversal attempts
        if ".." in str(path):
            raise ValueError("Path traversal detected")

        # Could add additional checks for allowed directories
        # For example, restrict to user's home directory
        # allowed_root = Path.home()
        # if not path.is_relative_to(allowed_root):
        #     raise ValueError(f"Path outside allowed directory: {allowed_root}")

        return path

    async def _read_file(self, path: Path) -> dict:
        """Read file contents"""
        if not path.exists():
            return {"success": False, "error": "File not found"}

        if not path.is_file():
            return {"success": False, "error": "Not a file"}

        # Check file size (limit to 10MB)
        max_size = 10 * 1024 * 1024
        if path.stat().st_size > max_size:
            return {"success": False, "error": f"File too large (>{max_size} bytes)"}

        try:
            async with aiofiles.open(path, 'r') as f:
                content = await f.read()

            return {
                "success": True,
                "data": {
                    "path": str(path),
                    "content": content,
                    "size": len(content),
                    "modified": path.stat().st_mtime
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _write_file(self, path: Path, content: str) -> dict:
        """Write content to file"""
        try:
            # Create parent directories if they don't exist
            path.parent.mkdir(parents=True, exist_ok=True)

            # Backup existing file if it exists
            backup_path = None
            if path.exists():
                backup_path = path.with_suffix(path.suffix + '.bak')
                path.rename(backup_path)

            try:
                async with aiofiles.open(path, 'w') as f:
                    await f.write(content)

                # Remove backup on success
                if backup_path and backup_path.exists():
                    backup_path.unlink()

                return {
                    "success": True,
                    "data": {
                        "path": str(path),
                        "bytes_written": len(content),
                        "backup_created": backup_path is not None
                    }
                }

            except Exception as e:
                # Restore backup on failure
                if backup_path and backup_path.exists():
                    backup_path.rename(path)
                raise e

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _list_directory(self, path: Path) -> dict:
        """List directory contents"""
        if not path.exists():
            return {"success": False, "error": "Directory not found"}

        if not path.is_dir():
            return {"success": False, "error": "Not a directory"}

        try:
            items = []
            for item in path.iterdir():
                items.append({
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else None,
                    "modified": item.stat().st_mtime
                })

            return {
                "success": True,
                "data": {
                    "path": str(path),
                    "items": items,
                    "count": len(items)
                }
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _delete_file(self, path: Path) -> dict:
        """Delete a file (with safety checks)"""
        if not path.exists():
            return {"success": False, "error": "File not found"}

        try:
            # Create backup before deletion
            backup_path = path.with_suffix(path.suffix + '.deleted')
            path.rename(backup_path)

            # Store deletion metadata
            metadata = {
                "original_path": str(path),
                "deleted_at": datetime.now().isoformat(),
                "backup_path": str(backup_path)
            }

            metadata_path = backup_path.with_suffix('.metadata.json')
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f)

            return {
                "success": True,
                "data": {
                    "path": str(path),
                    "backup": str(backup_path),
                    "recoverable": True
                }
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _move_file(self, source: Path, destination: Path) -> dict:
        """Move/rename a file"""
        if not source.exists():
            return {"success": False, "error": "Source file not found"}

        if destination.exists():
            return {"success": False, "error": "Destination already exists"}

        try:
            # Create parent directories for destination
            destination.parent.mkdir(parents=True, exist_ok=True)

            # Move the file
            source.rename(destination)

            return {
                "success": True,
                "data": {
                    "source": str(source),
                    "destination": str(destination)
                }
            }

        except Exception as e:
            return {"success": False, "error": str(e)}


# Example usage in a neuron
async def example_usage():
    """Example of how a neuron would use the filesystem tool"""

    # Create tool instance
    fs_tool = FileSystemTool()

    # Read a file
    result = await fs_tool.execute(
        operation="read",
        path="/home/user/document.txt"
    )
    print("Read result:", result)

    # Write a file
    result = await fs_tool.execute(
        operation="write",
        path="/tmp/test.txt",
        content="Hello from BRANE!"
    )
    print("Write result:", result)

    # List directory
    result = await fs_tool.execute(
        operation="list",
        path="/home/user"
    )
    print("List result:", result)