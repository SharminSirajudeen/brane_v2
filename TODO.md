# BRANE v2.0 - 12-Week MVP Roadmap

**Last Updated**: January 25, 2025
**Current Phase**: Week 1-2 (Desktop App + Auto-Discovery)
**Target**: Desktop app launch in 12 weeks

---

## 📌 Quick Navigation
- **Current Status**: See STATUS.md
- **Architecture & Research**: See RandD.md
- **Quick Setup**: See README.md

---

## 🎯 PHASE 1: Desktop App + Advanced RAG (Weeks 1-4)

### Week 1-2: Electron Foundation + Auto-Discovery ⚡ CURRENT

#### Desktop App Setup
- [ ] **Electron Project Init** (4 hours)
  - Install Electron 28+ and electron-builder
  - Create main process (Node.js)
  - Wrap existing React frontend (renderer process)
  - Set up IPC communication
  - Configure window management

- [ ] **One-Click Installer** (6 hours)
  - Package for macOS (DMG)
  - Package for Windows (MSI)
  - Optional: Bundle Ollama installer
  - Auto-update system (electron-updater)
  - Deep linking (brane:// protocol)

#### Auto-Discovery System
- [ ] **Brain Discovery** (8 hours)
  - Implement `backend/discovery/brain_discovery.py`
  - Check Ollama (port 11434), LM Studio (1234), GPT4All
  - List models per provider with capabilities
  - Infer model capabilities (text, vision, function_calling)
  - Generate dynamic functions (chuk-llm pattern)

- [ ] **UI for Brain Selection** (4 hours)
  - Settings page: Brain discovery results
  - Model selection dropdown
  - "Use Local Brain" vs "Add Cloud Brain" buttons
  - Test connection button
  - Model info cards (size, capabilities)

**Deliverable**: Electron app that auto-discovers local brains

---

### Week 3: Advanced RAG Foundation

#### Hybrid Search
- [ ] **Semantic + BM25 Search** (6 hours)
  - Install FAISS + BM25Retriever (LangChain)
  - Implement `backend/rag/hybrid_search.py`
  - Ensemble retriever (0.5/0.5 weighting)
  - Top 50-100 candidates
  - Benchmark vs basic semantic search

#### Reranking
- [ ] **FlashRank Integration** (4 hours)
  - Install FlashRank (4MB nano model)
  - Implement `backend/rag/reranker.py`
  - Rerank top 50 → top 10
  - Latency target: <50ms
  - Integrate with hybrid search

#### Semantic Chunking
- [ ] **Replace Fixed-Size Chunking** (4 hours)
  - Install sentence-transformers
  - Implement `backend/rag/semantic_chunker.py`
  - Cosine similarity threshold: 0.6
  - Sliding window: 3-5 sentences
  - Preserve topic boundaries

#### Embedding Model
- [ ] **BGE-Small Deployment** (2 hours)
  - Download BAAI/bge-small-en-v1.5 (133MB)
  - Test embedding quality
  - Integrate with ChromaDB
  - Benchmark speed (target: <10ms per chunk)

**Deliverable**: Hybrid search + reranking + semantic chunking working

---

### Week 4: Context Optimization + MCP Integration

#### Contextual Compression
- [ ] **7x Compression Implementation** (6 hours)
  - LangChain ContextualCompressionRetriever
  - LLMChainExtractor with local LLM
  - Test compression ratio (target: 4-7x)
  - Validate relevance preservation

#### Parent-Child Chunking
- [ ] **Hierarchical Retrieval** (6 hours)
  - ParentDocumentRetriever (LangChain)
  - Children: 512 tokens (search)
  - Parents: 2048 tokens (return)
  - Store parent_id references
  - Test coherence improvement

#### Context Window Utilization
- [ ] **Optimal Fill Logic** (2 hours)
  - Implement 60-75% utilization
  - Reserve tokens for system/query/response
  - Dynamic allocation based on model
  - Logging and metrics

#### MCP Core Tools
- [ ] **Bundle 5 Essential MCPs** (4 hours)
  - File system (already built)
  - HTTP client (already built)
  - Shell commands (already built)
  - GitHub MCP (integrate existing)
  - Slack MCP (integrate existing)
  - Pre-configure, zero setup required

**Deliverable**: Complete advanced RAG pipeline + 5 bundled MCPs

---

## 🧪 PHASE 2: Testing & Optimization (Weeks 5-7)

### Week 5: Automated Testing

#### E2E Test Suite
- [ ] **Playwright Tests** (12 hours)
  - Install Playwright
  - Test: Create neuron
  - Test: Upload document (RAG)
  - Test: Chat with memory recall
  - Test: Switch brains (local ↔ cloud)
  - Test: Tool execution (file, HTTP, shell)
  - Coverage target: >80% critical flows

#### Performance Benchmarks
- [ ] **Metrics Collection** (4 hours)
  - RAG latency (<300ms)
  - App startup time (<3s)
  - Memory usage (<500MB idle)
  - Context expansion ratio (target: 7-10x)
  - Create automated benchmark suite

**Deliverable**: Automated test suite with benchmarks

---

### Week 6: Performance Optimization

#### RAG Pipeline
- [ ] **Optimize Retrieval** (6 hours)
  - Profile bottlenecks (cProfile)
  - Optimize embedding calls (batch)
  - Cache frequently accessed chunks
  - Parallel retrieval where possible
  - Target: <200ms p95 latency

#### Startup & Memory
- [ ] **App Performance** (6 hours)
  - Reduce Electron bundle size
  - Lazy-load React components
  - Optimize vector DB startup
  - Memory leak detection
  - Target: <3s startup, <500MB memory

#### Streaming
- [ ] **Response Streaming** (4 hours)
  - Optimize LLM streaming
  - WebSocket vs SSE comparison
  - Reduce first-token latency
  - Handle errors gracefully

**Deliverable**: Optimized app (fast startup, low latency)

---

### Week 7: Polish & UX

#### Error Handling
- [ ] **User-Friendly Errors** (4 hours)
  - Wrap all API calls in try-catch
  - User-facing error messages
  - Toast notifications (success/error)
  - Error boundaries (React)
  - Retry logic for network failures

#### Offline Mode
- [ ] **Local-First Functionality** (4 hours)
  - Detect network status
  - Queue failed requests
  - Sync when back online
  - Offline indicators in UI

#### Loading States
- [ ] **UX Improvements** (4 hours)
  - Skeleton loaders
  - Progress indicators (RAG processing)
  - Streaming indicators ("Thinking...")
  - Smooth transitions

**Deliverable**: Production-ready desktop app

---

## 🎨 PHASE 3: Vision & Multi-Agent (Weeks 8-10)

### Week 8: Vision Support

#### LLaVA Integration
- [ ] **Vision Model Setup** (6 hours)
  - Pull LLaVA 1.6 via Ollama (7B)
  - Pull Moondream (1.8B, lightweight option)
  - Test image understanding
  - Benchmark quality vs speed

#### Image Upload UI
- [ ] **Frontend Components** (6 hours)
  - Image upload button in chat
  - Drag-and-drop support
  - Image preview
  - Screenshot capture tool
  - Image + text combined queries

#### Backend Integration
- [ ] **Multi-Modal Brain** (4 hours)
  - Implement `backend/brains/multimodal_brain.py`
  - Base64 image encoding
  - LiteLLM multi-modal support
  - Auto-switch to vision model when image detected

**Deliverable**: Vision-capable neurons

---

### Week 9-10: Multi-Agent (Basic)

#### Sequential Workflows
- [ ] **Agent Orchestration** (8 hours)
  - Implement Google ADK pattern
  - Workflow Agent (parent)
  - LLM Agent (child)
  - Sequential execution (A → B → C)
  - Pass context between agents

#### Agent Hierarchy
- [ ] **Parent-Child System** (6 hours)
  - Root agent (CEO)
  - Sub-agents (VPs, managers)
  - Single parent rule enforcement
  - Agent metadata (roles, tools)

#### Execution Visualizer
- [ ] **UI for Workflow Tracking** (6 hours)
  - Flowchart visualization (React Flow)
  - Show agent execution order
  - Display intermediate results
  - Execution timeline

#### Budget Monitoring (Cloud Only)
- [ ] **Token Usage Tracking** (4 hours)
  - Count tokens per agent
  - Show cost estimates (if cloud brain)
  - Budget limit enforcement
  - Warning when approaching limit

**Deliverable**: Multi-agent sequential workflows

---

## 📚 PHASE 4: Documentation & Launch (Weeks 11-12)

### Week 11: Documentation

#### User Guides
- [ ] **Setup Guide** (4 hours)
  - Installation (macOS/Windows)
  - First neuron creation
  - Brain selection
  - Document upload (RAG)
  - Tool permissions

#### Video Tutorials
- [ ] **Screen Recordings** (6 hours)
  - 5-minute quick start
  - RAG tutorial
  - Tool usage demo
  - Multi-agent example
  - Publish to YouTube

#### Developer Docs
- [ ] **Technical Documentation** (6 hours)
  - Building custom neurons
  - Creating MCPs
  - API reference
  - Architecture overview
  - Contributing guide

**Deliverable**: Complete documentation

---

### Week 12: Launch Prep

#### Landing Page Update
- [ ] **Marketing Site** (4 hours)
  - Update with v2.0 features
  - Add download buttons (macOS/Windows)
  - Feature highlights (context expansion, vision)
  - Screenshots and demos
  - "Try BRANE" → Download link

#### Community Setup
- [ ] **Discord Server** (2 hours)
  - Create channels (#general, #support, #showcase)
  - Invite beta users
  - Pin installation guide
  - Set up welcome bot

#### Launch
- [ ] **Public Release** (4 hours)
  - GitHub release v2.0.0
  - Product Hunt launch
  - HackerNews post
  - Reddit (r/LocalLLaMA, r/OpenAI)
  - Twitter/X announcement

**Deliverable**: Public launch 🚀

---

## 🚫 NOT IN MVP (Future Phases)

### Phase 5: Web App (Post-Launch)
- Reuse React frontend (100% code reuse)
- Deploy to GitHub Pages
- Cloud brain only (no local in browser)
- Share neurons via URL

### Phase 6: Mobile (3-6 months post-launch)
- Flutter rewrite (iOS + Android)
- Mobile-optimized UI
- Camera integration (vision)
- Local LLM via MLX (iOS)

### Advanced RAG (Post-MVP)
- HyDE (hypothetical documents)
- Query decomposition
- Auto-merging retrieval
- LongLLMLingua compression
- ColBERT (if storage OK)
- RAPTOR (hierarchical summarization)
- GraphRAG (knowledge graphs)

### Advanced Multi-Agent (Post-MVP)
- Parallel workflows
- Loop workflows
- Custom agents (Python logic)
- Agent marketplace

### Revenue Features (6+ months)
- Neuron marketplace (10-20% commission)
- Enterprise support contracts
- Hosted BRANE cloud (optional)
- Visual workflow builder (premium)

---

## 📊 Success Metrics (12 Months)

### Technical
- RAG latency: <300ms (p95)
- Context expansion: 10-20x measured
- App startup: <3s
- Memory usage: <500MB
- Crash rate: <0.1%

### User
- 10,000 total users
- 5,000 monthly active
- 70% use local brain, 30% cloud
- 100 community neurons created

### Community
- 1,000 GitHub stars
- 2,000 Discord members
- 50 contributors
- 20 community MCPs

---

## 🔧 Development Setup

### Prerequisites
```bash
# Backend
Python 3.11+
Poetry or uv
Ollama (local LLM)
Docker Desktop (for MCP)

# Frontend
Node.js 18+
npm or pnpm

# Desktop
Electron 28+
electron-builder
```

### Quick Start
```bash
# 1. Pull latest
git pull origin main

# 2. Backend (Codespace)
cd backend
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python main.py

# 3. Frontend (Local)
cd frontend
npm install
npm run dev

# 4. Electron (Local)
cd frontend
npm run electron:dev
```

---

## 📋 Weekly Checklist Template

**Week X: [Focus Area]**

Monday:
- [ ] Review last week's work
- [ ] Plan this week's tasks
- [ ] Set up environment

Tuesday-Thursday:
- [ ] Implementation
- [ ] Code reviews
- [ ] Testing

Friday:
- [ ] Documentation
- [ ] Commit all work
- [ ] Update STATUS.md
- [ ] Update TODO.md
- [ ] Push to GitHub
- [ ] Weekly demo/review

---

## ✅ Completed (v1)

- ✅ Backend (4,900 lines FastAPI)
- ✅ Frontend (7,085 lines React)
- ✅ Tool system (11,305 lines)
- ✅ Landing page (deployed)
- ✅ Memory consolidation (4-layer)
- ✅ Settings system
- ✅ Google OAuth
- ✅ Git cleanup
- ✅ Architecture research (consolidated in RandD.md)

---

## 🔗 Quick Links

- **Status**: STATUS.md (where we are NOW)
- **Research**: RandD.md (all technical deep dives)
- **Setup**: README.md (quick start guide)
- **Codespace**: https://animated-halibut-vj4vj54p4vcwg9j.github.dev
- **GitHub**: https://github.com/SharminSirajudeen/brane_v2
- **Landing Page**: https://sharminsirajudeen.github.io/brane_v2/

---

**This is the ONLY TODO file - single source of truth for v2.0 roadmap.**

*Last Updated: January 25, 2025*
*See STATUS.md for current progress and RandD.md for technical details.*
