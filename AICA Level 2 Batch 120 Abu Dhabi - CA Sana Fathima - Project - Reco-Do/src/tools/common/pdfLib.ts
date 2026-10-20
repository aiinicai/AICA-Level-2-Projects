// pdf-lib access shared by Merge PDFs and Split PDF.

import { PDFDocument } from 'pdf-lib'
import { EDIT_PROTECTED_MESSAGE, passwordError, throwIfAborted, toPdfOpenError, ToolError } from './errors'
import { closePdfJsDocument, openPdfJsDocument, type PdfJsLib } from './pdfjs'

export interface PdfInfo {
  pages: number
  /** True for any encrypted PDF (user or owner password). The tools refuse these. */
  encrypted: boolean
  /** Page sizes in points, after the page's own rotation is applied. */
  pageSizes: { width: number; height: number; rotation: number }[]
}

function bytes(data: ArrayBuffer | Uint8Array): Uint8Array {
  return data instanceof Uint8Array ? data : new Uint8Array(data)
}

/** Page count and encryption flag. Never throws for encrypted files; damaged files throw `invalid-pdf`. */
export async function pdfInfo(data: ArrayBuffer | Uint8Array): Promise<PdfInfo> {
  let doc: PDFDocument
  try {
    doc = await PDFDocument.load(bytes(data), { ignoreEncryption: true, updateMetadata: false })
  } catch (e) {
    throw toPdfOpenError(e)
  }
  let pageSizes: PdfInfo['pageSizes'] = []
  let pages = 0
  try {
    const all = doc.getPages()
    pages = all.length
    pageSizes = all.map((p) => {
      const { width, height } = p.getSize()
      const rotation = ((p.getRotation().angle % 360) + 360) % 360
      return rotation === 90 || rotation === 270 ? { width: height, height: width, rotation } : { width, height, rotation }
    })
  } catch {
    // An encrypted file can hide its page tree; report 0 pages rather than failing.
    pages = 0
  }
  return { pages, encrypted: doc.isEncrypted, pageSizes }
}

/**
 * What kind of protection an encrypted PDF has: 'open-password' when a password is needed to open it,
 * 'edit-only' when it opens freely but is protected against changes (an owner password / permissions only).
 * pdf.js decides (it opens edit-only files without asking); when pdf.js is not available the answer is
 * 'open-password'.
 */
export async function pdfProtection(data: ArrayBuffer | Uint8Array, pdfjs?: PdfJsLib): Promise<'open-password' | 'edit-only'> {
  try {
    const doc = await openPdfJsDocument(data, { pdfjs })
    await closePdfJsDocument(doc)
    return 'edit-only'
  } catch {
    return 'open-password'
  }
}

/** The ToolError for an encrypted PDF that Merge / Split cannot change. */
export async function protectedPdfError(data: ArrayBuffer | Uint8Array, pdfjs?: PdfJsLib): Promise<ToolError> {
  return (await pdfProtection(data, pdfjs)) === 'edit-only' ? new ToolError('edit-protected', EDIT_PROTECTED_MESSAGE) : passwordError()
}

/**
 * Loads a PDF for editing. Encrypted files throw `password-protected` when they need a password to open and
 * `edit-protected` when they open but are protected against editing (pdf-lib cannot rewrite either).
 */
export async function loadEditablePdf(data: ArrayBuffer | Uint8Array, signal?: AbortSignal, pdfjs?: PdfJsLib): Promise<PDFDocument> {
  throwIfAborted(signal)
  let doc: PDFDocument
  try {
    doc = await PDFDocument.load(bytes(data), { ignoreEncryption: true, updateMetadata: false })
  } catch (e) {
    throw toPdfOpenError(e)
  }
  if (doc.isEncrypted) throw await protectedPdfError(data, pdfjs)
  if (doc.getPageCount() === 0) throw new ToolError('empty-result', 'This PDF has no pages.')
  return doc
}
