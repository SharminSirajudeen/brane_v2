import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Plus } from 'lucide-react'
import { neuronsAPI } from '../api/neurons'
import NeuronCard from '../components/neurons/NeuronCard'
import NeuronForm from '../components/neurons/NeuronForm'
import Modal from '../components/ui/Modal'
import Button from '../components/ui/Button'
import Loading from '../components/ui/Loading'

export default function Dashboard() {
  const [showCreateModal, setShowCreateModal] = useState(false)

  const { data: neurons, isLoading, error } = useQuery({
    queryKey: ['neurons'],
    queryFn: neuronsAPI.list
  })

  if (isLoading) return <Loading />

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-tier-2 mb-4">Failed to load neurons</p>
          <Button onClick={() => window.location.reload()}>Retry</Button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold mb-2">Your Neurons</h1>
            <p className="text-gray-400">
              Manage your AI agents with complete privacy control
            </p>
          </div>
          <Button
            variant="primary"
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2"
          >
            <Plus size={20} />
            Create Neuron
          </Button>
        </div>

        {/* Empty state */}
        {neurons && neurons.length === 0 && (
          <div className="text-center py-16">
            <div className="inline-flex items-center justify-center w-20 h-20 bg-gray-800 rounded-full mb-4">
              <Plus size={32} className="text-gray-400" />
            </div>
            <h3 className="text-xl font-semibold mb-2">No neurons yet</h3>
            <p className="text-gray-400 mb-6">
              Create your first neuron to get started
            </p>
            <Button variant="primary" onClick={() => setShowCreateModal(true)}>
              Create Your First Neuron
            </Button>
          </div>
        )}

        {/* Neuron grid */}
        {neurons && neurons.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {neurons.map((neuron) => (
              <NeuronCard key={neuron.id} neuron={neuron} />
            ))}
          </div>
        )}

        {/* Create modal */}
        <Modal
          isOpen={showCreateModal}
          onClose={() => setShowCreateModal(false)}
          title="Create New Neuron"
        >
          <NeuronForm onSuccess={() => setShowCreateModal(false)} />
        </Modal>
      </div>
    </div>
  )
}
