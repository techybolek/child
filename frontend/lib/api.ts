/**
 * API client for communicating with the FastAPI backend
 */

import { ChatRequest, ChatResponse, HealthResponse } from './types'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * Ask the chatbot a question
 *
 * @param question - The question to ask
 * @param sessionId - Optional session ID for conversation tracking
 * @returns Promise with the chatbot response
 * @throws Error if the request fails
 */
export async function askQuestion(
  question: string,
  sessionId?: string
): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE_URL}/api/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      question,
      session_id: sessionId,
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
