// pdf.js / OCR wiring for the tool screens, plus a small page-thumbnail cache.
// Everything here uses the assets bundled with the app (src/renderer/src/lib/offlineAssets.ts); nothing is downloaded.

import { offscreenCanvasFactory, openThumbnailSource, type PdfJsLib, type ThumbnailSource } from '@tools/common'
import type { OcrOptions } from '@tools/pdf-to-excel'
import { loadPdfJs, ocrCorePath, ocrLangPath, ocrWorkerPath, PDFJS_DOCUMENT_OPTIONS } from '@/lib/offlineAssets'

export interface PdfRuntime {
  pdfjs: PdfJsLib
  documentParams: Record<string, unknown>
}

/** pdf.js with its bundled worker, plus the offline CMaps / fonts / wasm locations. */
export async function pdfRuntime(): Promise<PdfRuntime> {
  const pdfjs = await loadPdfJs()
  return { pdfjs, documentParams: { ...PDFJS_DOCUMENT_OPTIONS } }
}

/** Offline OCR assets (tesseract worker, core and English language data shipped with the app). */
export const OCR_OPTIONS: OcrOptions = {
  workerPath: ocrWorkerPath,
  corePath: ocrCorePath,
  langPath: ocrLangPath,
  gzip: true
}

// ───────────────────────── Thumbnails ─────────────────────────

const sources = new Map<string, Promise<ThumbnailSource<OffscreenCanvas>>>()
const urls = new Map<string, Promise<string>>()

function source(key: string, data: ArrayBuffer | Uint8Array): Promise<ThumbnailSource<OffscreenCanvas>> {
  let s = sources.get(key)
  if (!s) {
    s = pdfRuntime().then((rt) => openThumbnailSource<OffscreenCanvas>(data, { ...rt, canvasFactory: offscreenCanvasFactory }))
    sources.set(key, s)
    s.catch(() => sources.delete(key))
  }
  return s
}

/**
 * Object URL of a PNG thumbnail of page `pageIndex` (0-based), `width` pixels wide. `key` identifies the
 * file (one open pdf.js document per key); results are cached until `releaseThumbnails(key)`.
 */
export function thumbnailUrl(key: string, data: ArrayBuffer | Uint8Array, pageIndex: number, width: number): Promise<string> {
  const id = `${key}|${pageIndex}|${width}`
  let u = urls.get(id)
  if (!u) {
    u = source(key, data)
      .then((src) => src.render(pageIndex, width))
      .then((t) => t.canvas.convertToBlob({ type: 'image/png' }))
      .then((blob) => URL.createObjectURL(blob))
    urls.set(id, u)
    u.catch(() => urls.delete(id))
  }
  return u
}

/** Frees the thumbnails and the open document of one file. */
export function releaseThumbnails(key: string): void {
  for (const [id, u] of urls) {
    if (!id.startsWith(`${key}|`)) continue
    urls.delete(id)
    void u.then((url) => URL.revokeObjectURL(url)).catch(() => undefined)
  }
  const s = sources.get(key)
  if (s) {
    sources.delete(key)
    void s.then((src) => src.destroy()).catch(() => undefined)
  }
}
