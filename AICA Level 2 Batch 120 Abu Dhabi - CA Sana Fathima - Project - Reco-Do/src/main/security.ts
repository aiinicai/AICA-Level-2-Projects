// Network and content rules for the app's windows. Pure functions (no Electron imports) so they can be unit-tested.

import type { AiProvider } from '../shared/contracts'
import { AI_PROVIDER_INFO, checkBaseUrl, isLocalHost } from '../shared/aiProviders'

/**
 * Content Security Policy of the app page and its workers. The same policy is in src/renderer/index.html; the
 * protocol handler also sends it as a response header, which (unlike the meta tag) applies to workers too.
 * 'wasm-unsafe-eval' lets the bundled OCR (tesseract) and PDF (pdf.js) WebAssembly run.
 */
export const APP_CSP = [
  "default-src 'self'",
  "script-src 'self' 'wasm-unsafe-eval'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob:",
  "font-src 'self' data:",
  "connect-src 'self'",
  "worker-src 'self' blob:",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'none'"
].join('; ')

/** The print page for PDF export loads nothing at all: inline styles and embedded images only, no scripts. */
export const PRINT_CSP = "default-src 'none'; style-src 'unsafe-inline'; img-src data: blob:; font-src data:; base-uri 'none'; form-action 'none'"

/** Puts PRINT_CSP first in the export HTML's <head> (or in front of the document when it has none). */
export function withPrintCsp(html: string): string {
  const meta = `<meta http-equiv="Content-Security-Policy" content="${PRINT_CSP}">`
  const head = /<head(\s[^>]*)?>/i.exec(html)
  if (head) return html.slice(0, head.index + head[0].length) + meta + html.slice(head.index + head[0].length)
  return `<!doctype html><html><head><meta charset="utf-8">${meta}</head><body>${html}</body></html>`
}

/**
 * Requests the app window's session may make: the app's own files, in-memory blob:/data: URLs and DevTools.
 * In development the Vite dev server (http + its websocket) is allowed too. Everything else, including any
 * attempt to reach the internet from the page, is cancelled. The Smart Recon call uses its own session.
 */
export function isAllowedAppRequest(url: string, devServerUrl?: string): boolean {
  if (/^(app|blob|data|devtools|chrome-extension):/i.test(url)) return true
  if (devServerUrl) {
    try {
      const dev = new URL(devServerUrl)
      const u = new URL(url)
      if ((u.protocol === 'http:' || u.protocol === 'https:' || u.protocol === 'ws:' || u.protocol === 'wss:') && u.host === dev.host) return true
    } catch {
      return false
    }
  }
  return false
}

/**
 * The Smart Recon session of `provider` may reach that provider's official API origin and nothing else:
 * api.anthropic.com, api.openai.com, generativelanguage.googleapis.com or api.deepseek.com, always over https.
 * For 'custom', only `customOrigin` (the base URL the user saved in Settings) is allowed: https, or plain http
 * when it is this computer (localhost / 127.0.0.1). With no saved origin, nothing is allowed.
 */
export function isAllowedAiRequest(url: string, provider: AiProvider = 'anthropic', customOrigin?: string | null): boolean {
  let u: URL
  try {
    u = new URL(url)
  } catch {
    return false
  }
  if (u.username || u.password) return false
  const official = AI_PROVIDER_INFO[provider].origin
  if (official) return u.protocol === 'https:' && u.origin === official
  if (!customOrigin) return false
  const check = checkBaseUrl(customOrigin)
  return check.ok && u.origin === check.origin && (u.protocol === 'https:' || (u.protocol === 'http:' && isLocalHost(u.hostname)))
}
