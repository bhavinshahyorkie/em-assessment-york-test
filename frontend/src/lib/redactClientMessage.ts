/**
 * Sanitize error strings shown in the browser so we never surface tokens that look like API keys
 * if a provider ever echoes them in an error body (defense in depth; keys stay server-side only).
 */
export function redactLikelySecrets(message: string): string {
  return message
    .replace(/\bsk-[a-zA-Z0-9_-]{8,}\b/g, '[redacted]')
    .replace(/\bBearer\s+[A-Za-z0-9._-]+\b/gi, 'Bearer [redacted]')
    .replace(/\bapi[_-]?key\s*[:=]\s*\S+/gi, 'api_key=[redacted]')
}
