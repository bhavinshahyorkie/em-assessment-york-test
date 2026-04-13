/**
 * Match endpoint URL and error parsing. Uses Vite dev proxy `/api` unless `VITE_API_BASE` is set.
 */
import { redactLikelySecrets } from './redactClientMessage'

const API_BASE = (import.meta.env.VITE_API_BASE ?? '').replace(/\/$/, '')

export function getMatchEndpointUrl(): string {
  return API_BASE ? `${API_BASE}/match` : '/api/match'
}

/** Maps HTTP/API errors to a short user-visible string; strips patterns that could resemble tokens. */
export function parseApiError(res: Response, raw: string, data: unknown): string {
  let out: string
  if (typeof data === 'object' && data !== null && 'detail' in data) {
    const d = (data as { detail: unknown }).detail
    if (typeof d === 'string') {
      out = d
    } else if (Array.isArray(d)) {
      out = JSON.stringify(d)
    } else {
      out = `${res.status} ${res.statusText}`
    }
  } else {
    const lower = raw.toLowerCase()
    if (
      lower.includes('econnrefused') ||
      lower.includes('connect refused') ||
      lower.includes('socket hang up') ||
      lower.includes('econnreset')
    ) {
      out =
        'Cannot reach the API on port 8000. Start the backend (see README), then try again.'
    } else if (
      res.status === 500 &&
      (!raw.trim() || lower.includes('<!doctype') || lower.includes('<html') || lower.includes('internal server error'))
    ) {
      out = 'Server error. If the API is running, check the uvicorn terminal for details.'
    } else if (raw.trim()) {
      out = raw.length > 400 ? `${raw.slice(0, 400)}…` : raw
    } else {
      out = `${res.status} ${res.statusText}`
    }
  }
  return redactLikelySecrets(out)
}
