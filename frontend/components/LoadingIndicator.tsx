/**
 * LoadingIndicator Component
 * Displays an animated "Thinking..." message while waiting for chatbot response
 */

export function LoadingIndicator() {
  return (
    <div className="flex items-center gap-2 text-gray-500">
      <div className="flex items-center gap-1">
        <span className="text-sm font-medium">Thinking</span>
        <span className="flex gap-0.5">
          <span className="animate-bounce [animation-delay:0ms]">.</span>
          <span className="animate-bounce [animation-delay:150ms]">.</span>
          <span className="animate-bounce [animation-delay:300ms]">.</span>
        </span>
      </div>
      <div className="h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600" />
    </div>
  )
}
