import { useState, useRef } from 'react'
import { chatAPI } from '../api/chat'
import type { StreamChunk } from '../types/chat'

interface UseChatStreamOptions {
  neuronId: string
  sessionId?: string
  onComplete?: (fullResponse: string, tokens: number, latency: number) => void
  onError?: (error: string) => void
}

export function useChatStream({
  neuronId,
  sessionId,
  onComplete,
  onError
}: UseChatStreamOptions) {
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamedMessage, setStreamedMessage] = useState('')
  const eventSourceRef = useRef<EventSource | null>(null)

  const sendMessage = async (message: string) => {
    setIsStreaming(true)
    setStreamedMessage('')

    const streamURL = chatAPI.getStreamURL(neuronId, message, sessionId)

    try {
      const eventSource = new EventSource(streamURL)
      eventSourceRef.current = eventSource

      eventSource.onmessage = (event) => {
        try {
          const data: StreamChunk = JSON.parse(event.data)

          if (data.done) {
            // Stream complete
            eventSource.close()
            setIsStreaming(false)
            onComplete?.(
              streamedMessage,
              data.tokens || 0,
              data.latency_ms || 0
            )
          } else if (data.chunk) {
            // Append chunk
            setStreamedMessage((prev) => prev + data.chunk)
          } else if (data.error) {
            // Error occurred
            eventSource.close()
            setIsStreaming(false)
            onError?.(data.error)
          }
        } catch (err) {
          console.error('Failed to parse SSE data:', err)
        }
      }

      eventSource.onerror = () => {
        eventSource.close()
        setIsStreaming(false)
        onError?.('Connection lost. Please try again.')
      }
    } catch (err) {
      setIsStreaming(false)
      onError?.('Failed to start chat stream.')
    }
  }

  const stopStreaming = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
    setIsStreaming(false)
  }

  return {
    sendMessage,
    stopStreaming,
    isStreaming,
    streamedMessage
  }
}
