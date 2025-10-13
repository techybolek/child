/**
 * Utility functions for the Texas Childcare Chatbot frontend
 */

import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

/**
 * Merge Tailwind CSS classes with proper precedence
 *
 * @param inputs - Class names to merge
 * @returns Merged class string
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Format a timestamp to a human-readable time string
 *
 * @param timestamp - ISO 8601 timestamp string
 * @returns Formatted time string (e.g., "3:45 PM")
 */
export function formatTime(timestamp: string): string {
  try {
    const date = new Date(timestamp)
    return date.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
    })
  } catch {
    return ''
  }
}

/**
 * Format processing time in seconds to a readable string
 *
 * @param seconds - Processing time in seconds
 * @returns Formatted string (e.g., "3.2s")
 */
export function formatProcessingTime(seconds: number): string {
  return `${seconds.toFixed(1)}s`
}

/**
 * Generate a unique ID for messages
 *
 * @returns Unique ID string
 */
export function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
}
