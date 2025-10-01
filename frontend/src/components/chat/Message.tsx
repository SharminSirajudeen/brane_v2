import { User, Bot } from 'lucide-react'
import type { Message as MessageType } from '../../types/chat'

interface MessageProps {
  message: MessageType | { role: 'user' | 'assistant'; content: string }
  isStreaming?: boolean
}

export default function Message({ message, isStreaming = false }: MessageProps) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex gap-4 ${isUser ? 'justify-end' : 'justify-start'} mb-6`}>
      {!isUser && (
        <div className="flex-shrink-0 w-8 h-8 bg-primary rounded-full flex items-center justify-center">
          <Bot size={16} className="text-white" />
        </div>
      )}

      <div
        className={`max-w-[70%] rounded-lg px-4 py-3 ${
          isUser
            ? 'bg-primary text-white'
            : 'bg-gray-800 text-gray-100 border border-gray-700'
        }`}
      >
        <p className="text-sm whitespace-pre-wrap break-words">{message.content}</p>

        {isStreaming && !isUser && (
          <div className="mt-2 flex gap-1">
            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
          </div>
        )}
      </div>

      {isUser && (
        <div className="flex-shrink-0 w-8 h-8 bg-gray-700 rounded-full flex items-center justify-center">
          <User size={16} className="text-gray-300" />
        </div>
      )}
    </div>
  )
}
