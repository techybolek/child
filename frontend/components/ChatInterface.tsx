/**
 * ChatInterface Component
 * Main container component that manages chat state and coordinates all sub-components
 */

'use client'

import { useState, useEffect } from 'react'
import { Message, ModelsResponse, RetrievalMode, ChatMode, OPENAI_AGENT_MODELS, VERTEX_AGENT_MODELS, BEDROCK_AGENT_MODELS } from '@/lib/types'
import { askQuestion, askQuestionStream, fetchAvailableModels } from '@/lib/api'
import { generateId } from '@/lib/utils'
import { MessageList } from './MessageList'
import { InputBar } from './InputBar'
import { ErrorMessage } from './ErrorMessage'
import { ModelSettings } from './ModelSettings'

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sessionId, setSessionId] = useState<string>(generateId())
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
  const [conversationalMode, setConversationalMode] = useState<boolean>(true)
  const [retrievalMode, setRetrievalMode] = useState<RetrievalMode>('dense')
  const [streamingMode, setStreamingMode] = useState<boolean>(true)
  const [streamingMessageId, setStreamingMessageId] = useState<string | null>(null)
  const [chatMode, setChatMode] = useState<ChatMode>('rag_pipeline')
  const [openaiAgentModel, setOpenaiAgentModel] = useState<string>(OPENAI_AGENT_MODELS[2].id) // gpt-5-nano default
  const [vertexAgentModel, setVertexAgentModel] = useState<string>(VERTEX_AGENT_MODELS[0].id) // gemini-2.5-flash default
  const [bedrockAgentModel, setBedrockAgentModel] = useState<string>(BEDROCK_AGENT_MODELS[0].id) // nova-micro default

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

  // Keyboard shortcut: Ctrl+Shift+K to clear chat (not R, that's browser refresh)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.shiftKey && e.key === 'K') {
        e.preventDefault()
        setMessages([])
        setError(null)
        setLastQuestion('')
        setSessionId(generateId())
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

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

  const handleModeChange = (mode: ChatMode) => {
    setChatMode(mode)
    // Clear conversation and start fresh session on mode switch
    setMessages([])
    setError(null)
    setLastQuestion('')
    setSessionId(generateId())
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

    // For OpenAI Agent mode, we only need the model selection
    // For RAG Pipeline mode, we need all the model options
    const modelOptions = chatMode === 'rag_pipeline' ? {
      provider: selectedProvider,
      llm_model: selectedModels.generator || undefined,
      reranker_model: selectedModels.reranker || undefined,
      intent_model: selectedModels.classifier || undefined,
      retrieval_mode: retrievalMode,
    } : {}

    // Agent modes don't support streaming
    if (streamingMode && chatMode === 'rag_pipeline') {
      // Streaming mode
      const assistantMessageId = generateId()
      setStreamingMessageId(assistantMessageId)

      // Add empty assistant message that will be updated with streamed tokens
      const assistantMessage: Message = {
        id: assistantMessageId,
        role: 'assistant',
        content: '',
        timestamp: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, assistantMessage])

      await askQuestionStream(
        question,
        sessionId,
        modelOptions,
        conversationalMode,
        // onToken
        (token: string) => {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? { ...msg, content: msg.content + token }
                : msg
            )
          )
        },
        // onDone
        (response) => {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? {
                    ...msg,
                    content: response.answer,
                    sources: response.sources,
                    action_items: response.action_items,
                    response_type: response.response_type,
                    processing_time: response.processing_time,
                  }
                : msg
            )
          )
          setIsLoading(false)
          setStreamingMessageId(null)
        },
        // onError
        (errorMsg: string) => {
          setError(errorMsg)
          setIsLoading(false)
          setStreamingMessageId(null)
        }
      )
    } else {
      // Non-streaming mode (or agent modes which don't support streaming)
      try {
        const response = await askQuestion(
          question,
          sessionId,
          modelOptions,
          chatMode === 'rag_pipeline' ? conversationalMode : undefined,
          chatMode,
          chatMode === 'openai_agent' ? openaiAgentModel : undefined,
          chatMode === 'vertex_agent' ? vertexAgentModel : undefined,
          chatMode === 'bedrock_agent' ? bedrockAgentModel : undefined
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
    setMessages([])
    setError(null)
    setLastQuestion('')
    setSessionId(generateId())  // New session resets backend conversation memory
  }

  return (
    <div className="flex h-screen flex-col bg-gray-50">
      {/* Header */}
      <header className="border-b border-gray-200 bg-white px-4 py-4 shadow-sm">
        <div className="mx-auto flex max-w-4xl items-center justify-between">
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
              retrievalMode={retrievalMode}
              onRetrievalModeChange={setRetrievalMode}
              conversationalMode={conversationalMode}
              onConversationalModeChange={setConversationalMode}
              streamingMode={streamingMode}
              onStreamingModeChange={setStreamingMode}
              chatMode={chatMode}
              onChatModeChange={handleModeChange}
              openaiAgentModel={openaiAgentModel}
              onOpenaiAgentModelChange={setOpenaiAgentModel}
              vertexAgentModel={vertexAgentModel}
              onVertexAgentModelChange={setVertexAgentModel}
              bedrockAgentModel={bedrockAgentModel}
              onBedrockAgentModelChange={setBedrockAgentModel}
            />
            {messages.length > 0 && (
              <button
                onClick={handleClearConversation}
                className="rounded-lg px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100"
              >
                Clear Chat
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Error banner */}
      {error && (
        <div className="border-b border-red-200 px-4 py-3">
          <div className="mx-auto max-w-4xl">
            <ErrorMessage
              message={error}
              onRetry={lastQuestion ? handleRetry : undefined}
              onDismiss={handleDismissError}
            />
          </div>
        </div>
      )}

      {/* Messages */}
      <MessageList messages={messages} isLoading={isLoading} streamingMessageId={streamingMessageId} />

      {/* Input */}
      <InputBar onSubmit={handleSubmit} isLoading={isLoading} />
    </div>
  )
}
