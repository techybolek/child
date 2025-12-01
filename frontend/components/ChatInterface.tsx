/**
 * ChatInterface Component
 * Main container component that manages chat state and coordinates all sub-components
 */

'use client'

import { useState, useEffect } from 'react'
import { Message, ModelsResponse } from '@/lib/types'
import { askQuestion, fetchAvailableModels } from '@/lib/api'
import { generateId } from '@/lib/utils'
import { MessageList } from './MessageList'
import { InputBar } from './InputBar'
import { ErrorMessage } from './ErrorMessage'
import { ModelSettings } from './ModelSettings'

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sessionId] = useState<string>(generateId())
  const [lastQuestion, setLastQuestion] = useState<string>('')
  const [selectedProvider, setSelectedProvider] = useState<string>('groq')
  const [availableModels, setAvailableModels] = useState<ModelsResponse | null>(null)
  const [selectedModels, setSelectedModels] = useState<{
    generator: string | null
    reranker: string | null
    classifier: string | null
  }>({
    generator: null,
    reranker: null,
    classifier: null,
  })
  const [conversationalMode, setConversationalMode] = useState<boolean>(false)

  // Fetch available models on mount and when provider changes
  useEffect(() => {
    console.log('[ChatInterface] Provider changed to:', selectedProvider)
    const loadModels = async () => {
      try {
        console.log('[ChatInterface] Fetching models for provider:', selectedProvider)
        const models = await fetchAvailableModels(selectedProvider)
        console.log('[ChatInterface] Fetched models:', models)
        setAvailableModels(models)
      } catch (err) {
        console.error('Failed to fetch models:', err)
      }
    }
    loadModels()
  }, [selectedProvider])

  const handleProviderChange = (provider: string) => {
    console.log('[ChatInterface] handleProviderChange called with:', provider)
    setSelectedProvider(provider)
    // Reset model selections when provider changes
    setSelectedModels({
      generator: null,
      reranker: null,
      classifier: null,
    })
  }

  const handleModelChange = (
    type: 'generator' | 'reranker' | 'classifier',
    modelId: string | null
  ) => {
    setSelectedModels((prev) => ({
      ...prev,
      [type]: modelId,
    }))
  }

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
      // Call API with selected provider, models, and conversational mode
      const response = await askQuestion(
        question,
        sessionId,
        {
          provider: selectedProvider,
          llm_model: selectedModels.generator || undefined,
          reranker_model: selectedModels.reranker || undefined,
          intent_model: selectedModels.classifier || undefined,
        },
        conversationalMode
      )

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
          <div className="flex items-center gap-2">
            <ModelSettings
              availableModels={availableModels}
              selectedProvider={selectedProvider}
              selectedModels={selectedModels}
              onProviderChange={handleProviderChange}
              onModelChange={handleModelChange}
              conversationalMode={conversationalMode}
              onConversationalModeChange={setConversationalMode}
            />
            {messages.length > 0 && (
              <button
                onClick={handleClearConversation}
                className="rounded-lg px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100"
              >
                Clear
              </button>
            )}
          </div>
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
