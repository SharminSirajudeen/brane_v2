# BRANE React Frontend - Architecture & Pseudocode

## Tech Stack Decision

### Core
- **React 18** with TypeScript - Type safety, modern hooks
- **Vite** - Fast dev server, optimized builds
- **React Router v6** - Client-side routing

### State Management
- **Zustand** - Lightweight, simple (NOT Redux - over-engineered for this)
- **TanStack Query (React Query)** - Server state, caching, SSE streaming

### UI Framework
- **Tailwind CSS** - Utility-first, matches landing page
- **Headless UI** - Accessible components (modals, dropdowns)
- **Lucide React** - Beautiful icons

### Auth
- **Google OAuth** - Redirect flow to backend

### Real-time
- **EventSource API** - SSE for chat streaming (native, no library needed)

---

## Folder Structure

```
frontend/
├── src/
│   ├── main.tsx                 # Entry point
│   ├── App.tsx                  # Root component, routes
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Header.tsx       # Top nav
│   │   │   ├── Sidebar.tsx      # Neuron list
│   │   │   └── Layout.tsx       # Main layout wrapper
│   │   ├── chat/
│   │   │   ├── ChatWindow.tsx   # Main chat UI
│   │   │   ├── MessageList.tsx  # Scrollable messages
│   │   │   ├── Message.tsx      # Single message bubble
│   │   │   └── ChatInput.tsx    # Textarea + send button
│   │   ├── neurons/
│   │   │   ├── NeuronCard.tsx   # Neuron grid item
│   │   │   ├── NeuronForm.tsx   # Create/edit neuron
│   │   │   └── PrivacyBadge.tsx # Tier 0/1/2 badge
│   │   └── ui/
│   │       ├── Button.tsx       # Reusable button
│   │       ├── Modal.tsx        # Dialog wrapper
│   │       └── Loading.tsx      # Spinner
│   ├── pages/
│   │   ├── Login.tsx            # Google OAuth button
│   │   ├── Dashboard.tsx        # Neuron grid
│   │   ├── Chat.tsx             # Chat page (uses ChatWindow)
│   │   └── Settings.tsx         # User settings
│   ├── stores/
│   │   ├── authStore.ts         # User, token, logout
│   │   ├── neuronStore.ts       # Selected neuron, list
│   │   └── chatStore.ts         # Active session, messages
│   ├── api/
│   │   ├── client.ts            # Axios instance with auth
│   │   ├── auth.ts              # Login, logout
│   │   ├── neurons.ts           # CRUD neurons
│   │   └── chat.ts              # Chat API, SSE streaming
│   ├── types/
│   │   ├── neuron.ts            # Neuron, PrivacyTier types
│   │   ├── chat.ts              # Message, Session types
│   │   └── user.ts              # User type
│   ├── hooks/
│   │   ├── useChatStream.ts     # SSE chat hook
│   │   └── useNeurons.ts        # React Query neurons
│   └── utils/
│       ├── formatDate.ts        # Date formatting
│       └── privacyConfig.ts     # Privacy tier metadata
├── index.html
├── vite.config.ts
├── tailwind.config.js
├── tsconfig.json
└── package.json
```

---

## Pseudocode for Key Components

### 1. `stores/authStore.ts` (Zustand)

```typescript
// Purpose: Global auth state, persist token in localStorage
interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean

  // Actions
  login: (token: string, user: User) => void
  logout: () => void
}

// Implementation:
create<AuthState>((set) => ({
  user: null,
  token: localStorage.getItem('brane_token'),
  isAuthenticated: !!localStorage.getItem('brane_token'),

  login: (token, user) => {
    localStorage.setItem('brane_token', token)
    set({ token, user, isAuthenticated: true })
  },

  logout: () => {
    localStorage.removeItem('brane_token')
    set({ token: null, user: null, isAuthenticated: false })
  }
}))
```

---

### 2. `api/client.ts` (Axios with Auth)

```typescript
// Purpose: Centralized HTTP client with auto auth headers
import axios from 'axios'
import { useAuthStore } from '@/stores/authStore'

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api'
})

// Request interceptor: Add token to all requests
client.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor: Handle 401 (logout)
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default client
```

---

### 3. `hooks/useChatStream.ts` (SSE Streaming)

```typescript
// Purpose: Stream chat responses from backend via SSE
import { useState } from 'react'

interface UseChatStreamOptions {
  neuronId: string
  sessionId?: string
  onComplete?: (fullResponse: string, tokens: number) => void
}

function useChatStream({ neuronId, sessionId, onComplete }: UseChatStreamOptions) {
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamedMessage, setStreamedMessage] = useState('')

  const sendMessage = async (message: string) => {
    setIsStreaming(true)
    setStreamedMessage('')

    const token = useAuthStore.getState().token

    // Create SSE connection
    const eventSource = new EventSource(
      `http://localhost:8000/api/chat/${neuronId}/stream?message=${encodeURIComponent(message)}&session_id=${sessionId}&token=${token}`
    )

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data)

      if (data.done) {
        // Stream complete
        eventSource.close()
        setIsStreaming(false)
        onComplete?.(streamedMessage, data.tokens)
      } else if (data.chunk) {
        // Append chunk
        setStreamedMessage((prev) => prev + data.chunk)
      } else if (data.error) {
        // Error occurred
        console.error(data.error)
        eventSource.close()
        setIsStreaming(false)
      }
    }

    eventSource.onerror = () => {
      eventSource.close()
      setIsStreaming(false)
    }
  }

  return { sendMessage, isStreaming, streamedMessage }
}
```

---

### 4. `components/chat/ChatWindow.tsx`

```typescript
// Purpose: Main chat interface with message list + input

function ChatWindow({ neuronId }: { neuronId: string }) {
  const [messages, setMessages] = useState<Message[]>([])
  const [sessionId, setSessionId] = useState<string | null>(null)

  const { sendMessage, isStreaming, streamedMessage } = useChatStream({
    neuronId,
    sessionId,
    onComplete: (fullResponse, tokens) => {
      // Add assistant message to history
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: fullResponse, tokens }
      ])
    }
  })

  const handleSend = (userMessage: string) => {
    // Add user message to UI
    setMessages((prev) => [
      ...prev,
      { role: 'user', content: userMessage }
    ])

    // Send to backend
    sendMessage(userMessage)
  }

  return (
    <div className="flex flex-col h-full">
      {/* Message list (scrollable) */}
      <MessageList messages={messages} />

      {/* Streaming indicator */}
      {isStreaming && (
        <Message role="assistant" content={streamedMessage} isStreaming />
      )}

      {/* Input */}
      <ChatInput onSend={handleSend} disabled={isStreaming} />
    </div>
  )
}
```

---

### 5. `components/neurons/NeuronCard.tsx`

```typescript
// Purpose: Display neuron in grid with privacy tier badge

function NeuronCard({ neuron }: { neuron: Neuron }) {
  const navigate = useNavigate()

  const privacyColors = {
    0: 'bg-tier-0 text-green-900',  // Local
    1: 'bg-tier-1 text-orange-900', // Private cloud
    2: 'bg-tier-2 text-red-900'     // Public API
  }

  return (
    <div
      className="p-6 border border-gray-700 rounded-lg hover:border-primary cursor-pointer"
      onClick={() => navigate(`/chat/${neuron.id}`)}
    >
      {/* Header */}
      <div className="flex justify-between items-start mb-4">
        <h3 className="text-xl font-semibold">{neuron.name}</h3>
        <PrivacyBadge tier={neuron.privacy_tier} />
      </div>

      {/* Description */}
      <p className="text-gray-400 text-sm mb-4">{neuron.description}</p>

      {/* Stats */}
      <div className="flex gap-4 text-xs text-gray-500">
        <span>{neuron.total_interactions} chats</span>
        <span>{neuron.total_tokens} tokens</span>
      </div>
    </div>
  )
}
```

---

### 6. `pages/Dashboard.tsx`

```typescript
// Purpose: Main page - grid of user's neurons

function Dashboard() {
  const { data: neurons, isLoading } = useQuery({
    queryKey: ['neurons'],
    queryFn: () => api.neurons.list()
  })

  const [showCreateModal, setShowCreateModal] = useState(false)

  if (isLoading) return <Loading />

  return (
    <Layout>
      {/* Header */}
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">Your Neurons</h1>
        <Button onClick={() => setShowCreateModal(true)}>
          + Create Neuron
        </Button>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {neurons.map((neuron) => (
          <NeuronCard key={neuron.id} neuron={neuron} />
        ))}
      </div>

      {/* Create modal */}
      {showCreateModal && (
        <Modal onClose={() => setShowCreateModal(false)}>
          <NeuronForm onSuccess={() => setShowCreateModal(false)} />
        </Modal>
      )}
    </Layout>
  )
}
```

---

### 7. `App.tsx` (Routes)

```typescript
// Purpose: Root component with routing and auth guard

function App() {
  const { isAuthenticated } = useAuthStore()

  return (
    <BrowserRouter>
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={<Login />} />

        {/* Protected routes */}
        <Route element={<RequireAuth />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/chat/:neuronId" element={<Chat />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

// Auth guard
function RequireAuth() {
  const { isAuthenticated } = useAuthStore()
  const location = useLocation()

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return <Outlet />
}
```

---

## Privacy Tier Implementation

```typescript
// utils/privacyConfig.ts

export const PRIVACY_TIERS = {
  0: {
    name: 'Local Only',
    description: 'Data never leaves your machine. HIPAA/GDPR compliant.',
    color: 'green',
    icon: 'Lock',
    requirements: 'Ollama or local LLM required'
  },
  1: {
    name: 'Private Cloud',
    description: 'Self-hosted cloud. You control encryption keys.',
    color: 'orange',
    icon: 'Cloud',
    requirements: 'Docker or VPS required'
  },
  2: {
    name: 'Public API',
    description: 'Use OpenAI, Anthropic, etc. Convenient but less private.',
    color: 'red',
    icon: 'Globe',
    requirements: 'API key required'
  }
}
```

---

## API Integration

```typescript
// api/chat.ts

export const chatAPI = {
  // Create EventSource for streaming
  streamChat: (neuronId: string, message: string, sessionId?: string) => {
    const params = new URLSearchParams({
      message,
      ...(sessionId && { session_id: sessionId })
    })

    const token = useAuthStore.getState().token

    return new EventSource(
      `${API_URL}/chat/${neuronId}/stream?${params}&token=${token}`
    )
  },

  // Get chat history
  getSessions: (neuronId: string) =>
    client.get(`/chat/${neuronId}/sessions`),

  // Get messages
  getMessages: (sessionId: string) =>
    client.get(`/chat/sessions/${sessionId}/messages`)
}
```

---

## Key Features

### 1. **Real-time Streaming**
- Uses native `EventSource` API (no extra library)
- Handles connection errors gracefully
- Shows typing indicator while streaming

### 2. **Privacy-First UX**
- Color-coded badges (green/orange/red) for tiers
- Warning modals when switching to Tier 2
- Clear explanation of data flow

### 3. **Responsive Design**
- Mobile-first (Tailwind responsive classes)
- Collapsible sidebar on mobile
- Touch-friendly chat input

### 4. **Performance**
- React Query caching (don't re-fetch neurons on every navigation)
- Virtualized message list (react-window) for long chats
- Lazy-loaded routes

---

## Dependencies (`package.json`)

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "zustand": "^4.4.7",
    "@tanstack/react-query": "^5.14.2",
    "axios": "^1.6.2",
    "lucide-react": "^0.294.0",
    "@headlessui/react": "^1.7.17"
  },
  "devDependencies": {
    "typescript": "^5.3.3",
    "vite": "^5.0.7",
    "@vitejs/plugin-react": "^4.2.1",
    "tailwindcss": "^3.3.6",
    "autoprefixer": "^10.4.16",
    "postcss": "^8.4.32"
  }
}
```

---

## Build & Deploy Strategy

### Development
```bash
cd frontend
npm install
npm run dev  # Vite dev server on localhost:5173
```

### Production
```bash
npm run build  # Output to frontend/dist/
```

### Deployment Options
1. **GitHub Pages** (static hosting)
   - Build frontend → `/docs` folder
   - Enable GitHub Pages from `/docs`
   - API calls to deployed backend

2. **Vercel/Netlify** (better for SPAs)
   - Auto-deploy from `main` branch
   - Environment variable for API URL

3. **Self-hosted** (with backend)
   - Nginx serves `frontend/dist` + proxies `/api` to backend
   - Single domain, no CORS issues

---

## Next Steps (Implementation Order)

1. ✅ **Design complete** (this document)
2. Initialize Vite + TypeScript project
3. Set up Tailwind + base layout
4. Implement auth flow (Login page + store)
5. Build Dashboard + Neuron CRUD
6. Build ChatWindow + SSE streaming
7. Add Settings page
8. Polish UI + responsive design
9. Deploy to Vercel (frontend) + Render (backend)

---

**Philosophy**:
- **Simple > Complex** (Zustand > Redux, Vite > Webpack)
- **Type-safe** (TypeScript everywhere)
- **Privacy-first** (tier badges, warnings, clear data flow)
- **No placeholders** (every component does what it says)
