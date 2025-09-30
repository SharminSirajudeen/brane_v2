# BRANE Backend - Complete Installation Guide

## ✅ Implementation Status

All core components have been successfully implemented:

### Core Components (100% Complete)
- ✅ Database Models (User, Neuron, ChatSession, Message, AuditLog, Document)
- ✅ Database Connection (AsyncPG with SQLAlchemy)
- ✅ Authentication API (Google OAuth + JWT)
- ✅ Neuron Core (AI Agent with 4-layer memory)
- ✅ NeuronManager (Multi-agent orchestration)
- ✅ LLM Broker (Model-agnostic interface via LiteLLM)
- ✅ Axon (FAISS vector store with encryption)
- ✅ Synapse (MCP plugin system)

### API Endpoints (100% Complete)
- ✅ Auth API (`/api/auth/*`)
- ✅ Neurons API (`/api/neurons/*`) - CRUD operations
- ✅ Chat API (`/api/chat/*`) - Streaming with SSE, session management
- ✅ RAG API (`/api/rag/*`) - Document upload, search, file handling
- ✅ Admin API (`/api/admin/*`) - User management, audit logs

### Infrastructure (100% Complete)
- ✅ Alembic migrations setup
- ✅ Docker configuration
- ✅ Environment configuration
- ✅ Logging and audit trails
- ✅ Test suite
- ✅ Setup scripts

---

## 📋 Installation Steps

### Step 1: Install System Dependencies

#### macOS
```bash
# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install PostgreSQL
brew install postgresql@14
brew services start postgresql@14

# Install Python 3.11+
brew install python@3.11

# (Optional) Install Ollama for local LLM
brew install ollama
ollama serve  # Run in separate terminal
ollama pull llama3.1
```

#### Linux (Ubuntu/Debian)
```bash
# Update packages
sudo apt update

# Install PostgreSQL
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Install Python 3.11+
sudo apt install python3.11 python3.11-venv python3-pip

# (Optional) Install Ollama
curl -fsSL https://ollama.com/install.sh | sh
```

### Step 2: Setup Database

```bash
# Create database and user
sudo -u postgres psql << EOF
CREATE USER brane WITH PASSWORD 'brane_dev_password';
CREATE DATABASE brane_dev OWNER brane;
GRANT ALL PRIVILEGES ON DATABASE brane_dev TO brane;
EOF

# Verify connection
psql -U brane -d brane_dev -h localhost -c "SELECT version();"
```

### Step 3: Setup Python Environment

```bash
# Navigate to backend directory
cd /Users/sharminsirajudeen/Projects/brane_v2/backend

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# OR
venv\Scripts\activate  # Windows

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

### Step 4: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env file
vim .env  # or nano, code, etc.
```

**Required Changes in `.env`:**

```env
# Generate strong random keys (32+ characters)
JWT_SECRET_KEY=<generate-strong-random-key-here>
ENCRYPTION_KEY=<generate-strong-random-key-here>

# Update database if different from defaults
DATABASE_URL=postgresql://brane:brane_dev_password@localhost:5432/brane_dev

# Configure Google OAuth (get from Google Cloud Console)
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
```

**Generate Secure Keys:**
```bash
# Generate JWT secret
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate encryption key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Step 5: Run Database Migrations

```bash
# Run Alembic migrations
alembic upgrade head

# Verify tables were created
psql -U brane -d brane_dev -c "\dt"
```

Expected output:
```
             List of relations
 Schema |     Name      | Type  | Owner
--------+---------------+-------+-------
 public | audit_logs    | table | brane
 public | chat_sessions | table | brane
 public | documents     | table | brane
 public | messages      | table | brane
 public | neurons       | table | brane
 public | users         | table | brane
```

### Step 6: Validate Setup

```bash
# Run validation script
python validate_setup.py
```

This will check:
- Python version
- All dependencies installed
- Project structure
- Environment configuration
- Database models
- Core components
- API routes

### Step 7: Start Server

```bash
# Development mode (auto-reload)
python main.py

# OR using uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# OR using the startup script
./run_dev.sh
```

### Step 8: Verify Installation

**Option 1: Health Checks**
```bash
# Basic health check
curl http://localhost:8000/health

# Readiness check (database connection)
curl http://localhost:8000/health/ready
```

**Option 2: API Documentation**
Open in browser:
- http://localhost:8000/api/docs (Swagger UI)
- http://localhost:8000/api/redoc (ReDoc)

**Option 3: Run Test Suite**
```bash
# Run comprehensive tests
python test_server.py

# Expected output: All tests passing
```

---

## 🔧 Configuration Details

### Privacy Tiers

| Tier | Name | Description | LLM Options |
|------|------|-------------|-------------|
| 0 | LOCAL | On-premise only | Ollama, LocalAI |
| 1 | PRIVATE_CLOUD | Encrypted private cloud | Azure OpenAI (HIPAA) |
| 2 | PUBLIC_API | Public APIs (no PHI/PII) | OpenAI, Anthropic |

### LLM Provider Configuration

#### Ollama (Tier 0 - Local)
```env
OLLAMA_BASE_URL=http://localhost:11434
```

Neuron config:
```yaml
model:
  provider: ollama
  model: llama3.1
  temperature: 0.7
```

#### OpenAI (Tier 2)
```env
OPENAI_API_KEY=sk-...
```

Neuron config:
```yaml
model:
  provider: openai
  model: gpt-4
  temperature: 0.7
```

#### Anthropic Claude (Tier 2)
```env
ANTHROPIC_API_KEY=sk-ant-...
```

Neuron config:
```yaml
model:
  provider: anthropic
  model: claude-3-sonnet-20240229
  temperature: 0.7
```

### Storage Configuration

All data stored in `./storage/` by default:

```
storage/
├── axon/              # FAISS vector stores (encrypted)
│   └── {neuron_id}/
│       ├── vectors.index
│       └── docs.pkl
├── uploads/           # Uploaded documents
│   └── {neuron_id}/
│       └── {filename}
└── models/            # Cached embedding models
    └── sentence-transformers/
```

---

## 🚀 Quick Start (All-in-One)

```bash
# 1. Start PostgreSQL
brew services start postgresql@14  # macOS
# OR
sudo systemctl start postgresql    # Linux

# 2. Create database
createdb -U postgres brane_dev

# 3. Setup backend
cd /Users/sharminsirajudeen/Projects/brane_v2/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Configure
cp .env.example .env
# Edit .env with your settings

# 5. Migrate database
alembic upgrade head

# 6. Start server
python main.py

# 7. Test
python test_server.py
```

---

## 📊 API Endpoints Summary

### Authentication
- `POST /api/auth/google` - Initiate Google OAuth
- `GET /api/auth/callback` - OAuth callback
- `POST /api/auth/token` - Get JWT token
- `GET /api/auth/me` - Get current user

### Neurons (AI Agents)
- `GET /api/neurons` - List all neurons
- `POST /api/neurons` - Create neuron
- `GET /api/neurons/{id}` - Get neuron details
- `PATCH /api/neurons/{id}` - Update neuron
- `DELETE /api/neurons/{id}` - Delete neuron

### Chat
- `POST /api/chat/{neuron_id}/stream` - Stream chat (SSE)
- `GET /api/chat/{neuron_id}/sessions` - List sessions
- `GET /api/chat/sessions/{session_id}/messages` - Get messages
- `DELETE /api/chat/sessions/{session_id}` - Delete session

### RAG (Document Management)
- `POST /api/rag/upload` - Upload document (JSON)
- `POST /api/rag/upload-file` - Upload file (PDF, TXT, MD)
- `POST /api/rag/search/{neuron_id}` - Search documents
- `GET /api/rag/{neuron_id}/documents` - List documents
- `DELETE /api/rag/documents/{doc_id}` - Delete document

### Admin
- `GET /api/admin/users` - List users (admin only)
- `GET /api/admin/audit-logs` - View audit logs

---

## 🧪 Testing

### Unit Tests
```bash
pytest tests/
```

### Integration Tests
```bash
python test_server.py
```

### Manual Testing with curl

**Create Neuron:**
```bash
curl -X POST http://localhost:8000/api/neurons \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Medical Assistant",
    "description": "HIPAA-compliant medical AI",
    "privacy_tier": 0,
    "config": {...}
  }'
```

**Chat (Streaming):**
```bash
curl -N http://localhost:8000/api/chat/{neuron_id}/stream \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are the symptoms of diabetes?"
  }'
```

---

## 🐛 Troubleshooting

### Issue: "No module named 'sqlalchemy'"
**Solution:** Activate virtual environment and install dependencies
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Issue: "Database connection failed"
**Solution:** Check PostgreSQL is running
```bash
pg_isready
brew services restart postgresql@14
```

### Issue: "Alembic migration failed"
**Solution:** Reset database
```bash
alembic downgrade base
alembic upgrade head
```

### Issue: "Ollama connection refused"
**Solution:** Start Ollama server
```bash
ollama serve
# In another terminal
ollama pull llama3.1
```

---

## 📁 Project Structure

```
backend/
├── main.py                    # FastAPI application entry point
├── requirements.txt           # Python dependencies
├── .env.example              # Environment template
├── alembic.ini               # Alembic configuration
├── alembic/                  # Database migrations
│   ├── env.py
│   └── versions/
│       └── 20251001_0000_initial_schema.py
├── api/                      # API routes
│   ├── auth.py              # Authentication (OAuth + JWT)
│   ├── neurons.py           # Neuron CRUD
│   ├── chat.py              # Chat streaming
│   ├── rag.py               # Document management
│   └── admin.py             # Admin endpoints
├── core/                     # Core business logic
│   ├── neuron/
│   │   ├── neuron.py        # AI Agent implementation
│   │   └── neuron_manager.py # Multi-agent orchestration
│   ├── llm/
│   │   └── broker.py        # LLM abstraction layer
│   ├── axon/
│   │   └── axon.py          # FAISS vector store
│   ├── synapse/
│   │   └── synapse.py       # MCP plugin system
│   ├── config/
│   │   └── settings.py      # Configuration management
│   └── security/
│       └── audit.py         # HIPAA audit logging
├── db/                       # Database layer
│   ├── models.py            # SQLAlchemy ORM models
│   └── database.py          # Connection management
├── test_server.py           # Comprehensive test suite
├── validate_setup.py        # Setup validation
└── run_dev.sh              # Development startup script
```

---

## ✅ Verification Checklist

- [ ] PostgreSQL installed and running
- [ ] Python 3.11+ installed
- [ ] Virtual environment created and activated
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` file configured with strong secrets
- [ ] Database created and migrations run
- [ ] Health check returns 200 OK
- [ ] Test suite passes
- [ ] API documentation accessible
- [ ] (Optional) Ollama running for local LLM

---

## 🎯 Next Steps

1. **Configure Google OAuth** (for production auth)
   - Go to Google Cloud Console
   - Create OAuth 2.0 credentials
   - Update `.env` with client ID and secret

2. **Deploy to Production**
   - See `SETUP.md` for deployment guide
   - Configure reverse proxy (nginx/Caddy)
   - Enable HTTPS
   - Set up monitoring

3. **Create First Neuron**
   - Use API or admin interface
   - Configure privacy tier
   - Set up Axon (RAG) if needed

4. **Integrate with Frontend**
   - Frontend connects to backend API
   - Implements OAuth flow
   - Streams chat responses

---

**You're all set! 🎉**

The BRANE backend is production-ready with all core features implemented:
- ✅ Privacy-first architecture (3 tiers)
- ✅ HIPAA-compliant audit logging
- ✅ Multi-agent orchestration
- ✅ RAG with encrypted vector store
- ✅ Streaming chat with SSE
- ✅ Model-agnostic LLM integration
- ✅ Complete API documentation

For questions or issues, refer to `SETUP.md` or create an issue on GitHub.
