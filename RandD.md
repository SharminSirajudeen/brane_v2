# BRANE v2.0 - Research & Development Documentation

**Last Updated**: January 25, 2025
**Purpose**: Central repository for all research, architecture decisions, and technical explorations

---

## Table of Contents
1. [Complete Architecture](#complete-architecture)
2. [Advanced RAG Research](#advanced-rag-research)
3. [Multi-Agent System (ADK)](#multi-agent-system-adk)
4. [Tool System Research](#tool-system-research)
5. [Universal Tool Access Architecture](#universal-tool-access-architecture)
6. [Hardware Bundling Research](#hardware-bundling-research)

---

## Complete Architecture

**Source**: Originally in `BRANE_COMPLETE_ARCHITECTURE.md`

### Executive Summary

BRANE is a **local-first AI agent platform** that solves the fundamental limitation of local LLMs: limited context windows. Through advanced RAG techniques, BRANE achieves **10-20x effective context expansion**, making 4K context local models competitive with 100K+ context cloud models.

**Core Value Proposition:**
> "ChatGPT-level capabilities on YOUR computer, with YOUR files, protecting YOUR privacy, at ZERO cost, with 500+ tools built-in."

**Business Model:** Platform (like VS Code), not SaaS. Users provide their own LLM brains (local or cloud API keys). BRANE never charges for core features.

### What BRANE Is

- **Downloadable neuron platform** (agents you own forever)
- **Brain-agnostic** (works with ANY LLM provider via LiteLLM)
- **Local-first** (everything runs on user's machine)
- **Privacy-preserving** (no data sent to BRANE servers, because there are none)
- **Zero vendor lock-in** (neurons are portable .brane files)
- **Open source** (all models, all code, all protocols)

### Core Architecture Layers

1. **Platform Layer**: Desktop (Electron), Web (React), Mobile (future)
2. **Neuron Layer**: Downloadable .brane packages with config, knowledge, tools, memory
3. **Advanced RAG System**: 10-20x context expansion (the killer feature)
4. **Tool Layer**: MCP protocol, 500+ tools via Docker gateway
5. **Brain Abstraction**: LiteLLM routing to local/cloud LLMs

### The Killer Feature: Context Window Domination

Physical Context Window: **4,096 tokens** (e.g., Llama 3 8B)

**5-Step Pipeline** (executes in 200-300ms):

1. **Hybrid Search** (semantic + BM25) → Top 100 chunks
2. **FlashRank Reranking** (4MB local) → Top 10 chunks
3. **Contextual Compression** (7x ratio) → 70% smaller
4. **Parent-Child Assembly** → Full context
5. **Context Window Fill** (60-75% optimal) → To LLM

**Result**: 4K physical context = 28K effective context

**Why This Matters**:
- Competes with cloud (4K local ≈ 80K cloud with compression)
- Fully private (no data leaves machine)
- Zero cost (no API calls)
- Fast (<300ms retrieval + compression)
- Accurate (40-50% better recall)

### Technical Stack

**Backend**:
- FastAPI, Python 3.11+, Pydantic v2
- LiteLLM (100+ providers)
- LangChain 0.1+ (orchestration)
- ChromaDB (embedded vector DB)
- FAISS (vector search)
- BM25 (keyword search)
- FlashRank (4MB reranking)
- BAAI/bge-small-en-v1.5 (133MB embeddings)

**Frontend**:
- React 18.2+, TypeScript 5.0+, Vite 5.0+
- Tailwind CSS, shadcn/ui
- Zustand (state), React Query

**Desktop**:
- Electron 28+, electron-builder
- 100% React frontend reuse
- Auto-updater, native dialogs

**Database**:
- SQLite (dev), PostgreSQL (prod)
- Alembic migrations
- ChromaDB (embedded) → Qdrant (production)

---

## Advanced RAG Research

**Source**: Originally in `ADVANCED_RAG_RESEARCH_REPORT.md`

### Key Techniques Implemented

#### 1. Hybrid Search (Semantic + BM25)
- **Problem**: Semantic search misses exact keyword matches
- **Solution**: Combine semantic (embeddings) + BM25 (TF-IDF)
- **Implementation**: LangChain EnsembleRetriever (0.5/0.5 weighting)
- **Improvement**: +31% F1 score over semantic-only

#### 2. FlashRank Reranking
- **Problem**: Initial retrieval has false positives
- **Solution**: Deep semantic reranking with 4MB model
- **Implementation**: FlashRank Nano (no dependencies, CPU-only)
- **Latency**: <50ms for 100 candidates
- **Improvement**: +15% F1 score on top of hybrid search

#### 3. Semantic Chunking
- **Problem**: Fixed-size chunking splits topics mid-sentence
- **Solution**: Chunk by semantic similarity (topic boundaries)
- **Implementation**: sentence-transformers cosine similarity
- **Threshold**: 0.6 (tune per use case)
- **Improvement**: Better coherence, fewer irrelevant chunks

#### 4. Contextual Compression
- **Problem**: Retrieved chunks have irrelevant sentences
- **Solution**: LLM extracts only query-relevant content
- **Implementation**: LangChain ContextualCompressionRetriever
- **Compression Ratio**: 7x typical, up to 20x possible
- **Quality**: Faithfulness >95%

#### 5. Parent-Child Chunking
- **Problem**: Small chunks lack context, large chunks dilute relevance
- **Solution**: Search small (512 tokens), return large (2048 tokens)
- **Implementation**: LangChain ParentDocumentRetriever
- **Result**: Precision of small + context of large

#### 6. Context Window Utilization (60-75%)
- **Research Finding**: Filling 100% of context causes "lost in the middle" problem
- **Optimal Range**: 60-75% utilization
- **Implementation**: Dynamic allocation based on model
- **Result**: Better accuracy, room for query + response

### Performance Benchmarks

**Retrieval Quality** (F1 Score):
- Basic semantic search: 61%
- Hybrid search: 80% (+31%)
- Hybrid + reranking: 89% (+46%)
- Full pipeline: 92% overall quality

**Latency**:
- Hybrid search: 70ms
- Reranking: 50ms
- Compression: 80ms
- Parent assembly: 20ms
- **Total**: ~220ms (p95 <300ms)

**Effective Context Expansion**:
- Physical context: 4,096 tokens
- Effective context: 28,672 tokens
- **Expansion ratio**: 7x (conservative), up to 20x possible

### Future Advanced Techniques (Post-MVP)

1. **HyDE** (Hypothetical Document Embeddings): Generate fake answer, search for it
2. **Query Decomposition**: Break complex query into sub-questions
3. **Auto-Merging Retrieval**: Merge adjacent chunks if both retrieved
4. **LongLLMLingua**: 4-6x prompt compression with <1% quality loss
5. **ColBERT**: Token-level embeddings (high accuracy, high storage)
6. **RAPTOR**: Hierarchical summarization (20% improvement)
7. **GraphRAG**: Knowledge graph for multi-hop reasoning

---

## Multi-Agent System (ADK)

**Source**: Originally in `ADK_RESEARCH_REPORT.md`

### Google ADK Pattern

**3 Agent Types**:

1. **LLM Agent** (brain): Reasoning, decision-making via LLM
2. **Workflow Agent** (manager): Orchestration (sequential/parallel/loop)
3. **Custom Agent** (specialist): Python logic without LLM

### BRANE Implementation

**Phase 1 (MVP)**: Single agent only

**Phase 2 (Post-MVP)**: Multi-agent workflows

**Example**: Research Report Generator

```yaml
Neuron = Workflow Agent (parent)
├─ Research Agent (LLM Agent)
│  Tools: [web_search, wikipedia, arxiv]
│  Task: Find 5 papers on quantum computing
│
├─ Summarization Agent (LLM Agent)
│  Tools: [document_read]
│  Task: Summarize each paper to 200 words
│
└─ Report Agent (LLM Agent)
   Tools: [markdown_write]
   Task: Compile research report

Orchestration: Sequential (research → summarize → report)
```

### Agent Hierarchy

```
CEO Neuron (root agent)
├─ Research VP (sub-agent)
│  ├─ Web Search Manager
│  └─ Paper Analysis Manager
│
├─ Development VP (sub-agent)
│  ├─ Frontend Team (3 agents)
│  └─ Backend Team (2 agents)
│
└─ Testing VP (sub-agent)
   └─ QA Agent
```

**Rules**:
- Each sub-agent has ONE parent
- Parent can have MULTIPLE sub-agents
- Emergent behavior: Simple local rules → complex global patterns

### Workflow Types

1. **Sequential**: A → B → C (assembly line)
2. **Parallel**: A + B + C (simultaneous)
3. **Loop**: Repeat A until condition met

---

## Tool System Research

**Source**: Originally in `BRANE_TOOL_SYSTEM_RESEARCH.md`

### MCP (Model Context Protocol)

**What It Is**: Anthropic-backed standard for AI tool integration

**Architecture**:
- **Client**: BRANE (desktop/web app)
- **Server**: MCP server (Docker container)
- **Protocol**: HTTP Streamable or STDIO
- **Transport**: JSON-RPC 2.0

**Why MCP Over Custom**:
- Industry standard (growing ecosystem)
- 500+ servers via Docker catalog
- Interoperability (tools work across platforms)
- Community contributions
- Lower maintenance

### MCP Integration Phases

**Phase 1 (MVP)**: Bundled Core MCPs (5 tools, zero setup)
1. File System MCP (read, write, list, search, delete)
2. HTTP MCP (fetch, post, download)
3. Shell MCP (execute commands, run scripts)
4. GitHub MCP (issues, repos, files)
5. Slack MCP (messages, channels)

**Phase 2 (Post-Launch)**: Docker MCP Gateway
- One-click install from catalog (500+ servers)
- Auto-configuration via UI
- Container management (auto start/stop)
- Popular: fetch, YouTube, Playwright, Context7, databases

**Phase 3 (Future)**: BRANE MCP Marketplace
- Developer uploads custom MCP
- Users rate and review
- Revenue sharing (90/10 split)
- Auto-install with neurons

### Docker MCP Gateway

**How It Works**:

```
BRANE Neuron
    │
    ▼
Docker MCP Gateway (localhost:8089)
    │
    ├─ YouTube Container (running)
    ├─ Slack Container (stopped)
    └─ Playwright Container (running)

Flow:
1. Neuron calls: get_transcript(url)
2. Gateway receives request
3. If container stopped → spin up
4. Execute tool
5. Return result
6. Spin down container (save memory)
```

**Benefits**:
- Zero configuration (Docker handles dependencies)
- Isolation (containers can't access host)
- Resource limits (CPU, memory, disk)
- Auto-cleanup

---

## Universal Tool Access Architecture

**Source**: Originally in `BRANE_UNIVERSAL_TOOL_ACCESS_ARCHITECTURE.md`

### Vision

Enable AI Neurons to interact with **digital AND physical** world:
- Digital: Files, APIs, databases, web services
- Physical: IoT devices, smart home, robotics

### Tool Categories

1. **File System**: Read/write/list with workspace sandboxing
2. **Shell**: Safe command execution with whitelist
3. **HTTP**: REST API calls with auth support
4. **SSH**: Remote server access (RejectPolicy for security)
5. **Database**: SQL/NoSQL queries
6. **Cloud**: AWS, GCP, Azure SDKs
7. **IoT**: MQTT, Zigbee, Z-Wave protocols
8. **Smart Home**: Philips Hue, Nest, Ring
9. **Custom**: User-defined Python tools

### Permission System

**3-Tier Privacy Model**:

- **Tier 0 (Local)**: Never leave device, PII/PHI redaction
- **Tier 1 (Private Cloud)**: Your VPC, encrypted at rest
- **Tier 2 (Public API)**: OpenAI/Anthropic, no sensitive data

**Permission Levels**:
- **Low**: Read-only, no state changes
- **Medium**: Write data, limited scope
- **High**: System commands, network access
- **Critical**: Delete operations, admin actions

**User Controls**:
- Explicit consent per tool
- Workspace restrictions (e.g., only ~/Documents/Finance)
- Domain allowlist (e.g., only *.bloomberg.com)
- Audit logging (track all tool executions)

### Security Mechanisms

1. **Sandboxing**: Docker containers for MCPs
2. **Whitelisting**: Approved commands/domains only
3. **Input Validation**: Reject dangerous patterns (rm -rf, sudo)
4. **Rate Limiting**: Max calls per minute
5. **Encryption**: At-rest (SQLite DB) and in-transit (HTTPS)

---

## Hardware Bundling Research

**Source**: Originally in `BRANE_HARDWARE_BUNDLING_RESEARCH.md`

### The Opportunity

**Problem**: Users want local AI but don't have capable hardware

**Solution**: Hardware-as-a-Service (HaaS) bundles

### Quantization Insights

**From Video Research**: 70B models can run on 16GB RAM with Q2 quantization

**User-Friendly Abstraction**:
- Technical: "Q2_K quantization, 4-bit precision"
- User-Facing: "Lightning Fast mode (uses less RAM)"

**Hardware-Adaptive Selection**:
- Auto-detect available RAM
- Recommend quantization level
- UI: "Your Mac has 16GB RAM → Can run 70B Lightning Fast (Q2)"

### Business Model: Hardware Bundles

**Tier 1**: Entry ($399/month or $9,999 one-time)
- Mac Mini M4 (16GB RAM)
- Runs 7B-13B models (Q4/Q5)
- Target: Individuals, small teams

**Tier 2**: Professional ($699/month or $19,999 one-time)
- Mac Studio M4 Max (64GB RAM)
- Runs 34B-70B models (Q4)
- Target: Professionals, small companies

**Tier 3**: Enterprise ($1,499/month or $49,999 one-time)
- Mac Studio M4 Ultra (192GB RAM)
- Runs 70B-405B models (Q4/Q5)
- Target: Large companies, research labs

**Revenue Projections** (Year 5):
- 100 Tier 1 users × $399/mo = $39,900/mo
- 50 Tier 2 users × $699/mo = $34,950/mo
- 20 Tier 3 users × $1,499/mo = $29,980/mo
- **Total**: $104,830/mo × 12 = **$1,257,960/year**

(Conservative estimate, assumes subscription model)

### Marketing Angle

**Tagline**: "Run 70B Models on a 16GB Laptop!"

**Key Messages**:
- No cloud costs (pay once, use forever)
- Complete privacy (data never leaves your office)
- No internet required (fully offline)
- Enterprise-grade security (physical isolation)

### Implementation Notes

**Phase 1 (MVP)**: Software-only, users bring their own hardware

**Phase 2 (Post-Launch)**: Hardware bundles as optional add-on

**Phase 3 (Scale)**: Hardware-as-a-Service with maintenance/support

---

## Key Research Citations

### Papers

1. **"Long Context RAG Performance of LLMs"** (Nov 2024)
   - https://arxiv.org/abs/2411.03538
   - Finding: 16K-32K optimal retrieval zone

2. **"Introducing Context Window Utilization"** (July 2024)
   - https://arxiv.org/abs/2407.19794
   - Finding: 60-75% utilization optimal

3. **"LongLLMLingua: Prompt Compression"** (Oct 2023)
   - https://arxiv.org/abs/2310.06839
   - Finding: 4-6x compression, 21.4% accuracy boost

4. **"RAPTOR: Recursive Abstractive Processing"** (Jan 2024)
   - https://arxiv.org/abs/2401.18059
   - Finding: 20% improvement with hierarchical summarization

### Tools & Frameworks

- **chuk-llm**: https://github.com/chrisusher/chuk-llm (auto-discovery pattern)
- **Docker MCP Catalog**: https://www.docker.com/products/mcp/ (500+ MCP servers)
- **FlashRank**: https://github.com/PrithivirajDamodaran/FlashRank (4MB reranker)
- **LangChain**: https://python.langchain.com/ (RAG orchestration)
- **LiteLLM**: https://github.com/BerriAI/litellm (100+ LLM providers)
- **Google ADK**: https://github.com/google/adk (multi-agent patterns)

### Community Resources

- **RAG Techniques Repo**: https://github.com/NirDiamant/RAG_Techniques (30+ notebooks)
- **Awesome RAG**: https://github.com/coree/awesome-rag (curated list)
- **MCP Servers**: https://github.com/modelcontextprotocol/servers (official registry)

---

## Decision Log

### Why Local-First?
- Privacy is core value proposition
- Differentiation from ChatGPT/Claude
- Zero operating costs for BRANE
- User owns their data and neurons
- Regulatory compliance (GDPR, HIPAA easier)

### Why Advanced RAG Over Large Context?
- Research shows: Most LLMs effective only up to 16K-32K (even with 100K+ windows)
- Context window utilization: 60-75% optimal (not 100%)
- Advanced RAG = 10-20x effective expansion
- Works with ANY model (future-proof)

### Why MCP Over Custom Tool Protocol?
- Industry standard (Anthropic-backed)
- Growing ecosystem (500+ servers)
- Interoperability
- Lower maintenance

### Why Electron Over Flutter for Desktop?
- React frontend already built (100% reuse)
- Electron = 1 week vs Flutter = 3 weeks
- Time to market critical
- Flutter migration post-launch for performance

---

**END OF R&D DOCUMENTATION**

This file consolidates all research, architecture decisions, and technical explorations for BRANE v2.0. For current status and actionable tasks, see STATUS.md and TODO.md respectively.
