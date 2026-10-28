// Split PDF engine (pdf-lib + JSZip). Pure functions, no React.
//
//   const files = await splitPdf(data, { mode: 'every', pages: 5 }, { fileName: 'Statement.pdf' })
//   // → Statement_p1-5.pdf, Statement_p6-10.pdf, Statement_p11-12.pdf
//   const zip = files.length > 1 ? await zipFiles(files) : files[0].data

import { PDFDocument } from 'pdf-lib'
import {
  baseName,
  formatPageList,
  loadEditablePdf,
  parsePageRanges,
  safeFileName,
  throwIfAborted,
  ToolError,
  type OutputFile,
  type PdfJsLib
} from '../common'

export { zipFiles, type OutputFile } from '../common'

export type SplitPlan =
  /** (a) A new file every N pages; the last file holds the remainder. */
  | { mode: 'every'; pages: number }
  /** (b) One file per comma-separated range, e.g. "1-3, 4-6, 7". */
  | { mode: 'ranges'; ranges: string }
  /** (c) The chosen pages (1-based, output in the order given) in one new file. */
  | { mode: 'select'; pages: number[] }
  /** (d) One file per page. */
  | { mode: 'single' }

export interface SplitOptions {
  /** Source file name; output names are `<base>_p1-3.pdf`. Default "document". */
  fileName?: string
  signal?: AbortSignal
  /** pdf.js build used only to tell edit-protected PDFs from password-protected ones. Default: lazy `pdfjs-dist`. */
  pdfjs?: PdfJsLib
  onProgress?: (p: { file: number; files: number }) => void
}

/** Works out which 1-based pages go into which output file. Exposed so the UI can preview the result. */
export function planGroups(plan: SplitPlan, pageCount: number): number[][] {
  const groups: number[][] = []
  switch (plan.mode) {
    case 'every': {
      const n = Math.floor(plan.pages)
      if (!(n >= 1)) throw new ToolError('invalid-option', 'Enter how many pages each file should have (1 or more).')
      for (let p = 1; p <= pageCount; p += n) groups.push(range(p, Math.min(pageCount, p + n - 1)))
      break
    }
    case 'ranges':
      for (const r of parsePageRanges(plan.ranges, pageCount)) groups.push(range(r.from, r.to))
      break
    case 'select': {
      if (plan.pages.length === 0) throw new ToolError('invalid-option', 'Select at least one page.')
      for (const p of plan.pages) {
        if (!Number.isInteger(p) || p < 1 || p > pageCount) throw new ToolError('invalid-option', `Page ${p} does not exist. This PDF has ${pageCount} pages.`)
      }
      groups.push([...plan.pages])
      break
    }
    case 'single':
      for (let p = 1; p <= pageCount; p++) groups.push([p])
      break
  }
  return groups
}

function range(from: number, to: number): number[] {
  return Array.from({ length: to - from + 1 }, (_, i) => from + i)
}

/** Longest output file name (with ".pdf"); long page lists are summarised so names stay usable on Windows. */
export const MAX_SPLIT_NAME = 120
const MAX_BASE = 80

/**
 * "Statement" + [1,2,3] → "Statement_p1-3.pdf"; [2,5,6] → "Statement_p2_5-6.pdf". A page list too long for a
 * file name becomes "Statement_p1-599_selected.pdf" (first and last page), and a very long base name is cut.
 */
export function splitFileName(base: string, pages: number[]): string {
  const b = safeFileName(base).slice(0, MAX_BASE).trim() || 'document'
  const full = safeFileName(`${b}_p${formatPageList(pages, '_')}`)
  if (full.length + 4 <= MAX_SPLIT_NAME) return `${full}.pdf`
  const first = Math.min(...pages)
  const last = Math.max(...pages)
  return `${safeFileName(`${b}_p${first}-${last}_selected`)}.pdf`
}

/** Splits a PDF according to the plan. Encrypted files throw the standard password ToolError. */
export async function splitPdf(data: ArrayBuffer | Uint8Array, plan: SplitPlan, opts: SplitOptions = {}): Promise<OutputFile[]> {
  const src = await loadEditablePdf(data, opts.signal, opts.pdfjs)
  const groups = planGroups(plan, src.getPageCount())
  const base = baseName(opts.fileName ?? 'document.pdf')
  const out: OutputFile[] = []
  for (let g = 0; g < groups.length; g++) {
    throwIfAborted(opts.signal)
    const doc = await PDFDocument.create()
    const pages = await doc.copyPages(src, groups[g].map((p) => p - 1))
    pages.forEach((p) => doc.addPage(p))
    doc.setProducer('Reco-Do')
    doc.setCreator('Reco-Do')
    out.push({ name: splitFileName(base, groups[g]), data: await doc.save() })
    opts.onProgress?.({ file: g + 1, files: groups.length })
  }
  return out
}
