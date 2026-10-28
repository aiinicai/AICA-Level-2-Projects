// Page thumbnails for the Merge / Split / PDF → Excel screens (renderer side, pdf.js + injected canvas).

import type { PDFDocumentProxy } from 'pdfjs-dist'
import { ToolError } from './errors'
import { closePdfJsDocument, openPdfJsDocument, renderPageToCanvas, type CanvasFactory, type PdfJsOptions } from './pdfjs'

export interface ThumbnailOptions<C> extends PdfJsOptions {
  /** Canvas factory (e.g. `offscreenCanvasFactory`). Default: pdf.js's own for the environment. */
  canvasFactory?: CanvasFactory<C>
}

export interface Thumbnail<C> {
  canvas: C
  /** Pixel size of the canvas. */
  width: number
  height: number
  /** 0-based page index. */
  pageIndex: number
}

/**
 * An open PDF that renders thumbnails on demand. Open once per file, render many pages, then `destroy()`.
 * Rendering a page twice is cheap for pdf.js but the caller should cache canvases/blobs it keeps.
 */
export interface ThumbnailSource<C> {
  pageCount: number
  /** Renders page `pageIndex` (0-based) so that the image is `width` pixels wide. */
  render(pageIndex: number, width: number): Promise<Thumbnail<C>>
  destroy(): Promise<void>
}

async function renderOne<C>(doc: PDFDocumentProxy, pageIndex: number, width: number, factory?: CanvasFactory<C>): Promise<Thumbnail<C>> {
  if (!Number.isInteger(pageIndex) || pageIndex < 0 || pageIndex >= doc.numPages) {
    throw new ToolError('invalid-option', `Page ${pageIndex + 1} does not exist. This PDF has ${doc.numPages} pages.`)
  }
  if (!(width > 0)) throw new ToolError('invalid-option', 'Thumbnail width must be greater than zero.')
  const page = await doc.getPage(pageIndex + 1)
  const natural = page.getViewport({ scale: 1 }).width
  page.cleanup()
  const scale = width / natural
  const r = await renderPageToCanvas(doc, pageIndex + 1, scale, factory)
  return { canvas: r.canvas, width: r.width, height: r.height, pageIndex }
}

/** Opens a PDF for repeated thumbnail rendering. Password-protected files throw the standard ToolError. */
export async function openThumbnailSource<C = unknown>(data: ArrayBuffer | Uint8Array, opts: ThumbnailOptions<C> = {}): Promise<ThumbnailSource<C>> {
  const doc = await openPdfJsDocument(data, opts)
  return {
    pageCount: doc.numPages,
    render: (pageIndex, width) => renderOne(doc, pageIndex, width, opts.canvasFactory),
    destroy: () => closePdfJsDocument(doc)
  }
}

/** One-shot helper: renders a single page thumbnail `width` pixels wide. */
export async function renderThumbnail<C = unknown>(
  data: ArrayBuffer | Uint8Array,
  pageIndex: number,
  width: number,
  opts: ThumbnailOptions<C> = {}
): Promise<Thumbnail<C>> {
  const src = await openThumbnailSource<C>(data, opts)
  try {
    return await src.render(pageIndex, width)
  } finally {
    await src.destroy()
  }
}
