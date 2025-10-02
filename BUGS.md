# 🐛 BRANE Bug Tracker

**Purpose**: Track bugs discovered during testing
**Usage**: Both sessions add bugs here, assign to backend/frontend session

---

## 📋 Bug Status Legend

- 🔴 **Critical**: Blocks core functionality
- 🟡 **High**: Major feature broken
- 🟢 **Medium**: Minor feature issue
- ⚪ **Low**: Cosmetic or edge case

---

## 🔴 Critical Bugs (P0)

### Bug #1: Backend Missing .env File
- **Status**: Open
- **Discovered by**: Architecture analysis
- **Priority**: 🔴 Critical
- **Assigned to**: Backend session
- **Symptom**: Backend crashes on startup with missing environment variables
- **Location**: `backend/.env` (file doesn't exist)
- **Impact**: Backend cannot start
- **Fix**:
  1. Copy `.env.example` to `.env`
  2. Fill in required values (DATABASE_URL, JWT_SECRET, etc.)
- **ETA**: 30 minutes
- **Notes**: Template exists, just needs actual values

---

### Bug #2: Database Model Error - 'metadata' Reserved Name
- **Status**: ✅ Fixed
- **Discovered by**: Backend session (during alembic upgrade)
- **Priority**: 🔴 Critical
- **Assigned to**: Backend session
- **Symptom**: SQLAlchemy error: "Attribute name 'metadata' is reserved when using the Declarative API"
- **Location**: `backend/db/models.py:200` (Document class)
- **Impact**: Database migrations fail, backend cannot start
- **Root Cause**: Document model has column named `metadata` which conflicts with SQLAlchemy's reserved attribute
- **Fix Applied**: Renamed attribute to `doc_metadata` while keeping column name as "metadata"
  - Changed: `metadata = Column(JSON...)`
  - To: `doc_metadata = Column("metadata", JSON...)`
- **Additional Fixes**:
  - Fixed `DEFAULT_PRIVACY_TIER` type mismatch (Literal to int with validation)
  - Installed missing `greenlet` dependency for async SQLAlchemy
- **Fixed in commit**: [Next commit]

---

### Bug #3: Chat Streaming Authentication Fails
- **Status**: Open
- **Discovered by**: Code review (never tested)
- **Priority**: 🔴 Critical
- **Assigned to**: Backend session (or Frontend session if backend fix needed)
- **Symptom**: EventSource connection fails with 401 Unauthorized
- **Location**: `frontend/src/api/chat.ts:13`
- **Root Cause**: EventSource passes JWT as query param, backend expects `Authorization: Bearer <token>` header
- **Impact**: Chat feature completely broken
- **Fix Options**:
  1. **Backend fix**: Add middleware to accept token from query param
  2. **Frontend fix**: Switch from EventSource to fetch() with manual stream parsing
  3. **Frontend fix**: Use WebSocket instead of SSE
- **Recommendation**: Backend fix is cleaner (EventSource limitation)
- **ETA**: 1-2 hours
- **Code**:
  ```typescript
  // CURRENT (BROKEN):
  const params = new URLSearchParams({
    message,
    ...(token && { token })  // ❌ Backend doesn't check query params
  })

  // FIX OPTION 1 (Backend middleware):
  // Add to backend: Check for token in query params OR Authorization header

  // FIX OPTION 2 (Frontend - use fetch):
  // Replace EventSource with fetch() + ReadableStream
  ```

---

## 🟡 High Priority Bugs (P1)

### Bug #4: Settings Test Connection Doesn't Work
- **Status**: Open
- **Discovered by**: Other session during implementation
- **Priority**: 🟡 High
- **Assigned to**: Backend session
- **Symptom**: "Test Connection" button makes naive fetch to `${baseUrl}/health`, most LLM providers won't respond
- **Location**: `frontend/src/pages/Settings.tsx`
- **Impact**: Users can't test if their model configuration works
- **Fix**: Add backend endpoint `POST /api/neurons/{id}/test-connection`
  - Takes provider/model/api_key config
  - Uses LiteLLM to test actual connection
  - Returns success/failure + error details
- **ETA**: 1 hour
- **Notes**: Frontend UI is ready, just needs backend endpoint

---

### Bug #5: Google OAuth Not Configured
- **Status**: Open (Expected)
- **Priority**: 🟡 High
- **Assigned to**: Backend session
- **Symptom**: OAuth login will fail (no credentials)
- **Location**: `.env` file (GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET)
- **Impact**: Cannot test login flow
- **Fix**:
  1. Go to Google Cloud Console
  2. Create OAuth 2.0 credentials
  3. Add redirect URI: `http://localhost:8000/api/auth/callback`
  4. Add credentials to `.env`
- **ETA**: 15 minutes (if account already exists)
- **Notes**: Can skip for now, test other features first

---

## 🟢 Medium Priority Bugs (P2)

### Bug #6: No RAG Upload UI
- **Status**: In Progress
- **Discovered by**: Architecture analysis
- **Priority**: 🟢 Medium
- **Assigned to**: Frontend session
- **Symptom**: Backend RAG APIs work, but no UI to upload documents
- **Location**: Missing `frontend/src/pages/Documents.tsx`
- **Impact**: Users can't use RAG feature
- **Fix**: Build document upload UI with:
  - Drag-and-drop file upload
  - Document list (grid view)
  - Delete document
  - Filter by neuron
- **ETA**: 2 hours
- **Notes**: Backend APIs are complete, just needs frontend

---

### Bug #7: No Chat Session Management UI
- **Status**: Open
- **Discovered by**: Architecture analysis
- **Priority**: 🟢 Medium
- **Assigned to**: Frontend session
- **Symptom**: Sessions are created in backend, but no UI to list/switch/delete them
- **Location**: `frontend/src/pages/Chat.tsx` (needs session sidebar)
- **Impact**: Users stuck in single session
- **Fix**: Add session management:
  - List all sessions for neuron
  - Switch between sessions
  - Rename session
  - Delete session
- **ETA**: 1 hour
- **Notes**: Backend APIs exist, just needs UI

---

## ⚪ Low Priority Bugs (P3)

### Bug #8: No Error Boundaries
- **Status**: Open
- **Priority**: ⚪ Low
- **Symptom**: React errors crash entire app
- **Location**: `frontend/src/App.tsx` (missing ErrorBoundary)
- **Impact**: Poor user experience on errors
- **Fix**: Add React ErrorBoundary components
- **ETA**: 30 minutes

---

### Bug #9: No Retry Logic
- **Status**: Open
- **Priority**: ⚪ Low
- **Symptom**: Failed API calls don't retry
- **Location**: `frontend/src/api/client.ts`
- **Impact**: Network blips cause failures
- **Fix**: Add axios interceptor with exponential backoff
- **ETA**: 30 minutes

---

## ✅ Fixed Bugs

(None yet - testing hasn't started)

---

## 📊 Bug Summary

- **Total Open**: 9
- **Critical (P0)**: 3
- **High (P1)**: 2
- **Medium (P2)**: 2
- **Low (P3)**: 2
- **Fixed**: 0

---

## 🎯 Bug Fixing Strategy

### Phase 1: Critical Bugs (Must Fix First)
1. Bug #1: Backend .env file
2. Bug #2: Database initialization
3. Bug #3: Chat authentication

**Goal**: Get basic functionality working

### Phase 2: High Priority (Fix Next)
4. Bug #4: Test connection endpoint
5. Bug #5: Google OAuth (optional, can skip initially)

**Goal**: Core features work

### Phase 3: Medium Priority (After Core Works)
6. Bug #6: RAG upload UI
7. Bug #7: Session management UI

**Goal**: Complete feature set

### Phase 4: Polish (Final)
8. Bug #8: Error boundaries
9. Bug #9: Retry logic

**Goal**: Production-ready

---

## 📝 How to Use This File

### Discovering a Bug
1. Add new section under appropriate priority
2. Fill in all fields (status, symptom, location, etc.)
3. Assign to backend or frontend session
4. Update STATUS.md with blocker if critical

### Fixing a Bug
1. Change status to "In Progress"
2. Work on fix
3. Test fix
4. Move to "Fixed Bugs" section
5. Add fix details and commit SHA

### Bug Template
```markdown
### Bug #X: Short Description
- **Status**: Open | In Progress | Fixed
- **Discovered by**: Session name or testing
- **Priority**: 🔴🟡🟢⚪ Critical/High/Medium/Low
- **Assigned to**: Backend session | Frontend session
- **Symptom**: What happens?
- **Location**: File path and line number
- **Impact**: Why does it matter?
- **Fix**: How to fix it?
- **ETA**: Estimated time to fix
- **Notes**: Additional context
```

---

**Keep this file updated! Both sessions should check for new bugs regularly.**

*Last updated: October 2, 2025 - Session start*
