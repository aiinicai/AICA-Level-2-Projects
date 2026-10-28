// Provider-agnostic Smart Recon AI layer: request building, reply parsing and error mapping per provider, key
// storage and migration, the network allowlist and the full main-process call with a mocked Electron (no real
// network, no real API calls).

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'fs'
import { tmpdir } from 'os'
import { join } from 'path'
import type { AiRequest } from '../../src/shared/contracts'

const electron = vi.hoisted(() => {
  const state = {
    userData: '',
    encryption: true,
    fetch: vi.fn<(url: string, init: RequestInit) => Promise<Response>>(),
    filters: new Map<string, (url: string) => boolean>()
  }
  return { state }
})

vi.mock('electron', () => ({
  app: { getPath: () => electron.state.userData },
  safeStorage: {
    isEncryptionAvailable: () => electron.state.encryption,
    encryptString: (s: string) => Buffer.from(`enc:${s}`, 'utf8'),
    decryptString: (b: Buffer) => {
      const s = b.toString('utf8')
      if (!s.startsWith('enc:')) throw new Error('bad')
      return s.slice(4)
    }
  },
  session: {
    fromPartition: (name: string) => ({
      webRequest: {
        onBeforeRequest: (fn: (d: { url: string }, cb: (r: { cancel: boolean }) => void) => void) => {
          electron.state.filters.set(name, (url) => {
            let cancel = true
            fn({ url }, (r) => (cancel = r.cancel))
            return !cancel
          })
        }
      },
      setPermissionRequestHandler: () => undefined,
      fetch: (url: string, init: RequestInit) => {
        // The session filter runs first, like Electron's webRequest.
        const allowed = electron.state.filters.get(name)
        if (allowed && !allowed(url)) return Promise.reject(new Error('net::ERR_BLOCKED_BY_CLIENT'))
        return electron.state.fetch(url, init)
      }
    })
  }
}))

import { buildProviderRequest } from '../../src/main/aiHttp'
import { aiMessages, errorResult, successResult } from '../../src/main/aiErrors'
import { isAllowedAiRequest } from '../../src/main/security'
import { aiRequest, customBaseUrl, MAX_AI_TOKENS, MAX_PROMPT_CHARS } from '../../src/main/validate'
import { forgetApiKey, keyStatus, readApiKey, readCustomBaseUrl, saveApiKey, saveCustomBaseUrl, savedCustomOrigin } from '../../src/main/secrets'
import { completeAi } from '../../src/main/ai'
import { checkBaseUrl, isValidModelName, maskKey, supportsEffort } from '../../src/shared/aiProviders'
import { activeAi } from '../../src/renderer/src/features/smart-recon/aiSettings'

const base: AiRequest = { model: 'm', system: 'SYS', messages: [{ role: 'user', content: 'ROWS' }], maxTokens: 16_000, effort: 'medium' }

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } })
}

describe('request building per provider', () => {
  it('Anthropic: Messages API with x-api-key and effort', () => {
    const r = buildProviderRequest({ ...base, model: 'claude-sonnet-5-5' }, 'sk-ant-key')
    expect(r.url).toBe('https://api.anthropic.com/v1/messages')
    expect(r.headers['x-api-key']).toBe('sk-ant-key')
    expect(r.headers['anthropic-version']).toBe('2023-06-01')
    expect(r.body).toEqual({ model: 'claude-sonnet-5-5', max_tokens: 16_000, messages: base.messages, system: 'SYS', output_config: { effort: 'medium' } })
  })

  it('OpenAI: Responses API with a bearer key, store off, effort only for reasoning models', () => {
    const r = buildProviderRequest({ ...base, provider: 'openai', model: 'gpt-6.1-sol' }, 'sk-proj-key')
    expect(r.url).toBe('https://api.openai.com/v1/responses')
    expect(r.headers.authorization).toBe('Bearer sk-proj-key')
    expect(r.body).toEqual({ model: 'gpt-6.1-sol', instructions: 'SYS', input: [{ role: 'user', content: 'ROWS' }], max_output_tokens: 16_000, store: false, reasoning: { effort: 'medium' } })
    const old = buildProviderRequest({ ...base, provider: 'openai', model: 'gpt-4o' }, 'k')
    expect(old.body.reasoning).toBeUndefined()
    expect(old.body.response_format).toBeUndefined()
  })

  it('Gemini: generateContent with the key in x-goog-api-key, never in the URL', () => {
    const r = buildProviderRequest({ ...base, provider: 'gemini', model: 'models/gemini-3.8-flash' }, 'AIzaKEY')
    expect(r.url).toBe('https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent')
    expect(r.url).not.toContain('AIzaKEY')
    expect(r.headers['x-goog-api-key']).toBe('AIzaKEY')
    expect(r.body).toEqual({
      contents: [{ role: 'user', parts: [{ text: 'ROWS' }] }],
      systemInstruction: { parts: [{ text: 'SYS' }] },
      generationConfig: { maxOutputTokens: 16_000, responseMimeType: 'application/json', thinkingConfig: { thinkingLevel: 'medium' } }
    })
    const older = buildProviderRequest({ ...base, provider: 'gemini', model: 'gemini-2.5-flash' }, 'k')
    expect((older.body.generationConfig as Record<string, unknown>).thinkingConfig).toBeUndefined()
  })

  it('DeepSeek and Other: OpenAI-compatible Chat Completions, no forced response_format', () => {
    const d = buildProviderRequest({ ...base, provider: 'deepseek', model: 'deepseek-flash' }, 'sk-ds')
    expect(d.url).toBe('https://api.deepseek.com/chat/completions')
    expect(d.headers.authorization).toBe('Bearer sk-ds')
    expect(d.body).toEqual({
      model: 'deepseek-flash',
      messages: [
        { role: 'system', content: 'SYS' },
        { role: 'user', content: 'ROWS' }
      ],
      max_tokens: 16_000,
      stream: false,
      reasoning_effort: 'medium'
    })
    const c = buildProviderRequest({ ...base, provider: 'custom', model: 'llama3.1:8b' }, null, 'http://localhost:11434/v1')
    expect(c.url).toBe('http://localhost:11434/v1/chat/completions')
    expect(c.headers.authorization).toBeUndefined()
    expect(c.body.reasoning_effort).toBeUndefined()
    expect(c.body.response_format).toBeUndefined()
    expect(() => buildProviderRequest({ ...base, provider: 'custom' }, null, null)).toThrow(/base URL/)
  })

  it('knows which models take an effort setting', () => {
    expect(supportsEffort('openai', 'o4-mini')).toBe(true)
    expect(supportsEffort('openai', 'gpt-4.1')).toBe(false)
    expect(supportsEffort('gemini', 'gemini-4-argon')).toBe(true)
    expect(supportsEffort('custom', 'anything')).toBe(false)
  })
})

describe('reply parsing per provider', () => {
  it('reads OpenAI Responses output text and usage', () => {
    const r = successResult(
      { status: 'completed', output: [{ type: 'reasoning', summary: [] }, { type: 'message', content: [{ type: 'output_text', text: '[]' }] }], usage: { input_tokens: 900, output_tokens: 40 } },
      'openai'
    )
    expect(r).toEqual({ ok: true, response: { text: '[]', inputTokens: 900, outputTokens: 40 } })
    expect(successResult({ status: 'incomplete', output: [] }, 'openai')).toMatchObject({ ok: false, message: expect.stringMatching(/reply limit/) })
    expect(successResult({ output: [{ type: 'message', content: [{ type: 'refusal', refusal: 'No.' }] }] }, 'openai')).toMatchObject({ ok: false, message: expect.stringMatching(/declined/) })
  })

  it('reads Gemini candidates, skips thought parts, counts thinking as output', () => {
    const r = successResult(
      {
        candidates: [{ finishReason: 'STOP', content: { parts: [{ text: 'thinking…', thought: true }, { text: '[{"a_ids":[]}]' }] } }],
        usageMetadata: { promptTokenCount: 1000, candidatesTokenCount: 20, thoughtsTokenCount: 300 }
      },
      'gemini'
    )
    expect(r).toEqual({ ok: true, response: { text: '[{"a_ids":[]}]', inputTokens: 1000, outputTokens: 320 } })
    expect(successResult({ promptFeedback: { blockReason: 'SAFETY' } }, 'gemini')).toMatchObject({ ok: false, message: expect.stringMatching(/Gemini blocked/) })
    expect(successResult({ candidates: [{ finishReason: 'MAX_TOKENS', content: { parts: [] } }] }, 'gemini').ok).toBe(false)
  })

  it('reads Chat Completions replies and strips <think> blocks from local models', () => {
    const r = successResult({ choices: [{ finish_reason: 'stop', message: { content: '<think>let me see [x]</think>\n[]' } }], usage: { prompt_tokens: 50, completion_tokens: 5 } }, 'custom', 'http://localhost:1234/v1')
    expect(r).toEqual({ ok: true, response: { text: '[]', inputTokens: 50, outputTokens: 5 } })
    expect(successResult({ choices: [{ finish_reason: 'length', message: { content: null } }] }, 'deepseek').ok).toBe(false)
    expect(successResult({ nope: 1 }, 'deepseek')).toMatchObject({ ok: false, message: expect.stringMatching(/DeepSeek API sent back a reply/) })
  })
})

describe('error mapping per provider', () => {
  it('names the provider in every message', () => {
    expect(aiMessages('openai')['bad-key']).toMatch(/Your OpenAI API key was not accepted/)
    expect(aiMessages('gemini')['rate-limit']).toMatch(/Gemini API rate limit/)
    expect(aiMessages('deepseek').overloaded).toMatch(/^The DeepSeek API is busy/)
    expect(aiMessages('custom', 'http://localhost:1234/v1').network).toMatch(/AI service at localhost:1234.*local server is running/)
  })

  it('maps statuses and provider-specific bodies to the app codes', () => {
    expect(errorResult(401, { error: { message: 'Incorrect API key provided' } }, 'openai')).toEqual({ ok: false, code: 'bad-key', message: aiMessages('openai')['bad-key'] })
    expect(errorResult(400, { error: { code: 400, message: 'API key not valid. Please pass a valid API key.', status: 'INVALID_ARGUMENT', details: [{ reason: 'API_KEY_INVALID' }] } }, 'gemini')).toMatchObject({ code: 'bad-key' })
    expect(errorResult(400, { error: { message: 'Bad model' } }, 'gemini')).toMatchObject({ code: 'api', message: expect.stringContaining('Bad model') })
    expect(errorResult(429, { error: { type: 'rate_limit_error', code: 'slow_down' } }, 'openai')).toMatchObject({ code: 'rate-limit' })
    expect(errorResult(429, { error: { type: 'insufficient_quota', code: 'insufficient_quota' } }, 'openai')).toMatchObject({ code: 'api', message: expect.stringMatching(/no credit/) })
    expect(errorResult(402, { error: { message: 'Insufficient Balance' } }, 'deepseek')).toMatchObject({ code: 'api', message: expect.stringMatching(/DeepSeek account has no credit/) })
    expect(errorResult(503, {}, 'deepseek')).toMatchObject({ code: 'overloaded' })
    expect(errorResult(529, {}, 'anthropic')).toMatchObject({ code: 'overloaded' })
    expect(errorResult(404, {}, 'custom', 'https://openrouter.ai/api/v1')).toMatchObject({ code: 'api', message: expect.stringMatching(/openrouter\.ai.*base URL/) })
  })
})

describe('network allowlist', () => {
  it('lets each provider reach only its official https host', () => {
    expect(isAllowedAiRequest('https://api.anthropic.com/v1/messages')).toBe(true)
    expect(isAllowedAiRequest('https://api.openai.com/v1/responses', 'openai')).toBe(true)
    expect(isAllowedAiRequest('https://generativelanguage.googleapis.com/v1beta/models/x:generateContent', 'gemini')).toBe(true)
    expect(isAllowedAiRequest('https://api.deepseek.com/chat/completions', 'deepseek')).toBe(true)
    // Another provider's host, http, look-alikes and credentials are blocked.
    expect(isAllowedAiRequest('https://api.anthropic.com/v1/messages', 'openai')).toBe(false)
    expect(isAllowedAiRequest('http://api.openai.com/v1/responses', 'openai')).toBe(false)
    expect(isAllowedAiRequest('https://api.openai.com.evil.example/', 'openai')).toBe(false)
    expect(isAllowedAiRequest('https://user:pw@api.deepseek.com/', 'deepseek')).toBe(false)
    expect(isAllowedAiRequest('https://example.com/', 'gemini')).toBe(false)
    expect(isAllowedAiRequest('not a url', 'anthropic')).toBe(false)
  })

  it('allows a custom origin only once it is saved, and http only for this computer', () => {
    expect(isAllowedAiRequest('http://localhost:1234/v1/chat/completions', 'custom')).toBe(false)
    expect(isAllowedAiRequest('http://localhost:1234/v1/chat/completions', 'custom', null)).toBe(false)
    expect(isAllowedAiRequest('http://localhost:1234/v1/chat/completions', 'custom', 'http://localhost:1234')).toBe(true)
    expect(isAllowedAiRequest('http://localhost:9999/v1/chat/completions', 'custom', 'http://localhost:1234')).toBe(false)
    expect(isAllowedAiRequest('https://openrouter.ai/api/v1/chat/completions', 'custom', 'https://openrouter.ai')).toBe(true)
    expect(isAllowedAiRequest('https://api.openai.com/v1/responses', 'custom', 'https://openrouter.ai')).toBe(false)
    expect(isAllowedAiRequest('http://openrouter.ai/api/v1/chat/completions', 'custom', 'http://openrouter.ai')).toBe(false)
  })

  it('checks base URLs: https, or http only for localhost / 127.0.0.1', () => {
    expect(checkBaseUrl('http://localhost:1234/v1/')).toMatchObject({ ok: true, url: 'http://localhost:1234/v1', host: 'localhost:1234', local: true })
    expect(checkBaseUrl('http://127.0.0.1:11434/v1')).toMatchObject({ ok: true, local: true })
    expect(checkBaseUrl('https://api.groq.com/openai/v1')).toMatchObject({ ok: true, origin: 'https://api.groq.com', local: false })
    expect(checkBaseUrl('http://192.168.1.20:1234/v1').ok).toBe(false)
    expect(checkBaseUrl('http://example.com/v1').ok).toBe(false)
    expect(checkBaseUrl('ftp://localhost/v1').ok).toBe(false)
    expect(checkBaseUrl('https://u:p@example.com/v1').ok).toBe(false)
    expect(checkBaseUrl('https://example.com/v1?key=1').ok).toBe(false)
    expect(checkBaseUrl('').ok).toBe(false)
    expect(customBaseUrl('  ')).toBeNull()
    expect(() => customBaseUrl('http://example.com')).toThrow(/https/)
  })
})

describe('request validation caps', () => {
  const msg = (content: string): { role: 'user'; content: string } => ({ role: 'user', content })

  it('validates provider, model and base URL', () => {
    expect(aiRequest({ model: 'claude-sonnet-5-5', messages: [msg('hi')], maxTokens: 10 }).provider).toBeUndefined()
    expect(aiRequest({ provider: 'openai', model: 'gpt-6.1-sol', messages: [msg('hi')], maxTokens: 10 }).provider).toBe('openai')
    expect(aiRequest({ provider: 'gemini', model: 'models/gemini-3.8-flash', messages: [msg('hi')], maxTokens: 10 }).model).toBe('gemini-3.8-flash')
    expect(() => aiRequest({ provider: 'gemini', model: 'gemini-3:streamGenerateContent', messages: [msg('hi')], maxTokens: 10 })).toThrow(/model name/)
    expect(() => aiRequest({ provider: 'nope', model: 'm', messages: [msg('hi')], maxTokens: 10 })).toThrow(/not supported/)
    const c = aiRequest({ provider: 'custom', baseUrl: 'http://localhost:11434/v1/', model: 'llama3.1:8b', messages: [msg('hi')], maxTokens: 10 })
    expect(c.baseUrl).toBe('http://localhost:11434/v1')
    expect(aiRequest({ provider: 'custom', baseUrl: 'https://openrouter.ai/api/v1', model: 'meta-llama/llama-3.1-8b-instruct', messages: [msg('hi')], maxTokens: 10 }).model).toBe('meta-llama/llama-3.1-8b-instruct')
    expect(() => aiRequest({ provider: 'custom', model: 'm', messages: [msg('hi')], maxTokens: 10 })).toThrow(/base URL/)
    expect(() => aiRequest({ provider: 'custom', baseUrl: 'http://10.0.0.5/v1', model: 'm', messages: [msg('hi')], maxTokens: 10 })).toThrow()
    expect(isValidModelName('custom', 'llama 3')).toBe(false)
  })

  it('keeps the size caps for every provider', () => {
    expect(() => aiRequest({ provider: 'deepseek', model: 'm', messages: [msg('x'.repeat(MAX_PROMPT_CHARS + 1))], maxTokens: 100 })).toThrow()
    expect(() => aiRequest({ provider: 'openai', model: 'm', messages: [msg('hi')], maxTokens: MAX_AI_TOKENS + 1 })).toThrow(/32,000/)
  })
})

describe('key storage and migration (mocked safeStorage)', () => {
  beforeEach(() => {
    electron.state.userData = mkdtempSync(join(tmpdir(), 'reco-do-keys-'))
    electron.state.encryption = true
  })
  afterEach(() => rmSync(electron.state.userData, { recursive: true, force: true }))

  it('stores one encrypted key per provider and reports only masked values', async () => {
    await saveApiKey('openai', 'sk-proj-abcdefghijklmnop1234')
    await saveApiKey('gemini', 'AIzaSyA1234567890abcdefghijklmnopqrstu')
    const file = join(electron.state.userData, 'ai-keys', 'openai.bin')
    expect(readFileSync(file, 'utf8')).toBe('enc:sk-proj-abcdefghijklmnop1234')
    expect(await readApiKey('openai')).toBe('sk-proj-abcdefghijklmnop1234')
    const s = await keyStatus()
    expect(s.providers.openai).toEqual({ hasKey: true, masked: 'sk-proj-…1234' })
    expect(s.providers.gemini).toEqual({ hasKey: true, masked: 'AIza…rstu' })
    expect(s.providers.anthropic.hasKey).toBe(false)
    expect(s.hasKey).toBe(false)
    expect(JSON.stringify(s)).not.toContain('abcdefghijklmnop')
    await forgetApiKey('openai')
    expect(await readApiKey('openai')).toBeNull()
    expect(await readApiKey('gemini')).not.toBeNull()
  })

  it('moves the old claude-api-key.bin into the Anthropic slot', async () => {
    const legacy = join(electron.state.userData, 'claude-api-key.bin')
    writeFileSync(legacy, 'enc:sk-ant-api03-legacykey9999')
    const s = await keyStatus()
    expect(s.hasKey).toBe(true)
    expect(s.masked).toBe('sk-ant-…9999')
    expect(existsSync(legacy)).toBe(false)
    expect(existsSync(join(electron.state.userData, 'ai-keys', 'anthropic.bin'))).toBe(true)
    expect(await readApiKey()).toBe('sk-ant-api03-legacykey9999')
  })

  it('keeps a newer Anthropic key over a stale legacy file', async () => {
    await saveApiKey('anthropic', 'sk-ant-api03-newkey00001111')
    writeFileSync(join(electron.state.userData, 'claude-api-key.bin'), 'enc:sk-ant-api03-oldkey')
    expect(await readApiKey('anthropic')).toBe('sk-ant-api03-newkey00001111')
    expect(existsSync(join(electron.state.userData, 'claude-api-key.bin'))).toBe(false)
  })

  it('refuses to save without secure storage, and treats unreadable files as no key', async () => {
    electron.state.encryption = false
    await expect(saveApiKey('deepseek', 'sk-x')).rejects.toThrow(/secure storage/)
    electron.state.encryption = true
    await saveApiKey('deepseek', 'sk-0123456789abcdef0123')
    writeFileSync(join(electron.state.userData, 'ai-keys', 'deepseek.bin'), 'garbage')
    expect(await readApiKey('deepseek')).toBeNull()
  })

  it('saves and clears the custom base URL used by the allowlist', async () => {
    expect(await readCustomBaseUrl()).toBeNull()
    await saveCustomBaseUrl('http://localhost:1234/v1')
    expect(savedCustomOrigin()).toBe('http://localhost:1234')
    expect(await readCustomBaseUrl()).toBe('http://localhost:1234/v1')
    expect((await keyStatus()).customBaseUrl).toBe('http://localhost:1234/v1')
    await saveCustomBaseUrl(null)
    expect(savedCustomOrigin()).toBeNull()
  })
})

describe('completeAi (mocked Electron session)', () => {
  beforeEach(() => {
    electron.state.userData = mkdtempSync(join(tmpdir(), 'reco-do-ai-'))
    electron.state.fetch.mockReset()
  })
  afterEach(() => rmSync(electron.state.userData, { recursive: true, force: true }))

  it('reports a missing key without touching the network', async () => {
    const r = await completeAi({ ...base, provider: 'openai', model: 'gpt-6.1-sol' })
    expect(r).toEqual({ ok: false, code: 'no-key', message: aiMessages('openai')['no-key'] })
    expect(electron.state.fetch).not.toHaveBeenCalled()
  })

  it('sends to the provider and maps a refused key', async () => {
    await saveApiKey('gemini', 'AIzaFAKEFAKEFAKEFAKEFAKEFAKEFAKEFAKE00')
    electron.state.fetch.mockResolvedValueOnce(json(400, { error: { code: 400, message: 'API key not valid. Please pass a valid API key.', status: 'INVALID_ARGUMENT', details: [{ reason: 'API_KEY_INVALID' }] } }))
    const r = await completeAi({ ...base, provider: 'gemini', model: 'gemini-3.8-flash' })
    expect(r).toMatchObject({ ok: false, code: 'bad-key', message: expect.stringMatching(/Gemini API key/) })
    const [url, init] = electron.state.fetch.mock.calls[0]
    expect(url).toBe('https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent')
    expect((init.headers as Record<string, string>)['x-goog-api-key']).toBe('AIzaFAKEFAKEFAKEFAKEFAKEFAKEFAKEFAKE00')
  })

  it('returns the reply text on success', async () => {
    await saveApiKey('deepseek', 'sk-0123456789abcdef0123')
    electron.state.fetch.mockResolvedValueOnce(json(200, { choices: [{ finish_reason: 'stop', message: { content: '[]' } }], usage: { prompt_tokens: 10, completion_tokens: 2 } }))
    expect(await completeAi({ ...base, provider: 'deepseek', model: 'deepseek-flash' })).toEqual({ ok: true, response: { text: '[]', inputTokens: 10, outputTokens: 2 } })
  })

  it('maps network failures', async () => {
    await saveApiKey('openai', 'sk-proj-abcdefghijklmnop1234')
    electron.state.fetch.mockRejectedValueOnce(new TypeError('fetch failed'))
    expect(await completeAi({ ...base, provider: 'openai', model: 'gpt-6.1-sol' })).toMatchObject({ ok: false, code: 'network', message: expect.stringMatching(/OpenAI API/) })
  })

  it('refuses a custom address that was not saved, and calls the saved one without a key', async () => {
    const req: AiRequest = { ...base, provider: 'custom', baseUrl: 'http://localhost:1234/v1', model: 'local-model' }
    const unsaved = await completeAi(req)
    expect(unsaved).toMatchObject({ ok: false, message: expect.stringMatching(/has not been saved/) })
    expect(electron.state.fetch).not.toHaveBeenCalled()
    await saveCustomBaseUrl('http://localhost:1234/v1')
    electron.state.fetch.mockResolvedValueOnce(json(200, { choices: [{ message: { content: '[]' } }] }))
    expect((await completeAi(req)).ok).toBe(true)
    expect(electron.state.fetch.mock.calls[0][0]).toBe('http://localhost:1234/v1/chat/completions')
    // A different address in the request is refused even after saving.
    expect((await completeAi({ ...req, baseUrl: 'http://localhost:9999/v1' })).ok).toBe(false)
  })

  it("blocks a redirect to another host through the provider's session filter", async () => {
    await saveApiKey('anthropic', 'sk-ant-api03-abcdefghijklmnop')
    const filters = electron.state.filters
    await completeAi({ ...base, model: 'claude-sonnet-5-5' }).catch(() => undefined)
    const allowed = filters.get('reco-do-ai')
    expect(allowed?.('https://api.anthropic.com/v1/messages')).toBe(true)
    expect(allowed?.('https://evil.example/collect')).toBe(false)
  })
})

describe('Settings → active provider', () => {
  it('defaults to Anthropic so existing users see no change', () => {
    expect(activeAi({ aiModel: 'claude-opus-5-5' })).toMatchObject({ provider: 'anthropic', model: 'claude-opus-5-5', host: 'api.anthropic.com' })
    expect(activeAi({ aiProvider: 'bogus' }).provider).toBe('anthropic')
  })

  it('uses the per-provider model or the default, and the saved base URL for Other', () => {
    expect(activeAi({ aiProvider: 'openai', aiModels: {} })).toMatchObject({ model: 'gpt-6.1-sol', host: 'api.openai.com', shortName: 'OpenAI' })
    expect(activeAi({ aiProvider: 'gemini', aiModels: { gemini: 'gemini-2.5-pro' } }).model).toBe('gemini-2.5-pro')
    expect(activeAi({ aiProvider: 'custom', aiModels: { custom: 'qwen3' }, aiBaseUrl: 'http://localhost:1234/v1/' })).toMatchObject({
      baseUrl: 'http://localhost:1234/v1',
      host: 'localhost:1234',
      shortName: 'localhost:1234'
    })
    expect(activeAi({ aiProvider: 'custom', aiBaseUrl: 'http://evil.example' }).host).toBeNull()
  })

  it('masks keys without revealing them', () => {
    expect(maskKey('sk-ant-api03-abcdefghijklmnop3f9a')).toBe('sk-ant-…3f9a')
    expect(maskKey('short')).toBe('••••')
    expect(maskKey('0123456789abcdefWXYZ')).toBe('…WXYZ')
  })
})
