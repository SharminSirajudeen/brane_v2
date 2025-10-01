import client from './client'
import type { ChatSession, Message } from '../types/chat'

export const chatAPI = {
  // Get EventSource URL for streaming
  getStreamURL: (neuronId: string, message: string, sessionId?: string): string => {
    const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'
    const token = localStorage.getItem('brane_token')

    const params = new URLSearchParams({
      message,
      ...(sessionId && { session_id: sessionId }),
      ...(token && { token })
    })

    return `${API_URL}/chat/${neuronId}/stream?${params}`
  },

  // List chat sessions for neuron
  getSessions: async (neuronId: string): Promise<ChatSession[]> => {
    const response = await client.get(`/chat/${neuronId}/sessions`)
    return response.data
  },

  // Get messages in session
  getMessages: async (sessionId: string): Promise<Message[]> => {
    const response = await client.get(`/chat/sessions/${sessionId}/messages`)
    return response.data
  },

  // Delete session
  deleteSession: async (sessionId: string): Promise<void> => {
    await client.delete(`/chat/sessions/${sessionId}`)
  }
}
