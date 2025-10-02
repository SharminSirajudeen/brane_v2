import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Settings as SettingsIcon } from 'lucide-react'
import { neuronsAPI } from '../api/neurons'
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
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const [messages, setMessages] = useState<MessageType[]>([])
  const [sessionId] = useState<string | null>(null)

  const { data: neuron, isLoading, error } = useQuery({
    queryKey: ['neuron', neuronId],
    queryFn: () => neuronsAPI.get(neuronId!),
    enabled: !!neuronId
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

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamedMessage])

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
    <div className="h-screen flex flex-col bg-background">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-700 bg-gray-900">
        <div className="flex items-center gap-4">
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
  )
}
