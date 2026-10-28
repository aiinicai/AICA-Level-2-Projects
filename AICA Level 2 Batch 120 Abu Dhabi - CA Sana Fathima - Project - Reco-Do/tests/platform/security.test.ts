import { readFileSync } from 'fs'
import { join } from 'path'
import { describe, expect, it } from 'vitest'
import { APP_CSP, isAllowedAiRequest, isAllowedAppRequest, PRINT_CSP, withPrintCsp } from '../../src/main/security'
import { aiRequest, aiRequestId, MAX_AI_TOKENS, MAX_PROMPT_CHARS } from '../../src/main/validate'
import type { HistoryEntry } from '../../src/shared/kpis'
import { lastRunLabel } from '../../src/renderer/src/lib/lastRun'
import { errorDetails, errorMessage, isTechnicalError } from '../../src/renderer/src/lib/useAsync'
import { DatabaseError } from '../../src/renderer/src/lib/db'

describe('content security policy', () => {
  it('is the same policy as the meta tag in index.html', () => {
    const html = readFileSync(join(__dirname, '../../src/renderer/index.html'), 'utf8')
    const meta = /http-equiv="Content-Security-Policy"\s+content="([^"]+)"/.exec(html)?.[1]
    expect(meta).toBe(APP_CSP)
    expect(APP_CSP).toContain("connect-src 'self'")
    expect(APP_CSP).not.toMatch(/https?:/)
  })

  it('puts a no-network policy first in the print HTML', () => {
    const out = withPrintCsp('<!doctype html><html><head><meta charset="utf-8"><title>x</title></head><body>Hi</body></html>')
    expect(out.indexOf('Content-Security-Policy')).toBeLessThan(out.indexOf('<title>'))
    expect(out).toContain(PRINT_CSP)
    expect(PRINT_CSP).toContain("default-src 'none'")
    expect(withPrintCsp('<p>No head</p>')).toMatch(/^<!doctype html><html><head>.*Content-Security-Policy.*<p>No head<\/p>/)
  })
})

describe('network allow-lists', () => {
  it('lets the app window load only its own files, blob:, data: and DevTools', () => {
    expect(isAllowedAppRequest('app://reco-do/index.html')).toBe(true)
    expect(isAllowedAppRequest('blob:app://reco-do/1234')).toBe(true)
    expect(isAllowedAppRequest('data:image/png;base64,AAAA')).toBe(true)
    expect(isAllowedAppRequest('devtools://devtools/bundled/inspector.html')).toBe(true)
    expect(isAllowedAppRequest('https://cdn.jsdelivr.net/npm/tesseract.js-core/x.wasm')).toBe(false)
    expect(isAllowedAppRequest('https://api.anthropic.com/v1/messages')).toBe(false)
    expect(isAllowedAppRequest('file:///C:/Windows/win.ini')).toBe(false)
    expect(isAllowedAppRequest('file://server/share/x.html')).toBe(false)
  })

  it('allows the dev server (http and websocket) only in development', () => {
    expect(isAllowedAppRequest('http://localhost:5173/src/main.tsx', 'http://localhost:5173')).toBe(true)
    expect(isAllowedAppRequest('ws://localhost:5173/', 'http://localhost:5173/')).toBe(true)
    expect(isAllowedAppRequest('http://localhost:5173/src/main.tsx')).toBe(false)
    expect(isAllowedAppRequest('http://evil.example/x', 'http://localhost:5173')).toBe(false)
  })

  it('lets the Smart Recon session reach the Anthropic API only', () => {
    expect(isAllowedAiRequest('https://api.anthropic.com/v1/messages')).toBe(true)
    expect(isAllowedAiRequest('http://api.anthropic.com/v1/messages')).toBe(false)
    expect(isAllowedAiRequest('https://api.anthropic.com.evil.example/')).toBe(false)
  })
})

describe('Smart Recon request limits (R16)', () => {
  const msg = (content: string): { role: 'user'; content: string } => ({ role: 'user', content })

  it('refuses requests far larger than a batch, with a clear message', () => {
    expect(MAX_PROMPT_CHARS).toBeLessThanOrEqual(400_000)
    expect(() => aiRequest({ model: 'm', messages: [msg('x'.repeat(MAX_PROMPT_CHARS + 1))], maxTokens: 100 })).toThrow()
    expect(() => aiRequest({ model: 'm', system: 'x'.repeat(250_000), messages: [msg('y'.repeat(200_000))], maxTokens: 100 })).toThrow(/too large/)
    expect(() => aiRequest({ model: 'm', messages: [msg('hi')], maxTokens: MAX_AI_TOKENS + 1 })).toThrow(/32,000/)
    expect(aiRequest({ model: 'm', messages: [msg('hi')], maxTokens: MAX_AI_TOKENS }).maxTokens).toBe(32_000)
  })

  it('accepts and checks the optional request id used for Cancel', () => {
    expect(aiRequest({ model: 'm', messages: [msg('hi')], maxTokens: 10, requestId: 'abc-123' }).requestId).toBe('abc-123')
    expect(aiRequest({ model: 'm', messages: [msg('hi')], maxTokens: 10 }).requestId).toBeUndefined()
    expect(() => aiRequest({ model: 'm', messages: [msg('hi')], maxTokens: 10, requestId: '../x' })).toThrow()
    expect(aiRequestId('6f1c2a7e-0b2d-4c55-9a77-3f1d2e4b5c6d')).toBe('6f1c2a7e-0b2d-4c55-9a77-3f1d2e4b5c6d')
    expect(() => aiRequestId(42)).toThrow()
  })
})

describe('plain-English errors (Q16)', () => {
  it('replaces technical messages with the fallback and keeps them as details', () => {
    const err = new TypeError("Cannot read properties of undefined (reading 'map')")
    expect(isTechnicalError(err)).toBe(true)
    expect(errorMessage(err, 'The list could not be loaded.')).toBe('The list could not be loaded.')
    expect(errorDetails(err)).toBe("TypeError: Cannot read properties of undefined (reading 'map')")
    expect(errorMessage(new DOMException('Key already exists', 'ConstraintError'))).toBe('Something went wrong. Please try again.')
  })

  it('shows our own plain-English messages unchanged', () => {
    expect(errorMessage(new Error('The file is too large to save (limit 512 MB).'))).toBe('The file is too large to save (limit 512 MB).')
    expect(errorDetails(new Error('The file is too large to save (limit 512 MB).'))).toBeNull()
    const db = new DatabaseError('There is not enough free disk space to save.', 'QuotaExceededError: quota')
    expect(errorMessage(db)).toBe('There is not enough free disk space to save.')
    expect(errorDetails(db)).toBe('QuotaExceededError: quota')
  })
})

describe('Dashboard last run (Q24)', () => {
  const h = (moduleId: string, finishedAt: string): HistoryEntry => ({
    id: finishedAt,
    moduleId: moduleId as HistoryEntry['moduleId'],
    accountLabel: 'x',
    finishedAt,
    totalLines: 1,
    autoMatchedLines: 1,
    openItemCount: 0,
    openItemAmount: 0,
    oldestOpenItemDate: null
  })

  it('uses DD-MMM-YYYY, or "today HH:MM" for today', () => {
    const now = new Date(2026, 9, 18, 16, 0)
    expect(lastRunLabel('bank', [], now)).toBe('Last run: never')
    expect(lastRunLabel('bank', [h('bank', new Date(2026, 9, 5, 9, 30).toISOString()), h('bank', new Date(2026, 8, 1).toISOString())], now)).toBe('Last run: 05-Oct-2026')
    expect(lastRunLabel('bank', [h('bank', new Date(2026, 9, 18, 14, 5).toISOString())], now)).toBe('Last run: today 14:05')
    expect(lastRunLabel('ar', [h('bank', new Date(2026, 9, 18, 14, 5).toISOString())], now)).toBe('Last run: never')
  })
})
