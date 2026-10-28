// Serves the built renderer from app://reco-do/ instead of file://.
// A real (standard, secure) origin lets the page and its workers fetch the bundled OCR and PDF assets
// (Chromium blocks fetch() on file:// URLs), and gives IndexedDB a stable origin. Only files inside
// the renderer output folder can be served.

import { readFile } from 'fs/promises'
import { extname, resolve, sep } from 'path'
import type { Protocol } from 'electron'
import { APP_CSP } from './security'

export const APP_SCHEME = 'app'
export const APP_HOST = 'reco-do'
export const APP_ORIGIN = `${APP_SCHEME}://${APP_HOST}`

const MIME: Record<string, string> = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.wasm': 'application/wasm',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.ttf': 'font/ttf',
  '.pfb': 'application/octet-stream',
  '.bcmap': 'application/octet-stream',
  '.icc': 'application/vnd.iccprofile',
  '.gz': 'application/octet-stream',
  '.map': 'application/json; charset=utf-8'
}

export function registerAppScheme(protocol: Protocol): void {
  protocol.registerSchemesAsPrivileged([
    { scheme: APP_SCHEME, privileges: { standard: true, secure: true, supportFetchAPI: true, codeCache: true } }
  ])
}

function notFound(): Response {
  return new Response('Not found', { status: 404, headers: { 'content-type': 'text/plain' } })
}

export function registerAppProtocol(protocol: Protocol, rendererRoot: string): void {
  const root = resolve(rendererRoot)
  protocol.handle(APP_SCHEME, async (request) => {
    let url: URL
    try {
      url = new URL(request.url)
    } catch {
      return notFound()
    }
    if (url.host !== APP_HOST || request.method !== 'GET') return notFound()
    let pathname: string
    try {
      pathname = decodeURIComponent(url.pathname)
    } catch {
      return notFound()
    }
    if (pathname === '/' || pathname === '') pathname = '/index.html'
    const file = resolve(root, `.${pathname}`)
    if (!file.startsWith(root + sep)) return notFound()
    try {
      const body = await readFile(file)
      return new Response(body, {
        status: 200,
        headers: {
          'content-type': MIME[extname(file).toLowerCase()] ?? 'application/octet-stream',
          'x-content-type-options': 'nosniff',
          // Sent with every file: the page gets it in addition to its meta tag, and workers get it only this way.
          'content-security-policy': APP_CSP
        }
      })
    } catch {
      return notFound()
    }
  })
}
