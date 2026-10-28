// PDF → Excel engine. Pure TypeScript, no React.
//
//   import * as pdfjs from 'pdfjs-dist'                       // renderer (worker configured once at start-up)
//   const result = await extractPdf(buffer, {
//     pdfjs, fileName: 'Statement.pdf', pages: '1-3, 5', layout: 'raw',
//     ocr: { workerPath, corePath, langPath }                  // from src/renderer/src/lib/offlineAssets.ts
//   }, (p) => setProgress(p), abortController.signal)
//   // Option changes in the preview (layout, renames, types, join, date order) need no re-read:
//   const updated = reshapeResult(result, { layout: 'bank', columnEdits: { Withdrawals: { name: 'Debit' } } })
//   const xlsx = await toWorkbook(updated, { oneSheetPerTable: true, addPageColumn: true })
//
// Errors are ToolErrors with plain-English messages (password-protected, invalid-pdf, invalid-option,
// empty-result, ocr-failed, cancelled).

import { closePdfJsDocument, openPdfJsDocument, parsePageSelection, throwIfAborted, ToolError } from '../common'
import { reconstruct, type PageWords } from './layout'
import { createOcrEngine, ocrPage, OCR_START_FAILED_MESSAGE, type OcrEngine } from './ocr'
import { shapeTables } from './shape'
import { readTextWords } from './textLayer'
import type { PdfExtractOptions, PdfExtractResult, PdfPageInfo, PdfProgress, PdfShapeOptions } from './types'

export * from './types'
export { toWorkbook, AMOUNT_FORMAT, DATE_FORMAT, LOW_CONFIDENCE_FILL } from './workbook'
export { suggestBankMapping, resolveBankMapping } from './bank'
export {
  createOcrEngine,
  ocrPage,
  pixelWordsToPdfWords,
  canvasToOcrImage,
  isOcrNoise,
  isLocalAssetPath,
  assertLocalOcrAssets,
  tesseractLoader,
  OCR_START_FAILED_MESSAGE,
  OCR_ASSETS_MISSING_MESSAGE,
  type OcrEngine,
  type OcrImage,
  type OcrPixelWord
} from './ocr'
export { buildLines, reconstruct, isAmountText, isDateText, isPageNumberText, type PageWords, type Line, type Segment } from './layout'
export { shapeTables, repairOcrAmount, convertCell, headersMatch, uniqueColumnNames } from './shape'

export const DEFAULT_LOW_CONFIDENCE = 85
export const DEFAULT_OCR_DPI = 300
export const DEFAULT_SCANNED_TEXT_THRESHOLD = 20

const now = (): number => (typeof performance !== 'undefined' ? performance.now() : Date.now())

/**
 * Reads the chosen pages of a PDF and rebuilds their tables.
 * Digital pages use the text layer; pages with (almost) no text are rendered and OCR'd when `opts.ocr` is given.
 * `onProgress` fires before each page (stage 'text') and again before OCR (stage 'ocr').
 */
export async function extractPdf(
  data: ArrayBuffer | Uint8Array,
  opts: PdfExtractOptions = {},
  onProgress?: (p: PdfProgress) => void,
  signal?: AbortSignal
): Promise<PdfExtractResult> {
  const started = now()
  const doc = await openPdfJsDocument(data, opts, signal)
  const lowConfidenceBelow = opts.ocr?.lowConfidenceBelow ?? DEFAULT_LOW_CONFIDENCE
  const threshold = opts.scannedTextThreshold ?? DEFAULT_SCANNED_TEXT_THRESHOLD
  const dpi = opts.ocr?.dpi ?? DEFAULT_OCR_DPI
  try {
    const pageCount = doc.numPages
    const selected = parsePageSelection(opts.pages, pageCount)
    const pageWords: PageWords[] = []
    const pages: PdfPageInfo[] = []
    const warnings: string[] = []
    let engine: OcrEngine | null = null
    /** Set when the OCR engine could not start: scanned pages are then skipped, digital pages still read. */
    let ocrStartError: ToolError | null = null
    try {
      for (let k = 0; k < selected.length; k++) {
        throwIfAborted(signal)
        const pn = selected[k]
        onProgress?.({ page: pn, pages: selected.length, index: k + 1, stage: 'text' })
        const page = await doc.getPage(pn)
        const words = await readTextWords(page)
        page.cleanup()
        const chars = words.reduce((n, w) => n + w.text.replace(/\s/g, '').length, 0)
        if (chars >= threshold) {
          pageWords.push({ page: pn, method: 'text', words })
          pages.push({ page: pn, method: 'text', words: words.length })
          continue
        }
        if (!opts.ocr) {
          pages.push({ page: pn, method: 'scanned-skipped', words: words.length })
          warnings.push(`Page ${pn} looks scanned (no text layer) and text recognition is not available, so it was skipped.`)
          continue
        }
        if (!engine && !ocrStartError) {
          onProgress?.({ page: pn, pages: selected.length, index: k + 1, stage: 'ocr' })
          try {
            engine = await createOcrEngine(opts.ocr)
          } catch (e) {
            ocrStartError = e instanceof ToolError ? e : new ToolError('ocr-failed', OCR_START_FAILED_MESSAGE, String(e))
          }
          throwIfAborted(signal)
        } else onProgress?.({ page: pn, pages: selected.length, index: k + 1, stage: 'ocr' })
        if (!engine) {
          pages.push({ page: pn, method: 'scanned-skipped', words: words.length })
          warnings.push(`Page ${pn} looks scanned (no text layer), but text recognition (OCR) could not start, so it was skipped.`)
          continue
        }
        try {
          const r = await ocrPage(doc, pn, engine, { dpi, canvasFactory: opts.canvasFactory }, signal)
          if (r.words.length === 0) {
            pages.push({ page: pn, method: 'empty', words: 0 })
            warnings.push(`Page ${pn} is blank or unreadable; no text was found.`)
          } else {
            pageWords.push({ page: pn, method: 'ocr', words: r.words })
            pages.push({ page: pn, method: 'ocr', words: r.words.length, ocrConfidence: r.meanConfidence })
          }
        } catch (e) {
          if (e instanceof ToolError && e.code === 'cancelled') throw e
          pages.push({ page: pn, method: 'empty', words: 0 })
          warnings.push(`Page ${pn} could not be read with text recognition (OCR) and was skipped.`)
        }
      }
    } finally {
      if (engine) await engine.terminate()
    }
    throwIfAborted(signal)

    const layout = reconstruct(pageWords)
    const shaped = shapeTables(layout.fragments, layout.excluded, opts, lowConfidenceBelow)
    if (shaped.tables.length === 0) {
      const allScanned = pages.length > 0 && pages.every((p) => p.method === 'scanned-skipped')
      if (allScanned && ocrStartError) throw ocrStartError
      throw new ToolError(
        'empty-result',
        allScanned
          ? 'This PDF is a scanned image and text recognition (OCR) is not available, so no table could be read.'
          : 'No table was found in the selected pages. The PDF may contain only plain text or pictures.'
      )
    }
    return {
      fileName: opts.fileName ?? 'document.pdf',
      pageCount,
      pages,
      ocrPages: pages.filter((p) => p.method === 'ocr').map((p) => p.page),
      ...shaped,
      warnings,
      lowConfidenceBelow,
      fragments: layout.fragments,
      pageExcluded: layout.excluded,
      durationMs: Math.round(now() - started)
    }
  } finally {
    await closePdfJsDocument(doc)
  }
}

/**
 * Re-applies shape options (layout, bank mapping, join, repeated headers, conversion, date order, column edits)
 * to an existing result without reading the PDF again. Options not given keep their current values.
 */
export function reshapeResult(result: PdfExtractResult, opts: PdfShapeOptions): PdfExtractResult {
  const merged: PdfShapeOptions = { ...result.options, ...opts }
  const shaped = shapeTables(result.fragments, result.pageExcluded, merged, result.lowConfidenceBelow)
  return { ...result, ...shaped }
}
