import { resolve, join, extname, relative, sep } from 'path'
import { cpSync, createReadStream, existsSync, mkdirSync, readFileSync, statSync } from 'fs'
import { defineConfig, externalizeDepsPlugin } from 'electron-vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import type { Plugin } from 'vite'

const alias = {
  '@': resolve('src/renderer/src'),
  '@shared': resolve('src/shared'),
  '@engine': resolve('src/engine'),
  '@tools': resolve('src/tools'),
  '@export': resolve('src/export')
}

// Offline OCR and PDF assets. They are copied from node_modules into the renderer output at build time
// (and served from node_modules by the dev server), so nothing large is committed and nothing is
// downloaded at run time. The URLs are exposed to the UI by src/renderer/src/lib/offlineAssets.ts.
const NM = resolve('node_modules')
const OFFLINE_ASSETS: Array<{ url: string; from: string }> = [
  { url: 'ocr/worker.min.js', from: join(NM, 'tesseract.js/dist/worker.min.js') },
  ...[
    'tesseract-core.wasm.js',
    'tesseract-core-simd.wasm.js',
    'tesseract-core-relaxedsimd.wasm.js',
    'tesseract-core-lstm.wasm.js',
    'tesseract-core-simd-lstm.wasm.js',
    'tesseract-core-relaxedsimd-lstm.wasm.js'
  ].map((f) => ({ url: `ocr/core/${f}`, from: join(NM, 'tesseract.js-core', f) })),
  { url: 'ocr/lang/eng.traineddata.gz', from: join(NM, '@tesseract.js-data/eng/4.0.0/eng.traineddata.gz') },
  // pdf.js extras: CMaps, standard fonts, image-decoder wasm and colour profiles.
  { url: 'pdfjs/cmaps', from: join(NM, 'pdfjs-dist/cmaps') },
  { url: 'pdfjs/standard_fonts', from: join(NM, 'pdfjs-dist/standard_fonts') },
  { url: 'pdfjs/wasm', from: join(NM, 'pdfjs-dist/wasm') },
  { url: 'pdfjs/iccs', from: join(NM, 'pdfjs-dist/iccs') }
]

const DEV_MIME: Record<string, string> = {
  '.js': 'text/javascript',
  '.mjs': 'text/javascript',
  '.wasm': 'application/wasm',
  '.json': 'application/json'
}

function offlineAssets(): Plugin {
  let outDir = ''
  return {
    name: 'reco-do-offline-assets',
    configResolved(config) {
      outDir = resolve(config.root, config.build.outDir)
    },
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const path = decodeURIComponent((req.url ?? '').split('?')[0]).replace(/^\/+/, '')
        const asset = OFFLINE_ASSETS.find((a) => path === a.url || path.startsWith(`${a.url}/`))
        if (!asset) return next()
        const file = resolve(asset.from, relative(asset.url, path))
        if (file !== asset.from && !file.startsWith(asset.from + sep)) return next()
        if (!existsSync(file) || !statSync(file).isFile()) return next()
        res.setHeader('Content-Type', DEV_MIME[extname(file)] ?? 'application/octet-stream')
        createReadStream(file).pipe(res)
      })
    },
    writeBundle() {
      for (const asset of OFFLINE_ASSETS) {
        if (!existsSync(asset.from)) this.error(`Offline asset missing: ${asset.from}. Run npm install.`)
        const target = join(outDir, asset.url)
        mkdirSync(resolve(target, '..'), { recursive: true })
        cpSync(asset.from, target, { recursive: true })
      }
    }
  }
}

/**
 * The dev server needs an inline React Refresh preamble and a websocket for hot reload.
 * Relax the CSP for `electron-vite dev` only; production builds keep the strict policy from index.html.
 */
function devCsp(): Plugin {
  return {
    name: 'reco-do-dev-csp',
    apply: 'serve',
    transformIndexHtml(html) {
      return html
        .replace("script-src 'self'", "script-src 'self' 'unsafe-inline'")
        .replace("connect-src 'self'", "connect-src 'self' ws://localhost:* http://localhost:*")
    }
  }
}

// Shown in Settings → About. Fixed when the app is built, so every copy of one build shows the same date.
const BUILD_DATE = JSON.stringify(new Date().toISOString())
// Reco-Do's own version from package.json. app.getVersion() reports Electron's version when the app
// is launched through a script (e.g. the screenshot script), so the main process uses this instead.
const APP_VERSION = JSON.stringify((JSON.parse(readFileSync(resolve('package.json'), 'utf8')) as { version: string }).version)

export default defineConfig({
  main: { plugins: [externalizeDepsPlugin()], resolve: { alias }, define: { __RECODO_VERSION__: APP_VERSION } },
  preload: { plugins: [externalizeDepsPlugin()] },
  renderer: { resolve: { alias }, define: { __RECODO_BUILD_DATE__: BUILD_DATE }, plugins: [react(), tailwindcss(), offlineAssets(), devCsp()] }
})
