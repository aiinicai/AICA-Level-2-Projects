// Builds the one HTTP request each AI provider needs for a single, non-streaming Smart Recon reply.
// Pure (no Electron imports) so the exact URL, headers and body can be unit-tested. Every provider gets the same
// system prompt and rows; only the envelope differs. The reply is read by successResult in aiErrors.ts.

import type { AiProvider, AiRequest } from '../shared/contracts'
import { AI_PROVIDER_INFO, cleanModelName, supportsEffort } from '../shared/aiProviders'

export interface ProviderHttpRequest {
  url: string
  headers: Record<string, string>
  body: Record<string, unknown>
}

/**
 * @param key  the provider's API key (may be null only for 'custom', e.g. a local server)
 * @param customBaseUrl  the saved, already-checked base URL (required for 'custom')
 */
export function buildProviderRequest(req: AiRequest, key: string | null, customBaseUrl?: string | null): ProviderHttpRequest {
  const provider: AiProvider = req.provider ?? 'anthropic'
  const model = cleanModelName(provider, req.model)
  const effort = req.effort && supportsEffort(provider, model) ? req.effort : undefined
  const bearer: Record<string, string> = key ? { authorization: `Bearer ${key}` } : {}

  switch (provider) {
    case 'anthropic': {
      const body: Record<string, unknown> = { model, max_tokens: req.maxTokens, messages: req.messages }
      if (req.system) body.system = req.system
      if (effort) body.output_config = { effort }
      return {
        url: `${AI_PROVIDER_INFO.anthropic.origin}/v1/messages`,
        headers: { 'content-type': 'application/json', 'x-api-key': key ?? '', 'anthropic-version': '2023-06-01' },
        body
      }
    }
    case 'openai': {
      // Responses API. store: false so OpenAI does not keep the rows for later retrieval.
      const body: Record<string, unknown> = {
        model,
        input: req.messages.map((m) => ({ role: m.role, content: m.content })),
        max_output_tokens: req.maxTokens,
        store: false
      }
      if (req.system) body.instructions = req.system
      if (effort) body.reasoning = { effort }
      return { url: `${AI_PROVIDER_INFO.openai.origin}/v1/responses`, headers: { 'content-type': 'application/json', ...bearer }, body }
    }
    case 'gemini': {
      // The key goes in the x-goog-api-key header, never in the URL. A JSON reply is requested; an array is valid JSON.
      const generationConfig: Record<string, unknown> = { maxOutputTokens: req.maxTokens, responseMimeType: 'application/json' }
      if (effort) generationConfig.thinkingConfig = { thinkingLevel: effort }
      const body: Record<string, unknown> = {
        contents: req.messages.map((m) => ({ role: m.role === 'assistant' ? 'model' : 'user', parts: [{ text: m.content }] })),
        generationConfig
      }
      if (req.system) body.systemInstruction = { parts: [{ text: req.system }] }
      return {
        url: `${AI_PROVIDER_INFO.gemini.origin}/v1beta/models/${encodeURIComponent(model)}:generateContent`,
        headers: { 'content-type': 'application/json', 'x-goog-api-key': key ?? '' },
        body
      }
    }
    case 'deepseek':
    case 'custom': {
      // OpenAI-compatible Chat Completions. JSON is asked for in the prompt; response_format is not forced, because
      // JSON mode on many servers requires an object while Smart Recon replies with an array.
      const messages = [...(req.system ? [{ role: 'system', content: req.system }] : []), ...req.messages.map((m) => ({ role: m.role, content: m.content }))]
      const body: Record<string, unknown> = { model, messages, max_tokens: req.maxTokens, stream: false }
      if (effort) body.reasoning_effort = effort
      const base = provider === 'deepseek' ? AI_PROVIDER_INFO.deepseek.origin : customBaseUrl
      if (!base) throw new Error('Save the base URL of the AI service in Settings first.')
      return { url: `${base}/chat/completions`, headers: { 'content-type': 'application/json', ...bearer }, body }
    }
  }
}
