# BRANE Backend - Fly.io Environment Variables Reference

**Complete list of environment variables for Fly.io deployment**

---

## How to Set Variables

### Public Variables (Non-Sensitive)
Set in `fly.toml` under `[env]` section:
```toml
[env]
  APP_NAME = "BRANE"
  DEBUG = "false"
```

### Secret Variables (Sensitive)
Set using Fly.io CLI (encrypted storage):
```bash
fly secrets set KEY="value"
```

**NEVER put secrets in fly.toml or commit them to Git!**

---

## Required Secrets (Must Set Before Deploy)

### 1. DATABASE_URL
**Description:** PostgreSQL connection string for Neon database

**Format:**
```bash
postgresql://[user]:[password]@[host]/[database]?sslmode=require
```

**Example:**
```bash
fly secrets set DATABASE_URL="postgresql://brane_user:abc123xyz@ep-cool-wind-123456.us-east-2.aws.neon.tech/brane_prod?sslmode=require"
```

**How to get:**
1. Go to [Neon Console](https://console.neon.tech/)
2. Create project and database
3. Copy "Connection string" from dashboard
4. Ensure it ends with `?sslmode=require`

**Why required:**
- Stores users, neurons, chats, RAG data
- Used by Alembic for database migrations
- App will crash on startup if missing or invalid

---

### 2. JWT_SECRET_KEY
**Description:** Secret key for signing JWT authentication tokens

**Format:** Random string (minimum 32 characters)

**Generate securely:**
```bash
# Recommended: Use openssl to generate random hex string
fly secrets set JWT_SECRET_KEY="$(openssl rand -hex 32)"
```

**Manual alternative:**
```bash
fly secrets set JWT_SECRET_KEY="your-super-secret-random-string-at-least-32-chars-long"
```

**Why required:**
- Signs JWT tokens for user authentication
- Anyone with this key can forge valid tokens (huge security risk!)
- Must be kept secret and never exposed

**Security notes:**
- Use cryptographically random value
- Never reuse across environments (dev/staging/prod)
- Rotate periodically (invalidates all existing tokens)

---

### 3. ENCRYPTION_KEY
**Description:** Secret key for encrypting sensitive data in database

**Format:** Random string (minimum 32 characters)

**Generate securely:**
```bash
# Recommended: Use openssl to generate random hex string
fly secrets set ENCRYPTION_KEY="$(openssl rand -hex 32)"
```

**Manual alternative:**
```bash
fly secrets set ENCRYPTION_KEY="another-different-random-string-min-32-chars"
```

**Why required:**
- Encrypts user API keys, credentials, private data
- Used by BRANE's privacy tier system
- Losing this key = permanent data loss (cannot decrypt)

**Security notes:**
- Different from JWT_SECRET_KEY (never reuse!)
- Back up securely (e.g., password manager)
- If lost, encrypted data is unrecoverable

---

### 4. CORS_ORIGINS
**Description:** Comma-separated list of allowed frontend origins

**Format:**
```bash
https://domain1.com,https://domain2.com,http://localhost:5173
```

**Example:**
```bash
fly secrets set CORS_ORIGINS="https://yourusername.github.io,https://brane-app.vercel.app,http://localhost:5173"
```

**Why required:**
- Prevents unauthorized websites from accessing your API
- Browser enforces Same-Origin Policy (CORS prevents it)
- Must include all frontend URLs that need API access

**Common origins:**
- GitHub Pages: `https://yourusername.github.io/brane`
- Vercel: `https://brane-frontend.vercel.app`
- Netlify: `https://brane-app.netlify.app`
- Custom domain: `https://app.yourdomain.com`
- Local dev: `http://localhost:5173` (Vite default)
- Local dev: `http://localhost:3000` (Next.js default)

**Wildcards NOT supported** - must list each origin explicitly

---

## Optional Secrets (Set If Using Feature)

### 5. GOOGLE_CLIENT_ID
**Description:** Google OAuth 2.0 Client ID for "Sign in with Google"

**Format:** `123456789-abc123def456.apps.googleusercontent.com`

**How to get:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create project → Enable "Google+ API"
3. Credentials → Create OAuth 2.0 Client ID
4. Application type: "Web application"
5. Authorized redirect URIs: `https://brane-backend.fly.dev/api/auth/callback`
6. Copy Client ID

**Set secret:**
```bash
fly secrets set GOOGLE_CLIENT_ID="123456789-abc123def456.apps.googleusercontent.com"
```

**Why optional:**
- Only needed if using Google OAuth login
- Users can still register with email/password
- Improves UX (one-click login)

---

### 6. GOOGLE_CLIENT_SECRET
**Description:** Google OAuth 2.0 Client Secret (paired with Client ID)

**Format:** `GOCSPX-xxxxxxxxxxxxxxxxxxxxx`

**How to get:**
- Same as GOOGLE_CLIENT_ID above
- Copy "Client Secret" from Google Cloud Console

**Set secret:**
```bash
fly secrets set GOOGLE_CLIENT_SECRET="GOCSPX-your-secret-here"
```

**Security notes:**
- Keep secret! Never commit to Git or share publicly
- Rotate periodically for security

---

### 7. GOOGLE_REDIRECT_URI
**Description:** OAuth callback URL where Google redirects after login

**Format:** `https://[your-app-domain]/api/auth/callback`

**Set secret:**
```bash
fly secrets set GOOGLE_REDIRECT_URI="https://brane-backend.fly.dev/api/auth/callback"
```

**Important:**
- Must match exactly what's configured in Google Cloud Console
- Must use HTTPS in production (not HTTP)
- If using custom domain, update this to match

---

### 8. OPENAI_API_KEY
**Description:** OpenAI API key for GPT-3.5/GPT-4 models

**Format:** `sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

**Set secret:**
```bash
fly secrets set OPENAI_API_KEY="sk-your-openai-api-key-here"
```

**Why optional:**
- Users can configure their own API keys via BRANE UI
- Set this only if you want a server-wide default key
- Useful for testing or shared team access

**How to get:**
1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Sign up/login
3. API Keys → Create new secret key
4. Copy key (only shown once!)

---

### 9. ANTHROPIC_API_KEY
**Description:** Anthropic API key for Claude models

**Format:** `sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

**Set secret:**
```bash
fly secrets set ANTHROPIC_API_KEY="sk-ant-your-anthropic-api-key-here"
```

**Why optional:**
- Same as OPENAI_API_KEY (user-configurable)
- Set for server-wide default access to Claude

**How to get:**
1. Go to [Anthropic Console](https://console.anthropic.com/)
2. Sign up/login
3. API Keys → Create key
4. Copy key

---

### 10. REDIS_URL
**Description:** Redis connection string for caching and rate limiting

**Format:**
```bash
redis://[user]:[password]@[host]:[port]
# Or with TLS:
rediss://[user]:[password]@[host]:[port]
```

**Set secret:**
```bash
fly secrets set REDIS_URL="redis://default:abc123xyz@fly-brane-redis.upstash.io:6379"
```

**Why optional:**
- Not required for basic functionality
- Improves performance (caches LLM responses, reduces API costs)
- Enables rate limiting (prevents abuse)
- Stores session data (faster auth)

**How to get (Upstash free tier):**
1. Go to [Upstash](https://upstash.com/)
2. Create account
3. Create Redis database (free tier: 10k requests/day)
4. Copy connection URL

---

## Public Environment Variables (Already Set in fly.toml)

These are set in `fly.toml` `[env]` section - no action needed:

| Variable | Value | Purpose |
|----------|-------|---------|
| `APP_NAME` | `"BRANE"` | Application name (used in logs, API responses) |
| `APP_VERSION` | `"0.1.0"` | Version number (returned in /health endpoint) |
| `ENVIRONMENT` | `"production"` | Environment identifier (enables production mode) |
| `DEBUG` | `"false"` | Debug mode (disabled in prod for security) |
| `HOST` | `"0.0.0.0"` | Server bind address (listen on all interfaces) |
| `PORT` | `"8000"` | Server port (matches fly.toml internal_port) |
| `STORAGE_PATH` | `"/app/storage"` | File storage directory (ephemeral on free tier) |
| `AXON_STORAGE_PATH` | `"/app/storage/axon"` | Agent data directory |
| `MODELS_PATH` | `"/app/storage/models"` | ML models cache directory |
| `OLLAMA_BASE_URL` | `"http://localhost:11434"` | Ollama URL (not used on Fly.io) |
| `LOG_LEVEL` | `"INFO"` | Logging verbosity (DEBUG/INFO/WARNING/ERROR) |
| `LOG_FORMAT` | `"json"` | Log format (json for structured logging) |
| `DEFAULT_EMBEDDING_MODEL` | `"sentence-transformers/all-MiniLM-L6-v2"` | Text embedding model for RAG |
| `DEFAULT_CONTEXT_WINDOW` | `"4096"` | Max tokens for LLM context |
| `DEFAULT_MAX_TOKENS` | `"2048"` | Max tokens in LLM response |
| `RATE_LIMIT_PER_MINUTE` | `"60"` | API rate limit per user/IP |

**To override any of these:**
```bash
fly secrets set VARIABLE_NAME="new_value"
# Secrets take precedence over [env] values
```

---

## Advanced Configuration (Rarely Needed)

### JWT_ALGORITHM
**Description:** Algorithm for JWT signing

**Default:** `"HS256"` (already set in code)

**Override:**
```bash
fly secrets set JWT_ALGORITHM="HS512"
# Options: HS256, HS512, RS256, ES256
```

---

### JWT_EXPIRE_MINUTES
**Description:** JWT token expiration time (in minutes)

**Default:** `1440` (24 hours)

**Override:**
```bash
fly secrets set JWT_EXPIRE_MINUTES="720"  # 12 hours
fly secrets set JWT_EXPIRE_MINUTES="10080"  # 7 days
```

---

### DEFAULT_PRIVACY_TIER
**Description:** Default privacy tier for new neurons

**Values:**
- `0` = Local only (no external APIs)
- `1` = Private cloud (encrypted, user-controlled)
- `2` = Public cloud (OpenAI, Anthropic, etc.)

**Default:** `0` (most private)

**Override:**
```bash
fly secrets set DEFAULT_PRIVACY_TIER="1"
```

---

## Environment Variables Checklist

**Before first deployment, ensure you have:**

- [x] `DATABASE_URL` (Neon PostgreSQL connection string)
- [x] `JWT_SECRET_KEY` (generated with openssl rand -hex 32)
- [x] `ENCRYPTION_KEY` (generated with openssl rand -hex 32)
- [x] `CORS_ORIGINS` (your frontend URLs)

**Optional (add as needed):**

- [ ] `GOOGLE_CLIENT_ID` (if using Google OAuth)
- [ ] `GOOGLE_CLIENT_SECRET` (if using Google OAuth)
- [ ] `GOOGLE_REDIRECT_URI` (if using Google OAuth)
- [ ] `OPENAI_API_KEY` (if using OpenAI models server-wide)
- [ ] `ANTHROPIC_API_KEY` (if using Claude models server-wide)
- [ ] `REDIS_URL` (if using caching/rate limiting)

---

## Verify Configuration

**List all set secrets:**
```bash
fly secrets list
```

**Expected output (before deploy):**
```
NAME              DIGEST          CREATED AT
CORS_ORIGINS      abc123def...    1m ago
DATABASE_URL      def456ghi...    2m ago
ENCRYPTION_KEY    ghi789jkl...    2m ago
JWT_SECRET_KEY    jkl012mno...    3m ago
```

**Test configuration after deploy:**
```bash
# Check health endpoint
curl https://brane-backend.fly.dev/health

# Check database connection
curl https://brane-backend.fly.dev/health/ready

# Check CORS (replace with your frontend URL)
curl -I -X OPTIONS https://brane-backend.fly.dev/api/auth/login \
  -H "Origin: https://yourdomain.com" \
  -H "Access-Control-Request-Method: POST"
```

---

## Security Best Practices

1. **Never commit secrets to Git**
   - Use `.env` only for local development
   - Add `.env` to `.gitignore`
   - Use `fly secrets set` for production

2. **Use strong random values**
   - Generate with `openssl rand -hex 32`
   - Never use predictable values
   - Don't reuse keys across environments

3. **Rotate secrets periodically**
   - JWT_SECRET_KEY: Every 3-6 months (invalidates all tokens)
   - ENCRYPTION_KEY: Only if compromised (breaks encrypted data!)
   - API keys: As recommended by provider

4. **Back up critical secrets**
   - Store ENCRYPTION_KEY in password manager
   - Losing it = permanent data loss
   - Document where secrets are stored

5. **Use separate keys per environment**
   - Dev: Different DATABASE_URL, JWT_SECRET_KEY, etc.
   - Staging: Different keys
   - Production: Unique keys
   - Prevents cross-contamination

---

## Troubleshooting

### Problem: "Secret not found" error in logs

**Cause:** Required secret not set in Fly.io

**Solution:**
```bash
fly secrets set MISSING_SECRET="value"
fly deploy  # Restart to pick up new secret
```

---

### Problem: "Invalid JWT secret" or token errors

**Cause:** JWT_SECRET_KEY too short or missing

**Solution:**
```bash
fly secrets set JWT_SECRET_KEY="$(openssl rand -hex 32)"
fly deploy
```

---

### Problem: CORS errors in frontend

**Cause:** CORS_ORIGINS doesn't include frontend URL

**Solution:**
```bash
fly secrets set CORS_ORIGINS="https://yourfrontend.com,http://localhost:5173"
fly deploy
```

---

### Problem: Database connection fails

**Cause:** DATABASE_URL invalid or missing `?sslmode=require`

**Solution:**
```bash
# Ensure connection string ends with ?sslmode=require
fly secrets set DATABASE_URL="postgresql://user:pass@host/db?sslmode=require"
fly deploy
```

---

**Reference complete! Use this guide to configure all environment variables for BRANE on Fly.io.**
