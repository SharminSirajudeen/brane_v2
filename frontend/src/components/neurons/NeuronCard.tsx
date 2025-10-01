import { useNavigate } from 'react-router-dom'
import type { Neuron } from '../../types/neuron'
import PrivacyBadge from './PrivacyBadge'
import { MessageSquare, Zap } from 'lucide-react'

interface NeuronCardProps {
  neuron: Neuron
}

export default function NeuronCard({ neuron }: NeuronCardProps) {
  const navigate = useNavigate()

  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`
    return num.toString()
  }

  return (
    <div
      onClick={() => navigate(`/chat/${neuron.id}`)}
      className="group p-6 bg-gray-900 border border-gray-700 rounded-lg hover:border-primary hover:shadow-lg hover:shadow-primary/20 transition-all cursor-pointer"
    >
      {/* Header */}
      <div className="flex justify-between items-start mb-4">
        <h3 className="text-xl font-semibold group-hover:text-primary transition-colors">
          {neuron.name}
        </h3>
        <PrivacyBadge tier={neuron.privacy_tier} showLabel={false} />
      </div>

      {/* Description */}
      <p className="text-gray-400 text-sm mb-4 line-clamp-2">{neuron.description}</p>

      {/* Stats */}
      <div className="flex items-center gap-4 text-xs text-gray-500">
        <div className="flex items-center gap-1">
          <MessageSquare size={14} />
          <span>{formatNumber(neuron.total_interactions)} chats</span>
        </div>
        <div className="flex items-center gap-1">
          <Zap size={14} />
          <span>{formatNumber(neuron.total_tokens)} tokens</span>
        </div>
      </div>

      {/* Status indicator */}
      <div className="mt-4 pt-4 border-t border-gray-800">
        <div className="flex items-center gap-2">
          <div
            className={`w-2 h-2 rounded-full ${
              neuron.status === 'active'
                ? 'bg-green-500'
                : neuron.status === 'error'
                ? 'bg-red-500'
                : 'bg-gray-500'
            }`}
          />
          <span className="text-xs text-gray-500 capitalize">{neuron.status}</span>
        </div>
      </div>
    </div>
  )
}
