# BRANE Backend - Fly.io Quick Start

**Fast deployment guide - copy/paste commands to get BRANE running on Fly.io in 5 minutes**

---

## Prerequisites (One-Time Setup)

```bash
# 1. Install Fly.io CLI
curl -L https://fly.io/install.sh | sh

# 2. Login to Fly.io
fly auth login

# 3. Create Neon database at https://console.neon.tech/
# Copy the connection string (looks like):
# postgresql://user:password@host/database?sslmode=require
```

---

## Deployment (Copy/Paste These Commands)

```bash
# 1. Navigate to backend directory
cd /Users/sharminsirajudeen/Projects/brane_v2/backend

# 2. Launch app (creates resources, doesn't deploy yet)
fly launch --no-deploy
# → Choose app name (or press Enter for "brane-backend")
# → Choose region (or press Enter for "ord" - Chicago)
# → Say NO to Fly Postgres (we're using Neon)
# → Say NO to Redis (optional, add later)
# → Say NO to deploy now (need to set secrets first)

# 3. Set required secrets
# Replace the values below with your actual credentials

# Database (use your Neon connection string)
fly secrets set DATABASE_URL="postgresql://user:password@host/database?sslmode=require"

# JWT secret (generates secure random key)
fly secrets set JWT_SECRET_KEY="$(openssl rand -hex 32)"

# Encryption key (generates secure random key)
fly secrets set ENCRYPTION_KEY="$(openssl rand -hex 32)"

# CORS origins (replace with your frontend URLs)
fly secrets set CORS_ORIGINS="https://yourusername.github.io,http://localhost:5173"

# 4. Deploy to Fly.io
fly deploy

# 5. Verify deployment
fly status
curl https://brane-backend.fly.dev/health
```

---

## Expected Output

**After `fly launch`:**
```
Your app is ready! Deploy with `flyctl deploy`
```

**After `fly secrets set` (x4):**
```
Secrets are staged for the first deployment
```

**After `fly deploy`:**
```
==> Building image
==> Pushing image to registry
==> Creating release
--> v0 deployed successfully
```

**After `fly status`:**
```
App
  Name     = brane-backend
  Status   = running
  Hostname = brane-backend.fly.dev

Instances
ID       STATUS  HEALTH CHECKS      RESTARTS
abc123   running 1 total, 1 passing 0
```

**After `curl` health check:**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "environment": "production"
}
```

---

## Your Backend is Live! 🎉

**Backend URL:** `https://brane-backend.fly.dev`

**Next steps:**

1. **Update frontend to use backend URL:**
   ```javascript
   // .env or config
   VITE_API_BASE_URL=https://brane-backend.fly.dev
   ```

2. **Test authentication:**
   ```bash
   # Register user
   curl -X POST https://brane-backend.fly.dev/api/auth/register \
     -H "Content-Type: application/json" \
     -d '{"email":"test@example.com","password":"securepass123"}'
   ```

3. **View live logs:**
   ```bash
   fly logs
   ```

---

## Optional: Add Google OAuth

```bash
# Get credentials from https://console.cloud.google.com/
# Create OAuth 2.0 Client ID → Web application
# Redirect URI: https://brane-backend.fly.dev/api/auth/callback

fly secrets set GOOGLE_CLIENT_ID="123456789-xxx.apps.googleusercontent.com"
fly secrets set GOOGLE_CLIENT_SECRET="GOCSPX-xxx"
fly secrets set GOOGLE_REDIRECT_URI="https://brane-backend.fly.dev/api/auth/callback"

fly deploy
```

---

## Optional: Add LLM API Keys

```bash
# OpenAI
fly secrets set OPENAI_API_KEY="sk-xxx"

# Anthropic
fly secrets set ANTHROPIC_API_KEY="sk-ant-xxx"

fly deploy
```

---

## Common Commands

```bash
# View app status
fly status

# Stream logs
fly logs

# SSH into VM
fly ssh console

# List secrets
fly secrets list

# Update secret
fly secrets set KEY="new_value"

# Re-deploy
fly deploy

# Restart app
fly apps restart
```

---

## Troubleshooting

### Deployment fails
```bash
# Check logs
fly logs

# Re-deploy with no cache
fly deploy --no-cache
```

### Health checks fail
```bash
# SSH into VM and debug
fly ssh console
curl http://localhost:8000/health
```

### Database connection fails
```bash
# Verify DATABASE_URL
fly secrets list

# Test from local machine
psql "postgresql://user:password@host/database?sslmode=require"
```

### CORS errors
```bash
# Update CORS_ORIGINS
fly secrets set CORS_ORIGINS="https://yourfrontend.com,http://localhost:5173"
fly deploy
```

---

## Cost

**Free tier:** $0/month
- 1 shared-cpu-1x VM (512MB RAM)
- Auto-stops when idle
- Auto-starts on request (~5s cold start)

**Perfect for:** Development, demos, low-traffic production

---

**Done! Your BRANE backend is deployed and ready to use.**

For detailed docs, see:
- `FLY_DEPLOYMENT_GUIDE.md` - Full deployment guide
- `FLY_ENV_VARS.md` - Environment variables reference
