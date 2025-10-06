# BRANE Backend - Fly.io Deployment Guide

**Complete step-by-step guide to deploy BRANE backend to Fly.io with Neon PostgreSQL**

---

## Prerequisites

### 1. Install Fly.io CLI

**macOS/Linux:**
```bash
curl -L https://fly.io/install.sh | sh
```

**Windows (PowerShell):**
```powershell
iwr https://fly.io/install.ps1 -useb | iex
```

**Verify installation:**
```bash
fly version
# Should show: flyctl v0.x.x ...
```

### 2. Create Fly.io Account
```bash
# Sign up (opens browser)
fly auth signup

# Or login if you have an account
fly auth login
```

### 3. Set Up Neon PostgreSQL Database

**Why Neon?**
- **Free tier**: 0.5GB storage, 1 compute unit (sufficient for BRANE)
- **Serverless**: Auto-scales to zero when idle (cost savings)
- **Instant provisioning**: Database ready in seconds
- **Branch support**: Separate dev/staging/prod databases

**Steps:**

1. **Go to [Neon Console](https://console.neon.tech/)**

2. **Create a new project:**
   - Name: `brane-production` (or any name)
   - Region: Choose same as Fly.io region (e.g., `US East (Ohio)` for `ord`)
   - PostgreSQL version: 15 (recommended)

3. **Copy the connection string:**
   - Format: `postgresql://user:password@host/database?sslmode=require`
   - Example: `postgresql://brane_user:abc123xyz@ep-cool-wind-123456.us-east-2.aws.neon.tech/brane_prod?sslmode=require`
   - **Save this!** You'll need it in the next section

4. **Create the database schema (optional if using Alembic migrations):**
   ```bash
   # Connect to Neon database
   psql "postgresql://user:password@host/database?sslmode=require"

   # Create schema (or let Alembic do it automatically)
   # Alembic will run migrations on first deploy
   ```

---

## Deployment Steps

### Step 1: Navigate to Backend Directory

```bash
cd /Users/sharminsirajudeen/Projects/brane_v2/backend
```

**Why this directory?**
- `fly.toml` is here
- `Dockerfile` is here
- Fly.io needs to be run from where these files are located

---

### Step 2: Launch Fly.io Application

```bash
fly launch --no-deploy
```

**What this does:**
- Reads `fly.toml` configuration
- Creates the app on Fly.io platform
- Allocates resources (VM, networking)
- **Does NOT deploy yet** (we need to set secrets first)

**Interactive prompts:**

1. **"Choose an app name"**:
   - Press Enter to use `brane-backend` (from fly.toml)
   - Or type a custom name if `brane-backend` is taken

2. **"Choose a region for deployment"**:
   - Press Enter to use `ord` (Chicago)
   - Or select another region (choose same as Neon database)

3. **"Would you like to set up a Postgresql database?"**:
   - **Choose NO** (we're using Neon, not Fly Postgres)

4. **"Would you like to set up an Upstash Redis database?"**:
   - **Choose NO** (optional for now, can add later for caching)

5. **"Would you like to deploy now?"**:
   - **Choose NO** (we need to set secrets first)

**Expected output:**
```
Your app is ready! Deploy with `flyctl deploy`
```

---

### Step 3: Set Environment Secrets

**CRITICAL: Never commit secrets to Git!**

Fly.io stores secrets encrypted and injects them as environment variables at runtime.

#### Required Secrets

**1. Database Connection String**

```bash
# Use your Neon connection string from Step 3 above
fly secrets set DATABASE_URL="postgresql://user:password@host/database?sslmode=require"
```

**Example:**
```bash
fly secrets set DATABASE_URL="postgresql://brane_user:abc123xyz@ep-cool-wind-123456.us-east-2.aws.neon.tech/brane_prod?sslmode=require"
```

**Why needed?**
- Connects to Neon PostgreSQL
- Used by Alembic for migrations
- Required for FastAPI app to store users, neurons, chats

---

**2. JWT Secret Key**

```bash
# Generate a secure random key (32+ characters)
fly secrets set JWT_SECRET_KEY="$(openssl rand -hex 32)"
```

**What this does:**
- `openssl rand -hex 32`: Generates 64-character random hex string
- Used to sign JWT authentication tokens
- **Must remain secret** (anyone with this can forge tokens)

**Manual alternative (if openssl not available):**
```bash
fly secrets set JWT_SECRET_KEY="your-super-secret-random-string-min-32-characters-long"
```

---

**3. Encryption Key**

```bash
# Generate another secure random key (32+ characters)
fly secrets set ENCRYPTION_KEY="$(openssl rand -hex 32)"
```

**Why needed?**
- Encrypts sensitive data in database (API keys, credentials)
- Used by BRANE's privacy features
- **Must remain secret** (decrypts user data)

---

**4. CORS Origins**

```bash
# Replace with your actual frontend URL(s)
fly secrets set CORS_ORIGINS="https://yourusername.github.io,https://brane-frontend.vercel.app"
```

**Why needed?**
- Controls which domains can make API requests
- Prevents unauthorized access from other websites
- Add all frontend URLs (GitHub Pages, Vercel, custom domains)

**Examples:**
- GitHub Pages: `https://yourusername.github.io/brane`
- Vercel: `https://brane-frontend.vercel.app`
- Custom domain: `https://brane.yourdomain.com`
- Local dev: `http://localhost:5173` (add for testing)

**Multiple origins:**
```bash
fly secrets set CORS_ORIGINS="https://yourdomain.com,https://app.yourdomain.com,http://localhost:5173"
```

---

#### Optional Secrets (Add if Needed)

**5. Google OAuth (if using Google login)**

```bash
fly secrets set GOOGLE_CLIENT_ID="123456789-abc.apps.googleusercontent.com"
fly secrets set GOOGLE_CLIENT_SECRET="GOCSPX-your-secret-here"
fly secrets set GOOGLE_REDIRECT_URI="https://brane-backend.fly.dev/api/auth/callback"
```

**How to get Google OAuth credentials:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or use existing)
3. Enable "Google+ API"
4. Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client ID"
5. Application type: "Web application"
6. Authorized redirect URIs: `https://brane-backend.fly.dev/api/auth/callback`
7. Copy Client ID and Client Secret

---

**6. LLM API Keys (if using external LLMs)**

```bash
# OpenAI (for GPT models)
fly secrets set OPENAI_API_KEY="sk-your-openai-key-here"

# Anthropic (for Claude models)
fly secrets set ANTHROPIC_API_KEY="sk-ant-your-anthropic-key-here"
```

**Why optional?**
- Users can configure their own API keys via BRANE UI
- Set these only if you want server-side defaults

---

**7. Redis (if using caching)**

```bash
# Upstash Redis (free tier available)
fly secrets set REDIS_URL="redis://default:password@host:port"
```

**How to get Redis:**
1. Go to [Upstash](https://upstash.com/)
2. Create free Redis database
3. Copy connection URL (starts with `redis://` or `rediss://`)

**Why use Redis?**
- Cache LLM responses (reduce API costs)
- Rate limiting (prevent abuse)
- Session storage (faster auth)

---

### Step 4: Verify Secrets

```bash
fly secrets list
```

**Expected output:**
```
NAME              DIGEST          CREATED AT
CORS_ORIGINS      abc123def...    1m ago
DATABASE_URL      def456ghi...    2m ago
ENCRYPTION_KEY    ghi789jkl...    2m ago
JWT_SECRET_KEY    jkl012mno...    3m ago
```

**Note:** Digests are shown, not actual values (for security)

**To reveal a secret (use carefully, never share output):**
```bash
fly secrets list --reveal
```

---

### Step 5: Deploy to Fly.io

```bash
fly deploy
```

**What happens:**

1. **Build Phase (3-5 minutes):**
   - Uploads code to Fly.io builders
   - Builds Docker image using multi-stage Dockerfile
   - Optimizes layers for caching
   - Pushes image to Fly.io registry

   **Console output:**
   ```
   ==> Building image
   --> Building with Dockerfile
   [builder] Step 1/15: FROM python:3.10-slim AS builder
   [builder] Step 2/15: WORKDIR /app
   ...
   [builder] Successfully built abc123def456
   ==> Pushing image to registry
   ```

2. **Release Phase (30 seconds):**
   - Creates new VM from image
   - Stops old VM (if exists)
   - Configures networking and health checks

   **Console output:**
   ```
   ==> Creating release
   --> Release v1 created
   ```

3. **Health Check Phase (30-60 seconds):**
   - Runs database migrations (`alembic upgrade head`)
   - Starts FastAPI server
   - Waits for `/health` endpoint to respond

   **Console output:**
   ```
   --> Monitoring deployment
   1 desired, 1 placed, 1 healthy, 0 unhealthy [health checks: 1 total, 1 passing]
   --> v0 deployed successfully
   ```

**Total deployment time:** 5-7 minutes

---

### Step 6: Verify Deployment

**1. Check app status:**
```bash
fly status
```

**Expected output:**
```
App
  Name     = brane-backend
  Owner    = your-org
  Version  = v0
  Status   = running
  Hostname = brane-backend.fly.dev

Instances
ID       PROCESS VERSION REGION DESIRED STATUS  HEALTH CHECKS      RESTARTS CREATED
abc123   app     v0      ord    run     running 1 total, 1 passing 0        1m ago
```

**2. Test the health endpoint:**
```bash
curl https://brane-backend.fly.dev/health
```

**Expected response:**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "environment": "production"
}
```

**3. Test the readiness endpoint (database check):**
```bash
curl https://brane-backend.fly.dev/health/ready
```

**Expected response:**
```json
{
  "status": "ready",
  "database": "connected",
  "version": "0.1.0"
}
```

**If database fails:**
```json
{
  "status": "not_ready",
  "database": "disconnected",
  "error": "connection refused"
}
```
→ Check DATABASE_URL secret is correct

**4. View live logs:**
```bash
fly logs
```

**Expected log output:**
```json
{"timestamp": "2025-10-07T10:30:00Z", "level": "INFO", "module": "main", "message": "🚀 Starting BRANE backend..."}
{"timestamp": "2025-10-07T10:30:01Z", "level": "INFO", "module": "alembic", "message": "Running migrations..."}
{"timestamp": "2025-10-07T10:30:03Z", "level": "INFO", "module": "main", "message": "✅ Database initialized"}
{"timestamp": "2025-10-07T10:30:04Z", "level": "INFO", "module": "main", "message": "✅ Storage directories created"}
{"timestamp": "2025-10-07T10:30:05Z", "level": "INFO", "module": "main", "message": "🧠 BRANE v0.1.0 ready on 0.0.0.0:8000"}
```

**5. Open in browser:**
```bash
fly open
```

Opens: `https://brane-backend.fly.dev`

**Expected response:**
```json
{
  "name": "BRANE",
  "version": "0.1.0",
  "description": "Privacy-first AI agent orchestration platform",
  "docs": null
}
```

---

## Post-Deployment Configuration

### 1. Update Frontend Configuration

Update your frontend to use the Fly.io backend URL:

**React/Vue/Svelte config:**
```javascript
// .env or config file
VITE_API_BASE_URL=https://brane-backend.fly.dev
```

**Next.js config:**
```javascript
// next.config.js
module.exports = {
  env: {
    API_BASE_URL: 'https://brane-backend.fly.dev',
  },
}
```

---

### 2. Configure Custom Domain (Optional)

**Why?** Professional URL instead of `brane-backend.fly.dev`

**Steps:**

1. **Add certificate:**
   ```bash
   fly certs add api.yourdomain.com
   ```

2. **Add DNS record:**
   - Type: `CNAME`
   - Name: `api` (or `brane-api`)
   - Value: `brane-backend.fly.dev`
   - TTL: 300 (5 minutes)

3. **Verify certificate:**
   ```bash
   fly certs show api.yourdomain.com
   ```

4. **Update CORS and OAuth redirect URIs** to use new domain

---

### 3. Set Up Monitoring (Optional)

**View metrics dashboard:**
```bash
fly dashboard
```

**Set up alerts:**
```bash
fly alerts
```

**Monitor resource usage:**
```bash
fly metrics
```

---

## Troubleshooting

### Problem: Deployment Fails at Build Stage

**Error:** `ERROR: failed to solve: process "/bin/sh -c pip install ..." did not complete successfully`

**Solutions:**

1. **Check requirements.txt compatibility:**
   ```bash
   # Test locally in Docker
   docker build -t brane-test -f Dockerfile .
   ```

2. **Add missing system dependencies to Dockerfile:**
   ```dockerfile
   RUN apt-get update && apt-get install -y \
       your-missing-package \
       && rm -rf /var/lib/apt/lists/*
   ```

3. **Check Python version compatibility** (Dockerfile uses 3.10, requirements may need 3.11+)

---

### Problem: Health Checks Fail

**Error:** `Health check on port 8000 has failed`

**Debug steps:**

1. **Check logs for errors:**
   ```bash
   fly logs
   ```

2. **SSH into the VM:**
   ```bash
   fly ssh console

   # Inside VM
   curl http://localhost:8000/health
   cat /app/logs/error.log  # if logging to file
   ```

3. **Common causes:**
   - Port mismatch (ensure `PORT=8000` in fly.toml and Dockerfile)
   - Database connection fails (check DATABASE_URL)
   - Migrations fail (check Alembic configuration)

---

### Problem: Database Connection Fails

**Error:** `sqlalchemy.exc.OperationalError: could not connect to server`

**Solutions:**

1. **Verify DATABASE_URL secret:**
   ```bash
   fly secrets list
   fly secrets set DATABASE_URL="postgresql://..."  # Re-set if wrong
   ```

2. **Check Neon database is running:**
   - Go to [Neon Console](https://console.neon.tech/)
   - Ensure database is active (not suspended)
   - Check connection string is correct

3. **Test connection from local machine:**
   ```bash
   psql "postgresql://user:password@host/database?sslmode=require"
   ```

4. **Check SSL mode:**
   - Neon requires `?sslmode=require` at end of connection string
   - Example: `postgresql://user:pass@host/db?sslmode=require`

---

### Problem: CORS Errors in Frontend

**Error:** `Access to fetch at 'https://brane-backend.fly.dev' from origin 'https://yourdomain.com' has been blocked by CORS policy`

**Solutions:**

1. **Update CORS_ORIGINS secret:**
   ```bash
   fly secrets set CORS_ORIGINS="https://yourdomain.com,https://app.yourdomain.com"
   ```

2. **Re-deploy to apply changes:**
   ```bash
   fly deploy
   ```

3. **Test CORS headers:**
   ```bash
   curl -I -X OPTIONS https://brane-backend.fly.dev/api/auth/login \
     -H "Origin: https://yourdomain.com" \
     -H "Access-Control-Request-Method: POST"
   ```

   **Expected response:**
   ```
   access-control-allow-origin: https://yourdomain.com
   access-control-allow-methods: *
   access-control-allow-headers: *
   ```

---

### Problem: App Crashes or Restarts Frequently

**Error:** `Instance restarted due to out of memory`

**Solutions:**

1. **Increase VM memory:**
   ```bash
   # Edit fly.toml
   [[vm]]
   size = "shared-cpu-1x"
   memory = "1024mb"  # Increase from 512mb

   # Deploy
   fly deploy
   ```

2. **Check for memory leaks in logs:**
   ```bash
   fly logs | grep -i "memory"
   ```

3. **Optimize model loading:**
   - Pre-download sentence-transformers model in Dockerfile
   - Use smaller embedding models
   - Add model caching with Redis

---

## Useful Fly.io Commands

### App Management

```bash
# View app info
fly status

# View app configuration
fly config show

# Scale VM count
fly scale count 1  # 1 instance (free tier)

# Scale VM size
fly scale vm shared-cpu-2x --memory 1024  # Upgrade resources

# Restart app
fly apps restart

# Destroy app (careful!)
fly apps destroy brane-backend
```

### Logs & Debugging

```bash
# Stream live logs
fly logs

# View last 100 log lines
fly logs --lines 100

# Filter logs by instance
fly logs --instance abc123

# SSH into VM
fly ssh console

# Run command in VM
fly ssh console --command "cat /app/main.py"
```

### Secrets Management

```bash
# List secrets
fly secrets list

# Set secret
fly secrets set KEY=value

# Remove secret
fly secrets unset KEY

# Set multiple secrets from file
fly secrets import < secrets.env
```

### Database Access

```bash
# Connect to Neon database from local machine
fly proxy 5432 -a brane-backend  # Proxy to local port
psql "postgresql://user:password@localhost:5432/database"
```

### Deployment

```bash
# Deploy with specific Dockerfile
fly deploy --dockerfile Dockerfile.production

# Deploy without cache (fresh build)
fly deploy --no-cache

# Deploy with remote builder (faster on slow internet)
fly deploy --remote-only
```

---

## Cost Optimization (Free Tier)

**Fly.io Free Tier Limits:**
- 3 shared-cpu-1x VMs (256MB RAM each)
- 3GB persistent storage
- 160GB outbound bandwidth per month

**BRANE Backend Usage:**
- 1 VM (shared-cpu-1x, 512MB RAM) = **Within free tier**
- Auto-stop when idle = **$0/month when no traffic**
- Auto-start on request = **5-10s cold start delay**

**Tips to stay in free tier:**

1. **Use Neon for database** (not Fly Postgres - saves 1 VM)
2. **Use Upstash for Redis** (free tier available)
3. **Enable auto-stop** (already configured in fly.toml)
4. **Set `min_machines_running = 0`** (scale to zero)

**Expected monthly cost:** **$0** (free tier) for low traffic (<10k requests/month)

---

## Next Steps

1. ✅ **Deploy backend** (you just did this!)
2. 🌐 **Update frontend** to use `https://brane-backend.fly.dev`
3. 🔐 **Set up Google OAuth** (optional)
4. 📊 **Monitor metrics** in Fly.io dashboard
5. 🚀 **Deploy frontend** (GitHub Pages, Vercel, Netlify)
6. 🎉 **BRANE is live!**

---

## Support & Resources

- **Fly.io Docs:** https://fly.io/docs/
- **Fly.io Community:** https://community.fly.io/
- **Neon Docs:** https://neon.tech/docs/
- **BRANE Issues:** https://github.com/yourusername/brane/issues

---

**Deployment complete! Your BRANE backend is now running on Fly.io with Neon PostgreSQL.** 🎉
