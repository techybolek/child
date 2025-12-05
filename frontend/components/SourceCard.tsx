/**
 * SourceCard Component
 * Displays collapsible list of document sources with page numbers
 */

'use client'

import { useState } from 'react'
import { Source } from '@/lib/types'

interface SourceCardProps {
  sources: Source[]
}

export function SourceCard({ sources }: SourceCardProps) {
  const [expanded, setExpanded] = useState(false)

  if (!sources || sources.length === 0) {
    return null
  }

  return (
    <div className="mt-3 border-t border-gray-200 pt-3">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 text-sm font-medium text-gray-700 hover:text-gray-900"
      >
        <svg
          className={`h-4 w-4 transition-transform ${expanded ? 'rotate-90' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
        <span>📚 {sources.length} {sources.length === 1 ? 'source' : 'sources'}</span>
      </button>

      {expanded && (
        <ul className="mt-2 space-y-2">
          {sources.map((source, index) => (
            <li key={index} className="flex items-start gap-2 text-sm">
              <svg
                className="mt-0.5 h-4 w-4 flex-shrink-0 text-blue-600"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
              <div className="flex-1">
                {source.url ? (
                  <a
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:underline"
                  >
                    {source.doc}
                  </a>
                ) : (
                  <span className="text-gray-700">{source.doc}</span>
                )}
                {source.pages.length > 0 && (
                  <span className="ml-1 text-gray-500">
                    (Page {source.pages.join(', ')})
                  </span>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
