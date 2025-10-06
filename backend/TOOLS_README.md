# 🔧 BRANE Tools System

**Enable your neurons to interact with the real world** - SSH, HTTP APIs, files, and 50+ battle-tested integrations.

## Overview

BRANE's tool system gives neurons **hands and feet** in both digital and physical worlds:

- **SSH** - Execute commands on remote servers
- **HTTP** - Call REST APIs, webhooks, cloud services
- **Files** - Read/write/search local filesystem
- **MCP Servers** - 50+ official integrations (GitHub, Slack, databases, etc.)

## Architecture

```
┌─────────────────────────────────────┐
│        Neuron (AI Agent)            │
│                                      │
│  ┌──────────────────────────────┐  │
│  │   LiteLLM Broker             │  │
│  │   (Ollama/OpenAI/Anthropic)  │  │
│  └──────────┬───────────────────┘  │
│             │                       │
│  ┌──────────▼───────────────────┐  │
│  │   Tool Integration Layer     │  │
│  │                               │  │
│  │  ┌────────┐   ┌───────────┐ │  │
│  │  │LangChain│   │    MCP    │ │  │
│  │  │  Tools │   │  Servers  │ │  │
│  │  └────────┘   └───────────┘ │  │
│  └──────────────────────────────┘  │
│                                      │
│  ┌──────────────────────────────┐  │
│  │   Actual Execution           │  │
│  │  • SSH commands              │  │
│  │  • HTTP requests             │  │
│  │  • File operations           │  │
│  │  • MCP tools (GitHub, etc.)  │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
```

## Quick Start

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Available Tools

#### Built-in LangChain Tools

**SSH Tool** (`backend/tools/ssh_tool.py`)
```python
# Execute commands on remote servers
await ssh_tool.execute(
    host="192.168.1.10",
    command="df -h",
    username="admin",
    key_path="~/.ssh/id_rsa"
)
```

**HTTP Tool** (`backend/tools/http_tool.py`)
```python
# Call REST APIs
await http_tool.execute(
    url="https://api.github.com/repos/python/cpython",
    method="GET"
)
```

**Filesystem Tool** (`backend/tools/examples/filesystem_tool.py`)
```python
# Read/write files
await fs_tool.execute(
    operation="read",
    path="/home/user/document.txt"
)
```

#### MCP Server Tools (50+ integrations)

**Official MCP Servers:**
- **Filesystem** - Sandboxed file access
- **Fetch** - HTTP requests with CORS support
- **GitHub** - Repository management
- **Slack** - Team communication
- **Postgres** - Database operations
- **Google Drive** - Cloud storage
- **Puppeteer** - Browser automation

**To enable MCP tools:**

1. The MCP adapter auto-initializes on first neuron chat
2. Default servers: filesystem (sandboxed to `/tmp/brane`) and fetch
3. Customize in `backend/tools/mcp_adapter.py` → `DEFAULT_MCP_SERVERS`

## Tool Safety

### Risk Levels

- **LOW** - Read-only operations (safe)
- **MEDIUM** - Write operations, reversible
- **HIGH** - System changes, network calls
- **CRITICAL** - Irreversible, dangerous

### Dangerous Command Detection

SSH tool automatically flags commands like:
- `rm`, `del`, `format`
- `shutdown`, `reboot`
- `chmod -R`, `chown -R`

### Sandboxing (Recommended)

For production, integrate **E2B sandboxing**:

```bash
pip install e2b
```

See research: https://e2b.dev (150ms Firecracker microVMs)

## API Endpoints

### List Available Tools

```bash
GET /api/tools
Authorization: Bearer <token>
```

Response:
```json
[
  {
    "name": "ssh_execute",
    "description": "Execute commands on remote servers via SSH",
    "category": "network",
    "risk_level": "high",
    "requires_confirmation": true,
    "parameters": [...]
  }
]
```

### Get Tool Details

```bash
GET /api/tools/ssh_execute
Authorization: Bearer <token>
```

## Configuration

### Enable/Disable Tools Per Neuron

Edit neuron's YAML config:

```yaml
# neuron_config.yaml
metadata:
  name: "DevOps Assistant"

tools:
  - id: "ssh"
    enabled: true
  - id: "http"
    enabled: true
  - id: "filesystem"
    enabled: false  # Disable for this neuron
```

### MCP Server Configuration

Customize MCP servers in `backend/tools/mcp_adapter.py`:

```python
DEFAULT_MCP_SERVERS = [
    {
        "name": "github",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"]
    },
    {
        "name": "postgres",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-postgres"]
    }
]
```

## Testing with Ollama

### 1. Install Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### 2. Pull Function-Calling Model

```bash
ollama pull qwen2.5:7b
# or
ollama pull hermes3:8b
```

### 3. Create Test Neuron

```python
# Create neuron with Ollama
neuron_config = {
    "metadata": {"name": "Test Agent"},
    "model": {
        "provider": "ollama",
        "model": "qwen2.5:7b",
        "endpoint": "http://localhost:11434"
    }
}

# Chat with tools enabled
response = await neuron.chat(
    user_message="Check disk space on 192.168.1.10",
    user_id="test_user",
    session_id="test_session"
)
```

The neuron will automatically:
1. Detect SSH tool is needed
2. Call `ssh_execute(host="192.168.1.10", command="df -h")`
3. Return formatted results

## Development

### Adding Custom Tools

1. **Create tool class** (inherit from `DigitalTool` or `PhysicalTool`):

```python
# backend/tools/my_tool.py
from .base import DigitalTool, ToolSchema, ToolParameter

class MyCustomTool(DigitalTool):
    def __init__(self):
        schema = ToolSchema(
            name="my_tool",
            description="What this tool does",
            category=ToolCategory.CUSTOM,
            risk_level=ToolRiskLevel.LOW,
            parameters=[
                ToolParameter(
                    name="input",
                    type="string",
                    description="Input parameter"
                )
            ],
            returns={"type": "object"}
        )
        super().__init__(schema)

    async def execute(self, **kwargs):
        # Tool implementation
        return {"success": True, "result": "..."}

    async def validate_parameters(self, **kwargs):
        return True
```

2. **Register in `backend/api/tools.py`**:

```python
AVAILABLE_TOOLS = {
    "ssh": SSHTool,
    "http": HTTPTool,
    "filesystem": FileSystemTool,
    "my_tool": MyCustomTool  # Add here
}
```

3. **Auto-loaded on next neuron chat**

### Adding MCP Servers

1. Find MCP server on npm/PyPI
2. Add to `DEFAULT_MCP_SERVERS` in `mcp_adapter.py`
3. Restart backend

## Best Practices

### 1. Privacy-First

- Tools run from user's machine (not BRANE servers)
- Credentials stored in OS keychain
- No telemetry on tool usage

### 2. Rate Limiting

Default limits per tool (configurable in `ToolSchema`):
- `max_calls_per_minute`: 60
- `max_calls_per_hour`: 1000
- `max_data_mb_per_hour`: 100

### 3. Error Handling

All tools return structured responses:

```python
{
    "success": bool,
    "data": any,           # On success
    "error": str,          # On failure
    "metadata": {...}
}
```

### 4. Logging

Tools use Python logging:

```python
import logging
logger = logging.getLogger(__name__)

logger.info(f"Tool executed: {tool_name}")
logger.error(f"Tool failed: {error}")
```

## Roadmap

### Phase 1: MVP ✅
- [x] LangChain SSH, HTTP, File tools
- [x] LiteLLM integration
- [x] MCP adapter
- [x] Tools API endpoints

### Phase 2: Enhanced Tools (Current)
- [ ] E2B sandboxing integration
- [ ] Composio authentication (250+ tools)
- [ ] Tool marketplace
- [ ] Usage analytics

### Phase 3: Downloadable Neurons
- [ ] Package tools with neurons
- [ ] Offline tool execution
- [ ] Local credential management
- [ ] Sync tool state across devices

## Troubleshooting

### MCP Tools Not Loading

**Problem:** MCP servers not starting

**Solution:**
```bash
# Ensure Node.js installed
node --version  # v18+

# Test MCP server directly
npx -y @modelcontextprotocol/server-filesystem /tmp/test
```

### SSH Authentication Fails

**Problem:** `paramiko.AuthenticationException`

**Solution:**
1. Check SSH key permissions: `chmod 600 ~/.ssh/id_rsa`
2. Add to SSH agent: `ssh-add ~/.ssh/id_rsa`
3. Test connection: `ssh user@host`

### Ollama Function Calling Not Working

**Problem:** Model doesn't use tools

**Solution:**
1. Use function-calling model: `ollama pull qwen2.5:7b`
2. Check LiteLLM logs for tool format errors
3. Verify `capabilities.native_tools` in broker.py

## Support

- **Issues:** https://github.com/sharminsirajudeen/brane_v2/issues
- **Research:** See `RESEARCH_TOOLS.md` for battle-tested frameworks
- **MCP Docs:** https://modelcontextprotocol.io

## License

Same as BRANE - MIT License

---

**Built with love for privacy-first AI agents** 🧠🔧
