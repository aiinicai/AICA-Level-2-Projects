// Page-range text such as "1-3, 5, 8-" used by PDF → Excel and Split PDF. Page numbers are 1-based.

import { ToolError } from './errors'

export interface PageRange {
  /** First page, 1-based, inclusive. */
  from: number
  /** Last page, 1-based, inclusive. */
  to: number
}

const PART = /^(\d+)?\s*(?:(-|–|to)\s*(\d+)?)?$/i

/**
 * Parses "1-3, 5, 8-" into ranges, in the order written. An open end ("8-") runs to the last page,
 * an open start ("-3") starts at page 1. Empty text or "all" means every page.
 * Throws an `invalid-option` ToolError with a plain-English message for anything unreadable or
 * outside 1..pageCount.
 */
export function parsePageRanges(text: string | undefined | null, pageCount: number): PageRange[] {
  const trimmed = (text ?? '').trim()
  if (pageCount < 1) throw new ToolError('empty-result', 'This PDF has no pages.')
  if (trimmed === '' || /^all$/i.test(trimmed)) return [{ from: 1, to: pageCount }]
  const ranges: PageRange[] = []
  for (const raw of trimmed.split(/[,;]/)) {
    const part = raw.trim()
    if (part === '') continue
    const m = PART.exec(part)
    if (!m || (m[1] === undefined && m[3] === undefined)) {
      throw new ToolError('invalid-option', `"${part}" is not a page or page range. Use numbers like 1-3, 5.`)
    }
    const from = m[1] !== undefined ? Number(m[1]) : 1
    const to = m[2] ? (m[3] !== undefined ? Number(m[3]) : pageCount) : from
    if (from < 1 || to < 1) throw new ToolError('invalid-option', 'Page numbers start at 1.')
    if (from > pageCount || to > pageCount) {
      throw new ToolError('invalid-option', `Page ${Math.max(from, to)} does not exist. This PDF has ${pageCount} page${pageCount === 1 ? '' : 's'}.`)
    }
    if (to < from) throw new ToolError('invalid-option', `"${part}" runs backwards. Write the lower page first, e.g. ${to}-${from}.`)
    ranges.push({ from, to })
  }
  if (ranges.length === 0) throw new ToolError('invalid-option', 'Enter at least one page number.')
  return ranges
}

/** Unique sorted 1-based page numbers covered by the range text. */
export function parsePageSelection(text: string | undefined | null, pageCount: number): number[] {
  const set = new Set<number>()
  for (const r of parsePageRanges(text, pageCount)) for (let p = r.from; p <= r.to; p++) set.add(p)
  return [...set].sort((a, b) => a - b)
}

/** [1,2,3,5,7,8] → "1-3, 5, 7-8" (sep ", ") or "1-3_5_7-8" (sep "_"). */
export function formatPageList(pages: number[], sep = ', '): string {
  const sorted = [...new Set(pages)].sort((a, b) => a - b)
  const parts: string[] = []
  for (let i = 0; i < sorted.length; ) {
    let j = i
    while (j + 1 < sorted.length && sorted[j + 1] === sorted[j] + 1) j++
    parts.push(i === j ? `${sorted[i]}` : `${sorted[i]}-${sorted[j]}`)
    i = j + 1
  }
  return parts.join(sep)
}
