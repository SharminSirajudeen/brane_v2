# BRANE Backend Setup Guide

## Prerequisites

- Python 3.11+
- PostgreSQL 14+
- (Optional) Ollama for local LLM inference
- (Optional) Redis for multi-instance deployments

## Quick Start

### 1. Clone and Navigate

```bash
cd /Users/sharminsirajudeen/Projects/brane_v2/backend
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
cp .env.example .env
# Edit .env with your configuration
```

**Critical settings to update:**
- `DATABASE_URL` - Your PostgreSQL connection string
- `JWT_SECRET_KEY` - Generate strong random key
- `ENCRYPTION_KEY` - Generate strong random key (32+ chars)
- `GOOGLE_CLIENT_ID` & `GOOGLE_CLIENT_SECRET` - From Google Cloud Console

### 5. Setup Database

#### Start PostgreSQL

```bash
# macOS (Homebrew)
brew services start postgresql@14

# Linux
sudo systemctl start postgresql

# Docker
docker run -d \
  --name brane-postgres \
  -e POSTGRES_USER=brane \
  -e POSTGRES_PASSWORD=brane_dev_password \
  -e POSTGRES_DB=brane_dev \
  -p 5432:5432 \
  postgres:14
```

#### Run Migrations

```bash
# Upgrade to latest schema
alembic upgrade head

# Or use init_db() on first startup (creates tables automatically)
```

### 6. Start Server

```bash
# Development (with auto-reload)
python main.py

# Or using uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 7. Verify Installation

```bash
# Run test suite
python test_server.py

# Check health
curl http://localhost:8000/health

# View API docs
open http://localhost:8000/api/docs
```

## Development Workflow

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Running Tests

```bash
# Full test suite
pytest

# With coverage
pytest --cov=. --cov-report=html

# Integration tests
python test_server.py
```

### Code Quality

```bash
# Format code
black .

# Lint
ruff check .

# Type checking
mypy .
```

## Configuration

### Privacy Tiers

- **0 (LOCAL)**: On-premise only, no data leaves infrastructure
- **1 (PRIVATE_CLOUD)**: Encrypted private cloud (HIPAA compliant)
- **2 (PUBLIC_API)**: Public LLM APIs (no PHI/PII allowed)

### LLM Providers

#### Ollama (Local, Privacy Tier 0)

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull model
ollama pull llama3.1

# Start server (runs on localhost:11434)
ollama serve
```

#### OpenAI (Privacy Tier 2)

Set `OPENAI_API_KEY` in `.env`

#### Anthropic Claude (Privacy Tier 2)

Set `ANTHROPIC_API_KEY` in `.env`

### Storage Paths

All data stored in `./storage/` by default:
- `storage/axon/` - FAISS vector stores (encrypted)
- `storage/uploads/` - Uploaded documents
- `storage/models/` - Cached embedding models

## Docker Deployment

### Build Image

```bash
docker build -t brane-backend .
```

### Run with Docker Compose

```bash
docker-compose up -d
```

This starts:
- Backend API
- PostgreSQL
- Redis (optional)

## Production Deployment

### Environment Variables

**Must change in production:**

```bash
DEBUG=false
ENVIRONMENT=production
JWT_SECRET_KEY=<generate-strong-random-key>
ENCRYPTION_KEY=<generate-strong-random-key-32-chars-min>
DATABASE_URL=<production-database-url>
```

### Security Checklist

- [ ] Strong JWT secret (32+ chars, random)
- [ ] Strong encryption key (32+ chars, random)
- [ ] HTTPS enabled (reverse proxy: nginx/Caddy)
- [ ] Database SSL enabled
- [ ] CORS origins restricted
- [ ] Rate limiting configured
- [ ] Google OAuth configured
- [ ] Firewall rules (only 80/443 exposed)
- [ ] Backup strategy implemented
- [ ] Audit logs monitored

### Recommended Architecture

```
Internet
   ↓
Reverse Proxy (nginx/Caddy) - HTTPS/SSL
   ↓
Load Balancer
   ↓
BRANE Backend (multiple instances)
   ↓
PostgreSQL (primary + replica)
Redis (optional, for session/cache)
```

## Troubleshooting

### Database Connection Failed

```bash
# Check PostgreSQL is running
pg_isready

# Check credentials
psql -U brane -d brane_dev -h localhost

# Check DATABASE_URL format
# postgresql://user:password@host:port/database
```

### Alembic Migration Errors

```bash
# Reset database (CAUTION: destroys data)
alembic downgrade base
alembic upgrade head

# Or manually drop tables
psql -U brane -d brane_dev -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
```

### LLM Provider Errors

```bash
# Ollama not running
ollama serve

# API keys not set
echo $OPENAI_API_KEY

# Model not available
ollama list
```

### Import Errors

```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

## API Documentation

Once server is running, visit:

- **OpenAPI/Swagger**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

## Support

For issues, see:
- GitHub Issues: [link]
- Documentation: [link]
- Community: [link]

## License

[Your License]
