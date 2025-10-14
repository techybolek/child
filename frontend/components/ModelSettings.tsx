/**
 * ModelSettings Component
 * Collapsible settings panel for selecting GROQ models
 */

'use client'

import { useState } from 'react'
import { Model } from '@/lib/types'

interface ModelSettingsProps {
  availableModels: {
    generators: Model[]
    rerankers: Model[]
    classifiers: Model[]
    defaults: {
      generator: string
      reranker: string
      classifier: string
    }
  } | null
  selectedProvider: string
  selectedModels: {
    generator: string | null
    reranker: string | null
    classifier: string | null
  }
  onProviderChange: (provider: string) => void
  onModelChange: (type: 'generator' | 'reranker' | 'classifier', modelId: string | null) => void
}

export function ModelSettings({
  availableModels,
  selectedProvider,
  selectedModels,
  onProviderChange,
  onModelChange
}: ModelSettingsProps) {
  const [isOpen, setIsOpen] = useState(false)

  console.log('[ModelSettings] Rendering with provider:', selectedProvider)
  console.log('[ModelSettings] Available models:', availableModels)

  if (!availableModels) {
    return null
  }

  return (
    <div className="relative">
      {/* Settings button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="rounded-lg p-2 text-gray-600 hover:bg-gray-100 hover:text-gray-900"
        title="Model Settings"
      >
        <svg
          className="h-5 w-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
          />
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
          />
        </svg>
      </button>

      {/* Dropdown panel */}
      {isOpen && (
        <div className="absolute right-0 top-12 z-10 w-80 rounded-lg border border-gray-200 bg-white p-4 shadow-lg">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-900">Model Settings</h3>
            <button
              onClick={() => setIsOpen(false)}
              className="text-gray-400 hover:text-gray-600"
            >
              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div className="space-y-3">
            {/* Provider selector */}
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-700">
                Provider
              </label>
              <select
                value={selectedProvider}
                onChange={(e) => {
                  console.log('[ModelSettings] Provider dropdown changed to:', e.target.value)
                  onProviderChange(e.target.value)
                }}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="groq">Groq</option>
                <option value="openai">OpenAI</option>
              </select>
            </div>

            {/* Generator model */}
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-700">
                Generator Model
              </label>
              <select
                value={selectedModels.generator || ''}
                onChange={(e) => onModelChange('generator', e.target.value || null)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="">Default ({availableModels.defaults.generator})</option>
                {availableModels.generators.map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Reranker model */}
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-700">
                Reranker Model
              </label>
              <select
                value={selectedModels.reranker || ''}
                onChange={(e) => onModelChange('reranker', e.target.value || null)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="">Default ({availableModels.defaults.reranker})</option>
                {availableModels.rerankers.map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Intent classifier model */}
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-700">
                Intent Classifier Model
              </label>
              <select
                value={selectedModels.classifier || ''}
                onChange={(e) => onModelChange('classifier', e.target.value || null)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="">Default ({availableModels.defaults.classifier})</option>
                {availableModels.classifiers.map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Reset button */}
            <button
              onClick={() => {
                onModelChange('generator', null)
                onModelChange('reranker', null)
                onModelChange('classifier', null)
              }}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-xs font-medium text-gray-700 hover:bg-gray-50"
            >
              Reset to Defaults
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
