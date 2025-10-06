"""
BRANE Neuron Package Builder
Handles creation and packaging of downloadable neurons
"""

import os
import json
import yaml
import shutil
import zipfile
import hashlib
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from cryptography.fernet import Fernet
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

# Domain Models
class NeuronExportConfig(BaseModel):
    """Configuration for neuron export"""
    neuron_id: str
    include_memory: bool = True
    include_credentials: bool = False
    include_tools: bool = True
    encryption_key: Optional[str] = None
    compression_level: int = 6
    format: str = "brane"  # Future: support different formats

class ToolDefinition(BaseModel):
    """Tool definition for export"""
    name: str
    type: str
    version: str
    description: str
    parameters: Dict[str, Any]
    approval_required: bool = False
    rate_limits: Optional[Dict[str, Any]] = None
    implementation_path: Optional[str] = None

class MemoryLayer(BaseModel):
    """Memory layer configuration"""
    name: str
    table_name: str
    ttl: Optional[int] = None
    max_entries: Optional[int] = None
    index_type: Optional[str] = None  # 'vector', 'keyword', 'hybrid'

# Package Builder Class
class NeuronPackageBuilder:
    """Builds downloadable neuron packages"""

    def __init__(self, db_session: Session, storage_path: Path):
        self.db = db_session
        self.storage_path = storage_path
        self.templates_path = Path(__file__).parent / "templates"

    def build_package(self, config: NeuronExportConfig) -> Dict[str, Any]:
        """Build a complete neuron package"""

        # Fetch neuron from database
        neuron = self._fetch_neuron(config.neuron_id)
        if not neuron:
            raise ValueError(f"Neuron {config.neuron_id} not found")

        # Create temporary build directory
        with tempfile.TemporaryDirectory() as build_dir:
            package_dir = Path(build_dir) / f"neuron-{config.neuron_id}"
            package_dir.mkdir()

            # Build package components
            manifest = self._create_manifest(neuron, config)
            self._write_manifest(package_dir, manifest)
            self._export_neuron_config(package_dir, neuron)

            if config.include_tools:
                self._export_tools(package_dir, neuron)

            if config.include_memory:
                self._export_memory(package_dir, neuron)

            if config.include_credentials:
                encryption_key = self._export_credentials(
                    package_dir,
                    neuron,
                    config.encryption_key
                )
            else:
                encryption_key = None

            # Add runtime components
            self._add_runtime_files(package_dir, neuron)

            # Add Docker support
            self._add_docker_files(package_dir, neuron)

            # Create metadata
            self._create_metadata(package_dir)

            # Package into archive
            archive_path = self._create_archive(
                package_dir,
                config.compression_level
            )

            # Calculate final checksum
            checksum = self._calculate_checksum(archive_path)

            # Move to storage
            final_path = self._store_package(archive_path, config.neuron_id)

            return {
                "path": str(final_path),
                "checksum": checksum,
                "encryption_key": encryption_key,
                "manifest": manifest,
                "size": final_path.stat().st_size
            }

    def _create_manifest(
        self,
        neuron: Any,
        config: NeuronExportConfig
    ) -> Dict[str, Any]:
        """Create package manifest"""

        return {
            "version": "1.0.0",
            "format": config.format,
            "created_at": datetime.now().isoformat(),

            "neuron": {
                "id": neuron.id,
                "name": neuron.name,
                "description": neuron.description,
                "privacy_tier": neuron.privacy_tier,
                "created_at": neuron.created_at.isoformat(),
                "updated_at": neuron.updated_at.isoformat(),
                "tags": neuron.tags or [],
                "capabilities": neuron.capabilities or []
            },

            "runtime": {
                "min_python_version": "3.9",
                "preferred_llm": neuron.config.get("llm_model", "llama3.1:8b"),
                "fallback_llms": [
                    "mistral:7b",
                    "phi3:mini",
                    "gemma:2b"
                ],
                "supports_streaming": True,
                "supports_function_calling": self._check_function_support(neuron),
                "max_context_length": neuron.config.get("max_context", 8192)
            },

            "dependencies": {
                "python": [
                    "litellm>=1.0.0",
                    "langchain>=0.1.0",
                    "sqlalchemy>=2.0.0",
                    "cryptography>=41.0.0"
                ],
                "system": ["sqlite3", "openssh-client"],
                "optional": ["faiss-cpu", "chromadb", "pgvector"]
            },

            "sync": {
                "cloud_id": neuron.id,
                "last_sync": datetime.now().isoformat(),
                "sync_enabled": True,
                "conflict_resolution": "manual",
                "sync_interval": 300,  # seconds
                "excluded_paths": [".git", "__pycache__", "*.pyc"]
            },

            "security": {
                "credentials_encrypted": config.include_credentials,
                "encryption_algorithm": "Fernet" if config.include_credentials else None,
                "requires_approval": self._requires_approval(neuron),
                "allowed_networks": neuron.config.get("allowed_networks", ["*"]),
                "blocked_domains": neuron.config.get("blocked_domains", [])
            },

            "contents": {
                "has_memory": config.include_memory,
                "has_credentials": config.include_credentials,
                "has_tools": config.include_tools,
                "has_embeddings": self._has_embeddings(neuron),
                "memory_format": "sqlite" if config.include_memory else None
            }
        }

    def _export_neuron_config(self, package_dir: Path, neuron: Any):
        """Export neuron configuration"""

        config = {
            "id": neuron.id,
            "name": neuron.name,
            "description": neuron.description,
            "system_prompt": neuron.config.get("system_prompt", ""),
            "temperature": neuron.config.get("temperature", 0.7),
            "max_tokens": neuron.config.get("max_tokens", 2000),
            "top_p": neuron.config.get("top_p", 0.9),
            "frequency_penalty": neuron.config.get("frequency_penalty", 0),
            "presence_penalty": neuron.config.get("presence_penalty", 0),

            "memory_config": {
                "l1_ttl": 300,  # 5 minutes
                "l2_ttl": 3600,  # 1 hour
                "l3_max_entries": 1000,
                "l4_max_entries": 10000,
                "embedding_model": neuron.config.get(
                    "embedding_model",
                    "sentence-transformers/all-MiniLM-L6-v2"
                ),
                "vector_dimensions": 384
            },

            "tool_config": {
                "timeout": 30,
                "retry_attempts": 3,
                "parallel_execution": True,
                "max_parallel": 5
            },

            "behavior": {
                "auto_memory_management": True,
                "memory_compression": True,
                "context_window_management": "sliding",
                "response_format": neuron.config.get("response_format", "text"),
                "markdown_support": True
            }
        }

        with open(package_dir / "neuron.json", "w") as f:
            json.dump(config, f, indent=2)

    def _export_tools(self, package_dir: Path, neuron: Any):
        """Export tool definitions and implementations"""

        tools_dir = package_dir / "tools"
        tools_dir.mkdir()

        # Export tool definitions
        tools_config = {"tools": {}}

        for tool in neuron.tools:
            tool_def = ToolDefinition(
                name=tool.name,
                type=tool.type,
                version=tool.version or "1.0",
                description=tool.description,
                parameters=tool.parameters,
                approval_required=tool.approval_required
            )

            tools_config["tools"][tool.name] = tool_def.dict()

            # Copy custom implementations
            if tool.type == "custom" and tool.implementation_path:
                custom_dir = tools_dir / "custom"
                custom_dir.mkdir(exist_ok=True)

                impl_path = Path(tool.implementation_path)
                if impl_path.exists():
                    shutil.copy(impl_path, custom_dir / impl_path.name)

        # Add built-in tool schemas
        tools_config["builtin"] = self._get_builtin_tools()

        with open(tools_dir / "definitions.yaml", "w") as f:
            yaml.dump(tools_config, f, default_flow_style=False)

        # Add tool executor
        self._create_tool_executor(tools_dir)

    def _get_builtin_tools(self) -> Dict[str, Any]:
        """Get built-in tool definitions"""

        return {
            "ssh": {
                "description": "Execute commands via SSH",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "host": {"type": "string"},
                        "command": {"type": "string"},
                        "timeout": {"type": "integer", "default": 30}
                    },
                    "required": ["host", "command"]
                }
            },
            "http": {
                "description": "Make HTTP requests",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "format": "uri"},
                        "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE"]},
                        "headers": {"type": "object"},
                        "data": {"type": "object"}
                    },
                    "required": ["url"]
                }
            },
            "file": {
                "description": "File system operations",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "operation": {"type": "string", "enum": ["read", "write", "list", "exists"]},
                        "path": {"type": "string"},
                        "content": {"type": "string"}
                    },
                    "required": ["operation", "path"]
                }
            },
            "shell": {
                "description": "Execute shell commands",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string"},
                        "cwd": {"type": "string"},
                        "env": {"type": "object"}
                    },
                    "required": ["command"]
                }
            }
        }

    def _create_tool_executor(self, tools_dir: Path):
        """Create tool executor module"""

        executor_code = '''"""
Tool Executor for BRANE Neurons
Handles execution of various tool types
"""

import os
import json
import asyncio
import aiohttp
import asyncssh
from typing import Dict, Any, Optional
from pathlib import Path

class ToolExecutor:
    """Execute tools with proper isolation and security"""

    def __init__(self, credentials: Dict[str, Any], approval_callback=None):
        self.credentials = credentials
        self.approval_callback = approval_callback

    async def execute(self, tool_name: str, tool_type: str, args: Dict[str, Any]) -> Any:
        """Execute a tool with given arguments"""

        # Check approval if required
        if self.approval_callback:
            approved = await self.approval_callback(tool_name, args)
            if not approved:
                return {"error": "Tool execution not approved"}

        # Route to appropriate executor
        if tool_type == "ssh":
            return await self.execute_ssh(args)
        elif tool_type == "http":
            return await self.execute_http(args)
        elif tool_type == "file":
            return await self.execute_file(args)
        elif tool_type == "shell":
            return await self.execute_shell(args)
        elif tool_type == "custom":
            return await self.execute_custom(tool_name, args)
        else:
            return {"error": f"Unknown tool type: {tool_type}"}

    async def execute_ssh(self, args: Dict[str, Any]) -> str:
        """Execute SSH command"""
        host = args["host"]
        command = args["command"]
        timeout = args.get("timeout", 30)

        # Get credentials
        ssh_creds = self.credentials.get("ssh", {}).get(host, {})

        try:
            async with asyncssh.connect(
                host,
                username=ssh_creds.get("username"),
                password=ssh_creds.get("password"),
                known_hosts=None
            ) as conn:
                result = await asyncio.wait_for(
                    conn.run(command),
                    timeout=timeout
                )
                return result.stdout
        except Exception as e:
            return {"error": str(e)}

    async def execute_http(self, args: Dict[str, Any]) -> str:
        """Execute HTTP request"""
        url = args["url"]
        method = args.get("method", "GET")
        headers = args.get("headers", {})
        data = args.get("data")

        # Add authentication if available
        api_creds = self.credentials.get("api", {})
        for pattern, creds in api_creds.items():
            if pattern in url:
                if creds["type"] == "bearer":
                    headers["Authorization"] = f"Bearer {creds['token']}"
                elif creds["type"] == "api_key":
                    headers[creds["header"]] = creds["key"]

        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method, url, headers=headers, json=data
                ) as response:
                    return await response.text()
        except Exception as e:
            return {"error": str(e)}

    async def execute_file(self, args: Dict[str, Any]) -> Any:
        """Execute file operation"""
        operation = args["operation"]
        path = Path(args["path"])

        try:
            if operation == "read":
                return path.read_text()
            elif operation == "write":
                path.write_text(args["content"])
                return {"status": "success"}
            elif operation == "list":
                return [str(p) for p in path.iterdir()]
            elif operation == "exists":
                return path.exists()
        except Exception as e:
            return {"error": str(e)}

    async def execute_shell(self, args: Dict[str, Any]) -> str:
        """Execute shell command"""
        import subprocess

        command = args["command"]
        cwd = args.get("cwd")
        env = args.get("env", {})

        # Merge with current environment
        full_env = {**os.environ, **env}

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=cwd,
                env=full_env,
                timeout=30
            )
            return result.stdout if result.returncode == 0 else result.stderr
        except Exception as e:
            return {"error": str(e)}

    async def execute_custom(self, tool_name: str, args: Dict[str, Any]) -> Any:
        """Execute custom tool"""
        custom_path = Path(__file__).parent / "custom" / f"{tool_name}.py"

        if not custom_path.exists():
            return {"error": f"Custom tool {tool_name} not found"}

        # Dynamic import and execution
        import importlib.util
        spec = importlib.util.spec_from_file_location(tool_name, custom_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        if hasattr(module, "execute"):
            return await module.execute(args, self.credentials)
        else:
            return {"error": f"Custom tool {tool_name} missing execute function"}
'''

        with open(tools_dir / "executor.py", "w") as f:
            f.write(executor_code)

    def _export_memory(self, package_dir: Path, neuron: Any):
        """Export memory to SQLite"""

        import sqlite3

        memory_dir = package_dir / "memory"
        memory_dir.mkdir()

        # Create SQLite database
        db_path = memory_dir / "memory.db"
        conn = sqlite3.connect(str(db_path))

        # Create schema
        self._create_memory_schema(conn)

        # Export memory layers
        self._export_memory_layers(conn, neuron)

        # Export embeddings if available
        if self._has_embeddings(neuron):
            self._export_embeddings(memory_dir, neuron)

        conn.commit()
        conn.close()

    def _create_memory_schema(self, conn):
        """Create SQLite schema for memory"""

        schemas = [
            """
            CREATE TABLE l1_working_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                role TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                ttl INTEGER DEFAULT 300,
                metadata TEXT
            )
            """,
            """
            CREATE TABLE l2_short_term (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                embedding BLOB,
                category TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                ttl INTEGER DEFAULT 3600,
                access_count INTEGER DEFAULT 0,
                metadata TEXT
            )
            """,
            """
            CREATE TABLE l3_long_term (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                embedding BLOB,
                category TEXT,
                tags TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                importance REAL DEFAULT 0.5,
                metadata TEXT
            )
            """,
            """
            CREATE TABLE l4_persistent (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT NOT NULL,
                category TEXT,
                source TEXT,
                confidence REAL DEFAULT 1.0,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
            """,
            """
            CREATE INDEX idx_l1_timestamp ON l1_working_memory(timestamp);
            CREATE INDEX idx_l2_category ON l2_short_term(category);
            CREATE INDEX idx_l3_category ON l3_long_term(category);
            CREATE INDEX idx_l3_tags ON l3_long_term(tags);
            CREATE INDEX idx_l4_key ON l4_persistent(key);
            CREATE INDEX idx_l4_category ON l4_persistent(category);
            """
        ]

        for schema in schemas:
            conn.executescript(schema)

    def _export_memory_layers(self, conn, neuron: Any):
        """Export memory from PostgreSQL to SQLite"""

        # Map PostgreSQL data to SQLite
        memory_data = self._fetch_memory_data(neuron.id)

        for layer_name, records in memory_data.items():
            table_name = f"{layer_name}_memory"

            for record in records:
                # Prepare values based on layer
                if layer_name == "l1_working":
                    conn.execute(
                        f"INSERT INTO {table_name} (content, role, ttl, metadata) VALUES (?, ?, ?, ?)",
                        (record["content"], record.get("role"), record.get("ttl", 300),
                         json.dumps(record.get("metadata", {})))
                    )
                elif layer_name == "l4_persistent":
                    conn.execute(
                        f"INSERT INTO {table_name} (key, value, category, source, confidence, metadata) VALUES (?, ?, ?, ?, ?, ?)",
                        (record["key"], record["value"], record.get("category"),
                         record.get("source"), record.get("confidence", 1.0),
                         json.dumps(record.get("metadata", {})))
                    )
                else:
                    # L2 and L3
                    conn.execute(
                        f"INSERT INTO {table_name} (content, category, metadata) VALUES (?, ?, ?)",
                        (record["content"], record.get("category"),
                         json.dumps(record.get("metadata", {})))
                    )

    def _export_credentials(
        self,
        package_dir: Path,
        neuron: Any,
        encryption_key: Optional[str]
    ) -> str:
        """Export encrypted credentials"""

        creds_dir = package_dir / "credentials"
        creds_dir.mkdir()

        # Gather credentials
        credentials = self._gather_credentials(neuron)

        # Generate or use provided key
        if encryption_key:
            fernet = Fernet(encryption_key.encode())
        else:
            key = Fernet.generate_key()
            fernet = Fernet(key)
            encryption_key = key.decode()

        # Encrypt credentials
        encrypted = fernet.encrypt(json.dumps(credentials).encode())

        # Save encrypted vault
        with open(creds_dir / "vault.enc", "wb") as f:
            f.write(encrypted)

        # Save key hint (for development only)
        if os.environ.get("BRANE_DEV_MODE"):
            with open(creds_dir / ".key_hint", "w") as f:
                f.write(f"Development key hint: {encryption_key[:8]}...")

        return encryption_key

    def _gather_credentials(self, neuron: Any) -> Dict[str, Any]:
        """Gather all credentials for the neuron"""

        credentials = {
            "ssh": {},
            "api": {},
            "database": {},
            "cloud": {}
        }

        # Fetch from secure credential store
        for cred in neuron.credentials:
            if cred.type == "ssh":
                credentials["ssh"][cred.host] = {
                    "username": cred.username,
                    "password": cred.password,
                    "key_path": cred.key_path
                }
            elif cred.type == "api":
                credentials["api"][cred.pattern] = {
                    "type": cred.auth_type,
                    "token": cred.token,
                    "key": cred.api_key,
                    "header": cred.header_name
                }

        return credentials

    def _add_runtime_files(self, package_dir: Path, neuron: Any):
        """Add runtime files to package"""

        runtime_dir = package_dir / "runtime"
        runtime_dir.mkdir()

        # Copy runtime.py from templates
        runtime_template = self.templates_path / "runtime.py"
        if runtime_template.exists():
            shutil.copy(runtime_template, runtime_dir / "runtime.py")
        else:
            # Create minimal runtime
            self._create_minimal_runtime(runtime_dir)

        # Create requirements.txt
        self._create_requirements(runtime_dir)

        # Create configuration
        self._create_runtime_config(runtime_dir, neuron)

    def _create_minimal_runtime(self, runtime_dir: Path):
        """Create minimal runtime if template not found"""

        runtime_code = '''#!/usr/bin/env python3
"""
BRANE Neuron Runtime
Minimal runtime for executing neurons locally
"""

import sys
from pathlib import Path

# Add package directory to path
package_dir = Path(__file__).parent.parent
sys.path.insert(0, str(package_dir))

from runtime.executor import NeuronExecutor

def main():
    executor = NeuronExecutor(package_dir)
    executor.run()

if __name__ == "__main__":
    main()
'''

        with open(runtime_dir / "runtime.py", "w") as f:
            f.write(runtime_code)

        # Make executable
        (runtime_dir / "runtime.py").chmod(0o755)

    def _create_requirements(self, runtime_dir: Path):
        """Create requirements.txt"""

        requirements = """# Core dependencies
litellm>=1.0.0
langchain>=0.1.0
langchain-community>=0.0.10
sqlalchemy>=2.0.0
cryptography>=41.0.0
pydantic>=2.0.0

# Async support
aiohttp>=3.9.0
asyncssh>=2.14.0

# API framework (for API mode)
fastapi>=0.104.0
uvicorn>=0.24.0

# Optional: Vector stores
faiss-cpu>=1.7.4
chromadb>=0.4.0

# Optional: Embeddings
sentence-transformers>=2.2.0
"""

        with open(runtime_dir / "requirements.txt", "w") as f:
            f.write(requirements)

    def _create_runtime_config(self, runtime_dir: Path, neuron: Any):
        """Create runtime configuration"""

        config = {
            "mode": "interactive",  # 'interactive', 'api', 'batch'
            "api": {
                "host": "0.0.0.0",
                "port": 8100,
                "reload": False,
                "workers": 1
            },
            "llm": {
                "provider": "ollama",  # 'ollama', 'vllm', 'openai'
                "ollama_host": "http://localhost:11434",
                "vllm_host": "http://localhost:8000",
                "timeout": 120,
                "retry_attempts": 3
            },
            "memory": {
                "enable_persistence": True,
                "compression": True,
                "max_memory_mb": 500,
                "gc_interval": 300
            },
            "logging": {
                "level": "INFO",
                "format": "json",
                "file": "neuron.log",
                "rotate_size": "10MB",
                "backup_count": 5
            }
        }

        with open(runtime_dir / "config.yaml", "w") as f:
            yaml.dump(config, f, default_flow_style=False)

    def _add_docker_files(self, package_dir: Path, neuron: Any):
        """Add Docker support files"""

        docker_dir = package_dir / "docker"
        docker_dir.mkdir()

        # Create Dockerfile
        dockerfile = '''FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    sqlite3 \\
    openssh-client \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Install Ollama (optional, for local LLM)
RUN curl -fsSL https://ollama.ai/install.sh | sh || true

# Set working directory
WORKDIR /app

# Copy neuron package
COPY . /app/neuron

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/neuron/runtime/requirements.txt

# Set environment variables
ENV BRANE_MODE=local
ENV BRANE_NEURON_PATH=/app/neuron
ENV PYTHONUNBUFFERED=1

# Create non-root user
RUN useradd -m -s /bin/bash neuron && \\
    chown -R neuron:neuron /app
USER neuron

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD python -c "import requests; requests.get('http://localhost:8100/health')"

# Expose API port
EXPOSE 8100

# Entry point
ENTRYPOINT ["python", "/app/neuron/runtime/runtime.py"]
'''

        with open(docker_dir / "Dockerfile", "w") as f:
            f.write(dockerfile)

        # Create docker-compose.yml
        compose = '''version: '3.8'

services:
  neuron:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    ports:
      - "8100:8100"
    environment:
      - BRANE_MODE=local
      - OLLAMA_HOST=ollama:11434
    volumes:
      - neuron-data:/app/data
    networks:
      - neuron-net
    restart: unless-stopped

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama-data:/root/.ollama
    networks:
      - neuron-net
    restart: unless-stopped

volumes:
  neuron-data:
  ollama-data:

networks:
  neuron-net:
    driver: bridge
'''

        with open(docker_dir / "docker-compose.yml", "w") as f:
            f.write(compose)

    def _create_metadata(self, package_dir: Path):
        """Create package metadata"""

        meta_dir = package_dir / ".brane"
        meta_dir.mkdir()

        # Version file
        with open(meta_dir / "version", "w") as f:
            f.write("1.0.0")

        # Package info
        info = {
            "format_version": "1.0",
            "created_by": "BRANE Package Builder",
            "created_at": datetime.now().isoformat()
        }

        with open(meta_dir / "info.json", "w") as f:
            json.dump(info, f, indent=2)

    def _create_archive(
        self,
        package_dir: Path,
        compression_level: int
    ) -> Path:
        """Create compressed archive"""

        archive_path = package_dir.parent / f"{package_dir.name}.brane"

        with zipfile.ZipFile(
            archive_path,
            "w",
            zipfile.ZIP_DEFLATED,
            compresslevel=compression_level
        ) as zf:
            for root, dirs, files in os.walk(package_dir):
                # Skip hidden directories
                dirs[:] = [d for d in dirs if not d.startswith('.')]

                for file in files:
                    if not file.startswith('.'):
                        file_path = Path(root) / file
                        arcname = file_path.relative_to(package_dir.parent)
                        zf.write(file_path, arcname)

        return archive_path

    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file"""

        sha256 = hashlib.sha256()

        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)

        return sha256.hexdigest()

    def _store_package(self, archive_path: Path, neuron_id: str) -> Path:
        """Store package in designated location"""

        # Create storage directory structure
        storage_dir = self.storage_path / "exports" / neuron_id[:2] / neuron_id
        storage_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"neuron-{neuron_id}-{timestamp}.brane"

        final_path = storage_dir / filename
        shutil.move(archive_path, final_path)

        return final_path

    # Helper methods
    def _fetch_neuron(self, neuron_id: str) -> Any:
        """Fetch neuron from database"""
        # This would query your actual database
        # Return None if not found
        pass

    def _write_manifest(self, package_dir: Path, manifest: Dict):
        """Write manifest to package"""
        with open(package_dir / "manifest.yaml", "w") as f:
            yaml.dump(manifest, f, default_flow_style=False)

    def _check_function_support(self, neuron: Any) -> bool:
        """Check if neuron's LLM supports function calling"""
        model = neuron.config.get("llm_model", "").lower()
        return any(m in model for m in ["gpt", "claude", "llama3.1", "mistral-large"])

    def _requires_approval(self, neuron: Any) -> bool:
        """Check if neuron requires approval for tool execution"""
        return any(tool.approval_required for tool in neuron.tools)

    def _has_embeddings(self, neuron: Any) -> bool:
        """Check if neuron has embeddings"""
        # Check if neuron has vector embeddings stored
        return False  # Placeholder

    def _fetch_memory_data(self, neuron_id: str) -> Dict[str, List]:
        """Fetch memory data from database"""
        # This would query your PostgreSQL database
        return {
            "l1_working": [],
            "l2_short_term": [],
            "l3_long_term": [],
            "l4_persistent": []
        }

    def _export_embeddings(self, memory_dir: Path, neuron: Any):
        """Export vector embeddings"""
        # This would export FAISS index or other vector stores
        pass