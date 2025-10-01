import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { PrivacyTier } from '../../types/neuron'
import { neuronsAPI } from '../../api/neurons'
import { PRIVACY_TIERS } from '../../utils/privacyConfig'
import Button from '../ui/Button'

interface NeuronFormProps {
  onSuccess: () => void
}

export default function NeuronForm({ onSuccess }: NeuronFormProps) {
  const queryClient = useQueryClient()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [privacyTier, setPrivacyTier] = useState<PrivacyTier>(PrivacyTier.LOCAL)
  const [provider, setProvider] = useState('ollama')
  const [model, setModel] = useState('llama2')

  const createMutation = useMutation({
    mutationFn: neuronsAPI.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['neurons'] })
      onSuccess()
    }
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    const config = {
      model: {
        provider,
        model,
        temperature: 0.7
      },
      privacy_tier: privacyTier
    }

    createMutation.mutate({
      name,
      description,
      privacy_tier: privacyTier,
      config
    })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Name */}
      <div>
        <label className="block text-sm font-medium mb-2">Neuron Name</label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:border-primary focus:outline-none"
          placeholder="Medical Assistant"
          required
        />
      </div>

      {/* Description */}
      <div>
        <label className="block text-sm font-medium mb-2">Description</label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:border-primary focus:outline-none resize-none"
          rows={3}
          placeholder="HIPAA-compliant medical knowledge assistant"
          required
        />
      </div>

      {/* Privacy Tier */}
      <div>
        <label className="block text-sm font-medium mb-2">Privacy Tier</label>
        <div className="space-y-2">
          {Object.entries(PRIVACY_TIERS).map(([tier, config]) => {
            const Icon = config.icon
            return (
              <label
                key={tier}
                className={`flex items-start gap-3 p-4 border rounded-lg cursor-pointer transition-colors ${
                  privacyTier === Number(tier)
                    ? `${config.borderColor} bg-${config.color}/10`
                    : 'border-gray-700 hover:border-gray-600'
                }`}
              >
                <input
                  type="radio"
                  name="privacyTier"
                  value={tier}
                  checked={privacyTier === Number(tier)}
                  onChange={(e) => setPrivacyTier(Number(e.target.value) as PrivacyTier)}
                  className="mt-1"
                />
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <Icon size={16} className={config.textColor} />
                    <span className="font-medium">{config.name}</span>
                  </div>
                  <p className="text-xs text-gray-400">{config.description}</p>
                  <p className="text-xs text-gray-500 mt-1">{config.requirements}</p>
                </div>
              </label>
            )
          })}
        </div>
      </div>

      {/* Model Provider */}
      <div>
        <label className="block text-sm font-medium mb-2">Model Provider</label>
        <select
          value={provider}
          onChange={(e) => setProvider(e.target.value)}
          className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:border-primary focus:outline-none"
        >
          <option value="ollama">Ollama (Local)</option>
          <option value="openai">OpenAI</option>
          <option value="anthropic">Anthropic</option>
        </select>
      </div>

      {/* Model Name */}
      <div>
        <label className="block text-sm font-medium mb-2">Model</label>
        <input
          type="text"
          value={model}
          onChange={(e) => setModel(e.target.value)}
          className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:border-primary focus:outline-none"
          placeholder="llama2, gpt-4, claude-3-opus"
          required
        />
      </div>

      {/* Actions */}
      <div className="flex gap-3 pt-4">
        <Button
          type="submit"
          variant="primary"
          className="flex-1"
          disabled={createMutation.isPending}
        >
          {createMutation.isPending ? 'Creating...' : 'Create Neuron'}
        </Button>
      </div>

      {/* Error */}
      {createMutation.isError && (
        <p className="text-tier-2 text-sm">
          Failed to create neuron. Please try again.
        </p>
      )}
    </form>
  )
}
