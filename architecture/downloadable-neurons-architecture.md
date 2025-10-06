# BRANE Downloadable Neurons Architecture

## Executive Summary

Downloadable neurons enable users to export AI agents from BRANE's web UI and run them locally with full tool access and memory persistence. This architecture leverages containerization for portability while maintaining flexibility through multiple runtime options.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         BRANE Cloud                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   FastAPI    │  │  PostgreSQL  │  │   LiteLLM    │          │
│  │   Backend    │  │   Database   │  │   Router     │          │
│  └──────┬───────┘  └──────┬───────┘  └──────────────┘          │
│         │                  │                                     │
│         ▼                  ▼                                     │
│  ┌─────────────────────────────────┐                           │
│  │    Neuron Package Builder        │                           │
│  │  - Export neuron config          │                           │
│  │  - Bundle tools & credentials    │                           │
│  │  - Create manifest               │                           │
│  └─────────────┬───────────────────┘                           │
└────────────────┼────────────────────────────────────────────────┘
                 │
                 ▼ Download (.brane package)
┌─────────────────────────────────────────────────────────────────┐
│                         Local Machine                            │
│  ┌──────────────────────────────────────────────────┐          │
│  │           BRANE Neuron Package (.brane)          │          │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐ │          │
│  │  │  manifest  │  │   neuron   │  │   tools    │ │          │
│  │  │   .yaml    │  │   .json    │  │   .yaml    │ │          │
│  │  └────────────┘  └────────────┘  └────────────┘ │          │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐ │          │
│  │  │   memory   │  │ credentials│  │  runtime   │ │          │
│  │  │    .db     │  │   .enc     │  │    .py     │ │          │
│  │  └────────────┘  └────────────┘  └────────────┘ │          │
│  └──────────────────────┬───────────────────────────┘          │
│                         │                                        │
│         ┌───────────────┼───────────────┐                      │
│         ▼               ▼               ▼                      │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐              │
│  │   Docker   │  │   Python   │  │ Standalone │              │
│  │  Container │  │   Package  │  │ Executable │              │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘              │
│        │               │               │                       │
│        └───────────────┼───────────────┘                      │
│                        ▼                                       │
│  ┌──────────────────────────────────────────────┐            │
│  │          BRANE Local Runtime                  │            │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  │            │
│  │  │  Ollama  │  │   vLLM   │  │llama.cpp │  │            │
│  │  └──────────┘  └──────────┘  └──────────┘  │            │
│  └──────────────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

## 1. Package Structure

### Directory Layout of `.brane` Package

```
neuron-{uuid}.brane/
├── manifest.yaml           # Package metadata and version info
├── neuron.json            # Neuron configuration
├── tools/
│   ├── definitions.yaml   # Tool schemas and configurations
│   └── custom/           # Custom tool implementations
│       └── ssh_tool.py
├── memory/
│   ├── memory.db         # SQLite database (L1-L4 layers)
│   └── embeddings/       # Vector embeddings cache
│       └── index.faiss
├── credentials/
│   └── vault.enc         # Encrypted credentials store
├── runtime/
│   ├── requirements.txt  # Python dependencies
│   ├── runtime.py       # Main execution script
│   └── config.yaml      # Runtime configuration
├── docker/
│   └── Dockerfile       # Container definition
└── .brane/
    ├── version         # Package version
    └── checksum        # Integrity verification
```

## 2. Package Manifest Schema

```yaml
# manifest.yaml
version: "1.0.0"
neuron:
  id: "550e8400-e29b-41d4-a716-446655440000"
  name: "DevOps Assistant"
  description: "SSH management and server automation"
  privacy_tier: 0  # 0=local, 1=encrypted, 2=public
  created_at: "2024-01-15T10:30:00Z"
  updated_at: "2024-01-20T14:22:00Z"

runtime:
  min_python_version: "3.9"
  preferred_llm: "llama3.1:8b"
  fallback_llms:
    - "mistral:7b"
    - "phi3:mini"

tools:
  - type: "ssh"
    version: "1.0"
    required: true
  - type: "http_api"
    version: "2.0"
    required: false

sync:
  cloud_id: "550e8400-e29b-41d4-a716-446655440000"
  last_sync: "2024-01-20T14:22:00Z"
  sync_enabled: true
  conflict_resolution: "local_priority"  # or "cloud_priority", "manual"
```

## 3. Runtime Options

### Option A: Docker Container (Recommended for Production)

```dockerfile
# docker/Dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    sqlite3 \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama client
RUN curl -fsSL https://ollama.ai/install.sh | sh

WORKDIR /app

# Copy neuron package
COPY . /app/neuron

# Install Python dependencies
RUN pip install --no-cache-dir \
    litellm==1.0.0 \
    langchain==0.1.0 \
    sqlalchemy==2.0.0 \
    cryptography==41.0.0 \
    pydantic==2.0.0 \
    fastapi==0.104.0 \
    uvicorn==0.24.0

# Set environment variables
ENV BRANE_MODE=local
ENV BRANE_NEURON_PATH=/app/neuron
ENV OLLAMA_HOST=host.docker.internal:11434

# Expose API port
EXPOSE 8100

CMD ["python", "/app/neuron/runtime/runtime.py"]
```

### Option B: Python Package

```python
# setup.py for pip installation
from setuptools import setup, find_packages

setup(
    name="brane-neuron-{uuid}",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "litellm>=1.0.0",
        "langchain>=0.1.0",
        "sqlalchemy>=2.0.0",
        "cryptography>=41.0.0",
        "pydantic>=2.0.0",
    ],
    entry_points={
        "console_scripts": [
            "brane-neuron=brane_runtime.main:run",
        ],
    },
    package_data={
        "": ["*.yaml", "*.json", "*.db", "*.enc"],
    },
)
```

### Option C: Standalone Executable

```python
# build_executable.py using PyInstaller
import PyInstaller.__main__

PyInstaller.__main__.run([
    'runtime/runtime.py',
    '--name=brane-neuron',
    '--onefile',
    '--add-data=neuron.json:.',
    '--add-data=tools:tools',
    '--add-data=memory:memory',
    '--hidden-import=litellm',
    '--hidden-import=langchain',
    '--hidden-import=sqlalchemy',
])
```

## 4. Local Runtime Implementation

```python
# runtime/runtime.py
import os
import json
import yaml
import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet
from litellm import completion
from pydantic import BaseModel
import asyncio
from enum import Enum

class RuntimeMode(Enum):
    LOCAL = "local"
    CLOUD = "cloud"
    HYBRID = "hybrid"

class BraneNeuronRuntime:
    def __init__(self, package_path: Path):
        self.package_path = package_path
        self.manifest = self._load_manifest()
        self.neuron_config = self._load_neuron_config()
        self.tools = self._load_tools()
        self.memory_db = self._init_memory()
        self.credentials = self._load_credentials()
        self.mode = self._detect_mode()

    def _load_manifest(self) -> Dict[str, Any]:
        with open(self.package_path / "manifest.yaml") as f:
            return yaml.safe_load(f)

    def _load_neuron_config(self) -> Dict[str, Any]:
        with open(self.package_path / "neuron.json") as f:
            return json.load(f)

    def _init_memory(self) -> sqlite3.Connection:
        """Initialize SQLite for local memory storage"""
        db_path = self.package_path / "memory" / "memory.db"
        conn = sqlite3.connect(str(db_path))

        # Create memory tables if not exists
        conn.execute("""
            CREATE TABLE IF NOT EXISTS l1_working_memory (
                id INTEGER PRIMARY KEY,
                content TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                ttl INTEGER DEFAULT 300
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS l2_short_term (
                id INTEGER PRIMARY KEY,
                content TEXT,
                embedding BLOB,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                ttl INTEGER DEFAULT 3600
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS l3_long_term (
                id INTEGER PRIMARY KEY,
                content TEXT,
                embedding BLOB,
                category TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS l4_persistent (
                id INTEGER PRIMARY KEY,
                key TEXT UNIQUE,
                value TEXT,
                metadata TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        return conn

    def _load_credentials(self) -> Dict[str, Any]:
        """Load and decrypt credentials"""
        cred_path = self.package_path / "credentials" / "vault.enc"
        if not cred_path.exists():
            return {}

        # Get encryption key from environment or keyring
        key = os.environ.get("BRANE_CRED_KEY")
        if not key:
            try:
                import keyring
                key = keyring.get_password("brane", "neuron_key")
            except ImportError:
                print("Warning: keyring not available, credentials not loaded")
                return {}

        if key:
            fernet = Fernet(key.encode())
            with open(cred_path, 'rb') as f:
                encrypted_data = f.read()
            decrypted = fernet.decrypt(encrypted_data)
            return json.loads(decrypted)
        return {}

    def _detect_mode(self) -> RuntimeMode:
        """Detect if running locally, in cloud, or hybrid"""
        if os.environ.get("BRANE_MODE") == "local":
            return RuntimeMode.LOCAL
        elif os.environ.get("BRANE_MODE") == "cloud":
            return RuntimeMode.CLOUD
        else:
            # Check if we can reach cloud API
            try:
                import requests
                response = requests.get(
                    "http://api.brane.ai/health",
                    timeout=2
                )
                if response.status_code == 200:
                    return RuntimeMode.HYBRID
            except:
                pass
            return RuntimeMode.LOCAL

    def _get_llm_provider(self) -> Dict[str, Any]:
        """Determine LLM provider based on availability"""
        preferred = self.manifest["runtime"]["preferred_llm"]

        # Try Ollama first for local mode
        if self.mode == RuntimeMode.LOCAL:
            try:
                import requests
                response = requests.get("http://localhost:11434/api/tags")
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    model_names = [m["name"] for m in models]

                    if preferred in model_names:
                        return {
                            "provider": "ollama",
                            "model": preferred,
                            "api_base": "http://localhost:11434"
                        }

                    # Try fallback models
                    for fallback in self.manifest["runtime"]["fallback_llms"]:
                        if fallback in model_names:
                            return {
                                "provider": "ollama",
                                "model": fallback,
                                "api_base": "http://localhost:11434"
                            }
            except:
                pass

        # Try vLLM
        try:
            import requests
            response = requests.get("http://localhost:8000/v1/models")
            if response.status_code == 200:
                return {
                    "provider": "vllm",
                    "model": preferred,
                    "api_base": "http://localhost:8000/v1"
                }
        except:
            pass

        # Fallback to cloud if in hybrid mode
        if self.mode == RuntimeMode.HYBRID:
            return {
                "provider": "openai",
                "model": "gpt-3.5-turbo",
                "api_key": os.environ.get("OPENAI_API_KEY")
            }

        raise RuntimeError("No LLM provider available")

    async def execute(self, prompt: str) -> str:
        """Execute neuron with given prompt"""
        llm_config = self._get_llm_provider()

        # Build context from memory
        context = self._build_context()

        # Prepare messages
        messages = [
            {"role": "system", "content": self.neuron_config["system_prompt"]},
            {"role": "system", "content": f"Context: {context}"},
            {"role": "user", "content": prompt}
        ]

        # Check if model supports function calling
        supports_functions = self._check_function_support(llm_config["model"])

        if supports_functions and self.tools:
            # Use native function calling
            response = await self._execute_with_functions(
                messages,
                llm_config,
                self.tools
            )
        else:
            # Use ReAct pattern for models without function calling
            response = await self._execute_with_react(
                messages,
                llm_config,
                self.tools
            )

        # Store in memory
        self._update_memory(prompt, response)

        # Sync if in hybrid mode
        if self.mode == RuntimeMode.HYBRID:
            await self._sync_to_cloud()

        return response

    def _check_function_support(self, model: str) -> bool:
        """Check if model supports function calling"""
        function_models = [
            "gpt-3.5-turbo", "gpt-4",
            "claude-3", "claude-2",
            "llama3.1", "llama3.2",
            "mistral-large"
        ]
        return any(fm in model.lower() for fm in function_models)

    async def _execute_with_functions(
        self,
        messages: list,
        llm_config: dict,
        tools: dict
    ) -> str:
        """Execute with native function calling"""
        # Convert tools to OpenAI function format
        functions = []
        for tool_name, tool_config in tools.items():
            functions.append({
                "name": tool_name,
                "description": tool_config["description"],
                "parameters": tool_config["parameters"]
            })

        # Call LLM with functions
        response = completion(
            model=f"{llm_config['provider']}/{llm_config['model']}",
            messages=messages,
            functions=functions,
            api_base=llm_config.get("api_base"),
            api_key=llm_config.get("api_key")
        )

        # Handle function calls
        if response.choices[0].message.function_call:
            function_name = response.choices[0].message.function_call.name
            function_args = json.loads(
                response.choices[0].message.function_call.arguments
            )

            # Execute tool
            result = await self._execute_tool(function_name, function_args)

            # Get final response with function result
            messages.append(response.choices[0].message)
            messages.append({
                "role": "function",
                "name": function_name,
                "content": str(result)
            })

            final_response = completion(
                model=f"{llm_config['provider']}/{llm_config['model']}",
                messages=messages,
                api_base=llm_config.get("api_base"),
                api_key=llm_config.get("api_key")
            )

            return final_response.choices[0].message.content

        return response.choices[0].message.content

    async def _execute_with_react(
        self,
        messages: list,
        llm_config: dict,
        tools: dict
    ) -> str:
        """Execute using ReAct pattern for models without function calling"""
        # Build ReAct prompt
        react_prompt = self._build_react_prompt(tools)
        messages[0]["content"] += f"\n\n{react_prompt}"

        max_iterations = 5
        for i in range(max_iterations):
            response = completion(
                model=f"{llm_config['provider']}/{llm_config['model']}",
                messages=messages,
                api_base=llm_config.get("api_base"),
                api_key=llm_config.get("api_key")
            )

            content = response.choices[0].message.content

            # Parse ReAct response
            if "Action:" in content:
                action = self._parse_react_action(content)
                if action:
                    result = await self._execute_tool(
                        action["tool"],
                        action["args"]
                    )

                    # Add observation to messages
                    messages.append({
                        "role": "assistant",
                        "content": content
                    })
                    messages.append({
                        "role": "user",
                        "content": f"Observation: {result}"
                    })
                    continue

            # Final answer
            if "Final Answer:" in content:
                return content.split("Final Answer:")[-1].strip()

            return content

        return "Max iterations reached without final answer"

    def _build_react_prompt(self, tools: dict) -> str:
        """Build ReAct prompt with available tools"""
        tool_descriptions = []
        for name, config in tools.items():
            params = ", ".join(config["parameters"]["properties"].keys())
            tool_descriptions.append(
                f"- {name}({params}): {config['description']}"
            )

        return f"""
You have access to the following tools:
{chr(10).join(tool_descriptions)}

Use the following format:
Thought: reasoning about what to do
Action: tool_name
Action Input: {{"param1": "value1", "param2": "value2"}}
Observation: tool result
... (repeat Thought/Action/Observation as needed)
Thought: I now know the final answer
Final Answer: the final response to the user
"""

    def _parse_react_action(self, content: str) -> Optional[Dict]:
        """Parse ReAct action from LLM response"""
        import re

        action_match = re.search(r"Action: (.+)", content)
        input_match = re.search(r"Action Input: (.+)", content, re.DOTALL)

        if action_match and input_match:
            tool_name = action_match.group(1).strip()
            try:
                args = json.loads(input_match.group(1).strip())
                return {"tool": tool_name, "args": args}
            except json.JSONDecodeError:
                return None
        return None

    async def _execute_tool(self, tool_name: str, args: dict) -> Any:
        """Execute a tool with given arguments"""
        tool_config = self.tools.get(tool_name)
        if not tool_config:
            return f"Tool {tool_name} not found"

        tool_type = tool_config["type"]

        if tool_type == "ssh":
            return await self._execute_ssh_tool(args)
        elif tool_type == "http_api":
            return await self._execute_http_tool(args)
        elif tool_type == "custom":
            return await self._execute_custom_tool(tool_name, args)
        else:
            return f"Unknown tool type: {tool_type}"

    async def _execute_ssh_tool(self, args: dict) -> str:
        """Execute SSH command"""
        import asyncssh

        host = args.get("host")
        command = args.get("command")

        # Get credentials
        ssh_creds = self.credentials.get("ssh", {}).get(host, {})

        async with asyncssh.connect(
            host,
            username=ssh_creds.get("username"),
            password=ssh_creds.get("password"),
            known_hosts=None
        ) as conn:
            result = await conn.run(command)
            return result.stdout

    async def _execute_http_tool(self, args: dict) -> str:
        """Execute HTTP API call"""
        import aiohttp

        method = args.get("method", "GET")
        url = args.get("url")
        headers = args.get("headers", {})
        data = args.get("data")

        # Add auth from credentials if needed
        api_creds = self.credentials.get("apis", {})
        for api_pattern, creds in api_creds.items():
            if api_pattern in url:
                if creds.get("type") == "bearer":
                    headers["Authorization"] = f"Bearer {creds['token']}"
                elif creds.get("type") == "api_key":
                    headers[creds["header"]] = creds["key"]

        async with aiohttp.ClientSession() as session:
            async with session.request(
                method,
                url,
                headers=headers,
                json=data if method in ["POST", "PUT"] else None,
                params=data if method == "GET" else None
            ) as response:
                return await response.text()

    def _build_context(self) -> str:
        """Build context from memory layers"""
        context_parts = []

        # L1: Working memory (last 5 items)
        cursor = self.memory_db.execute(
            "SELECT content FROM l1_working_memory ORDER BY timestamp DESC LIMIT 5"
        )
        working = [row[0] for row in cursor.fetchall()]
        if working:
            context_parts.append(f"Recent context: {'; '.join(working)}")

        # L2: Short-term memory (relevant items)
        # This would use vector similarity in production
        cursor = self.memory_db.execute(
            "SELECT content FROM l2_short_term ORDER BY timestamp DESC LIMIT 10"
        )
        short_term = [row[0] for row in cursor.fetchall()]
        if short_term:
            context_parts.append(f"Short-term memory: {'; '.join(short_term[:3])}")

        # L4: Persistent facts
        cursor = self.memory_db.execute(
            "SELECT key, value FROM l4_persistent LIMIT 10"
        )
        facts = [f"{k}: {v}" for k, v in cursor.fetchall()]
        if facts:
            context_parts.append(f"Known facts: {'; '.join(facts)}")

        return "\n".join(context_parts)

    def _update_memory(self, prompt: str, response: str):
        """Update memory layers with new interaction"""
        import time

        # Add to L1 working memory
        self.memory_db.execute(
            "INSERT INTO l1_working_memory (content, ttl) VALUES (?, ?)",
            (f"User: {prompt[:200]}", 300)
        )
        self.memory_db.execute(
            "INSERT INTO l1_working_memory (content, ttl) VALUES (?, ?)",
            (f"Assistant: {response[:200]}", 300)
        )

        # Clean expired entries
        self.memory_db.execute(
            "DELETE FROM l1_working_memory WHERE datetime(timestamp, '+' || ttl || ' seconds') < datetime('now')"
        )

        self.memory_db.commit()

    async def _sync_to_cloud(self):
        """Sync neuron state to cloud"""
        if not self.manifest["sync"]["sync_enabled"]:
            return

        import aiohttp

        # Prepare sync payload
        sync_data = {
            "neuron_id": self.manifest["neuron"]["id"],
            "memory_snapshot": self._export_memory(),
            "last_execution": {
                "timestamp": "now",
                "mode": self.mode.value
            }
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.brane.ai/v1/neurons/sync",
                json=sync_data,
                headers={"Authorization": f"Bearer {os.environ.get('BRANE_API_KEY')}"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    # Handle any cloud updates
                    if result.get("updates"):
                        await self._apply_cloud_updates(result["updates"])

    def _export_memory(self) -> dict:
        """Export memory for sync"""
        memory_export = {}

        for table in ["l1_working_memory", "l2_short_term", "l3_long_term", "l4_persistent"]:
            cursor = self.memory_db.execute(f"SELECT * FROM {table}")
            memory_export[table] = cursor.fetchall()

        return memory_export

# Main entry point
async def main():
    import sys
    package_path = Path(sys.argv[1] if len(sys.argv) > 1 else ".")

    runtime = BraneNeuronRuntime(package_path)

    # Start interactive session or API server
    if os.environ.get("BRANE_API_MODE"):
        # Run as API server
        from fastapi import FastAPI, Request
        import uvicorn

        app = FastAPI()

        @app.post("/execute")
        async def execute(request: Request):
            data = await request.json()
            response = await runtime.execute(data["prompt"])
            return {"response": response}

        uvicorn.run(app, host="0.0.0.0", port=8100)
    else:
        # Interactive mode
        print(f"BRANE Neuron: {runtime.manifest['neuron']['name']}")
        print(f"Mode: {runtime.mode.value}")
        print("Type 'exit' to quit\n")

        while True:
            try:
                prompt = input("> ")
                if prompt.lower() == "exit":
                    break

                response = await runtime.execute(prompt)
                print(f"\n{response}\n")
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
```

## 5. Tool Definition Schema

```yaml
# tools/definitions.yaml
tools:
  ssh:
    type: "ssh"
    version: "1.0"
    description: "Execute commands on remote servers via SSH"
    parameters:
      type: "object"
      properties:
        host:
          type: "string"
          description: "Target hostname or IP"
        command:
          type: "string"
          description: "Command to execute"
        timeout:
          type: "integer"
          default: 30
          description: "Command timeout in seconds"
      required: ["host", "command"]

    approval_required: true
    approval_rules:
      - pattern: "rm -rf"
        level: "critical"
        message: "Destructive command detected"
      - pattern: "sudo"
        level: "warning"
        message: "Elevated privileges requested"

  http_api:
    type: "http_api"
    version: "2.0"
    description: "Make HTTP API calls"
    parameters:
      type: "object"
      properties:
        url:
          type: "string"
          format: "uri"
        method:
          type: "string"
          enum: ["GET", "POST", "PUT", "DELETE"]
        headers:
          type: "object"
        data:
          type: "object"
      required: ["url"]

    rate_limits:
      - domain: "api.github.com"
        requests_per_minute: 60
      - domain: "*"
        requests_per_minute: 100

  custom_db_query:
    type: "custom"
    implementation: "custom/db_tool.py"
    description: "Query internal database"
    parameters:
      type: "object"
      properties:
        query:
          type: "string"
        database:
          type: "string"
      required: ["query"]
```

## 6. Backend API Changes

```python
# backend/api/neurons/download.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import tempfile
import zipfile
import json
import yaml
from pathlib import Path
from typing import Optional
from cryptography.fernet import Fernet

router = APIRouter()

@router.post("/neurons/{neuron_id}/export")
async def export_neuron(
    neuron_id: str,
    include_memory: bool = True,
    include_credentials: bool = True,
    encryption_key: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Export neuron as downloadable package"""

    # Fetch neuron from database
    neuron = db.query(Neuron).filter(
        Neuron.id == neuron_id,
        Neuron.user_id == current_user.id
    ).first()

    if not neuron:
        raise HTTPException(404, "Neuron not found")

    # Create temporary directory for package
    with tempfile.TemporaryDirectory() as tmpdir:
        package_dir = Path(tmpdir) / f"neuron-{neuron_id}"
        package_dir.mkdir()

        # Create manifest
        manifest = {
            "version": "1.0.0",
            "neuron": {
                "id": neuron.id,
                "name": neuron.name,
                "description": neuron.description,
                "privacy_tier": neuron.privacy_tier,
                "created_at": neuron.created_at.isoformat(),
                "updated_at": neuron.updated_at.isoformat()
            },
            "runtime": {
                "min_python_version": "3.9",
                "preferred_llm": neuron.config.get("llm_model", "llama3.1:8b"),
                "fallback_llms": ["mistral:7b", "phi3:mini"]
            },
            "sync": {
                "cloud_id": neuron.id,
                "last_sync": datetime.now().isoformat(),
                "sync_enabled": True,
                "conflict_resolution": "manual"
            }
        }

        with open(package_dir / "manifest.yaml", "w") as f:
            yaml.dump(manifest, f)

        # Save neuron configuration
        with open(package_dir / "neuron.json", "w") as f:
            json.dump(neuron.config, f, indent=2)

        # Export tools
        tools_dir = package_dir / "tools"
        tools_dir.mkdir()

        tools_config = {}
        for tool in neuron.tools:
            tools_config[tool.name] = {
                "type": tool.type,
                "version": tool.version,
                "description": tool.description,
                "parameters": tool.parameters,
                "approval_required": tool.approval_required
            }

            # Copy custom tool implementations
            if tool.type == "custom" and tool.implementation_path:
                custom_dir = tools_dir / "custom"
                custom_dir.mkdir(exist_ok=True)
                # Copy implementation file
                shutil.copy(tool.implementation_path, custom_dir)

        with open(tools_dir / "definitions.yaml", "w") as f:
            yaml.dump({"tools": tools_config}, f)

        # Export memory if requested
        if include_memory:
            memory_dir = package_dir / "memory"
            memory_dir.mkdir()

            # Export to SQLite
            sqlite_path = memory_dir / "memory.db"
            export_memory_to_sqlite(neuron_id, sqlite_path, db)

            # Export embeddings if available
            if neuron.embeddings:
                embeddings_dir = memory_dir / "embeddings"
                embeddings_dir.mkdir()
                # Export FAISS index or other vector store
                export_embeddings(neuron_id, embeddings_dir)

        # Export credentials if requested
        if include_credentials:
            creds_dir = package_dir / "credentials"
            creds_dir.mkdir()

            # Encrypt credentials
            credentials = get_neuron_credentials(neuron_id, db)

            if encryption_key:
                fernet = Fernet(encryption_key.encode())
            else:
                # Generate new key
                key = Fernet.generate_key()
                fernet = Fernet(key)
                encryption_key = key.decode()

            encrypted = fernet.encrypt(json.dumps(credentials).encode())

            with open(creds_dir / "vault.enc", "wb") as f:
                f.write(encrypted)

        # Create runtime directory
        runtime_dir = package_dir / "runtime"
        runtime_dir.mkdir()

        # Copy runtime.py (from template)
        with open("templates/runtime.py", "r") as f:
            runtime_code = f.read()

        with open(runtime_dir / "runtime.py", "w") as f:
            f.write(runtime_code)

        # Create requirements.txt
        with open(runtime_dir / "requirements.txt", "w") as f:
            f.write("""litellm>=1.0.0
langchain>=0.1.0
sqlalchemy>=2.0.0
cryptography>=41.0.0
pydantic>=2.0.0
fastapi>=0.104.0
uvicorn>=0.24.0
asyncssh>=2.14.0
aiohttp>=3.9.0
""")

        # Create runtime config
        runtime_config = {
            "api_mode": False,
            "interactive_mode": True,
            "port": 8100,
            "log_level": "INFO"
        }

        with open(runtime_dir / "config.yaml", "w") as f:
            yaml.dump(runtime_config, f)

        # Create Docker directory
        docker_dir = package_dir / "docker"
        docker_dir.mkdir()

        # Copy Dockerfile template
        with open("templates/Dockerfile", "r") as f:
            dockerfile = f.read()

        with open(docker_dir / "Dockerfile", "w") as f:
            f.write(dockerfile)

        # Create .brane metadata directory
        meta_dir = package_dir / ".brane"
        meta_dir.mkdir()

        with open(meta_dir / "version", "w") as f:
            f.write("1.0.0")

        # Calculate checksum
        import hashlib
        checksum = calculate_package_checksum(package_dir)

        with open(meta_dir / "checksum", "w") as f:
            f.write(checksum)

        # Create zip archive
        archive_path = Path(tmpdir) / f"neuron-{neuron_id}.brane"
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(package_dir):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(package_dir.parent)
                    zf.write(file_path, arcname)

        # Read archive for response
        with open(archive_path, "rb") as f:
            archive_data = f.read()

        # Log export event
        log_export_event(neuron_id, current_user.id, db)

        return {
            "filename": f"neuron-{neuron_id}.brane",
            "size": len(archive_data),
            "checksum": checksum,
            "encryption_key": encryption_key if include_credentials else None,
            "data": base64.b64encode(archive_data).decode()
        }

@router.post("/neurons/import")
async def import_neuron(
    file: UploadFile,
    encryption_key: Optional[str] = None,
    merge_memory: bool = False,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Import neuron from package"""

    # Save uploaded file
    with tempfile.NamedTemporaryFile(suffix=".brane", delete=False) as tmp:
        tmp.write(await file.read())
        package_path = tmp.name

    try:
        # Extract and validate package
        with tempfile.TemporaryDirectory() as tmpdir:
            with zipfile.ZipFile(package_path, "r") as zf:
                zf.extractall(tmpdir)

            # Find package directory
            package_dir = None
            for item in Path(tmpdir).iterdir():
                if item.is_dir() and item.name.startswith("neuron-"):
                    package_dir = item
                    break

            if not package_dir:
                raise HTTPException(400, "Invalid package format")

            # Load manifest
            with open(package_dir / "manifest.yaml") as f:
                manifest = yaml.safe_load(f)

            # Check if neuron already exists
            neuron_id = manifest["neuron"]["id"]
            existing = db.query(Neuron).filter(
                Neuron.id == neuron_id,
                Neuron.user_id == current_user.id
            ).first()

            if existing:
                # Update existing neuron
                if not merge_memory:
                    # Replace completely
                    existing.config = json.load(open(package_dir / "neuron.json"))
                    existing.updated_at = datetime.now()
                else:
                    # Merge memory
                    merge_neuron_memory(existing, package_dir / "memory", db)
            else:
                # Create new neuron
                with open(package_dir / "neuron.json") as f:
                    config = json.load(f)

                neuron = Neuron(
                    id=neuron_id,
                    user_id=current_user.id,
                    name=manifest["neuron"]["name"],
                    description=manifest["neuron"]["description"],
                    privacy_tier=manifest["neuron"]["privacy_tier"],
                    config=config
                )
                db.add(neuron)

                # Import memory
                if (package_dir / "memory" / "memory.db").exists():
                    import_memory_from_sqlite(
                        neuron_id,
                        package_dir / "memory" / "memory.db",
                        db
                    )

                # Import tools
                if (package_dir / "tools" / "definitions.yaml").exists():
                    with open(package_dir / "tools" / "definitions.yaml") as f:
                        tools_config = yaml.safe_load(f)

                    for tool_name, tool_data in tools_config["tools"].items():
                        tool = NeuronTool(
                            neuron_id=neuron_id,
                            name=tool_name,
                            type=tool_data["type"],
                            version=tool_data["version"],
                            description=tool_data["description"],
                            parameters=tool_data["parameters"]
                        )
                        db.add(tool)

            db.commit()

            return {
                "neuron_id": neuron_id,
                "status": "updated" if existing else "created",
                "message": f"Neuron successfully imported"
            }

    finally:
        # Clean up temp file
        os.unlink(package_path)

def export_memory_to_sqlite(neuron_id: str, output_path: Path, db: Session):
    """Export PostgreSQL memory to SQLite"""
    import sqlite3

    conn = sqlite3.connect(str(output_path))

    # Copy memory layers from PostgreSQL to SQLite
    for layer in ["l1_working", "l2_short_term", "l3_long_term", "l4_persistent"]:
        # Fetch from PostgreSQL
        memories = db.query(Memory).filter(
            Memory.neuron_id == neuron_id,
            Memory.layer == layer
        ).all()

        # Create table in SQLite
        conn.execute(f"""
            CREATE TABLE {layer}_memory (
                id INTEGER PRIMARY KEY,
                content TEXT,
                embedding BLOB,
                metadata TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Insert data
        for memory in memories:
            conn.execute(
                f"INSERT INTO {layer}_memory (content, metadata) VALUES (?, ?)",
                (memory.content, json.dumps(memory.metadata))
            )

    conn.commit()
    conn.close()
```

## 7. Database Schema Updates

```sql
-- New tables for downloadable neurons support

CREATE TABLE neuron_exports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    neuron_id UUID REFERENCES neurons(id),
    user_id UUID REFERENCES users(id),
    export_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    package_checksum VARCHAR(64),
    package_size BIGINT,
    includes_memory BOOLEAN DEFAULT true,
    includes_credentials BOOLEAN DEFAULT false,
    metadata JSONB
);

CREATE TABLE neuron_sync_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    neuron_id UUID REFERENCES neurons(id),
    sync_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sync_direction VARCHAR(20), -- 'cloud_to_local', 'local_to_cloud'
    sync_status VARCHAR(20), -- 'success', 'conflict', 'failed'
    changes JSONB,
    conflict_resolution VARCHAR(20) -- 'local_priority', 'cloud_priority', 'manual'
);

CREATE TABLE neuron_tools (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    neuron_id UUID REFERENCES neurons(id),
    name VARCHAR(100),
    type VARCHAR(50), -- 'ssh', 'http_api', 'custom'
    version VARCHAR(20),
    description TEXT,
    parameters JSONB,
    approval_required BOOLEAN DEFAULT false,
    implementation_path TEXT, -- for custom tools
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_neuron_exports_user ON neuron_exports(user_id);
CREATE INDEX idx_neuron_sync_log_neuron ON neuron_sync_log(neuron_id);
CREATE INDEX idx_neuron_tools_neuron ON neuron_tools(neuron_id);
```

## 8. Sync Protocol

```python
# sync/protocol.py
from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime

class SyncDirection(Enum):
    CLOUD_TO_LOCAL = "cloud_to_local"
    LOCAL_TO_CLOUD = "local_to_cloud"
    BIDIRECTIONAL = "bidirectional"

class ConflictResolution(Enum):
    LOCAL_PRIORITY = "local_priority"
    CLOUD_PRIORITY = "cloud_priority"
    MANUAL = "manual"
    MERGE = "merge"

class SyncRequest(BaseModel):
    neuron_id: str
    local_version: str
    local_checksum: str
    last_sync: Optional[datetime]
    changes: Dict[str, Any]
    memory_snapshot: Optional[Dict[str, Any]]

class SyncResponse(BaseModel):
    status: str  # 'success', 'conflict', 'error'
    cloud_version: str
    cloud_checksum: str
    updates: Optional[Dict[str, Any]]
    conflicts: Optional[list]
    resolution_required: bool

class NeuronSyncManager:
    def __init__(self, db_session):
        self.db = db_session

    async def sync_neuron(
        self,
        sync_request: SyncRequest,
        resolution_strategy: ConflictResolution = ConflictResolution.MANUAL
    ) -> SyncResponse:
        """Handle neuron synchronization between local and cloud"""

        # Get cloud neuron state
        cloud_neuron = self.db.query(Neuron).filter(
            Neuron.id == sync_request.neuron_id
        ).first()

        if not cloud_neuron:
            return SyncResponse(
                status="error",
                cloud_version="unknown",
                cloud_checksum="",
                resolution_required=False
            )

        # Calculate cloud checksum
        cloud_checksum = self._calculate_checksum(cloud_neuron)

        # Detect conflicts
        conflicts = []
        if cloud_checksum != sync_request.local_checksum:
            # Check if changes conflict
            conflicts = self._detect_conflicts(
                cloud_neuron,
                sync_request.changes
            )

        if conflicts and resolution_strategy == ConflictResolution.MANUAL:
            return SyncResponse(
                status="conflict",
                cloud_version=cloud_neuron.version,
                cloud_checksum=cloud_checksum,
                conflicts=conflicts,
                resolution_required=True
            )

        # Apply resolution strategy
        if conflicts:
            if resolution_strategy == ConflictResolution.LOCAL_PRIORITY:
                # Apply local changes to cloud
                self._apply_local_changes(cloud_neuron, sync_request.changes)
            elif resolution_strategy == ConflictResolution.CLOUD_PRIORITY:
                # Return cloud state for local to adopt
                return SyncResponse(
                    status="success",
                    cloud_version=cloud_neuron.version,
                    cloud_checksum=cloud_checksum,
                    updates=self._serialize_neuron(cloud_neuron),
                    resolution_required=False
                )
            elif resolution_strategy == ConflictResolution.MERGE:
                # Attempt automatic merge
                merged = self._merge_changes(
                    cloud_neuron,
                    sync_request.changes
                )
                self._apply_local_changes(cloud_neuron, merged)
        else:
            # No conflicts, apply changes
            self._apply_local_changes(cloud_neuron, sync_request.changes)

        # Update memory if provided
        if sync_request.memory_snapshot:
            self._sync_memory(
                sync_request.neuron_id,
                sync_request.memory_snapshot
            )

        # Log sync event
        self._log_sync(
            sync_request.neuron_id,
            SyncDirection.LOCAL_TO_CLOUD,
            "success",
            sync_request.changes
        )

        self.db.commit()

        return SyncResponse(
            status="success",
            cloud_version=cloud_neuron.version,
            cloud_checksum=self._calculate_checksum(cloud_neuron),
            resolution_required=False
        )

    def _detect_conflicts(
        self,
        cloud_neuron: Neuron,
        local_changes: Dict
    ) -> list:
        """Detect conflicts between cloud and local states"""
        conflicts = []

        # Check config conflicts
        if "config" in local_changes:
            for key, value in local_changes["config"].items():
                if key in cloud_neuron.config:
                    if cloud_neuron.config[key] != value:
                        conflicts.append({
                            "field": f"config.{key}",
                            "cloud_value": cloud_neuron.config[key],
                            "local_value": value
                        })

        # Check tool conflicts
        if "tools" in local_changes:
            cloud_tools = {t.name: t for t in cloud_neuron.tools}
            for tool_name, tool_data in local_changes["tools"].items():
                if tool_name in cloud_tools:
                    cloud_tool = cloud_tools[tool_name]
                    if cloud_tool.parameters != tool_data.get("parameters"):
                        conflicts.append({
                            "field": f"tools.{tool_name}",
                            "cloud_value": cloud_tool.parameters,
                            "local_value": tool_data["parameters"]
                        })

        return conflicts

    def _merge_changes(
        self,
        cloud_neuron: Neuron,
        local_changes: Dict
    ) -> Dict:
        """Attempt to automatically merge changes"""
        merged = {}

        # Merge config (prefer newer timestamps)
        if "config" in local_changes:
            merged["config"] = {}
            for key, value in local_changes["config"].items():
                if key not in cloud_neuron.config:
                    # New key from local
                    merged["config"][key] = value
                elif isinstance(value, dict) and isinstance(cloud_neuron.config.get(key), dict):
                    # Deep merge dictionaries
                    merged["config"][key] = {
                        **cloud_neuron.config[key],
                        **value
                    }
                else:
                    # Use local value (could implement timestamp comparison)
                    merged["config"][key] = value

        return merged
```

## 9. CLI Tool for Package Management

```python
#!/usr/bin/env python3
# brane-cli.py

import click
import requests
import json
import yaml
from pathlib import Path
import subprocess
import os

@click.group()
def cli():
    """BRANE Neuron CLI - Manage downloadable neurons"""
    pass

@cli.command()
@click.argument('neuron_id')
@click.option('--output', '-o', default='.', help='Output directory')
@click.option('--include-memory/--no-memory', default=True)
@click.option('--include-credentials/--no-credentials', default=False)
@click.option('--api-key', envvar='BRANE_API_KEY', required=True)
def download(neuron_id, output, include_memory, include_credentials, api_key):
    """Download a neuron package from BRANE cloud"""

    response = requests.post(
        f"https://api.brane.ai/v1/neurons/{neuron_id}/export",
        json={
            "include_memory": include_memory,
            "include_credentials": include_credentials
        },
        headers={"Authorization": f"Bearer {api_key}"}
    )

    if response.status_code == 200:
        data = response.json()

        # Save package
        output_path = Path(output) / data["filename"]
        with open(output_path, "wb") as f:
            f.write(base64.b64decode(data["data"]))

        click.echo(f"Downloaded: {output_path}")

        if data.get("encryption_key"):
            click.echo(f"Encryption key: {data['encryption_key']}")
            click.echo("Save this key securely - required for credentials")
    else:
        click.echo(f"Error: {response.text}", err=True)

@cli.command()
@click.argument('package_path')
@click.option('--mode', type=click.Choice(['docker', 'python', 'standalone']), default='python')
@click.option('--ollama-host', default='localhost:11434')
@click.option('--api-mode/--interactive', default=False)
def run(package_path, mode, ollama_host, api_mode):
    """Run a neuron package locally"""

    package_path = Path(package_path)

    if not package_path.exists():
        click.echo(f"Package not found: {package_path}", err=True)
        return

    # Extract if needed
    if package_path.suffix == '.brane':
        import zipfile
        import tempfile

        tmpdir = tempfile.mkdtemp()
        with zipfile.ZipFile(package_path, 'r') as zf:
            zf.extractall(tmpdir)

        # Find extracted directory
        for item in Path(tmpdir).iterdir():
            if item.is_dir() and item.name.startswith("neuron-"):
                package_path = item
                break

    # Set environment variables
    os.environ["BRANE_MODE"] = "local"
    os.environ["OLLAMA_HOST"] = ollama_host
    if api_mode:
        os.environ["BRANE_API_MODE"] = "true"

    if mode == "docker":
        # Build and run Docker container
        subprocess.run([
            "docker", "build",
            "-t", f"brane-neuron:{package_path.name}",
            "-f", str(package_path / "docker" / "Dockerfile"),
            str(package_path)
        ])

        subprocess.run([
            "docker", "run",
            "-it" if not api_mode else "-d",
            "-p", "8100:8100",
            "--name", f"brane-{package_path.name}",
            f"brane-neuron:{package_path.name}"
        ])

    elif mode == "python":
        # Run with Python
        runtime_script = package_path / "runtime" / "runtime.py"
        subprocess.run(["python", str(runtime_script), str(package_path)])

    elif mode == "standalone":
        # Run pre-built executable
        executable = package_path / "brane-neuron"
        if not executable.exists():
            click.echo("Standalone executable not found. Build it first with 'brane build'", err=True)
            return
        subprocess.run([str(executable)])

@cli.command()
@click.argument('package_path')
@click.option('--encryption-key', prompt=True, hide_input=True)
@click.option('--api-key', envvar='BRANE_API_KEY', required=True)
def upload(package_path, encryption_key, api_key):
    """Upload/sync a neuron package to BRANE cloud"""

    with open(package_path, "rb") as f:
        files = {'file': (Path(package_path).name, f)}
        data = {'encryption_key': encryption_key}

        response = requests.post(
            "https://api.brane.ai/v1/neurons/import",
            files=files,
            data=data,
            headers={"Authorization": f"Bearer {api_key}"}
        )

    if response.status_code == 200:
        result = response.json()
        click.echo(f"Upload successful: {result['message']}")
    else:
        click.echo(f"Error: {response.text}", err=True)

@cli.command()
@click.argument('package_path')
def build(package_path):
    """Build standalone executable from neuron package"""

    package_path = Path(package_path)

    # Install PyInstaller if needed
    subprocess.run(["pip", "install", "pyinstaller"])

    # Build executable
    subprocess.run([
        "pyinstaller",
        "--onefile",
        "--name", "brane-neuron",
        "--add-data", f"{package_path}:neuron",
        str(package_path / "runtime" / "runtime.py")
    ])

    click.echo(f"Built executable: dist/brane-neuron")

if __name__ == "__main__":
    cli()
```

## 10. Migration Path

### Phase 1: Backend Preparation (Week 1)
1. Add database schema for tools, exports, and sync
2. Implement package builder API endpoints
3. Add sync protocol handlers
4. Create runtime template files

### Phase 2: Package Runtime (Week 2)
1. Implement local runtime with Ollama support
2. Add tool execution framework
3. Create memory SQLite adapter
4. Implement credential encryption

### Phase 3: Sync & Conflict Resolution (Week 3)
1. Build sync protocol
2. Add conflict detection
3. Implement merge strategies
4. Create version tracking

### Phase 4: CLI & Distribution (Week 4)
1. Build CLI tool
2. Create Docker templates
3. Add PyInstaller build support
4. Write documentation

### Phase 5: Testing & Refinement (Week 5)
1. End-to-end testing
2. Security audit
3. Performance optimization
4. User documentation

## Security Considerations

1. **Credential Encryption**: Always encrypt credentials using Fernet or similar
2. **Tool Approval**: Implement approval workflow for dangerous operations
3. **Network Isolation**: Option to run in network-isolated mode
4. **Code Signing**: Sign packages to verify authenticity
5. **Audit Logging**: Log all tool executions and data access

## Performance Optimizations

1. **Lazy Loading**: Load memory and embeddings on-demand
2. **Caching**: Cache LLM responses for identical prompts
3. **Streaming**: Support streaming responses for long outputs
4. **Compression**: Compress package contents to reduce size
5. **Incremental Sync**: Only sync changed data

This architecture provides a robust foundation for downloadable neurons that can run locally while maintaining full functionality and seamless sync with the cloud platform.