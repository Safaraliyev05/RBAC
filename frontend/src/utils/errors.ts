import { AxiosError } from 'axios'

/**
 * Extract a human-readable error message array from an Axios error.
 */
export function extractErrors(error: unknown): string[] {
  if (error instanceof AxiosError && error.response?.data) {
    const data = error.response.data as Record<string, unknown>
    const messages: string[] = []

    if (typeof data === 'string') return [data]

    for (const [key, value] of Object.entries(data)) {
      if (Array.isArray(value)) {
        value.forEach((v) => messages.push(key === 'non_field_errors' || key === 'detail' ? String(v) : `${key}: ${v}`))
      } else if (typeof value === 'string') {
        messages.push(key === 'detail' || key === 'non_field_errors' ? value : `${key}: ${value}`)
      } else if (typeof value === 'object' && value !== null) {
        messages.push(`${key}: ${JSON.stringify(value)}`)
      }
    }
    return messages.length ? messages : ['An unexpected error occurred.']
  }
  if (error instanceof Error) return [error.message]
  return ['An unexpected error occurred.']
}
