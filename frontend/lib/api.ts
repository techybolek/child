/**
 * API client for communicating with the FastAPI backend
 */

import { ChatRequest, ChatResponse, HealthResponse, ModelsResponse, ChatMode } from './types'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * Ask the chatbot a question
 *
 * @param question - The question to ask
 * @param sessionId - Optional session ID for conversation tracking
 * @param models - Optional model selection, provider, and retrieval mode
 * @param conversationalMode - Enable conversational memory
 * @param mode - Chat mode: 'rag_pipeline', 'openai_agent', 'vertex_agent', or 'bedrock_agent'
 * @param openaiAgentModel - Model for OpenAI Agent mode
 * @param vertexAgentModel - Model for Vertex Agent mode
 * @param bedrockAgentModel - Model for Bedrock Agent mode
 * @returns Promise with the chatbot response
 * @throws Error if the request fails
 */
export async function askQuestion(
  question: string,
  sessionId?: string,
  models?: {
    provider?: string
    llm_model?: string
    reranker_model?: string
    intent_model?: string
    retrieval_mode?: string
  },
  conversationalMode?: boolean,
  mode?: ChatMode,
  openaiAgentModel?: string,
  vertexAgentModel?: string,
  bedrockAgentModel?: string
): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE_URL}/api/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      question,
      session_id: sessionId,
      ...models,
      conversational_mode: conversationalMode,
      mode,
      openai_agent_model: openaiAgentModel,
      vertex_agent_model: vertexAgentModel,
      bedrock_agent_model: bedrockAgentModel,
    } as ChatRequest),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => null)
    const errorMessage = error?.detail?.message || error?.detail || 'Failed to get response from chatbot'
    throw new Error(errorMessage)
  }

  return response.json()
}

/**
 * Check the health status of the API
 *
 * @returns Promise with health status
 * @throws Error if the request fails
 */
export async function checkHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/api/health`)

  if (!response.ok) {
    throw new Error('Failed to check API health')
  }

  return response.json()
}

/**
 * Fetch available models for the specified provider
 *
 * @param provider - 'groq' or 'openai' (default: 'groq')
 * @returns Promise with available models
 * @throws Error if the request fails
 */
export async function fetchAvailableModels(provider: string = 'groq'): Promise<ModelsResponse> {
  console.log('[API] Fetching models from:', `${API_BASE_URL}/api/models?provider=${provider}`)
  const response = await fetch(`${API_BASE_URL}/api/models?provider=${provider}`)

  if (!response.ok) {
    console.error('[API] Failed to fetch models, status:', response.status)
    throw new Error('Failed to fetch available models')
  }

  const data = await response.json()
  console.log('[API] Received models data:', data)
  return data
}

/**
 * Fetch available models for Vertex Agent mode
 *
 * @returns Promise with available Vertex Agent models and default
 * @throws Error if the request fails
 */
export async function fetchVertexAgentModels(): Promise<{ models: { id: string; name: string }[]; default: string }> {
  console.log('[API] Fetching Vertex Agent models from:', `${API_BASE_URL}/api/models/vertex-agent`)
  const response = await fetch(`${API_BASE_URL}/api/models/vertex-agent`)

  if (!response.ok) {
    console.error('[API] Failed to fetch Vertex Agent models, status:', response.status)
    throw new Error('Failed to fetch Vertex Agent models')
  }

  const data = await response.json()
  console.log('[API] Received Vertex Agent models data:', data)
  return data
}

/**
 * Stream chat response via SSE
 *
 * @param question - The question to ask
 * @param sessionId - Optional session ID for conversation tracking
 * @param models - Optional model selection, provider, and retrieval mode
 * @param conversationalMode - Enable conversational memory
 * @param onToken - Callback for each token received
 * @param onDone - Callback when streaming completes with final response
 * @param onError - Callback for errors
 */
export async function askQuestionStream(
  question: string,
  sessionId: string | undefined,
  models: {
    provider?: string
    llm_model?: string
    reranker_model?: string
    intent_model?: string
    retrieval_mode?: string
  } | undefined,
  conversationalMode: boolean | undefined,
  onToken: (token: string) => void,
  onDone: (response: ChatResponse) => void,
  onError: (error: string) => void
): Promise<void> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        question,
        session_id: sessionId,
        ...models,
        conversational_mode: conversationalMode,
      } as ChatRequest),
    })

    if (!response.ok) {
      const error = await response.json().catch(() => null)
      const errorMessage = error?.detail?.message || error?.detail || 'Failed to get streaming response'
      throw new Error(errorMessage)
    }

    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error('No response body')
    }

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      // Parse SSE events from buffer
      const lines = buffer.split('\n')
      buffer = lines.pop() || '' // Keep incomplete line in buffer

      let eventType = ''
      for (const line of lines) {
        if (line.startsWith('event: ')) {
          eventType = line.slice(7).trim()
        } else if (line.startsWith('data: ')) {
          const data = line.slice(6)
          try {
            const parsed = JSON.parse(data)

            if (eventType === 'token') {
              onToken(parsed.content)
            } else if (eventType === 'done') {
              // Convert to ChatResponse format
              const chatResponse: ChatResponse = {
                answer: parsed.answer,
                sources: parsed.sources.map((s: { doc: string; pages: number[]; url: string }) => ({
                  doc: s.doc,
                  pages: s.pages,
                  url: s.url,
                })),
                response_type: parsed.response_type,
                action_items: parsed.action_items || [],
                processing_time: parsed.processing_time,
                session_id: parsed.session_id,
                timestamp: new Date().toISOString(),
              }
              onDone(chatResponse)
            } else if (eventType === 'error') {
              onError(parsed.message)
            }
          } catch {
            // Ignore JSON parse errors for incomplete data
          }
        }
      }
    }
  } catch (error) {
    onError(error instanceof Error ? error.message : 'Unknown error')
  }
}
