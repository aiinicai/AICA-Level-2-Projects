// Scanned pages: render with pdf.js, then on-device OCR with tesseract.js (word boxes + confidences).
// Asset paths are injected (offline bundle in the app, node_modules in tests); nothing is downloaded.

import type { PDFDocumentProxy } from 'pdfjs-dist'
import { CANCELLED_MESSAGE, renderPageToCanvas, ToolError, type CanvasFactory } from '../common'
import type { OcrOptions, PdfWord } from './types'

/** Image input accepted by tesseract.js in both the renderer and Node. */
export type OcrImage = Blob | Uint8Array | HTMLCanvasElement | OffscreenCanvas | string

export interface TessWord {
  text: string
  confidence: number
  bbox: { x0: number; y0: number; x1: number; y1: number }
}
export interface TessPage {
  blocks: { paragraphs: { lines: { words: TessWord[] }[] }[] }[] | null
}
export interface TessWorker {
  recognize(image: unknown, options?: Record<string, unknown>, output?: Record<string, boolean>): Promise<{ data: TessPage }>
  setParameters(params: Record<string, string>): Promise<unknown>
  terminate(): Promise<unknown>
}
export interface TessModule {
  createWorker(langs: string, oem: number, options: Record<string, unknown>): Promise<TessWorker>
}

/** A word found by OCR, in image pixels. */
export interface OcrPixelWord {
  text: string
  confidence: number
  x0: number
  y0: number
  x1: number
  y1: number
}

export interface OcrEngine {
  recognize(image: OcrImage, signal?: AbortSignal): Promise<OcrPixelWord[]>
  terminate(): Promise<void>
}

/** Overridable for tests: loads the tesseract.js module. */
export const tesseractLoader: { load: () => Promise<TessModule> } = { load: () => importTesseract() }

async function loadTesseract(): Promise<TessModule> {
  return tesseractLoader.load()
}

async function importTesseract(): Promise<TessModule> {
  // tesseract.js is CommonJS: the functions sit on the default export under ESM interop.
  const mod = (await import('tesseract.js')) as unknown as Partial<TessModule> & { default?: TessModule }
  const createWorker = mod.createWorker ?? mod.default?.createWorker
  if (!createWorker) throw new Error('tesseract.js createWorker not found')
  return { createWorker }
}

export const OCR_START_FAILED_MESSAGE =
  'The text recognition (OCR) engine could not start, so scanned pages cannot be read. Restart Reco-Do and try again.'
export const OCR_ASSETS_MISSING_MESSAGE =
  'Text recognition (OCR) is not set up in this installation (its files are missing), so scanned pages cannot be read. Reinstall Reco-Do to restore it.'

/**
 * True for a location on this computer: a file path, or a file:, app:, blob: or localhost URL (the dev server).
 * Anything else (a CDN such as jsdelivr) would download the OCR engine from the internet, which Reco-Do never does.
 */
export function isLocalAssetPath(path: string): boolean {
  const p = path.trim()
  if (p === '') return false
  const m = /^([a-z][a-z0-9+.-]*):/i.exec(p)
  if (!m || /^[a-z]$/i.test(m[1])) return true // no scheme, or a Windows drive letter ("C:\...")
  const scheme = m[1].toLowerCase()
  if (scheme === 'file' || scheme === 'app' || scheme === 'blob') return true
  if (scheme === 'http' || scheme === 'https') {
    try {
      const host = new URL(p).hostname
      return host === 'localhost' || host === '127.0.0.1' || host === '[::1]' || host === '::1'
    } catch {
      return false
    }
  }
  return false
}

/**
 * Checks that the worker script, the wasm core and the language data all come from explicit local paths.
 * tesseract.js would otherwise fall back to downloading them from a CDN.
 */
export function assertLocalOcrAssets(opts: Partial<OcrOptions>): void {
  const missing = (['workerPath', 'corePath', 'langPath'] as const).filter((k) => !opts[k] || !isLocalAssetPath(String(opts[k])))
  if (missing.length > 0) {
    throw new ToolError('ocr-failed', OCR_ASSETS_MISSING_MESSAGE, `OCR asset paths missing or not local: ${missing.join(', ')}`)
  }
}

/**
 * Starts one tesseract worker (English, LSTM). Call `terminate()` when done. The worker, core and language
 * paths are required and must be local (see `assertLocalOcrAssets`); nothing is downloaded.
 */
export async function createOcrEngine(opts: OcrOptions): Promise<OcrEngine> {
  assertLocalOcrAssets(opts)
  let worker: TessWorker | undefined
  try {
    const T = await loadTesseract()
    // workerBlobURL off: the worker script loads straight from its URL instead of through a blob: wrapper, which
    // the app's Content-Security-Policy need not allow (Node ignores the option).
    const options: Record<string, unknown> = {
      workerPath: opts.workerPath,
      corePath: opts.corePath,
      langPath: opts.langPath,
      gzip: opts.gzip ?? true,
      cacheMethod: 'none',
      workerBlobURL: false
    }
    worker = await T.createWorker('eng', 1, options)
    await worker.setParameters({ preserve_interword_spaces: '0', user_defined_dpi: String(opts.dpi ?? 300) })
  } catch (e) {
    // A worker that started but could not be configured must not stay alive in the background.
    if (worker) await worker.terminate().catch(() => undefined)
    throw new ToolError('ocr-failed', OCR_START_FAILED_MESSAGE, e instanceof Error ? e.message : String(e))
  }
  const started: TessWorker = worker
  let terminated = false
  const terminate = async (): Promise<void> => {
    if (terminated) return
    terminated = true
    await started.terminate()
  }
  return {
    terminate,
    async recognize(image, signal) {
      if (signal?.aborted) throw new ToolError('cancelled', CANCELLED_MESSAGE)
      let onAbort: (() => void) | undefined
      const aborted = new Promise<never>((_, reject) => {
        onAbort = () => {
          void terminate()
          reject(new ToolError('cancelled', CANCELLED_MESSAGE))
        }
        signal?.addEventListener('abort', onAbort, { once: true })
      })
      try {
        const res = await Promise.race([started.recognize(image, {}, { blocks: true, text: false }), aborted])
        const out: OcrPixelWord[] = []
        for (const b of res.data.blocks ?? [])
          for (const p of b.paragraphs)
            for (const l of p.lines)
              for (const w of l.words) {
                const text = w.text.trim()
                if (text) out.push({ text, confidence: w.confidence, x0: w.bbox.x0, y0: w.bbox.y0, x1: w.bbox.x1, y1: w.bbox.y1 })
              }
        return out
      } finally {
        if (onAbort) signal?.removeEventListener('abort', onAbort)
      }
    }
  }
}

/** Converts a rendered canvas into something tesseract.js reads in the current environment. */
export async function canvasToOcrImage(canvas: unknown): Promise<OcrImage> {
  const c = canvas as { toBuffer?: (mime: string) => Uint8Array; convertToBlob?: (o: { type: string }) => Promise<Blob> }
  if (typeof c.toBuffer === 'function') return c.toBuffer('image/png') // @napi-rs/canvas / node-canvas (Node)
  if (typeof OffscreenCanvas !== 'undefined' && canvas instanceof OffscreenCanvas) return canvas.convertToBlob({ type: 'image/png' })
  if (typeof c.convertToBlob === 'function') return c.convertToBlob({ type: 'image/png' })
  return canvas as HTMLCanvasElement
}

/** Specks and scan dirt read as symbols ("~~", "'") with low confidence. Real symbols such as "&" or "|" read with high confidence. */
export function isOcrNoise(w: OcrPixelWord): boolean {
  return !/[A-Za-z0-9]/.test(w.text) && w.confidence < 60
}

/** Pixel words → PdfWords in points (top-left origin), noise removed. Text height is scaled up to an approximate font size. */
export function pixelWordsToPdfWords(words: OcrPixelWord[], scale: number): PdfWord[] {
  return words.filter((w) => !isOcrNoise(w)).map((w) => {
    const height = (w.y1 - w.y0) / scale
    return {
      text: w.text,
      x0: w.x0 / scale,
      x1: w.x1 / scale,
      top: w.y0 / scale,
      bottom: w.y1 / scale,
      size: Math.max(4, height * 1.25),
      confidence: w.confidence
    }
  })
}

/** Renders a page at `dpi` and OCRs it. Returns the words in PDF points and the mean confidence. */
export async function ocrPage(
  doc: PDFDocumentProxy,
  pageNumber: number,
  engine: OcrEngine,
  opts: { dpi: number; canvasFactory?: CanvasFactory },
  signal?: AbortSignal
): Promise<{ words: PdfWord[]; meanConfidence: number }> {
  const scale = opts.dpi / 72
  const rendered = await renderPageToCanvas(doc, pageNumber, scale, opts.canvasFactory)
  const image = await canvasToOcrImage(rendered.canvas)
  const pixelWords = await engine.recognize(image, signal)
  // Release the large bitmap early (a 300 dpi A4 page is ~35 MB).
  const c = rendered.canvas as { width?: number; height?: number }
  if (image !== rendered.canvas && typeof c.width === 'number') {
    c.width = 0
    c.height = 0
  }
  const words = pixelWordsToPdfWords(pixelWords, scale)
  const meanConfidence = words.length ? Math.round(words.reduce((s, w) => s + (w.confidence ?? 0), 0) / words.length) : 0
  return { words, meanConfidence }
}
