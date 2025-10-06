"""
File Operations Tool - Safe file reading/writing with workspace sandboxing
Users love this: "Read my config file", "Save this analysis to report.md"
"""

import os
import aiofiles
from pathlib import Path
from typing import Optional
from ..base import DigitalTool, ToolSchema, ToolParameter, ToolCategory, ToolRiskLevel


class FileOpsTool(DigitalTool):
    """
    Read and write files safely within workspace boundaries.
    Automatic sandboxing to prevent access outside allowed paths.
    """

    def __init__(self, workspace_path: str = "./workspace"):
        schema = ToolSchema(
            name="file_ops",
            description="Read and write files safely within your workspace. Perfect for reading configs, saving reports, managing project files.",
            category=ToolCategory.FILE_SYSTEM,
            risk_level=ToolRiskLevel.MEDIUM,
            parameters=[
                ToolParameter(
                    name="action",
                    type="string",
                    description="Action to perform: 'read', 'write', 'append', 'list', 'exists'",
                    required=True
                ),
                ToolParameter(
                    name="path",
                    type="string",
                    description="File path relative to workspace (e.g., 'reports/analysis.md')",
                    required=True
                ),
                ToolParameter(
                    name="content",
                    type="string",
                    description="Content to write (only for write/append actions)",
                    required=False
                )
            ],
            returns={"type": "object", "description": "File operation result"},
            requires_confirmation=False,  # Reading is safe, writing shows what's being saved
            requires_filesystem=True
        )
        super().__init__(schema)
        self.workspace = Path(workspace_path).resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)

    def _get_safe_path(self, relative_path: str) -> Optional[Path]:
        """
        Ensure path is within workspace (prevent directory traversal attacks).
        Returns None if path escapes workspace.
        """
        target = (self.workspace / relative_path).resolve()

        # Check if target is within workspace
        try:
            target.relative_to(self.workspace)
            return target
        except ValueError:
            return None  # Path escapes workspace

    async def validate_parameters(self, action: str, path: str, content: Optional[str] = None, **kwargs) -> bool:
        """Validate parameters"""
        valid_actions = ["read", "write", "append", "list", "exists", "delete"]
        if action not in valid_actions:
            return False

        if action in ["write", "append"] and content is None:
            return False

        return self._get_safe_path(path) is not None

    async def execute(self, action: str, path: str, content: Optional[str] = None, **kwargs):
        """Execute file operation"""
        safe_path = self._get_safe_path(path)
        if not safe_path:
            return {"success": False, "error": f"Path '{path}' is outside workspace"}

        try:
            if action == "read":
                if not safe_path.exists():
                    return {"success": False, "error": f"File not found: {path}"}

                async with aiofiles.open(safe_path, 'r') as f:
                    content = await f.read()
                return {
                    "success": True,
                    "content": content,
                    "size_bytes": len(content),
                    "path": str(safe_path.relative_to(self.workspace))
                }

            elif action == "write":
                # Create parent directories if needed
                safe_path.parent.mkdir(parents=True, exist_ok=True)

                async with aiofiles.open(safe_path, 'w') as f:
                    await f.write(content)
                return {
                    "success": True,
                    "message": f"Written {len(content)} bytes to {path}",
                    "path": str(safe_path.relative_to(self.workspace))
                }

            elif action == "append":
                safe_path.parent.mkdir(parents=True, exist_ok=True)

                async with aiofiles.open(safe_path, 'a') as f:
                    await f.write(content)
                return {
                    "success": True,
                    "message": f"Appended {len(content)} bytes to {path}",
                    "path": str(safe_path.relative_to(self.workspace))
                }

            elif action == "list":
                if not safe_path.is_dir():
                    return {"success": False, "error": f"Not a directory: {path}"}

                files = []
                for item in safe_path.iterdir():
                    files.append({
                        "name": item.name,
                        "type": "directory" if item.is_dir() else "file",
                        "size": item.stat().st_size if item.is_file() else None
                    })
                return {"success": True, "files": files, "count": len(files)}

            elif action == "exists":
                return {"success": True, "exists": safe_path.exists()}

            elif action == "delete":
                if not safe_path.exists():
                    return {"success": False, "error": f"File not found: {path}"}

                safe_path.unlink()
                return {"success": True, "message": f"Deleted {path}"}

        except Exception as e:
            return {"success": False, "error": str(e)}
