"""
BRANE Built-in Tools - Ready to use out of the box!

These 3 tools cover 90% of use cases:
1. FileOps - Read/write files safely
2. WebRequest - Call any API or webhook
3. Shell - Run safe system commands

Users can extend with custom tools in /tools/custom/
"""

from .file_ops import FileOpsTool
from .web_request import WebRequestTool
from .shell import ShellTool, create_dev_shell_tool

# Initialize built-in tools
def get_builtin_tools(workspace_path: str = "./workspace"):
    """
    Get all built-in tools, ready to use.

    Returns:
        List of initialized tool instances
    """
    return [
        FileOpsTool(workspace_path=workspace_path),
        WebRequestTool(),
        create_dev_shell_tool(workspace_path=workspace_path)
    ]


__all__ = [
    'FileOpsTool',
    'WebRequestTool',
    'ShellTool',
    'create_dev_shell_tool',
    'get_builtin_tools'
]
