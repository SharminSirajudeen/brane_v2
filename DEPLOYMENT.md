# 🚀 BRANE Deployment Guide

Complete guide to deploy BRANE backend and frontend to production.

---

## 🎯 Quick Deploy (5 minutes)

### Backend: Railway

**1. Click to Deploy:**

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/brane-v2?referralCode=BRANE)

**2. Connect GitHub:**
- Login to Railway with GitHub
- Select repository: `SharminSirajudeen/brane_v2`
- Railway auto-detects `railway.json` and `Dockerfile`

**3. Set Environment Variables:**

In Railway dashboard, add these variables:

```bash
# Required
SECRET_KEY=<generate with: openssl rand -hex 32>
GOOGLE_CLIENT_ID=<from Google Cloud Console>
GOOGLE_CLIENT_SECRET=<from Google Cloud Console>
DATABASE_URL=<Railway provides this automatically>

# Optional (for cloud LLMs)
OPENAI_API_KEY=<your key>
ANTHROPIC_API_KEY=<your key>

# CORS (update after frontend deployment)
CORS_ORIGINS=https://sharminsirajudeen.github.io,http://localhost:5173
```

**4. Deploy!**
- Railway automatically builds and deploys
- Get your backend URL: `https://brane-production.up.railway.app`

---

### Frontend: GitHub Pages

**1. Update Backend URL:**

Edit `frontend/.env.production`:
```bash
VITE_API_URL=https://brane-production.up.railway.app
```

**2. Deploy:**
```bash
cd frontend
npm run build
npm run deploy
```

**3. Access:**
- Frontend: `https://sharminsirajudeen.github.io/brane_v2/`
- Login with Google OAuth

---

## 📋 Detailed Setup

### Backend Environment Variables

#### Required Variables

**SECRET_KEY**
```bash
# Generate with:
openssl rand -hex 32

# Or Python:
python -c "import secrets; print(secrets.token_hex(32))"
```

**GOOGLE_CLIENT_ID & GOOGLE_CLIENT_SECRET**

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create project: "BRANE"
3. Enable "Google+ API"
4. Create OAuth 2.0 credentials
5. Add authorized redirect URIs:
   ```
   https://brane-production.up.railway.app/api/auth/google/callback
   http://localhost:8000/api/auth/google/callback (for testing)
   ```

**DATABASE_URL**
- Railway provides PostgreSQL automatically
- Format: `postgresql://user:password@host:port/database`

#### Optional Variables

**LLM API Keys** (if using cloud providers):
```bash
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
TOGETHER_API_KEY=...
GROQ_API_KEY=...
```

**Storage** (default: local filesystem):
```bash
STORAGE_PATH=/app/storage
AXON_STORAGE_PATH=/app/axon_storage
MODELS_PATH=/app/models
```

**CORS**:
```bash
CORS_ORIGINS=https://sharminsirajudeen.github.io,http://localhost:5173
```

---

## 🔧 Alternative Deployment: Render

### Option 1: Web UI

1. **Create New Web Service**
   - Dashboard → New → Web Service
   - Connect repository: `SharminSirajudeen/brane_v2`

2. **Configure Service:**
   ```
   Name: brane-backend
   Region: Oregon (US West)
   Branch: main
   Root Directory: backend
   Environment: Python 3
   Build Command: pip install -r requirements.txt
   Start Command: alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port $PORT
   ```

3. **Add Environment Variables** (same as Railway above)

4. **Create PostgreSQL Database**
   - Dashboard → New → PostgreSQL
   - Copy "Internal Database URL" to `DATABASE_URL`

### Option 2: render.yaml (Infrastructure as Code)

Create `render.yaml`:
```yaml
services:
  - type: web
    name: brane-backend
    env: python
    region: oregon
    buildCommand: cd backend && pip install -r requirements.txt
    startCommand: cd backend && alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: SECRET_KEY
        generateValue: true
      - key: GOOGLE_CLIENT_ID
        sync: false
      - key: GOOGLE_CLIENT_SECRET
        sync: false
      - key: DATABASE_URL
        fromDatabase:
          name: brane-db
          property: connectionString
    healthCheckPath: /health

databases:
  - name: brane-db
    databaseName: brane
    user: brane
```

Deploy:
```bash
render deploy
```

---

## 🧪 Testing Deployment

### 1. Health Check

```bash
# Backend
curl https://brane-production.up.railway.app/health

# Expected:
{
  "status": "ok",
  "version": "0.1.0",
  "environment": "production"
}
```

### 2. Database Check

```bash
curl https://brane-production.up.railway.app/health/ready

# Expected:
{
  "status": "ready",
  "database": "connected"
}
```

### 3. API Docs

Visit: `https://brane-production.up.railway.app/api/docs`

### 4. Test Tools

```bash
# List available tools
curl https://brane-production.up.railway.app/api/tools

# Expected: SSH, HTTP, Filesystem tools
```

---

## 🔐 Security Checklist

Before production:

- [ ] Generate strong `SECRET_KEY` (32+ bytes)
- [ ] Set `DEBUG=false` in production
- [ ] Configure CORS with specific origins (not `*`)
- [ ] Use HTTPS only (Railway/Render provide this)
- [ ] Set up Google OAuth redirect URIs correctly
- [ ] Enable rate limiting (future)
- [ ] Set up monitoring (Railway provides metrics)
- [ ] Configure backups for database

---

## 📊 Monitoring

### Railway Dashboard

- **Metrics**: CPU, memory, network
- **Logs**: Real-time application logs
- **Deployments**: Version history, rollback

### Health Endpoints

```bash
# Basic health
GET /health

# Detailed readiness (includes DB check)
GET /health/ready
```

---

## 🐛 Troubleshooting

### Build Fails

**Problem:** `pip install` fails

**Solution:**
```bash
# Check requirements.txt syntax
# Ensure Python 3.10+ specified in railway.json
```

### Database Connection Error

**Problem:** `could not connect to server`

**Solution:**
1. Check `DATABASE_URL` is set correctly
2. Verify Railway PostgreSQL is running
3. Check database credentials

### CORS Error in Frontend

**Problem:** `blocked by CORS policy`

**Solution:**
```bash
# Update CORS_ORIGINS in Railway:
CORS_ORIGINS=https://sharminsirajudeen.github.io
```

### Tools Not Working

**Problem:** SSH/HTTP tools fail

**Solution:**
1. Check dependencies installed: `pip list | grep paramiko`
2. Verify MCP servers can start (may need Node.js for MCP)
3. Check tool logs in Railway dashboard

---

## 💰 Cost Estimation

### Railway (Recommended)

**Hobby Plan**: $5/month
- 512MB RAM, 1GB disk
- $0.000463/GB egress
- PostgreSQL included

**Pro Plan**: $20/month (if you need more)
- 8GB RAM, 100GB disk
- More concurrent connections

### Render

**Starter**: $7/month
- 512MB RAM
- PostgreSQL: $7/month extra

**Total**: ~$14/month

---

## 🚀 Production Optimizations

### Future Improvements

1. **CDN for Frontend**: Use Cloudflare
2. **Caching**: Add Redis for sessions
3. **Load Balancing**: Multiple Railway instances
4. **Background Jobs**: Celery for tool execution
5. **Monitoring**: Sentry for error tracking
6. **Analytics**: PostHog for usage metrics

---

## 📞 Support

- **Issues**: https://github.com/sharminsirajudeen/brane_v2/issues
- **Railway Docs**: https://docs.railway.app
- **Render Docs**: https://render.com/docs

---

**Ready to deploy? Follow the Quick Deploy section above! 🎉**
