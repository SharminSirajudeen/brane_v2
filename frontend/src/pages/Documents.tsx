import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Upload, File, Trash2, Search, ArrowLeft } from 'lucide-react'
import { uploadFile, getDocuments, deleteDocument } from '../api/rag'
import type { Document } from '../api/rag'

export default function Documents() {
  const { neuronId } = useParams<{ neuronId: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [dragging, setDragging] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [uploading, setUploading] = useState(false)

  // Fetch documents
  const { data: documents = [], isLoading } = useQuery({
    queryKey: ['documents', neuronId],
    queryFn: () => getDocuments(neuronId!),
    enabled: !!neuronId
  })

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadFile(neuronId!, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents', neuronId] })
      setUploading(false)
    },
    onError: (error: any) => {
      alert(`Upload failed: ${error.response?.data?.detail || error.message}`)
      setUploading(false)
    }
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: deleteDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents', neuronId] })
    }
  })

  // Handle file upload
  const handleFileUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return

    const file = files[0]

    // Validate file type
    const validTypes = ['.pdf', '.txt', '.md']
    const fileExt = file.name.substring(file.name.lastIndexOf('.')).toLowerCase()

    if (!validTypes.includes(fileExt)) {
      alert(`Invalid file type. Supported: ${validTypes.join(', ')}`)
      return
    }

    setUploading(true)
    uploadMutation.mutate(file)
  }

  // Drag and drop handlers
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setDragging(true)
  }

  const handleDragLeave = () => {
    setDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    handleFileUpload(e.dataTransfer.files)
  }

  // Filter documents by search query
  const filteredDocuments = documents.filter(doc =>
    doc.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    doc.content.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 p-8">
      {/* Header */}
      <div className="max-w-6xl mx-auto mb-8">
        <button
          onClick={() => navigate(`/chat/${neuronId}`)}
          className="flex items-center gap-2 text-gray-400 hover:text-white mb-4 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Chat
        </button>

        <h1 className="text-3xl font-bold text-white mb-2">Document Library</h1>
        <p className="text-gray-400">
          Upload documents to enhance your neuron's knowledge base
        </p>
      </div>

      {/* Search */}
      <div className="max-w-6xl mx-auto mb-6">
        <div className="relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search documents..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-12 pr-4 py-3 bg-gray-800/50 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition-colors"
          />
        </div>
      </div>

      {/* Upload Area */}
      <div className="max-w-6xl mx-auto mb-8">
        <div
          className={`border-2 border-dashed rounded-lg p-12 text-center transition-all ${
            dragging
              ? 'border-blue-500 bg-blue-500/10'
              : 'border-gray-700 bg-gray-800/30'
          } ${uploading ? 'opacity-50 pointer-events-none' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />

          {uploading ? (
            <p className="text-gray-400">Uploading...</p>
          ) : (
            <>
              <p className="text-white mb-2">
                Drag and drop files here, or click to select
              </p>
              <p className="text-gray-500 text-sm mb-4">
                Supported formats: PDF, TXT, MD
              </p>
              <label className="inline-block">
                <input
                  type="file"
                  className="hidden"
                  accept=".pdf,.txt,.md"
                  onChange={(e) => handleFileUpload(e.target.files)}
                />
                <span className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg cursor-pointer transition-colors inline-block">
                  Choose File
                </span>
              </label>
            </>
          )}
        </div>
      </div>

      {/* Documents Grid */}
      <div className="max-w-6xl mx-auto">
        {isLoading ? (
          <div className="text-center text-gray-400 py-12">
            Loading documents...
          </div>
        ) : filteredDocuments.length === 0 ? (
          <div className="text-center text-gray-500 py-12">
            {searchQuery ? 'No documents match your search' : 'No documents uploaded yet'}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredDocuments.map((doc) => (
              <DocumentCard
                key={doc.id}
                document={doc}
                onDelete={() => deleteMutation.mutate(doc.id)}
                deleting={deleteMutation.isPending}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// Document Card Component
interface DocumentCardProps {
  document: Document
  onDelete: () => void
  deleting: boolean
}

function DocumentCard({ document, onDelete, deleting }: DocumentCardProps) {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)

  const handleDelete = () => {
    if (showDeleteConfirm) {
      onDelete()
      setShowDeleteConfirm(false)
    } else {
      setShowDeleteConfirm(true)
      setTimeout(() => setShowDeleteConfirm(false), 3000)
    }
  }

  return (
    <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-4 hover:border-gray-600 transition-colors">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2 flex-1">
          <File className="w-5 h-5 text-blue-400 flex-shrink-0" />
          <h3 className="text-white font-medium truncate">{document.title}</h3>
        </div>
        <button
          onClick={handleDelete}
          disabled={deleting}
          className={`p-2 rounded transition-colors ${
            showDeleteConfirm
              ? 'bg-red-600 hover:bg-red-700'
              : 'hover:bg-gray-700'
          } ${deleting ? 'opacity-50 cursor-not-allowed' : ''}`}
          title={showDeleteConfirm ? 'Click again to confirm' : 'Delete document'}
        >
          <Trash2 className={`w-4 h-4 ${showDeleteConfirm ? 'text-white' : 'text-gray-400'}`} />
        </button>
      </div>

      <p className="text-gray-400 text-sm line-clamp-3 mb-3">
        {document.content.substring(0, 150)}...
      </p>

      <div className="flex items-center justify-between text-xs text-gray-500">
        <span>{new Date(document.created_at).toLocaleDateString()}</span>
        <span>{(document.content.length / 1000).toFixed(1)}K chars</span>
      </div>
    </div>
  )
}
