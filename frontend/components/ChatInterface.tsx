/**
 * ChatInterface Component
 * Main container component that manages chat state and coordinates all sub-components
 */

'use client'

import { useState } from 'react'
import { Message } from '@/lib/types'
import { askQuestion } from '@/lib/api'
import { generateId } from '@/lib/utils'
import { MessageList } from './MessageList'
import { InputBar } from './InputBar'
import { ErrorMessage } from './ErrorMessage'

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sessionId] = useState<string>(generateId())
  const [lastQuestion, setLastQuestion] = useState<string>('')

  const handleSubmit = async (question: string) => {
    // Clear any previous errors
    setError(null)

    // Store the question for retry functionality
    setLastQuestion(question)

    // Add user message
    const userMessage: Message = {
      id: generateId(),
      role: 'user',
      content: question,
      timestamp: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, userMessage])

    // Set loading state
    setIsLoading(true)

    try {
      // Call API
      const response = await askQuestion(question, sessionId)

      // Add assistant message
      const assistantMessage: Message = {
        id: generateId(),
        role: 'assistant',
        content: response.answer,
        sources: response.sources,
        action_items: response.action_items,
        response_type: response.response_type,
        timestamp: response.timestamp,
        processing_time: response.processing_time,
      }
      setMessages((prev) => [...prev, assistantMessage])
    } catch (err) {
      // Set error state
      const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred'
      setError(errorMessage)
      console.error('Chat error:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const handleRetry = () => {
    if (lastQuestion) {
      handleSubmit(lastQuestion)
    }
  }

  const handleDismissError = () => {
    setError(null)
  }

  const handleClearConversation = () => {
    if (confirm('Are you sure you want to clear the conversation?')) {
      setMessages([])
      setError(null)
      setLastQuestion('')
    }
  }

  return (
    <div className="flex h-screen flex-col bg-gray-50">
      {/* Header */}
      <header className="border-b border-gray-200 bg-white px-4 py-4 shadow-sm">
        <div className="mx-auto flex max-w-3xl items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-gray-900">
              Texas Childcare Chatbot
            </h1>
            <p className="text-sm text-gray-600">
              Get answers about childcare assistance in Texas
            </p>
          </div>
          {messages.length > 0 && (
            <button
              onClick={handleClearConversation}
              className="rounded-lg px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100"
            >
              Clear
            </button>
          )}
        </div>
      </header>

      {/* Error banner */}
      {error && (
        <div className="border-b border-red-200 px-4 py-3">
          <div className="mx-auto max-w-3xl">
            <ErrorMessage
              message={error}
              onRetry={lastQuestion ? handleRetry : undefined}
              onDismiss={handleDismissError}
            />
          </div>
        </div>
      )}

      {/* Messages */}
      <MessageList messages={messages} isLoading={isLoading} />

      {/* Input */}
      <InputBar onSubmit={handleSubmit} isLoading={isLoading} />
    </div>
  )
}
