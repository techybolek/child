/**
 * MessageBubble Component
 * Displays individual user and assistant messages
 */

'use client'

import { Message } from '@/lib/types'
import { formatTime, formatProcessingTime } from '@/lib/utils'
import { SourceCard } from './SourceCard'
import { ActionCard } from './ActionCard'
import ReactMarkdown from 'react-markdown'

interface MessageBubbleProps {
  message: Message
  isStreaming?: boolean
}

export function MessageBubble({ message, isStreaming = false }: MessageBubbleProps) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-full ${isUser ? 'order-2' : 'order-1'}`}>
        <div
          className={`rounded-lg px-4 py-3 ${
            isUser
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 text-gray-900'
          }`}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap text-sm">{message.content}</p>
          ) : (
            <div className="prose prose-sm max-w-none">
              <ReactMarkdown
                components={{
                  // Customize markdown rendering
                  p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                  ul: ({ children }) => <ul className="mb-2 ml-4 list-disc">{children}</ul>,
                  ol: ({ children }) => <ol className="mb-2 ml-4 list-decimal">{children}</ol>,
                  li: ({ children }) => <li className="mb-1">{children}</li>,
                  strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
                  em: ({ children }) => <em className="italic">{children}</em>,
                  code: ({ children }) => (
                    <code className="rounded bg-gray-200 px-1 py-0.5 text-xs font-mono">
                      {children}
                    </code>
                  ),
                  table: ({ children }) => (
                    <div className="overflow-x-auto">
                      <table className="min-w-full divide-y divide-gray-300">{children}</table>
                    </div>
                  ),
                  thead: ({ children }) => <thead className="bg-gray-50">{children}</thead>,
                  th: ({ children }) => (
                    <th className="px-3 py-2 text-left text-xs font-semibold">{children}</th>
                  ),
                  td: ({ children }) => (
                    <td className="px-3 py-2 text-xs">{children}</td>
                  ),
                }}
              >
                {message.content}
              </ReactMarkdown>
              {isStreaming && (
                <span className="inline-block w-2 h-4 ml-1 bg-gray-600 animate-pulse" />
              )}
            </div>
          )}

          {/* Action items for special responses */}
          {!isUser && message.action_items && message.action_items.length > 0 && (
            <ActionCard items={message.action_items} />
          )}

          {/* Sources for assistant messages */}
          {!isUser && message.sources && message.sources.length > 0 && (
            <SourceCard sources={message.sources} />
          )}
        </div>

        {/* Metadata */}
        <div className={`mt-1 flex items-center gap-2 px-1 text-xs text-gray-500 ${isUser ? 'justify-end' : 'justify-start'}`}>
          <span>{formatTime(message.timestamp)}</span>
          {!isUser && message.processing_time && (
            <>
              <span>•</span>
              <span>{formatProcessingTime(message.processing_time)}</span>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
