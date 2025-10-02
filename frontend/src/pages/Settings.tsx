import { useState, useEffect } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Save, TestTube } from 'lucide-react'
import { neuronsAPI } from '../api/neurons'
import Button from '../components/ui/Button'
import Loading from '../components/ui/Loading'
import { useParams, useNavigate } from 'react-router-dom'

const MODEL_PROVIDERS = [
  { value: 'ollama', label: 'Ollama (Local)', defaultModel: 'llama2', defaultUrl: 'http://localhost:11434' },
  { value: 'openai', label: 'OpenAI', defaultModel: 'gpt-4', defaultUrl: 'https://api.openai.com/v1' },
  { value: 'anthropic', label: 'Anthropic (Claude)', defaultModel: 'claude-3-opus-20240229', defaultUrl: 'https://api.anthropic.com' },
  { value: 'huggingface', label: 'HuggingFace', defaultModel: 'mistralai/Mistral-7B-Instruct-v0.1', defaultUrl: '' },
  { value: 'custom', label: 'Custom API', defaultModel: '', defaultUrl: '' }
]

export default function Settings() {
  const { neuronId } = useParams<{ neuronId: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [provider, setProvider] = useState('ollama')
  const [model, setModel] = useState('llama2')
  const [baseUrl, setBaseUrl] = useState('http://localhost:11434')
  const [apiKey, setApiKey] = useState('')
  const [temperature, setTemperature] = useState(0.7)
  const [testResult, setTestResult] = useState<{success: boolean, message: string} | null>(null)

  const { data: neuron, isLoading } = useQuery({
    queryKey: ['neuron', neuronId],
    queryFn: () => neuronsAPI.get(neuronId!),
    enabled: !!neuronId
  })

  // Pre-fill form when neuron data loads
  useEffect(() => {
    if (neuron?.config?.model) {
      const modelConfig = neuron.config.model
      setProvider(modelConfig.provider || 'ollama')
      setModel(modelConfig.model || 'llama2')
      setBaseUrl(modelConfig.base_url || 'http://localhost:11434')
      setTemperature(modelConfig.temperature || 0.7)
    }
  }, [neuron])

  const updateMutation = useMutation({
    mutationFn: async () => {
      const newConfig = {
        ...neuron?.config,
        model: {
          provider,
          model,
          base_url: baseUrl,
          api_key: apiKey || undefined,
          temperature
        }
      }

      return neuronsAPI.update(neuronId!, { config: newConfig })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['neuron', neuronId] })
      alert('Model settings updated successfully!')
    }
  })

  const handleProviderChange = (newProvider: string) => {
    setProvider(newProvider)
    const providerConfig = MODEL_PROVIDERS.find(p => p.value === newProvider)
    if (providerConfig) {
      setModel(providerConfig.defaultModel)
      setBaseUrl(providerConfig.defaultUrl)
    }
  }

  const testConnection = async () => {
    setTestResult(null)

    try {
      // Simple test: try to connect to the model endpoint
      // In a real implementation, this would call a backend /test-connection endpoint
      const response = await fetch(`${baseUrl}/health`, {
        method: 'GET',
        headers: apiKey ? { 'Authorization': `Bearer ${apiKey}` } : {}
      })

      if (response.ok) {
        setTestResult({ success: true, message: `✓ Connected to ${provider} successfully!` })
      } else {
        setTestResult({ success: false, message: `✗ Connection failed: ${response.statusText}` })
      }
    } catch (error) {
      setTestResult({ success: false, message: `✗ Connection failed: ${error}` })
    }
  }

  if (isLoading) return <Loading />

  if (!neuron) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-tier-2 mb-4">Neuron not found</p>
          <Button onClick={() => navigate('/')}>Back to Dashboard</Button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => navigate(`/chat/${neuronId}`)}
            className="text-gray-400 hover:text-white mb-4 transition-colors"
          >
            ← Back to Chat
          </button>
          <h1 className="text-3xl font-bold mb-2">Model Settings</h1>
          <p className="text-gray-400">Configure {neuron.name}'s AI model</p>
        </div>

        <form onSubmit={(e) => { e.preventDefault(); updateMutation.mutate() }} className="space-y-6">
          {/* Provider Selection */}
          <div>
            <label className="block text-sm font-medium mb-2">Model Provider</label>
            <select
              value={provider}
              onChange={(e) => handleProviderChange(e.target.value)}
              className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg focus:border-primary focus:outline-none"
            >
              {MODEL_PROVIDERS.map(p => (
                <option key={p.value} value={p.value}>{p.label}</option>
              ))}
            </select>
            <p className="text-xs text-gray-500 mt-1">
              Switch providers anytime - no vendor lock-in
            </p>
          </div>

          {/* Model Name */}
          <div>
            <label className="block text-sm font-medium mb-2">Model Name</label>
            <input
              type="text"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg focus:border-primary focus:outline-none"
              placeholder="llama2, gpt-4, claude-3-opus"
              required
            />
            <p className="text-xs text-gray-500 mt-1">
              Examples: llama2, gpt-4, claude-3-opus-20240229, mistral-7b
            </p>
          </div>

          {/* Base URL */}
          {provider !== 'openai' && provider !== 'anthropic' && (
            <div>
              <label className="block text-sm font-medium mb-2">Base URL</label>
              <input
                type="text"
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg focus:border-primary focus:outline-none font-mono text-sm"
                placeholder="http://localhost:11434"
              />
              <p className="text-xs text-gray-500 mt-1">
                Point to your local Ollama, rented GPU, or custom API
              </p>
            </div>
          )}

          {/* API Key */}
          {(provider === 'openai' || provider === 'anthropic' || provider === 'custom') && (
            <div>
              <label className="block text-sm font-medium mb-2">API Key</label>
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg focus:border-primary focus:outline-none font-mono text-sm"
                placeholder="sk-..."
              />
              <p className="text-xs text-gray-500 mt-1">
                Your API key is stored securely and never shared
              </p>
            </div>
          )}

          {/* Temperature */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Temperature: {temperature.toFixed(1)}
            </label>
            <input
              type="range"
              min="0"
              max="2"
              step="0.1"
              value={temperature}
              onChange={(e) => setTemperature(parseFloat(e.target.value))}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>Precise (0.0)</span>
              <span>Balanced (1.0)</span>
              <span>Creative (2.0)</span>
            </div>
          </div>

          {/* Test Connection */}
          <div>
            <Button
              type="button"
              variant="secondary"
              onClick={testConnection}
              className="flex items-center gap-2"
            >
              <TestTube size={16} />
              Test Connection
            </Button>

            {testResult && (
              <p className={`mt-2 text-sm ${testResult.success ? 'text-tier-0' : 'text-tier-2'}`}>
                {testResult.message}
              </p>
            )}
          </div>

          {/* Save Button */}
          <div className="flex gap-3 pt-4 border-t border-gray-700">
            <Button
              type="submit"
              variant="primary"
              disabled={updateMutation.isPending}
              className="flex items-center gap-2"
            >
              <Save size={16} />
              {updateMutation.isPending ? 'Saving...' : 'Save Settings'}
            </Button>

            <Button
              type="button"
              variant="secondary"
              onClick={() => navigate(`/chat/${neuronId}`)}
            >
              Cancel
            </Button>
          </div>

          {updateMutation.isError && (
            <p className="text-tier-2 text-sm">
              Failed to update settings. Please try again.
            </p>
          )}
        </form>

        {/* Info Box */}
        <div className="mt-8 p-6 bg-primary/10 border border-primary/30 rounded-lg">
          <h3 className="font-semibold mb-2">💡 Pro Tip: Model Switching</h3>
          <ul className="text-sm text-gray-300 space-y-2">
            <li>• Start with Ollama (local) for privacy, switch to OpenAI for better quality</li>
            <li>• Use lower temperature (0.1-0.3) for factual tasks, higher (0.7-1.2) for creative</li>
            <li>• Test connection before saving to avoid errors during chat</li>
            <li>• Switch anytime - your neuron keeps its memory across providers</li>
          </ul>
        </div>
      </div>
    </div>
  )
}
