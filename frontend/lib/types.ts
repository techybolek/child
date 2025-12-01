/**
 * TypeScript type definitions for the Texas Childcare Chatbot frontend
 */

export interface Source {
  doc: string
  page: number
  url: string
}

export interface ActionItem {
  type: string
  url: string
  label: string
  description?: string
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: Source[]
  action_items?: ActionItem[]
  response_type?: string
  timestamp: string
  processing_time?: number
}

export interface ChatRequest {
  question: string
  session_id?: string
  provider?: string
  llm_model?: string
  reranker_model?: string
  intent_model?: string
  conversational_mode?: boolean
}

export interface ChatResponse {
  answer: string
  sources: Source[]
  response_type?: string
  action_items?: ActionItem[]
  processing_time: number
  session_id: string
  timestamp: string
}

export interface HealthResponse {
  status: string
  chatbot_initialized: boolean
  timestamp: string
  error?: string
}

export interface Model {
  id: string
  name: string
}

export interface DefaultModels {
  generator: string
  reranker: string
  classifier: string
}

export interface ModelsResponse {
  provider: string
  generators: Model[]
  rerankers: Model[]
  classifiers: Model[]
  defaults: DefaultModels
}
