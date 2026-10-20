// Digital pages: pdf.js text items → positioned words in PDF points (top-left origin).

import type { PDFPageProxy } from 'pdfjs-dist'
import type { TextItem } from 'pdfjs-dist/types/src/display/api'
import type { PdfWord } from './types'

function isTextItem(x: unknown): x is TextItem {
  return typeof x === 'object' && x !== null && 'str' in x && 'transform' in x
}

/** pdf.js-style matrix product m1 × m2 for [a, b, c, d, e, f] affine matrices. */
function multiply(m1: number[], m2: number[]): number[] {
  return [
    m1[0] * m2[0] + m1[2] * m2[1],
    m1[1] * m2[0] + m1[3] * m2[1],
    m1[0] * m2[2] + m1[2] * m2[3],
    m1[1] * m2[2] + m1[3] * m2[3],
    m1[0] * m2[4] + m1[2] * m2[5] + m1[4],
    m1[1] * m2[4] + m1[3] * m2[5] + m1[5]
  ]
}

/**
 * Reads the text layer of a page as it is displayed: the page's own /Rotate (landscape statements stored as
 * rotated portrait pages) is applied through the viewport, so their text reads normally. Items that contain
 * wide runs of spaces ("Account No: 1      Currency: AED") are split so each part keeps its own position.
 * Text that is still rotated on the displayed page (watermarks, vertical labels) is ignored.
 */
export async function readTextWords(page: PDFPageProxy): Promise<PdfWord[]> {
  const viewport = page.getViewport({ scale: 1 })
  const content = await page.getTextContent()
  const words: PdfWord[] = []
  for (const item of content.items) {
    if (!isTextItem(item) || item.str.trim() === '') continue
    // Text matrix in viewport space (y grows downwards); upright text has a > 0 and b ≈ 0.
    const [a, b, c, d, e, f] = multiply(viewport.transform, item.transform as number[])
    if (Math.abs(b) > 0.2 * Math.abs(a) || a <= 0) continue
    const size = Math.hypot(c, d) || Math.hypot(a, b) || 1
    const x0 = e
    const x1 = Math.max(e + item.width * viewport.scale, x0 + 0.1)
    const top = f - size * 0.8
    const bottom = f + size * 0.2
    pushSplit(words, item.str, x0, x1, top, bottom, size)
  }
  return words
}

function pushSplit(out: PdfWord[], str: string, x0: number, x1: number, top: number, bottom: number, size: number): void {
  const parts = [...str.matchAll(/\S+(?: {1,2}\S+)*/g)]
  if (parts.length <= 1) {
    out.push({ text: str.trim(), x0, x1, top, bottom, size })
    return
  }
  const perChar = (x1 - x0) / Math.max(1, str.length)
  for (const m of parts) {
    const start = m.index ?? 0
    out.push({ text: m[0], x0: x0 + start * perChar, x1: x0 + (start + m[0].length) * perChar, top, bottom, size })
  }
}
