// pdf.js access shared by PDF → Excel and the thumbnail helper.
//
// The engines never import a pdf.js build directly at module load. The caller injects one:
//  - Renderer: `import * as pdfjs from 'pdfjs-dist'` with `GlobalWorkerOptions.workerSrc` set once at start-up.
//  - Node / Vitest: `import * as pdfjs from 'pdfjs-dist/legacy/build/pdf.mjs'` (no worker setup needed).
// When nothing is injected, `pdfjs-dist` is imported lazily (the renderer case).

import type { PDFDocumentProxy } from 'pdfjs-dist'
import { throwIfAborted, toPdfOpenError } from './errors'
import { toUint8Copy } from './files'

/** The parts of the pdf.js module the engines use. Both the modern and the legacy build satisfy it. */
export type PdfJsLib = Pick<typeof import('pdfjs-dist'), 'getDocument' | 'VerbosityLevel'>

export interface PdfJsOptions {
  /** Injected pdf.js module. Default: lazy `import('pdfjs-dist')`. */
  pdfjs?: PdfJsLib
  /**
   * Extra `getDocument` parameters, e.g. `standardFontDataUrl`, `cMapUrl`, `cMapPacked`, `wasmUrl`.
   * Needed only for rendering (OCR, thumbnails) of PDFs that use non-embedded fonts.
   */
  documentParams?: Record<string, unknown>
}

/** A canvas plus its 2D context, as created by a canvas factory. */
export interface CanvasAndContext<C = unknown> {
  canvas: C
  context: CanvasRenderingContext2D
}

/**
 * Creates canvases for rendering pages. In the renderer use `offscreenCanvasFactory` (or a DOM factory);
 * in Node pass one backed by `@napi-rs/canvas`. When omitted, pdf.js's own factory for the current
 * environment is used (DOM canvas in the renderer, `@napi-rs/canvas` in Node).
 */
export interface CanvasFactory<C = unknown> {
  create(width: number, height: number): CanvasAndContext<C>
}

/** Canvas factory using OffscreenCanvas (renderer and web workers). */
export const offscreenCanvasFactory: CanvasFactory<OffscreenCanvas> = {
  create(width, height) {
    const canvas = new OffscreenCanvas(Math.max(1, Math.round(width)), Math.max(1, Math.round(height)))
    const context = canvas.getContext('2d')
    if (!context) throw new Error('2D canvas is not available')
    // OffscreenCanvasRenderingContext2D implements everything pdf.js draws with.
    return { canvas, context: context as unknown as CanvasRenderingContext2D }
  }
}

export async function resolvePdfJs(lib?: PdfJsLib): Promise<PdfJsLib> {
  if (lib) return lib
  return import('pdfjs-dist')
}

/**
 * Opens a PDF with pdf.js. A PDF that needs a password throws the standard password ToolError;
 * a damaged file throws `invalid-pdf`. The input buffer is copied (pdf.js transfers it to its worker).
 */
export async function openPdfJsDocument(data: ArrayBuffer | Uint8Array, opts: PdfJsOptions = {}, signal?: AbortSignal): Promise<PDFDocumentProxy> {
  throwIfAborted(signal)
  const lib = await resolvePdfJs(opts.pdfjs)
  const task = lib.getDocument({
    data: toUint8Copy(data),
    verbosity: lib.VerbosityLevel.ERRORS,
    ...opts.documentParams
  })
  // Without an onPassword handler pdf.js rejects with PasswordException, which maps to the password message.
  let doc: PDFDocumentProxy
  try {
    doc = await task.promise
  } catch (e) {
    // Release the loading task (and its worker port) before reporting the failure.
    await task.destroy().catch(() => undefined)
    throw toPdfOpenError(e)
  }
  if (signal?.aborted) {
    // Cancelled while the file was opening: close the document instead of leaking it.
    await task.destroy().catch(() => undefined)
    throwIfAborted(signal)
  }
  return doc
}

/** Releases a document opened with `openPdfJsDocument` (and its worker resources). */
export async function closePdfJsDocument(doc: PDFDocumentProxy): Promise<void> {
  await doc.loadingTask.destroy()
}

/** Pages to images: renders one page at `scale` (1 = 72 dpi) on a canvas from the factory. */
export async function renderPageToCanvas<C>(
  doc: PDFDocumentProxy,
  pageNumber: number,
  scale: number,
  factory?: CanvasFactory<C>
): Promise<CanvasAndContext<C> & { width: number; height: number }> {
  const page = await doc.getPage(pageNumber)
  try {
    const viewport = page.getViewport({ scale })
    const width = Math.max(1, Math.ceil(viewport.width))
    const height = Math.max(1, Math.ceil(viewport.height))
    // pdf.js exposes its environment-specific factory on the document; its shape matches CanvasFactory.
    const f = (factory ?? (doc.canvasFactory as CanvasFactory<C>))
    const cc = f.create(width, height)
    cc.context.fillStyle = '#ffffff'
    cc.context.fillRect(0, 0, width, height)
    await page.render({ canvas: cc.canvas as unknown as HTMLCanvasElement, canvasContext: cc.context, viewport }).promise
    return { ...cc, width, height }
  } finally {
    page.cleanup()
  }
}
