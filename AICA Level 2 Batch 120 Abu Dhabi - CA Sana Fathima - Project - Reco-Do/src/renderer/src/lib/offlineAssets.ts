// URLs of the OCR and PDF assets bundled with the app (copied from node_modules at build time by
// electron.vite.config.ts). Nothing is downloaded at run time, so OCR and PDF reading work offline.
//
// Tesseract (OCR):
//   import { createWorker } from 'tesseract.js'
//   import { TESSERACT_OPTIONS } from '@/lib/offlineAssets'
//   const worker = await createWorker('eng', 1, { ...TESSERACT_OPTIONS, logger: (m) => onProgress(m) })
//
// pdf.js (the worker is configured once at start-up by App.tsx through loadPdfJs()):
//   import { loadPdfJs, PDFJS_DOCUMENT_OPTIONS } from '@/lib/offlineAssets'
//   const pdfjs = await loadPdfJs()
//   const doc = await pdfjs.getDocument({ data, ...PDFJS_DOCUMENT_OPTIONS }).promise
//   // or with src/tools/common: openPdfJsDocument(data, { pdfjs, documentParams: PDFJS_DOCUMENT_OPTIONS })
// The worker file itself comes from `import url from 'pdfjs-dist/build/pdf.worker.min.mjs?url'` (below).
//
// In the packaged app the page is served from app://reco-do/ (see src/main/protocol.ts), not file://,
// so fetch() and workers can load these files exactly as in dev.
//
// Pure engines under src/tools should not import this file (it reads document.baseURI); let the UI
// pass these options in.

import pdfWorkerAsset from 'pdfjs-dist/build/pdf.worker.min.mjs?url'

/** Absolute URL of a bundled asset. Workers need absolute URLs because they resolve against their own location. */
export function assetUrl(path: string): string {
  const base = typeof document !== 'undefined' ? document.baseURI : 'http://localhost/'
  return new URL(path, base).href
}

/** Tesseract worker script (tesseract.js/dist/worker.min.js). */
export const ocrWorkerPath = assetUrl('ocr/worker.min.js')
/** Folder holding tesseract.js-core *.wasm.js builds; tesseract picks the SIMD / LSTM variant itself. */
export const ocrCorePath = assetUrl('ocr/core')
/** Folder holding eng.traineddata.gz (from @tesseract.js-data/eng/4.0.0). */
export const ocrLangPath = assetUrl('ocr/lang')

/** Options for tesseract.js createWorker(). workerBlobURL is off so the worker loads straight from the app. */
export const TESSERACT_OPTIONS = {
  workerPath: ocrWorkerPath,
  corePath: ocrCorePath,
  langPath: ocrLangPath,
  workerBlobURL: false,
  gzip: true
} as const

/** pdf.js worker (pdfjs-dist/build/pdf.worker.min.mjs), emitted by Vite as a hashed asset. */
export const pdfWorkerUrl: string = assetUrl(pdfWorkerAsset)

/**
 * The pdf.js module with its worker configured. App.tsx calls this once at start-up, so any later
 * `import('pdfjs-dist')` (e.g. src/tools/common/pdfjs.ts) already has `GlobalWorkerOptions.workerSrc` set.
 */
export async function loadPdfJs(): Promise<typeof import('pdfjs-dist')> {
  const pdfjs = await import('pdfjs-dist')
  if (!pdfjs.GlobalWorkerOptions.workerSrc) pdfjs.GlobalWorkerOptions.workerSrc = pdfWorkerUrl
  return pdfjs
}

/** Extra pdf.js getDocument() options so CMaps, standard fonts, wasm decoders and ICC profiles load offline. */
export const PDFJS_DOCUMENT_OPTIONS = {
  cMapUrl: assetUrl('pdfjs/cmaps/'),
  cMapPacked: true,
  standardFontDataUrl: assetUrl('pdfjs/standard_fonts/'),
  wasmUrl: assetUrl('pdfjs/wasm/'),
  iccUrl: assetUrl('pdfjs/iccs/')
} as const
