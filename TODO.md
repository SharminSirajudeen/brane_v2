# 🎯 BRANE - Active Tasks

**Last Updated**: October 7, 2025 - 22:30
**Current Focus**: Fix critical issues → Deploy → Test

---

## 🔥 URGENT: Critical Fixes (DO FIRST)

### 1. Fix 5 Critical Security/Deployment Issues
**Priority**: 🔴 BLOCKING DEPLOYMENT
**Time**: 30 mins
**Where**: Local machine

```bash
# Generate new secrets
python3 -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(32))"
python3 -c "import secrets; print('ENCRYPTION_KEY=' + secrets.token_urlsafe(32))"
# Save these in password manager!
```

**Tasks**:
- [ ] 🔴 Regenerate JWT_SECRET_KEY and ENCRYPTION_KEY (current ones exposed in git)
- [ ] 🔴 Fix Dockerfile HEALTHCHECK (line 31) - replace `requests` with `urllib`
- [ ] 🟡 Remove duplicate httpx dependency (requirements.txt line 50)
- [ ] 🟡 Fix SSH tool security (ssh_tool.py line 120) - change `AutoAddPolicy()` to `RejectPolicy()`
- [ ] 🟡 Add missing `paramiko==3.4.0` to requirements.txt

**See**: STATUS.md lines 311-348 for detailed instructions

---

## 🚀 NEXT: Deploy Backend (After Critical Fixes)

### 2. Deploy to Fly.io + Neon PostgreSQL
**Priority**: 🔴 HIGH
**Time**: 20 mins
**Where**: GitHub Codespace
**Prerequisites**: Critical fixes complete ✅

**Setup Steps**:
1. [ ] Create Neon PostgreSQL database (https://console.neon.tech/)
2. [ ] Install Fly.io CLI in Codespace
3. [ ] Launch Fly.io app: `fly launch --name brane-backend --region ord --no-deploy`
4. [ ] Set secrets (DATABASE_URL, JWT_SECRET_KEY, ENCRYPTION_KEY, Google OAuth)
5. [ ] Deploy: `fly deploy`
6. [ ] Test: `curl https://brane-backend.fly.dev/health`
7. [ ] Update Google OAuth redirect URI with Fly.io URL

**See**: backend/FLY_QUICK_START.md for complete guide

---

## 🧪 THEN: Testing & Integration

### 3. End-to-End Testing
**Priority**: 🟡 HIGH
**Time**: 1-2 hours
**Where**: Codespace (backend) + Local (frontend)

**Test Flow**:
- [ ] Start backend in Codespace
- [ ] Start frontend locally (`npm run dev`)
- [ ] Test Google OAuth login
- [ ] Create a Neuron
- [ ] Chat with streaming
- [ ] Upload documents (RAG)
- [ ] Switch models in Settings
- [ ] Verify memory consolidation

### 4. Fix Known Bugs
**Priority**: 🟡 MEDIUM
**Time**: 2-3 hours

- [ ] 🔴 Chat Streaming Authentication (EventSource JWT issue)
- [ ] 🟡 Settings Test Connection (add backend endpoint)
- [ ] 🟡 Build RAG Upload UI
- [ ] 🟡 Build Session Management UI
- [ ] ⚪ Add Error Boundaries
- [ ] ⚪ Add API Retry Logic

**See**: STATUS.md lines 349-360 for bug details

---

## 🎨 FUTURE: Feature Enhancements

### 5. Additional Tools
- [ ] Database tool (SQL query execution)
- [ ] Cloud tool (AWS/GCP/Azure integration)
- [ ] IoT tool (smart home, hardware control)
- [ ] Advanced SSH tool (multiple connections, tunneling)

### 6. Desktop App (Electron)
- [ ] Set up Electron boilerplate
- [ ] Embed React frontend
- [ ] Add local backend auto-start
- [ ] Package for macOS/Windows/Linux

### 7. Enterprise Features
- [ ] Multi-user collaboration
- [ ] Team neuron sharing
- [ ] SAML/SSO authentication
- [ ] Advanced audit logging dashboard

---

## 📋 Quick Commands

### Local Development (Frontend Only)
```bash
cd frontend
npm run dev
# http://localhost:5173
```

### Codespace Development (Backend)
```bash
# Open: https://animated-halibut-vj4vj54p4vcwg9j.github.dev
cd backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env with API keys
alembic upgrade head
python main.py
# http://localhost:8000
```

### Production Build (Frontend)
```bash
cd frontend
npm run build
npm run deploy  # Deploy to GitHub Pages
```

### Git Workflow
```bash
git pull origin main
# Make changes...
git add .
git commit -m "[AREA] Description"
git push origin main
```

---

## ✅ Completed Recently

- ✅ Tool system (11,305 lines - file ops, shell, HTTP)
- ✅ Frontend UI complete (7,085 lines)
- ✅ Backend complete (4,900 lines)
- ✅ Landing page deployed
- ✅ Memory consolidation system
- ✅ Settings page (model switching)
- ✅ Fly.io deployment config
- ✅ Code quality review
- ✅ Google OAuth setup
- ✅ Git cleanup (removed venv/db)

---

## 🎯 Success Criteria

**MVP Launch Checklist**:
- [ ] All 5 critical fixes deployed
- [ ] Backend live on Fly.io
- [ ] Frontend deployed to GitHub Pages
- [ ] End-to-end testing complete
- [ ] Google OAuth working
- [ ] At least one demo Neuron working
- [ ] Documentation updated
- [ ] Landing page "Try BRANE" button works

**When done, users can**:
1. Visit landing page
2. Click "Try BRANE"
3. Login with Google
4. Create a Neuron
5. Chat with AI
6. Upload documents
7. Switch models
8. Everything works end-to-end!

---

**This is the ONLY TODO file - single source of truth for active tasks.**

*See STATUS.md for project status, architecture, and completed work.*
