import client from './client'
import type { Neuron, CreateNeuronRequest } from '../types/neuron'

export const neuronsAPI = {
  // List user's neurons
  list: async (): Promise<Neuron[]> => {
    const response = await client.get('/neurons')
    return response.data
  },

  // Get single neuron
  get: async (id: string): Promise<Neuron> => {
    const response = await client.get(`/neurons/${id}`)
    return response.data
  },

  // Create neuron
  create: async (data: CreateNeuronRequest): Promise<Neuron> => {
    const response = await client.post('/neurons', data)
    return response.data
  },

  // Update neuron
  update: async (id: string, data: Partial<CreateNeuronRequest>): Promise<Neuron> => {
    const response = await client.patch(`/neurons/${id}`, data)
    return response.data
  },

  // Delete neuron
  delete: async (id: string): Promise<void> => {
    await client.delete(`/neurons/${id}`)
  }
}
