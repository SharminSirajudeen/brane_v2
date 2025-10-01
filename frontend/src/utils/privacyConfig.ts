import { PrivacyTier } from '../types/neuron'
import { Lock, Cloud, Globe } from 'lucide-react'

export const PRIVACY_TIERS = {
  [PrivacyTier.LOCAL]: {
    name: 'Local Only',
    description: 'Data never leaves your machine. HIPAA/GDPR compliant.',
    color: 'tier-0',
    textColor: 'text-tier-0',
    bgColor: 'bg-tier-0',
    borderColor: 'border-tier-0',
    icon: Lock,
    requirements: 'Ollama or local LLM required'
  },
  [PrivacyTier.PRIVATE_CLOUD]: {
    name: 'Private Cloud',
    description: 'Self-hosted cloud. You control encryption keys.',
    color: 'tier-1',
    textColor: 'text-tier-1',
    bgColor: 'bg-tier-1',
    borderColor: 'border-tier-1',
    icon: Cloud,
    requirements: 'Docker or VPS required'
  },
  [PrivacyTier.PUBLIC_API]: {
    name: 'Public API',
    description: 'Use OpenAI, Anthropic, etc. Convenient but less private.',
    color: 'tier-2',
    textColor: 'text-tier-2',
    bgColor: 'bg-tier-2',
    borderColor: 'border-tier-2',
    icon: Globe,
    requirements: 'API key required'
  }
}
