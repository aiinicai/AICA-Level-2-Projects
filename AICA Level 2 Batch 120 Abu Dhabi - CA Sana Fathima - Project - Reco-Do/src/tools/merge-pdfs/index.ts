// Merge PDFs engine (pdf-lib). Pure functions, no React.
//
//   const out = await mergePdfs([
//     { name: 'Part1.pdf', data: a },                                        // every page, as is
//     { name: 'Part2.pdf', data: b, pages: [{ index: 1, rotate: 90 }, { index: 0, rotate: 0 }] }
//   ])
//
// Thumbnails for the page grid: `openThumbnailSource` / `renderThumbnail` in `src/tools/common/thumbnails.ts`.

import { degrees, PDFDocument } from 'pdf-lib'
import { loadEditablePdf, throwIfAborted, ToolError, type PdfJsLib } from '../common'

export type Rotation = 0 | 90 | 180 | 270

export interface MergePageSelection {
  /** 0-based page index in the source file. */
  index: number
  /** Extra clockwise rotation added to the page's own rotation. */
  rotate: Rotation
}

export interface MergeInputFile {
  name: string
  data: ArrayBuffer | Uint8Array
  /** Pages to take, in output order. Omit for every page in file order. A page may appear more than once. */
  pages?: MergePageSelection[]
}

export interface MergeOptions {
  /** Document title stored in the merged PDF. */
  title?: string
  signal?: AbortSignal
  /** pdf.js build used only to tell edit-protected PDFs from password-protected ones. Default: lazy `pdfjs-dist`. */
  pdfjs?: PdfJsLib
  /** Called after each input file is copied. */
  onProgress?: (p: { file: number; files: number }) => void
}

export { pdfInfo, type PdfInfo } from '../common'

/**
 * Merges files in the given order (and page selection / rotation) into one PDF.
 * Throws `password-protected` / `edit-protected` for encrypted inputs (naming the file), `invalid-pdf` for damaged ones,
 * `invalid-option` for page indexes that do not exist and `empty-result` when nothing is selected.
 */
export async function mergePdfs(files: MergeInputFile[], opts: MergeOptions = {}): Promise<Uint8Array> {
  if (files.length === 0) throw new ToolError('empty-result', 'Add at least one PDF to merge.')
  const out = await PDFDocument.create()
  let total = 0
  for (let f = 0; f < files.length; f++) {
    throwIfAborted(opts.signal)
    const file = files[f]
    let src: PDFDocument
    try {
      src = await loadEditablePdf(file.data, opts.signal, opts.pdfjs)
    } catch (e) {
      if (e instanceof ToolError && (e.code === 'password-protected' || e.code === 'edit-protected' || e.code === 'invalid-pdf' || e.code === 'empty-result')) {
        throw new ToolError(e.code, `${file.name}: ${e.message}`, e.detail)
      }
      throw e
    }
    const count = src.getPageCount()
    const selection: MergePageSelection[] = file.pages ?? Array.from({ length: count }, (_, index) => ({ index, rotate: 0 as Rotation }))
    for (const s of selection) {
      if (!Number.isInteger(s.index) || s.index < 0 || s.index >= count) {
        throw new ToolError('invalid-option', `${file.name}: page ${s.index + 1} does not exist (the file has ${count} pages).`)
      }
      if (![0, 90, 180, 270].includes(s.rotate)) throw new ToolError('invalid-option', 'Pages can only be rotated by 90, 180 or 270 degrees.')
    }
    if (selection.length === 0) continue
    const copied = await out.copyPages(src, selection.map((s) => s.index))
    copied.forEach((page, i) => {
      const extra = selection[i].rotate
      if (extra) page.setRotation(degrees((((page.getRotation().angle + extra) % 360) + 360) % 360))
      out.addPage(page)
    })
    total += copied.length
    opts.onProgress?.({ file: f + 1, files: files.length })
  }
  if (total === 0) throw new ToolError('empty-result', 'No pages are selected. Keep at least one page.')
  if (opts.title) out.setTitle(opts.title)
  out.setProducer('Reco-Do')
  out.setCreator('Reco-Do')
  throwIfAborted(opts.signal)
  return out.save()
}
