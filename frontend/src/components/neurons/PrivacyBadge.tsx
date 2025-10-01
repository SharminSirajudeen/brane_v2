import { PrivacyTier } from '../../types/neuron'
import { PRIVACY_TIERS } from '../../utils/privacyConfig'

interface PrivacyBadgeProps {
  tier: PrivacyTier
  showLabel?: boolean
}

export default function PrivacyBadge({ tier, showLabel = true }: PrivacyBadgeProps) {
  const config = PRIVACY_TIERS[tier]
  const Icon = config.icon

  return (
    <div
      className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-medium ${config.bgColor}/20 ${config.borderColor} border`}
    >
      <Icon size={12} className={config.textColor} />
      {showLabel && <span className={config.textColor}>{config.name}</span>}
    </div>
  )
}
