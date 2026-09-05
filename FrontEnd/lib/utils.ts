import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Safely validate and return a URL for use in href attributes.
 * Only allows http:// and https:// protocols.
 * Blocks javascript:, data:, and other dangerous schemes.
 *
 * @param url - The URL to validate
 * @returns The URL if valid, undefined otherwise
 */
export function safeExternalUrl(url: string | undefined | null): string | undefined {
  if (!url) return undefined

  try {
    const parsed = new URL(url)
    if (parsed.protocol === "https:" || parsed.protocol === "http:") {
      return url
    }
  } catch {
    // Invalid URL format
  }
  return undefined
}
