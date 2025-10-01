import { useState } from 'react'
import type { KeyboardEvent } from 'react'
import { Send } from 'lucide-react'
import Button from '../ui/Button'

interface ChatInputProps {
  onSend: (message: string) => void
  disabled?: boolean
}

export default function ChatInput({ onSend, disabled = false }: ChatInputProps) {
  const [message, setMessage] = useState('')

  const handleSend = () => {
    if (message.trim() && !disabled) {
      onSend(message.trim())
      setMessage('')
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="border-t border-gray-700 p-4 bg-gray-900">
      <div className="flex gap-3 items-end">
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your message... (Shift+Enter for new line)"
          disabled={disabled}
          rows={1}
          className="flex-1 px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg resize-none focus:border-primary focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed"
          style={{ minHeight: '48px', maxHeight: '120px' }}
        />
        <Button
          onClick={handleSend}
          disabled={disabled || !message.trim()}
          variant="primary"
          className="flex items-center gap-2"
        >
          <Send size={16} />
          Send
        </Button>
      </div>
    </div>
  )
}
