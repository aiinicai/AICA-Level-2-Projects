// Input validation for every IPC request. Pure functions (no Electron imports) so they can be unit-tested.
// The renderer is treated as untrusted: each handler validates its arguments before touching the disk or network.

import type { AiProvider, AiRequest, FileFilter } from '../shared/contracts'
import { checkBaseUrl, cleanModelName, isAiProvider, isValidModelName, keyProblem, keyShapeWarning, maskKey } from '../shared/aiProviders'

export class ValidationError extends Error {}

function fail(message: string): never {
  throw new ValidationError(message)
}

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null && !Array.isArray(v)
}

export function asRecord(v: unknown, what: string): Record<string, unknown> {
  if (!isRecord(v)) fail(`The ${what} request was not understood.`)
  return v
}

export function optionalString(v: unknown, field: string, max: number): string | undefined {
  if (v === undefined || v === null) return undefined
  if (typeof v !== 'string' || v.length > max) fail(`"${field}" must be text of at most ${max} characters.`)
  return v
}

export function requiredString(v: unknown, field: string, max: number): string {
  const s = optionalString(v, field, max)
  if (s === undefined || s.trim() === '') fail(`"${field}" is required.`)
  return s
}

export function optionalBoolean(v: unknown, field: string): boolean {
  if (v === undefined || v === null) return false
  if (typeof v !== 'boolean') fail(`"${field}" must be true or false.`)
  return v
}

const EXTENSION = /^(\*|[A-Za-z0-9]{1,10})$/

export function fileFilters(v: unknown): FileFilter[] | undefined {
  if (v === undefined || v === null) return undefined
  if (!Array.isArray(v) || v.length > 20) fail('The file type list was not understood.')
  return v.map((f) => {
    const r = asRecord(f, 'file type')
    const name = requiredString(r.name, 'filter name', 100)
    if (!Array.isArray(r.extensions) || r.extensions.length === 0 || r.extensions.length > 30) {
      fail('Each file type needs at least one extension.')
    }
    const extensions = r.extensions.map((e) => {
      if (typeof e !== 'string') fail('File extensions must be text.')
      const clean = e.replace(/^\./, '')
      if (!EXTENSION.test(clean)) fail(`"${e}" is not a valid file extension.`)
      return clean
    })
    return { name, extensions }
  })
}

// Characters Windows does not allow in file names, plus control characters.
const ILLEGAL_FILENAME = /[<>:"/\\|?*\u0000-\u001F]/g
const RESERVED_NAME = /^(con|prn|aux|nul|com\d|lpt\d)(\..*)?$/i

/** Turns any suggested name into a safe Windows file name (no folders, no reserved names). */
export function safeFileName(v: unknown, fallback = 'Reco-Do export'): string {
  const raw = typeof v === 'string' ? v : ''
  let name = raw.replace(ILLEGAL_FILENAME, '_').replace(/\s+/g, ' ').trim().replace(/[. ]+$/, '')
  if (name.length > 180) {
    const dot = name.lastIndexOf('.')
    const ext = dot > 0 && name.length - dot <= 10 ? name.slice(dot) : ''
    name = name.slice(0, 180 - ext.length) + ext
  }
  if (!name || name.replace(/_/g, '') === '' || RESERVED_NAME.test(name)) name = fallback
  return name
}

export const MAX_FILE_BYTES = 512 * 1024 * 1024

export function binaryData(v: unknown): Uint8Array {
  let bytes: Uint8Array
  if (v instanceof Uint8Array) bytes = v
  else if (v instanceof ArrayBuffer) bytes = new Uint8Array(v)
  else fail('There was no file content to save.')
  if (bytes.byteLength > MAX_FILE_BYTES) fail('The file is too large to save (limit 512 MB).')
  return bytes
}

/**
 * A sample path must be relative, use forward slashes, and stay inside sample-data.
 * Returns the cleaned path segments; the caller still checks the resolved path against the folder.
 */
export function samplePathSegments(v: unknown): string[] {
  const p = requiredString(v, 'sample path', 300)
  if (p.includes('\\') || p.includes('\0') || p.startsWith('/') || /^[A-Za-z]:/.test(p)) fail('That sample file path is not allowed.')
  const segments = p.split('/')
  if (segments.some((s) => s === '' || s === '.' || s === '..' || s.startsWith('.'))) fail('That sample file path is not allowed.')
  return segments
}

export const MAX_HTML_CHARS = 30 * 1024 * 1024

export function pdfRequest(v: unknown): { html: string; defaultName: string; landscape: boolean } {
  const r = asRecord(v, 'PDF')
  const html = requiredString(r.html, 'html', MAX_HTML_CHARS)
  let defaultName = safeFileName(r.defaultName, 'Reco-Do summary.pdf')
  if (!/\.pdf$/i.test(defaultName)) defaultName += '.pdf'
  return { html, defaultName, landscape: optionalBoolean(r.landscape, 'landscape') }
}

export { maskKey }

export function aiProviderArg(v: unknown): AiProvider {
  if (v === undefined || v === null) return 'anthropic'
  if (!isAiProvider(v)) fail('That AI provider is not supported.')
  return v
}

/**
 * A pasted key: trimmed, not empty, no spaces or control characters. The provider's usual format is only a
 * warning (formats change), returned with the key.
 */
export function apiKey(v: unknown, provider: AiProvider = 'anthropic'): { key: string; warning: string | null } {
  if (typeof v !== 'string') fail(keyProblem(provider, '') as string)
  const key = v.trim()
  const problem = keyProblem(provider, key)
  if (problem) fail(problem)
  return { key, warning: keyShapeWarning(provider, key) }
}

/** The key-save request: `{ provider, key }`, or a bare string (older form, an Anthropic key). */
export function apiKeyRequest(v: unknown): { provider: AiProvider; key: string; warning: string | null } {
  if (typeof v === 'string') return { provider: 'anthropic', ...apiKey(v, 'anthropic') }
  const r = asRecord(v, 'API key')
  const provider = aiProviderArg(r.provider)
  return { provider, ...apiKey(r.key, provider) }
}

/** A custom base URL to save, cleaned; null clears it. */
export function customBaseUrl(v: unknown): string | null {
  if (v === undefined || v === null || (typeof v === 'string' && v.trim() === '')) return null
  if (typeof v !== 'string') fail('The base URL must be text.')
  const c = checkBaseUrl(v)
  if (!c.ok) fail(c.message)
  return c.url
}

/**
 * Caps for one Smart Recon call. A batch is at most 500 lines of about 300 characters each plus the prompt, so
 * 400,000 characters leaves room while refusing anything far larger; replies never need more than 32,000 tokens.
 */
export const MAX_PROMPT_CHARS = 400_000
export const MAX_AI_TOKENS = 32_000
const REQUEST_ID = /^[A-Za-z0-9-]{1,64}$/

export function aiRequestId(v: unknown): string {
  if (typeof v !== 'string' || !REQUEST_ID.test(v)) fail('The Smart Recon request id was not understood.')
  return v
}

export function aiRequest(v: unknown): AiRequest {
  const r = asRecord(v, 'Smart Recon')
  const provider = aiProviderArg(r.provider)
  const model = cleanModelName(provider, requiredString(r.model, 'model', 200))
  if (!isValidModelName(provider, model)) fail('The AI model name in Settings is not valid.')
  const system = optionalString(r.system, 'system', MAX_PROMPT_CHARS) ?? ''
  if (!Array.isArray(r.messages) || r.messages.length === 0 || r.messages.length > 50) fail('The Smart Recon request has no messages.')
  let total = system.length
  const messages = r.messages.map((m) => {
    const msg = asRecord(m, 'message')
    const role: 'user' | 'assistant' =
      msg.role === 'user' || msg.role === 'assistant' ? msg.role : fail('A Smart Recon message has an unknown role.')
    const content = requiredString(msg.content, 'message content', MAX_PROMPT_CHARS)
    total += content.length
    return { role, content }
  })
  if (total > MAX_PROMPT_CHARS) fail('The Smart Recon request is too large to send in one go. Send fewer rows per batch.')
  const maxTokens = r.maxTokens
  if (typeof maxTokens !== 'number' || !Number.isInteger(maxTokens) || maxTokens < 1 || maxTokens > MAX_AI_TOKENS) {
    fail('The Smart Recon reply limit must be a whole number between 1 and 32,000 tokens.')
  }
  const out: AiRequest = { model, system, messages, maxTokens }
  if (r.provider !== undefined && r.provider !== null) out.provider = provider
  if (provider === 'custom') {
    const base = customBaseUrl(r.baseUrl)
    if (!base) fail('Enter and save the base URL of the AI service in Settings first.')
    out.baseUrl = base
  }
  if (r.requestId !== undefined && r.requestId !== null) out.requestId = aiRequestId(r.requestId)
  const effort = r.effort
  if (effort === undefined || effort === null) return out
  if (effort !== 'low' && effort !== 'medium' && effort !== 'high') fail('"effort" must be low, medium or high.')
  out.effort = effort
  return out
}
