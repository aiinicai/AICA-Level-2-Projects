// The AI services Smart Recon can use, shared by the main process (HTTP call, key storage, network allowlist) and
// the page (Settings, Smart Recon panel). Pure TypeScript: no Electron, no DOM.
//
// Endpoints and default models were checked against each provider's own documentation in October 2026:
//   Anthropic  https://api.anthropic.com/v1/messages                       (x-api-key)
//   OpenAI     https://api.openai.com/v1/responses                         (Authorization: Bearer)
//   Gemini     https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent (x-goog-api-key)
//   DeepSeek   https://api.deepseek.com/chat/completions                   (Authorization: Bearer, OpenAI format)
//   Other      <saved base URL>/chat/completions                           (Authorization: Bearer, optional)

import type { AiProvider } from './contracts'

export const AI_PROVIDERS: readonly AiProvider[] = ['anthropic', 'openai', 'gemini', 'deepseek', 'custom']

export interface AiProviderInfo {
  id: AiProvider
  /** Name in the provider picker. */
  label: string
  /** Short name used in sentences: "Your OpenAI API key…", "Sends to: OpenAI · gpt-…". */
  name: string
  /** Official API origin (null for 'custom', which uses the saved base URL). */
  origin: string | null
  /** Model used when the Settings field is empty ('' for 'custom': the user must enter one). */
  defaultModel: string
  /** Where to create a key, for hints and the bad-key message. */
  keyWhere: string
  /** Placeholder for the key field. */
  keyPlaceholder: string
  /** The usual key format; a key that does not match is saved anyway, with a warning (formats change). */
  keyShape: RegExp | null
  keyShapeText: string
  /** False only for 'custom': local servers usually need no key. */
  keyRequired: boolean
}

export const AI_PROVIDER_INFO: Record<AiProvider, AiProviderInfo> = {
  anthropic: {
    id: 'anthropic',
    label: 'Anthropic Claude',
    name: 'Claude',
    origin: 'https://api.anthropic.com',
    defaultModel: 'claude-sonnet-5-5',
    keyWhere: 'console.anthropic.com',
    keyPlaceholder: 'sk-ant-…',
    keyShape: /^sk-ant-[A-Za-z0-9_-]{10,}$/,
    keyShapeText: 'Claude keys usually start with "sk-ant-".',
    keyRequired: true
  },
  openai: {
    id: 'openai',
    label: 'OpenAI (ChatGPT)',
    name: 'OpenAI',
    origin: 'https://api.openai.com',
    defaultModel: 'gpt-6.1-sol',
    keyWhere: 'platform.openai.com (API keys)',
    keyPlaceholder: 'sk-…',
    keyShape: /^sk-[A-Za-z0-9_-]{16,}$/,
    keyShapeText: 'OpenAI keys usually start with "sk-" (for example "sk-proj-").',
    keyRequired: true
  },
  gemini: {
    id: 'gemini',
    label: 'Google Gemini',
    name: 'Gemini',
    origin: 'https://generativelanguage.googleapis.com',
    defaultModel: 'gemini-3.8-flash',
    keyWhere: 'Google AI Studio (aistudio.google.com)',
    keyPlaceholder: 'AIza…',
    keyShape: /^AIza[A-Za-z0-9_-]{30,}$/,
    keyShapeText: 'Gemini API keys from Google AI Studio usually start with "AIza".',
    keyRequired: true
  },
  deepseek: {
    id: 'deepseek',
    label: 'DeepSeek',
    name: 'DeepSeek',
    origin: 'https://api.deepseek.com',
    defaultModel: 'deepseek-flash',
    keyWhere: 'platform.deepseek.com (API keys)',
    keyPlaceholder: 'sk-…',
    keyShape: /^sk-[A-Za-z0-9_-]{16,}$/,
    keyShapeText: 'DeepSeek keys usually start with "sk-".',
    keyRequired: true
  },
  custom: {
    id: 'custom',
    label: 'Other (OpenAI-compatible)',
    name: 'the custom AI service',
    origin: null,
    defaultModel: '',
    keyWhere: "the service's own website",
    keyPlaceholder: 'Optional for local servers',
    keyShape: null,
    keyShapeText: '',
    keyRequired: false
  }
}

export function isAiProvider(v: unknown): v is AiProvider {
  return typeof v === 'string' && (AI_PROVIDERS as readonly string[]).includes(v)
}

// ───────────────────────── Keys ─────────────────────────

/** Longest key accepted (real keys are far shorter; gateway tokens can be long). */
export const MAX_KEY_CHARS = 2_000
/** Printable ASCII without spaces: every provider's keys fit, and a pasted sentence or line break does not. */
const KEY_CHARS = /^[\x21-\x7E]+$/

/** Plain-English problem with a pasted key that must block saving, or null when it can be saved. */
export function keyProblem(provider: AiProvider, key: string): string | null {
  const info = AI_PROVIDER_INFO[provider]
  if (!key) return provider === 'custom' ? 'Paste the API key for this service first.' : `Please paste your ${info.name} API key.`
  if (key.length > MAX_KEY_CHARS) return 'That key is far too long to be an API key. Copy just the key and try again.'
  if (!KEY_CHARS.test(key)) return `That key contains spaces or unexpected characters. Copy it again from ${info.keyWhere}.`
  return null
}

/** A warning (never a block) when the key does not look like the provider's usual format. */
export function keyShapeWarning(provider: AiProvider, key: string): string | null {
  const info = AI_PROVIDER_INFO[provider]
  if (!info.keyShape) return null
  if (provider !== 'anthropic' && /^sk-ant-/.test(key)) return `This looks like a Claude key, not a ${info.name} key. It was saved, but ${info.name} will probably refuse it.`
  if (provider !== 'gemini' && /^AIza/.test(key)) return `This looks like a Google key, not a ${info.name} key. It was saved, but ${info.name} will probably refuse it.`
  if (info.keyShape.test(key)) return null
  return `This key does not look like the usual format. ${info.keyShapeText} It was saved anyway; use Test connection to check it.`
}

const KNOWN_PREFIXES = ['sk-ant-', 'sk-proj-', 'sk-or-', 'sk-', 'gsk_', 'AIza']

/** "sk-ant-api03-…3f9a" → "sk-ant-…3f9a"; unknown formats show only the last four characters. */
export function maskKey(key: string): string {
  if (key.length < 12) return '••••'
  const prefix = KNOWN_PREFIXES.find((p) => key.startsWith(p)) ?? ''
  return `${prefix}…${key.slice(-4)}`
}

// ───────────────────────── Models ─────────────────────────

/**
 * Letters, digits and . _ : @ / + - (Ollama uses "llama3.1:8b", OpenRouter "openai/gpt-5"). Gemini puts the model
 * into the URL path, so ':' and '/' are not allowed there (an optional leading "models/" is removed first).
 */
const MODEL_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._:@/+-]{0,199}$/
const GEMINI_MODEL_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._-]{0,199}$/

export function cleanModelName(provider: AiProvider, model: string): string {
  const m = model.trim()
  return provider === 'gemini' ? m.replace(/^models\//, '') : m
}

export function isValidModelName(provider: AiProvider, model: string): boolean {
  const m = cleanModelName(provider, model)
  return provider === 'gemini' ? GEMINI_MODEL_PATTERN.test(m) : MODEL_PATTERN.test(m)
}

/** True when the model accepts a reasoning-effort setting through Reco-Do's request for that provider. */
export function supportsEffort(provider: AiProvider, model: string): boolean {
  const m = cleanModelName(provider, model).toLowerCase()
  switch (provider) {
    case 'anthropic':
      return true
    case 'openai':
      // Reasoning models only; older chat models (gpt-4o, gpt-4.1) reject the parameter.
      return /^(gpt-5|gpt-6|o\d)/.test(m)
    case 'gemini':
      return /^gemini-([3-9]|\d{2})/.test(m)
    case 'deepseek':
      return true
    default:
      // Unknown servers may reject unknown parameters.
      return false
  }
}

// ───────────────────────── Custom base URL ─────────────────────────

export const MAX_BASE_URL_CHARS = 300

const LOCAL_HOSTS = new Set(['localhost', '127.0.0.1', '[::1]'])

export function isLocalHost(hostname: string): boolean {
  return LOCAL_HOSTS.has(hostname.toLowerCase())
}

export type BaseUrlCheck = { ok: true; url: string; origin: string; host: string; local: boolean } | { ok: false; message: string }

/**
 * Checks and cleans an "Other (OpenAI-compatible)" base URL such as "https://openrouter.ai/api/v1" or
 * "http://localhost:1234/v1". https is required, except for this computer (localhost / 127.0.0.1). No user name,
 * password, query or fragment; the trailing slash is removed.
 */
export function checkBaseUrl(raw: string): BaseUrlCheck {
  const text = raw.trim()
  if (!text) return { ok: false, message: 'Enter the base URL of the service, for example http://localhost:1234/v1.' }
  if (text.length > MAX_BASE_URL_CHARS) return { ok: false, message: `The base URL must be at most ${MAX_BASE_URL_CHARS} characters.` }
  let u: URL
  try {
    u = new URL(text)
  } catch {
    return { ok: false, message: 'That is not a valid web address. It should look like https://api.example.com/v1.' }
  }
  const local = isLocalHost(u.hostname)
  if (u.protocol !== 'https:' && !(u.protocol === 'http:' && local)) {
    return { ok: false, message: 'The address must start with https:// (plain http:// is allowed only for a server on this computer, such as http://localhost:1234/v1).' }
  }
  if (u.username || u.password) return { ok: false, message: 'Do not put a user name or password in the address. Save the key in the key field instead.' }
  if (u.search || u.hash || text.includes('?') || text.includes('#')) return { ok: false, message: 'The base URL cannot contain "?" or "#". Use just the address, for example https://api.example.com/v1.' }
  const path = u.pathname.replace(/\/+$/, '')
  return { ok: true, url: `${u.origin}${path}`, origin: u.origin, host: u.host, local }
}

/** "https://api.openai.com" → "api.openai.com"; for 'custom', the saved base URL's host. */
export function providerHost(provider: AiProvider, customBaseUrl?: string | null): string | null {
  const origin = AI_PROVIDER_INFO[provider].origin
  if (origin) return new URL(origin).host
  if (!customBaseUrl) return null
  const c = checkBaseUrl(customBaseUrl)
  return c.ok ? c.host : null
}

/** Name for sentences, e.g. "OpenAI", or for 'custom' "the AI service at localhost:1234". */
export function providerDisplayName(provider: AiProvider, customBaseUrl?: string | null): string {
  if (provider !== 'custom') return AI_PROVIDER_INFO[provider].name
  const host = providerHost('custom', customBaseUrl)
  return host ? `the AI service at ${host}` : AI_PROVIDER_INFO.custom.name
}
