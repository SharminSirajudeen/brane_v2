import client from './client'

export interface Document {
  id: string
  neuron_id: string
  title: string
  content: string
  doc_metadata: Record<string, any>
  created_at: string
  updated_at: string
}

export interface SearchResult {
  content: string
  metadata: Record<string, any>
  score: number
}

// Upload document (text content)
export const uploadDocument = async (neuronId: string, title: string, content: string) => {
  const response = await client.post('/rag/upload', {
    neuron_id: neuronId,
    title,
    content
  })
  return response.data
}

// Upload document (file)
export const uploadFile = async (neuronId: string, file: File) => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('neuron_id', neuronId)

  const response = await client.post('/rag/upload-file', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
  return response.data
}

// Search documents
export const searchDocuments = async (neuronId: string, query: string, topK: number = 5) => {
  const response = await client.post<SearchResult[]>(`/rag/search/${neuronId}`, {
    query,
    top_k: topK
  })
  return response.data
}

// Get all documents for a neuron
export const getDocuments = async (neuronId: string) => {
  const response = await client.get<Document[]>(`/rag/${neuronId}/documents`)
  return response.data
}

// Delete document
export const deleteDocument = async (documentId: string) => {
  const response = await client.delete(`/rag/documents/${documentId}`)
  return response.data
}
