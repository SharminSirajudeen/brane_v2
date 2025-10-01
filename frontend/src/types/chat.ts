import { PrivacyTier } from './neuron'

export interface Message {
  id: string
  session_id: string
  role: 'user' | 'assistant'
  content: string
  privacy_tier: PrivacyTier
  tokens: number
  model_used?: string
  latency_ms?: number
  created_at: string
}

export interface ChatSession {
  id: string
  user_id: string
  neuron_id: string
  title: string
  message_count: number
  total_tokens: number
  created_at: string
  updated_at: string
}

export interface ChatRequest {
  message: string
  session_id?: string
}

export interface StreamChunk {
  chunk?: string
  done?: boolean
  tokens?: number
  latency_ms?: number
  error?: string
}
