/**
 * TypeScript type definitions for the Texas Childcare Chatbot frontend
 */

export interface Source {
  doc: string
  pages: number[]
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

export type RetrievalMode = 'dense' | 'hybrid' | 'kendra'

export type ChatMode = 'rag_pipeline' | 'openai_agent' | 'vertex_agent' | 'bedrock_agent'

export const OPENAI_AGENT_MODELS = [
  { id: 'gpt-4o-mini', name: 'GPT-4o Mini' },
  { id: 'gpt-4o', name: 'GPT-4o' },
  { id: 'gpt-5-nano', name: 'GPT-5 Nano' },
  { id: 'gpt-5-mini', name: 'GPT-5 Mini' },
  { id: 'gpt-5', name: 'GPT-5' },
] as const

export const VERTEX_AGENT_MODELS = [
  { id: 'gemini-2.5-flash', name: 'Gemini 2.5 Flash' },
  { id: 'gemini-2.5-pro', name: 'Gemini 2.5 Pro' },
  { id: 'gemini-2.0-flash', name: 'Gemini 2.0 Flash' },
] as const

export const BEDROCK_AGENT_MODELS = [
  { id: 'nova-micro', name: 'Nova Micro' },
  { id: 'nova-lite', name: 'Nova Lite' },
  { id: 'nova-pro', name: 'Nova Pro' },
] as const

export interface ChatRequest {
  question: string
  session_id?: string
  provider?: string
  llm_model?: string
  reranker_model?: string
  intent_model?: string
  retrieval_mode?: RetrievalMode
  conversational_mode?: boolean
  mode?: ChatMode
  openai_agent_model?: string
  vertex_agent_model?: string
  bedrock_agent_model?: string
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
