/**
 * MessageList Component
 * Scrollable container for displaying message history
 */

'use client'

import { useEffect, useRef } from 'react'
import { Message } from '@/lib/types'
import { MessageBubble } from './MessageBubble'
import { LoadingIndicator } from './LoadingIndicator'

interface MessageListProps {
  messages: Message[]
  isLoading: boolean
  streamingMessageId?: string | null
}

export function MessageList({ messages, isLoading, streamingMessageId }: MessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6">
      <div className="mx-auto max-w-3xl space-y-6">
        {/* Empty state */}
        {messages.length === 0 && !isLoading && (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <div className="mb-4 rounded-full bg-blue-100 p-6">
              <svg
                className="h-12 w-12 text-blue-600"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
                />
              </svg>
            </div>
            <h3 className="mb-2 text-lg font-semibold text-gray-900">
              Texas Childcare Chatbot
            </h3>
            <p className="text-sm text-gray-600">
              Ask me anything about Texas childcare assistance programs,
              eligibility, income limits, and more.
            </p>
          </div>
        )}

        {/* Messages */}
        {messages.map((message) => (
          <MessageBubble
            key={message.id}
            message={message}
            isStreaming={message.id === streamingMessageId}
          />
        ))}

        {/* Loading indicator - only show if not streaming */}
        {isLoading && !streamingMessageId && (
          <div className="flex justify-start">
            <div className="max-w-[80%]">
              <div className="rounded-lg bg-gray-100 px-4 py-3">
                <LoadingIndicator />
              </div>
            </div>
          </div>
        )}

        {/* Scroll anchor */}
        <div ref={messagesEndRef} />
      </div>
    </div>
  )
}
