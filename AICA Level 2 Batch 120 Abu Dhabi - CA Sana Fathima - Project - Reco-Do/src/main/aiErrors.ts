// Maps each AI provider's HTTP outcome to the app's AiResult, with plain-English messages naming the provider.
// Pure (no Electron imports) so it can be unit-tested.

import type { AiErrorCode, AiProvider, AiResult } from '../shared/contracts'
import { AI_PROVIDER_INFO, providerDisplayName } from '../shared/aiProviders'

/** "Claude API", "OpenAI API", … or "the AI service at localhost:1234". */
function apiName(provider: AiProvider, baseUrl?: string | null): string {
  return provider === 'custom' ? providerDisplayName('custom', baseUrl) : `${AI_PROVIDER_INFO[provider].name} API`
}

function upper(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1)
}

export function aiMessages(provider: AiProvider = 'anthropic', baseUrl?: string | null): Record<AiErrorCode, string> {
  const info = AI_PROVIDER_INFO[provider]
  const api = apiName(provider, baseUrl)
  const keyName = provider === 'custom' ? 'API key for this service' : `${info.name} API key`
  const local = provider === 'custom' && !!baseUrl && /^http:\/\//i.test(baseUrl)
  return {
    'no-key': `No ${keyName} is saved. Add one in Settings & API Key to use Smart Recon.`,
    'bad-key': `Your ${keyName} was not accepted. Check it in Settings & API Key, or create a new key at ${info.keyWhere}.`,
    'rate-limit': `The ${api} rate limit was reached. Wait a minute and try again, or send fewer rows.`,
    overloaded: `${upper(provider === 'custom' ? api : `the ${api}`)} is busy right now. Please try again in a few minutes.`,
    network: local
      ? `Could not reach ${api}. Check that the local server is running and has a model loaded, then try again.`
      : `Could not reach ${provider === 'custom' ? api : `the ${api}`}. Check your internet connection and try again.`,
    api: `${upper(provider === 'custom' ? api : `the ${api}`)} returned an error.`
  }
}

/** The Anthropic messages, kept under their original name. */
export const AI_MESSAGES: Record<AiErrorCode, string> = aiMessages('anthropic')

export function codeForStatus(status: number): AiErrorCode {
  if (status === 401 || status === 403) return 'bad-key'
  if (status === 429) return 'rate-limit'
  if (status === 529 || status === 503) return 'overloaded'
  return 'api'
}

function field(body: unknown, ...path: string[]): unknown {
  let v: unknown = body
  for (const k of path) {
    if (typeof v !== 'object' || v === null) return undefined
    v = (v as Record<string, unknown>)[k]
  }
  return v
}

/** Pulls the API's own error message out of a response body, if there is one (all providers use error.message). */
export function apiErrorDetail(body: unknown): string | null {
  const message = field(body, 'error', 'message')
  if (typeof message === 'string' && message.trim()) return message.trim().slice(0, 500)
  // Some OpenAI-compatible servers answer {"error":"text"} or {"message":"text"}.
  const flat = field(body, 'error') ?? field(body, 'message')
  return typeof flat === 'string' && flat.trim() ? flat.trim().slice(0, 500) : null
}

/** Gemini answers a wrong key with 400 INVALID_ARGUMENT and reason API_KEY_INVALID (newer: 401). */
function isGeminiBadKey(body: unknown): boolean {
  const details = field(body, 'error', 'details')
  if (Array.isArray(details) && details.some((d) => field(d, 'reason') === 'API_KEY_INVALID')) return true
  const message = apiErrorDetail(body) ?? ''
  return /api key (not valid|invalid|expired)/i.test(message)
}

/** OpenAI-style 429 that means no credit or a spend limit, where waiting does not help. */
const OUT_OF_CREDIT = /insufficient_quota|credit_balance_exhausted|spend_limit_exceeded|usage_limit_exceeded|billing/i

function outOfCreditMessage(provider: AiProvider, baseUrl?: string | null): string {
  const who = provider === 'custom' ? upper(providerDisplayName('custom', baseUrl)) : `Your ${AI_PROVIDER_INFO[provider].name} account`
  return `${who} has no credit left or reached its spending limit. Add credit or raise the limit on ${AI_PROVIDER_INFO[provider].keyWhere}, then try again.`
}

export function errorResult(status: number, body: unknown, provider: AiProvider = 'anthropic', baseUrl?: string | null): AiResult {
  const messages = aiMessages(provider, baseUrl)
  let code = codeForStatus(status)
  if (provider === 'gemini' && status === 400 && isGeminiBadKey(body)) code = 'bad-key'
  const errorCode = `${String(field(body, 'error', 'code') ?? '')} ${String(field(body, 'error', 'type') ?? '')}`
  if (status === 402 || (status === 429 && OUT_OF_CREDIT.test(errorCode))) {
    return { ok: false, code: 'api', message: outOfCreditMessage(provider, baseUrl) }
  }
  if (provider === 'custom' && status === 404) {
    return {
      ok: false,
      code: 'api',
      message: `${upper(providerDisplayName('custom', baseUrl))} answered "not found". Check the base URL (it usually ends in /v1) and the model name in Settings.`
    }
  }
  if (code !== 'api') return { ok: false, code, message: messages[code] }
  const detail = apiErrorDetail(body)
  return {
    ok: false,
    code,
    message: detail ? `${messages.api} (${status}) ${detail}` : `${messages.api} (status ${status}). Please try again.`
  }
}

function count(v: unknown): number {
  return typeof v === 'number' && Number.isFinite(v) && v >= 0 ? v : 0
}

function unreadable(provider: AiProvider, baseUrl?: string | null): AiResult {
  const who = provider === 'custom' ? upper(providerDisplayName('custom', baseUrl)) : `The ${apiName(provider)}`
  return { ok: false, code: 'api', message: `${who} sent back a reply the app could not read. Please try again.` }
}

function cutOff(provider: AiProvider, baseUrl?: string | null): AiResult {
  const who = provider === 'custom' ? upper(providerDisplayName('custom', baseUrl)) : `The ${apiName(provider)}`
  return { ok: false, code: 'api', message: `${who} stopped before writing an answer (it used its whole reply limit). Send fewer rows per batch, or try another model.` }
}

/** Local reasoning models (through LM Studio, Ollama …) often put their thinking inside <think>…</think>. */
function stripThinking(text: string): string {
  return text.replace(/<think>[\s\S]*?<\/think>/gi, '').trim()
}

function ok(text: string, inputTokens: number, outputTokens: number): AiResult {
  return { ok: true, response: { text, inputTokens, outputTokens } }
}

interface MessagesResponse {
  content?: Array<{ type?: string; text?: string }>
  stop_reason?: string
  usage?: { input_tokens?: number; output_tokens?: number }
}

function anthropicSuccess(body: unknown): AiResult {
  const r = (typeof body === 'object' && body !== null ? body : {}) as MessagesResponse
  if (!Array.isArray(r.content)) return unreadable('anthropic')
  const text = r.content
    .filter((b) => b.type === 'text' && typeof b.text === 'string')
    .map((b) => b.text as string)
    .join('')
  if (!text.trim() && r.stop_reason === 'max_tokens') return cutOff('anthropic')
  return ok(text, count(r.usage?.input_tokens), count(r.usage?.output_tokens))
}

interface ResponsesResponse {
  status?: string
  output_text?: string
  output?: Array<{ type?: string; content?: Array<{ type?: string; text?: string; refusal?: string }> }>
  usage?: { input_tokens?: number; output_tokens?: number }
}

function openAiSuccess(body: unknown): AiResult {
  const r = (typeof body === 'object' && body !== null ? body : {}) as ResponsesResponse
  if (!Array.isArray(r.output) && typeof r.output_text !== 'string') return unreadable('openai')
  const parts = (r.output ?? []).filter((o) => o.type === 'message').flatMap((o) => (Array.isArray(o.content) ? o.content : []))
  let text = parts
    .filter((c) => c.type === 'output_text' && typeof c.text === 'string')
    .map((c) => c.text as string)
    .join('')
  if (!text && typeof r.output_text === 'string') text = r.output_text
  if (!text.trim()) {
    const refusal = parts.find((c) => c.type === 'refusal' && typeof c.refusal === 'string')
    if (refusal) return { ok: false, code: 'api', message: `OpenAI declined this request: ${String(refusal.refusal).slice(0, 300)}` }
    if (r.status === 'incomplete') return cutOff('openai')
  }
  return ok(text, count(r.usage?.input_tokens), count(r.usage?.output_tokens))
}

interface ChatResponse {
  choices?: Array<{ finish_reason?: string; message?: { content?: unknown; refusal?: unknown } }>
  usage?: { prompt_tokens?: number; completion_tokens?: number }
}

function chatContent(content: unknown): string {
  if (typeof content === 'string') return content
  // A few compatible servers return content parts.
  if (Array.isArray(content)) {
    return content.map((p) => (typeof p === 'string' ? p : typeof field(p, 'text') === 'string' ? (field(p, 'text') as string) : '')).join('')
  }
  return ''
}

function chatSuccess(body: unknown, provider: AiProvider, baseUrl?: string | null): AiResult {
  const r = (typeof body === 'object' && body !== null ? body : {}) as ChatResponse
  if (!Array.isArray(r.choices) || r.choices.length === 0) return unreadable(provider, baseUrl)
  const choice = r.choices[0]
  const text = stripThinking(chatContent(choice.message?.content))
  if (!text) {
    if (typeof choice.message?.refusal === 'string' && choice.message.refusal) {
      return { ok: false, code: 'api', message: `${upper(providerDisplayName(provider, baseUrl))} declined this request: ${choice.message.refusal.slice(0, 300)}` }
    }
    if (choice.finish_reason === 'length') return cutOff(provider, baseUrl)
  }
  return ok(text, count(r.usage?.prompt_tokens), count(r.usage?.completion_tokens))
}

interface GeminiResponse {
  candidates?: Array<{ finishReason?: string; content?: { parts?: Array<{ text?: string; thought?: boolean }> } }>
  promptFeedback?: { blockReason?: string }
  usageMetadata?: { promptTokenCount?: number; candidatesTokenCount?: number; thoughtsTokenCount?: number }
}

function geminiSuccess(body: unknown): AiResult {
  const r = (typeof body === 'object' && body !== null ? body : {}) as GeminiResponse
  if (r.promptFeedback?.blockReason) {
    return { ok: false, code: 'api', message: `Gemini blocked this request (${r.promptFeedback.blockReason}). Try again with party names masked, or use another provider.` }
  }
  if (!Array.isArray(r.candidates)) return unreadable('gemini')
  const candidate = r.candidates[0]
  const parts = candidate?.content?.parts ?? []
  const text = parts
    .filter((p) => !p.thought && typeof p.text === 'string')
    .map((p) => p.text as string)
    .join('')
  if (!text.trim()) {
    if (candidate?.finishReason === 'MAX_TOKENS') return cutOff('gemini')
    if (candidate?.finishReason && candidate.finishReason !== 'STOP') {
      return { ok: false, code: 'api', message: `Gemini stopped without an answer (${candidate.finishReason}). Please try again.` }
    }
  }
  const u = r.usageMetadata
  return ok(text, count(u?.promptTokenCount), count(u?.candidatesTokenCount) + count(u?.thoughtsTokenCount))
}

/** Reads a successful (2xx) reply. Only the answer text and token counts are kept. */
export function successResult(body: unknown, provider: AiProvider = 'anthropic', baseUrl?: string | null): AiResult {
  switch (provider) {
    case 'anthropic':
      return anthropicSuccess(body)
    case 'openai':
      return openAiSuccess(body)
    case 'gemini':
      return geminiSuccess(body)
    default:
      return chatSuccess(body, provider, baseUrl)
  }
}

export function timeoutResult(provider: AiProvider = 'anthropic', baseUrl?: string | null): AiResult {
  const who = provider === 'custom' ? upper(providerDisplayName('custom', baseUrl)) : `The ${apiName(provider)}`
  return { ok: false, code: 'network', message: `${who} did not answer within 5 minutes. Try again, or send fewer rows per batch.` }
}

export function networkResult(provider: AiProvider = 'anthropic', baseUrl?: string | null): AiResult {
  return { ok: false, code: 'network', message: aiMessages(provider, baseUrl).network }
}
