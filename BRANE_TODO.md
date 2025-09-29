# 🧠 BRANE - Project Development Tracker

## 📍 Project Information
- **Project Location**: `/Users/sharminsirajudeen/Projects/brane_v2`
- **GitHub Repository**: `SharminSirajudeen/brane_v2` (to be created)
- **Project Type**: Electron Desktop App + Node.js Backend
- **Package Manager**: pnpm
- **Node Version**: v20 LTS
- **Start Date**: 2025-09-29

## 🎯 Project Vision
Brane is a **modular, hybrid AI agent creation platform** where users can download and run **Neurons** (AI agents) locally without any server costs. Each Neuron includes embedded LLM, RAG memory (Axon), plugin system (Synapses), and optional MCP connectivity.

## 🏗️ Architecture Overview

### Core Components
1. **Brane App** - Electron desktop application (runtime + GUI)
2. **Neuron** - Downloadable AI agent package
3. **Synapse** - Plugin/tool modules
4. **Axon** - Vector store for RAG memory
5. **Spark** - Execution/firing instance
6. **MCP** - Inter-Neuron communication protocol

### Tech Stack
- **Frontend**: Electron + React + Tailwind CSS
- **Chat UI**: OpenChat UI (embedded)
- **LLM Backend**: llama.cpp with Node.js bindings
- **Default Model**: Mistral 7B Q4_0 (quantized)
- **RAG/Vector DB**: FAISS or ChromaDB (disk-backed)
- **Embeddings**: SentenceTransformers (local)
- **Config**: JSON with AJV validation
- **Plugin System**: Dynamic ES Modules
- **State Management**: Zustand
- **Testing**: Jest + Playwright

## 📋 Development Phases

### Phase 1: Single-Neuron MVP (Current)
Build a working single Neuron with config switching and hot-reload

### Phase 2: Multi-Neuron Manager
Add ability to run multiple Neurons simultaneously

### Phase 3: MCP Inter-Neuron Communication
Enable Neurons to communicate with each other

### Phase 4: Marketplace & Ecosystem
User-published Neurons, Synapse library, revenue sharing

## ✅ Implementation Checklist

### 🔄 Setup & Infrastructure
- [ ] Create project directory at `/Users/sharminsirajudeen/Projects/brane_v2`
- [ ] Initialize pnpm project with Node.js v20
- [ ] Set up GitHub repository `SharminSirajudeen/brane_v2`
- [ ] Create initial commit with project structure
- [ ] Set up TypeScript configuration
- [ ] Configure ESLint and Prettier

### 📁 Project Structure
```
/Users/sharminsirajudeen/Projects/brane_v2/
├── package.json
├── pnpm-lock.yaml
├── tsconfig.json
├── BRANE_TODO.md (this file)
├── README.md
├── /core/               # Neuron runtime core
│   ├── neuron.ts       # Main Neuron class
│   ├── planner.ts      # Action planner
│   ├── executor.ts     # Command executor
│   └── sandbox.ts      # Execution sandbox
├── /llm/               # LLM integration layer
│   ├── llama-cpp.ts    # llama.cpp bindings
│   ├── model-loader.ts # Model management
│   └── ollama-client.ts # Optional Ollama integration
├── /config/            # Configuration management
│   ├── schema.json     # Neuron config schema
│   ├── validator.ts    # AJV validator
│   └── hot-reload.ts   # Config watcher
├── /rag/               # Axon (RAG/Vector store)
│   ├── vector-store.ts # FAISS/Chroma interface
│   ├── embeddings.ts   # Local embeddings
│   └── memory.ts       # Memory management
├── /synapses/          # Plugin system
│   ├── loader.ts       # Dynamic plugin loader
│   ├── registry.ts     # Synapse registry
│   └── /plugins/       # Built-in plugins
│       ├── web-search.ts
│       ├── grammar.ts
│       └── code-runner.ts
├── /mcp/               # MCP connectivity
│   ├── client.ts       # MCP client
│   ├── discovery.ts    # Neuron discovery
│   └── messaging.ts    # Inter-Neuron messaging
├── /electron/          # Electron main process
│   ├── main.ts         # Main process entry
│   ├── preload.ts      # Preload script
│   └── ipc.ts          # IPC handlers
├── /ui/                # React frontend
│   ├── index.tsx       # React entry point
│   ├── App.tsx         # Main app component
│   ├── /components/    # React components
│   │   ├── Dashboard.tsx
│   │   ├── ConfigEditor.tsx
│   │   ├── ChatInterface.tsx
│   │   └── SetupWizard.tsx
│   └── /styles/        # Tailwind styles
├── /scripts/           # Build & utility scripts
│   ├── build.ts
│   └── package.ts
└── /dist/              # Build output
```

### 🚀 Core Implementation Tasks

#### 1. Neuron Core [Priority: HIGH]
- [ ] Create Neuron class with state management
- [ ] Implement Planner (generates action steps from prompts)
- [ ] Build Executor (runs approved commands)
- [ ] Add Sandbox for safe execution
- [ ] Create Spark activation system

#### 2. Config System [Priority: HIGH]
- [ ] Define neuron.config.schema.json
- [ ] Implement AJV validator
- [ ] Build config loader with strict validation
- [ ] Add hot-reload file watcher
- [ ] Create safe config editor logic

#### 3. LLM Integration [Priority: HIGH]
- [ ] Install llama.cpp Node.js bindings
- [ ] Download Mistral 7B Q4_0 model
- [ ] Create model loader interface
- [ ] Implement dynamic model swapping
- [ ] Add fallback to embedded model
- [ ] Optional: Ollama endpoint support

#### 4. Axon (RAG/Memory) [Priority: MEDIUM]
- [ ] Set up FAISS or ChromaDB
- [ ] Implement disk-backed vector store
- [ ] Create local embeddings generator
- [ ] Build memory management (lazy loading)
- [ ] Add document indexing
- [ ] Optional: Google Drive sync

#### 5. Synapse Plugin System [Priority: MEDIUM]
- [ ] Design plugin interface
- [ ] Build dynamic module loader
- [ ] Create plugin registry
- [ ] Implement lazy loading
- [ ] Build sample plugins:
  - [ ] Web search adapter
  - [ ] Grammar checker
  - [ ] Code executor
  - [ ] Content summarizer

#### 6. Electron GUI [Priority: MEDIUM]
- [ ] Set up Electron with TypeScript
- [ ] Create main process handlers
- [ ] Build IPC communication
- [ ] Implement window management
- [ ] Add system tray integration

#### 7. React Frontend [Priority: MEDIUM]
- [ ] Set up React with TypeScript
- [ ] Configure Tailwind CSS
- [ ] Create component structure
- [ ] Build Dashboard view
- [ ] Implement Config Editor (GUI-only)
- [ ] Integrate OpenChat UI
- [ ] Add Setup Wizard for first-time users

#### 8. MCP Connectivity [Priority: LOW]
- [ ] Design MCP protocol
- [ ] Build WebSocket client
- [ ] Implement peer discovery
- [ ] Create secure messaging
- [ ] Add inter-Neuron communication

#### 9. Testing & QA [Priority: ONGOING]
- [ ] Set up Jest for unit tests
- [ ] Add Playwright for E2E tests
- [ ] Write tests for core modules
- [ ] Test config validation
- [ ] Verify hot-reload functionality
- [ ] Test sandboxed execution

#### 10. Packaging & Distribution [Priority: FINAL]
- [ ] Configure Electron Packager
- [ ] Create build scripts
- [ ] Generate installers (Windows/Mac/Linux)
- [ ] Create distributable ZIP
- [ ] Write installation documentation
- [ ] Add auto-update mechanism (optional)

## 🔒 Security Checklist
- [ ] Strict JSON schema validation (no code execution)
- [ ] Sandboxed command execution
- [ ] Path access limited to app directories
- [ ] URL validation for MCP/cloud endpoints
- [ ] No remote code execution
- [ ] Config changes only through GUI
- [ ] Fresh config generation on save
- [ ] Download-only config (no upload in MVP)

## 📝 Config Schema Example
```json
{
  "neuron_id": "research_assistant",
  "display_name": "Research Assistant",
  "runtime": {
    "backend": "llama.cpp",
    "params": {
      "gpu_enabled": false,
      "threads": 8,
      "context_length": 4096
    }
  },
  "model": {
    "name": "mistral-7b-q4",
    "source": "embedded",
    "quantization": "Q4"
  },
  "synapses": [
    {"id": "web_search", "enabled": true},
    {"id": "grammar", "enabled": false}
  ],
  "axon": {
    "rag_enabled": true,
    "storage": "local",
    "path": "./axon_storage",
    "max_docs": 500
  },
  "mcp": {
    "enabled": false,
    "servers": []
  }
}
```

## 📊 Progress Tracking

### Current Status: Project Initialization
- ✅ Requirements gathered and documented
- ✅ Architecture designed
- ✅ Tech stack decided
- ✅ Security approach defined
- 🔄 Creating project structure
- ⏳ Setting up development environment

### Next Steps
1. Create project directory structure
2. Initialize pnpm and install core dependencies
3. Set up TypeScript and build configuration
4. Create GitHub repository and initial commit
5. Start implementing Neuron Core

## 🎯 MVP Success Criteria
- [ ] Single Neuron runs locally with embedded LLM
- [ ] Config can be edited via GUI and hot-reloaded
- [ ] Basic chat interface works (OpenChat UI)
- [ ] At least 2 Synapses functional (web search, grammar)
- [ ] Axon stores and retrieves documents locally
- [ ] Can package as Electron app
- [ ] Zero server/hosting requirements
- [ ] Runs on Windows/Mac/Linux

## 📅 Timeline Estimate
- **Day 1-2**: Core setup, Neuron runtime, config system
- **Day 3-4**: LLM integration, basic Synapses
- **Day 5-6**: Electron GUI, React frontend
- **Day 7-8**: Axon RAG implementation
- **Day 9-10**: Testing, packaging, documentation

## 🔗 Important Links
- llama.cpp: https://github.com/ggerganov/llama.cpp
- Node bindings: https://github.com/withcatai/node-llama-cpp
- OpenChat UI: https://github.com/openchatai/OpenChat
- Electron: https://www.electronjs.org/
- FAISS: https://github.com/facebookresearch/faiss
- ChromaDB: https://www.trychroma.com/

## 📌 Notes & Decisions
- Starting with single-Neuron implementation
- Using llama.cpp for lightest footprint
- Config editing GUI-only for security
- Download-only config in MVP (no upload)
- MCP is optional/low priority for MVP
- Focus on offline-first functionality
- Power users can connect their own GPU/Ollama

---

*Last Updated: 2025-09-29*
*This file should be updated after each coding session*