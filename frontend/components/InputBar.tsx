/**
 * InputBar Component
 * Text input field with submit button for asking questions
 */

'use client'

import { useState, SyntheticEvent, KeyboardEvent, useRef, useEffect } from 'react'

interface InputBarProps {
  onSubmit: (question: string) => void
  isLoading: boolean
}

const MAX_LENGTH = 500

export function InputBar({ onSubmit, isLoading }: InputBarProps) {
  const [input, setInput] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSubmit = (e: SyntheticEvent) => {
    e.preventDefault()
    const trimmed = input.trim()
    if (trimmed && !isLoading) {
      onSubmit(trimmed)
      setInput('')
      // Reset textarea height
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto'
      }
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Submit on Enter (but not Shift+Enter)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  // Auto-grow textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`
    }
  }, [input])

  const remaining = MAX_LENGTH - input.length
  const isOverLimit = remaining < 0

  return (
    <form onSubmit={handleSubmit} className="border-t border-gray-200 bg-white p-4">
      <div className="flex flex-col gap-2">
        <div className="flex gap-2">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about Texas childcare assistance..."
            className={`flex-1 resize-none rounded-lg border px-4 py-3 text-sm focus:outline-none focus:ring-2 ${
              isOverLimit
                ? 'border-red-300 focus:ring-red-500'
                : 'border-gray-300 focus:ring-blue-500'
            }`}
            rows={1}
            maxLength={MAX_LENGTH + 100} // Soft limit, allow typing over for warning
            disabled={isLoading}
          />

          <button
            type="submit"
            disabled={!input.trim() || isLoading || isOverLimit}
            className="self-end rounded-lg bg-blue-600 px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-gray-300"
          >
            {isLoading ? (
              <svg className="h-5 w-5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
            ) : (
              'Send'
            )}
          </button>
        </div>

        <div className="flex items-center justify-between px-1">
          <span className="text-xs text-gray-500">
            Press Enter to send, Shift+Enter for new line
          </span>
          <span
            className={`text-xs ${
              isOverLimit ? 'font-medium text-red-600' : 'text-gray-500'
            }`}
          >
            {input.length}/{MAX_LENGTH}
          </span>
        </div>
      </div>
    </form>
  )
}
