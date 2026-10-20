import { describe, expect, it } from 'vitest'
import { AI_MESSAGES, codeForStatus, errorResult, successResult } from '../../src/main/aiErrors'
import { aiRequest, apiKey, apiKeyRequest, binaryData, fileFilters, maskKey, pdfRequest, safeFileName, samplePathSegments } from '../../src/main/validate'

describe('API key handling', () => {
  it('masks a key as sk-ant-…last4', () => {
    expect(maskKey('sk-ant-api03-abcdefghijklmnop3f9a')).toBe('sk-ant-…3f9a')
  })

  it('accepts a well-formed key and trims spaces', () => {
    expect(apiKey('  sk-ant-api03-abcDEF_123-xyz7890  ')).toEqual({ key: 'sk-ant-api03-abcDEF_123-xyz7890', warning: null })
  })

  it('blocks empty or garbled keys but only warns about an unusual format', () => {
    expect(() => apiKey('')).toThrow(/paste your Claude API key/)
    expect(() => apiKey('sk-ant-abc def ghi jkl mno')).toThrow(/spaces or unexpected characters/)
    expect(() => apiKey(42)).toThrow()
    expect(() => apiKey('x'.repeat(2_001), 'openai')).toThrow(/too long/)
    // A foreign-looking key is saved with a warning, never refused (formats change).
    expect(apiKey('sk-proj-abcdefghijklmnop').warning).toMatch(/usual format/)
    expect(apiKey('sk-ant-api03-abcdefghijklmnop', 'openai').warning).toMatch(/looks like a Claude key/)
    expect(apiKey('AIzaSyA1234567890abcdefghijklmnopqrstu', 'gemini').warning).toBeNull()
    expect(apiKey('anything-goes-here', 'custom').warning).toBeNull()
  })

  it('reads key-save requests in the new and the older form', () => {
    expect(apiKeyRequest('sk-ant-api03-abcdefghijklmnop')).toMatchObject({ provider: 'anthropic', key: 'sk-ant-api03-abcdefghijklmnop' })
    expect(apiKeyRequest({ provider: 'deepseek', key: 'sk-0123456789abcdef0123' })).toMatchObject({ provider: 'deepseek', warning: null })
    expect(() => apiKeyRequest({ provider: 'skynet', key: 'x' })).toThrow(/not supported/)
  })
})

describe('AI error mapping', () => {
  it('maps HTTP statuses to error codes', () => {
    expect(codeForStatus(401)).toBe('bad-key')
    expect(codeForStatus(403)).toBe('bad-key')
    expect(codeForStatus(429)).toBe('rate-limit')
    expect(codeForStatus(529)).toBe('overloaded')
    expect(codeForStatus(503)).toBe('overloaded')
    expect(codeForStatus(400)).toBe('api')
    expect(codeForStatus(500)).toBe('api')
  })

  it('uses fixed messages for known codes and the API detail for others', () => {
    expect(errorResult(401, {})).toEqual({ ok: false, code: 'bad-key', message: AI_MESSAGES['bad-key'] })
    const r = errorResult(400, { type: 'error', error: { type: 'invalid_request_error', message: 'model: not found' } })
    expect(r.ok).toBe(false)
    if (!r.ok) {
      expect(r.code).toBe('api')
      expect(r.message).toContain('model: not found')
    }
  })

  it('joins text blocks and reads usage', () => {
    const r = successResult({
      content: [
        { type: 'text', text: '[{"a_ids":' },
        { type: 'thinking', thinking: 'x' },
        { type: 'text', text: '[]}]' }
      ],
      usage: { input_tokens: 1200, output_tokens: 80 }
    })
    expect(r).toEqual({ ok: true, response: { text: '[{"a_ids":[]}]', inputTokens: 1200, outputTokens: 80 } })
  })

  it('reports an unreadable success body as an API error', () => {
    expect(successResult(null).ok).toBe(false)
  })
})

describe('request validation', () => {
  it('validates AI requests', () => {
    const ok = aiRequest({ model: 'claude-sonnet-5-5', system: 'sys', messages: [{ role: 'user', content: 'hi' }], maxTokens: 4000 })
    expect(ok.model).toBe('claude-sonnet-5-5')
    expect(ok.effort).toBeUndefined()
    expect(aiRequest({ model: 'm', messages: [{ role: 'user', content: 'hi' }], maxTokens: 10, effort: 'medium' }).effort).toBe('medium')
    expect(() => aiRequest({ model: 'm', messages: [{ role: 'user', content: 'hi' }], maxTokens: 10, effort: 'max' })).toThrow()
    expect(() => aiRequest({ model: 'x y', messages: [{ role: 'user', content: 'hi' }], maxTokens: 10 })).toThrow()
    expect(() => aiRequest({ model: 'm', messages: [], maxTokens: 10 })).toThrow()
    expect(() => aiRequest({ model: 'm', messages: [{ role: 'system', content: 'hi' }], maxTokens: 10 })).toThrow()
    expect(() => aiRequest({ model: 'm', messages: [{ role: 'user', content: 'hi' }], maxTokens: 1.5 })).toThrow()
  })

  it('rejects path traversal in sample paths', () => {
    expect(samplePathSegments('bank/GL_101200_Cash_Sep2026.xlsx')).toEqual(['bank', 'GL_101200_Cash_Sep2026.xlsx'])
    for (const bad of ['../package.json', 'bank/../../x', '/etc/passwd', 'C:/Windows/win.ini', 'bank\\x.xlsx', 'bank//x', '.hidden', '']) {
      expect(() => samplePathSegments(bad), bad).toThrow()
    }
  })

  it('makes safe Windows file names', () => {
    expect(safeFileName('Bank Recon: Sep/2026?.xlsx')).toBe('Bank Recon_ Sep_2026_.xlsx')
    expect(safeFileName('..\\..\\evil.pdf')).toBe('.._.._evil.pdf')
    expect(safeFileName('CON')).toBe('Reco-Do export')
    expect(safeFileName('')).toBe('Reco-Do export')
    expect(safeFileName('report. ')).toBe('report')
  })

  it('adds .pdf to PDF names and requires HTML', () => {
    expect(pdfRequest({ html: '<p>x</p>', defaultName: 'Summary' })).toEqual({ html: '<p>x</p>', defaultName: 'Summary.pdf', landscape: false })
    expect(pdfRequest({ html: '<p>x</p>', defaultName: 'S.PDF', landscape: true }).landscape).toBe(true)
    expect(() => pdfRequest({ html: '', defaultName: 'x' })).toThrow()
  })

  it('validates filters and binary data', () => {
    expect(fileFilters([{ name: 'Excel', extensions: ['.xlsx', 'xls'] }])).toEqual([{ name: 'Excel', extensions: ['xlsx', 'xls'] }])
    expect(() => fileFilters([{ name: 'Bad', extensions: ['x/y'] }])).toThrow()
    expect(binaryData(new Uint8Array([1, 2])).byteLength).toBe(2)
    expect(binaryData(new ArrayBuffer(3)).byteLength).toBe(3)
    expect(() => binaryData('text')).toThrow()
  })
})
