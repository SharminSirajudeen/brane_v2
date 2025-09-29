# 🧠 Brane - Modular AI Agent Platform

**Brane** is a local-first, modular AI agent creation platform where users can download and run **Neurons** (AI agents) without any server costs.

## 🚀 Features

- **Local-First**: Run AI agents completely offline with embedded LLMs
- **Modular Architecture**: Plugin system (Synapses) for extensibility
- **RAG Memory**: Built-in vector storage (Axon) for knowledge persistence
- **Hybrid LLMs**: Support for local (llama.cpp) and remote (Ollama) models
- **Multi-Agent**: Run multiple Neurons simultaneously (coming soon)
- **Zero Hosting**: No cloud costs, everything runs on user's machine

## 🏗️ Architecture

- **Neuron**: Individual AI agent (downloadable package)
- **Synapse**: Plugin/tool modules for extended capabilities
- **Axon**: Vector store for RAG memory
- **Spark**: Execution instance of a Neuron
- **MCP**: Inter-Neuron communication protocol

## 🛠️ Development

### Using GitHub Codespaces (Recommended)

1. Open this repository in GitHub Codespaces
2. The development environment will be automatically configured
3. Access the desktop environment at `http://localhost:6080` (password: `brane`)

### Local Development

```bash
# Clone the repository
git clone https://github.com/SharminSirajudeen/brane_v2.git
cd brane_v2

# Install dependencies
pnpm install

# Run CLI version
pnpm dev:cli

# Run Electron app
pnpm dev

# Build for production
pnpm build
```

## 📁 Project Structure

```
brane_v2/
├── src/
│   ├── core/        # Neuron runtime core
│   ├── llm/         # LLM integration layer
│   ├── config/      # Configuration management
│   ├── rag/         # Axon (RAG/Vector store)
│   ├── synapses/    # Plugin system
│   ├── mcp/         # MCP connectivity
│   ├── electron/    # Electron main process
│   ├── ui/          # React frontend
│   └── cli/         # CLI interface
├── models/          # LLM model files
├── dist/           # Build output
└── .devcontainer/  # Codespaces configuration
```

## 🔧 Configuration

Neurons are configured via JSON files with strict schema validation:

```json
{
  "neuron_id": "assistant",
  "runtime": {
    "backend": "llama.cpp",
    "params": {
      "threads": 8,
      "context_length": 4096
    }
  },
  "model": {
    "name": "mistral-7b-q4",
    "source": "embedded"
  },
  "synapses": [
    {"id": "web_search", "enabled": true}
  ],
  "axon": {
    "rag_enabled": true,
    "storage": "local"
  }
}
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🔗 Links

- [Documentation](docs/README.md)
- [API Reference](docs/API.md)
- [Plugin Development](docs/PLUGINS.md)

---

Built with ❤️ for the AI community
