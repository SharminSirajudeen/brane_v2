export const PrivacyTier = {
  LOCAL: 0,
  PRIVATE_CLOUD: 1,
  PUBLIC_API: 2
} as const

export type PrivacyTier = typeof PrivacyTier[keyof typeof PrivacyTier]

export interface Neuron {
  id: string
  owner_id: string
  name: string
  description: string
  privacy_tier: PrivacyTier
  config: Record<string, any>
  status: 'idle' | 'active' | 'error'
  total_interactions: number
  total_tokens: number
  last_used: string | null
  created_at: string
  updated_at: string
}

export interface CreateNeuronRequest {
  name: string
  description: string
  privacy_tier: PrivacyTier
  config: Record<string, any>
}
