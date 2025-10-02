import client from './client'
import type { Message } from '../types/chat'

export interface ChatSession {
  id: string
  title: string
  neuron_id: string
  message_count: number
  created_at: string
  updated_at: string
}

// Get all sessions for a neuron
export const getSessions = async (neuronId: string) => {
  const response = await client.get<ChatSession[]>(`/chat/${neuronId}/sessions`)
  return response.data
}

// Get messages for a session
export const getSessionMessages = async (sessionId: string) => {
  const response = await client.get<Message[]>(`/chat/sessions/${sessionId}/messages`)
  return response.data
}

// Delete a session
export const deleteSession = async (sessionId: string) => {
  const response = await client.delete(`/chat/sessions/${sessionId}`)
  return response.data
}
