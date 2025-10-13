/**
 * ActionCard Component
 * Displays clickable action items (links, buttons) for special responses
 */

'use client'

import { ActionItem } from '@/lib/types'

interface ActionCardProps {
  items: ActionItem[]
}

export function ActionCard({ items }: ActionCardProps) {
  if (!items || items.length === 0) {
    return null
  }

  return (
    <div className="mt-3 space-y-2 border-t border-gray-200 pt-3">
      {items.map((item, idx) => (
        <a
          key={idx}
          href={item.url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-between rounded-lg border-2 border-blue-600 bg-blue-50 px-4 py-3 transition-colors hover:bg-blue-100"
        >
          <div className="flex-1">
            <div className="font-semibold text-blue-900">{item.label}</div>
            {item.description && (
              <div className="mt-1 text-sm text-blue-700">{item.description}</div>
            )}
          </div>
          <svg
            className="ml-3 h-5 w-5 flex-shrink-0 text-blue-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
            />
          </svg>
        </a>
      ))}
    </div>
  )
}
