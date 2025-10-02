import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Settings as SettingsIcon, FileText, MessageSquare, Trash2, PanelLeftClose, PanelLeft } from 'lucide-react'
import { neuronsAPI } from '../api/neurons'
import { getSessions, getSessionMessages, deleteSession } from '../api/sessions'
import { useChatStream } from '../hooks/useChatStream'
import Message from '../components/chat/Message'
import ChatInput from '../components/chat/ChatInput'
import PrivacyBadge from '../components/neurons/PrivacyBadge'
import Loading from '../components/ui/Loading'
import Button from '../components/ui/Button'
import type { Message as MessageType } from '../types/chat'

export default function Chat() {
  const { neuronId } = useParams<{ neuronId: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const [messages, setMessages] = useState<MessageType[]>([])
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState(true)

  const { data: neuron, isLoading, error } = useQuery({
    queryKey: ['neuron', neuronId],
    queryFn: () => neuronsAPI.get(neuronId!),
    enabled: !!neuronId
  })

  // Fetch sessions
  const { data: sessions = [] } = useQuery({
    queryKey: ['sessions', neuronId],
    queryFn: () => getSessions(neuronId!),
    enabled: !!neuronId
  })

  // Delete session mutation
  const deleteMutation = useMutation({
    mutationFn: deleteSession,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions', neuronId] })
      if (sessionId && sessions.find(s => s.id === sessionId)) {
        setSessionId(null)
        setMessages([])
      }
    }
  })

  const { sendMessage, isStreaming, streamedMessage } = useChatStream({
    neuronId: neuronId!,
    sessionId: sessionId || undefined,
    onComplete: (fullResponse, tokens, latency) => {
      // Add assistant message to history
      const newMessage: MessageType = {
        id: Date.now().toString(),
        session_id: sessionId || '',
        role: 'assistant',
        content: fullResponse,
        privacy_tier: neuron!.privacy_tier,
        tokens,
        latency_ms: latency,
        created_at: new Date().toISOString()
      }
      setMessages((prev) => [...prev, newMessage])
    },
    onError: (error) => {
      alert(`Chat error: ${error}`)
    }
  })

  const handleSend = (userMessage: string) => {
    // Add user message to UI
    const newMessage: MessageType = {
      id: Date.now().toString(),
      session_id: sessionId || '',
      role: 'user',
      content: userMessage,
      privacy_tier: neuron!.privacy_tier,
      tokens: userMessage.split(' ').length,
      created_at: new Date().toISOString()
    }
    setMessages((prev) => [...prev, newMessage])

    // Send to backend
    sendMessage(userMessage)
  }

  // Load session messages when switching sessions
  useEffect(() => {
    if (sessionId) {
      getSessionMessages(sessionId).then(setMessages).catch(console.error)
    }
  }, [sessionId])

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamedMessage])

  // Handle session switch
  const handleSessionSwitch = (newSessionId: string) => {
    setSessionId(newSessionId)
  }

  // Handle new chat
  const handleNewChat = () => {
    setSessionId(null)
    setMessages([])
  }

  if (isLoading) return <Loading />

  if (error || !neuron) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-tier-2 mb-4">Failed to load neuron</p>
          <Button onClick={() => navigate('/')}>Back to Dashboard</Button>
        </div>
      </div>
    )
  }

  return (
    <div className="h-screen flex bg-background">
      {/* Sessions Sidebar */}
      {sidebarOpen && (
        <div className="w-64 border-r border-gray-700 bg-gray-900 flex flex-col">
          <div className="p-4 border-b border-gray-700">
            <button
              onClick={handleNewChat}
              className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors flex items-center justify-center gap-2"
            >
              <MessageSquare size={16} />
              New Chat
            </button>
          </div>

          <div className="flex-1 overflow-y-auto">
            {sessions.length === 0 ? (
              <div className="p-4 text-center text-gray-500 text-sm">
                No chat sessions yet
              </div>
            ) : (
              <div className="p-2">
                {sessions.map((session) => (
                  <div
                    key={session.id}
                    className={`group relative p-3 mb-2 rounded-lg cursor-pointer transition-colors ${
                      sessionId === session.id
                        ? 'bg-gray-800 border border-blue-500'
                        : 'hover:bg-gray-800/50'
                    }`}
                    onClick={() => handleSessionSwitch(session.id)}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <p className="text-white text-sm font-medium truncate">
                          {session.title}
                        </p>
                        <p className="text-gray-500 text-xs mt-1">
                          {session.message_count} messages
                        </p>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          if (confirm('Delete this session?')) {
                            deleteMutation.mutate(session.id)
                          }
                        }}
                        className="opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-red-400 transition-opacity"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-700 bg-gray-900">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="text-gray-400 hover:text-white transition-colors"
              title={sidebarOpen ? 'Hide sessions' : 'Show sessions'}
            >
              {sidebarOpen ? <PanelLeftClose size={20} /> : <PanelLeft size={20} />}
            </button>
            <button
              onClick={() => navigate('/')}
              className="text-gray-400 hover:text-white transition-colors"
            >
              <ArrowLeft size={20} />
            </button>
            <div>
              <h2 className="text-xl font-semibold">{neuron.name}</h2>
              <p className="text-sm text-gray-400">{neuron.description}</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate(`/documents/${neuronId}`)}
              className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
              title="Document Library"
            >
              <FileText size={20} />
            </button>
            <button
              onClick={() => navigate(`/settings/${neuronId}`)}
              className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
              title="Model Settings"
            >
              <SettingsIcon size={20} />
            </button>
            <PrivacyBadge tier={neuron.privacy_tier} />
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6">
          {messages.length === 0 && !isStreaming && (
            <div className="flex items-center justify-center h-full">
              <div className="text-center text-gray-500">
                <p className="text-lg mb-2">Start a conversation</p>
                <p className="text-sm">Ask me anything!</p>
              </div>
            </div>
          )}

          {messages.map((msg) => (
            <Message key={msg.id} message={msg} />
          ))}

          {isStreaming && (
            <Message
              message={{ role: 'assistant', content: streamedMessage }}
              isStreaming
            />
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <ChatInput onSend={handleSend} disabled={isStreaming} />
      </div>
    </div>
  )
}
