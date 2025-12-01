/**
 * API client for communicating with the FastAPI backend
 */

import { ChatRequest, ChatResponse, HealthResponse, ModelsResponse } from './types'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * Ask the chatbot a question
 *
 * @param question - The question to ask
 * @param sessionId - Optional session ID for conversation tracking
 * @param models - Optional model selection and provider
 * @param conversationalMode - Enable conversational memory
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
  },
  conversationalMode?: boolean
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
