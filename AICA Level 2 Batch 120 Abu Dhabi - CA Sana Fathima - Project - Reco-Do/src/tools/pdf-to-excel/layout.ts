// Table reconstruction from positioned words (digital text layer or OCR word boxes).
//
// words → lines (y-clustering that follows slight skew) → segments (words closer than ~0.6 em)
//       → header line per page (header words become column anchors; x-clustering when there is no header)
//       → rows (a line without a date/amount directly under a row is a wrapped continuation of that row)
//       → one fragment per table per page, plus the excluded lines with reasons.

import { detectHeaderRow, parseAmount, parseDate } from '@shared/parsing'
import type { PdfExcludedRow, PdfFragment, PdfFragmentRow, PdfWord } from './types'

export interface Segment {
  text: string
  x0: number
  x1: number
  words: PdfWord[]
}

export interface Line {
  words: PdfWord[]
  segments: Segment[]
  /** Median vertical centre. */
  y: number
  top: number
  bottom: number
  /** Median word size (font size in points). */
  size: number
  text: string
  /** Normalised text used to spot lines repeated across pages. */
  key: string
  hasDate: boolean
  hasAmount: boolean
}

export interface PageWords {
  page: number
  method: 'text' | 'ocr'
  words: PdfWord[]
}

interface Anchor {
  x0: number
  x1: number
}

interface ColumnModel {
  header: string[]
  anchors: Anchor[]
}

// ───────────────────────── token classification ─────────────────────────

const AMOUNT_SHAPE =
  /^(?:[A-Z]{3}\s?)?[(\-−]?\s?(?:\d{1,3}(?:[, ]\d{3})+|\d+)\.\d{1,2}\s?[)\-−]?(?:\s?(?:CR|DR|Cr|Dr|cr|dr))?$|^(?:[A-Z]{3}\s?)?[(\-]?\d{1,3}(?:\.\d{3})*,\d{2}[)\-]?$/

/** True for money-looking text: decimals with optional separators, brackets, minus, CR/DR, currency code. */
export function isAmountText(s: string): boolean {
  const t = s.trim()
  if (t.length < 3 || t.length > 30 || !AMOUNT_SHAPE.test(t)) return false
  return parseAmount(t) !== null
}

/** True for a date written as text ("03-Aug-2026", "03/08/2026", "2026-08-03"). Pure digit runs are never dates. */
export function isDateText(s: string): boolean {
  const t = s.trim()
  if (t.length < 6 || t.length > 30 || /^\d+$/.test(t) || !/\d/.test(t)) return false
  return parseDate(t) !== null
}

const PAGE_NUMBER = [
  /^page\s*\d+\s*(?:of|\/)\s*\d+$/i,
  /^page\s*(?:no\.?\s*)?\d+$/i,
  /^\d+\s*(?:of|\/)\s*\d+$/i,
  /^[-–]\s*\d+\s*[-–]$/,
  /^\(?(?:continued|contd\.?|cont'd)(?:\s+(?:on|from)\s+(?:next|previous)\s+page)?\)?\.*$/i,
  /^(?:continued|carried)\s+(?:on|from|forward|over)\b.*$/i
]

export function isPageNumberText(s: string): boolean {
  const t = s.trim()
  return PAGE_NUMBER.some((re) => re.test(t))
}

function normaliseKey(s: string): string {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, '')
}

function median(nums: number[]): number {
  if (nums.length === 0) return 0
  const s = [...nums].sort((a, b) => a - b)
  return s[Math.floor(s.length / 2)]
}

// ───────────────────────── words → lines → segments ─────────────────────────

/**
 * Groups words into lines. Words are visited left to right and attached to the line whose most recent
 * (right-most) word is vertically closest, so a slightly skewed scan still forms straight rows.
 */
export function buildLines(words: PdfWord[]): Line[] {
  const sorted = words.filter((w) => w.text.trim() !== '').sort((a, b) => a.x0 - b.x0 || a.top - b.top)
  const groups: { words: PdfWord[]; lastY: number; lastSize: number }[] = []
  for (const w of sorted) {
    const cy = (w.top + w.bottom) / 2
    let best = -1
    let bestDist = Infinity
    for (let i = 0; i < groups.length; i++) {
      const g = groups[i]
      const tol = 0.5 * Math.min(g.lastSize, w.size)
      const d = Math.abs(g.lastY - cy)
      if (d <= tol && d < bestDist) {
        best = i
        bestDist = d
      }
    }
    if (best < 0) groups.push({ words: [w], lastY: cy, lastSize: w.size })
    else {
      const g = groups[best]
      g.words.push(w)
      g.lastY = cy
      g.lastSize = w.size
    }
  }
  const lines = groups.map((g) => makeLine(g.words))
  lines.sort((a, b) => a.y - b.y)
  return lines
}

function makeLine(words: PdfWord[]): Line {
  const ws = [...words].sort((a, b) => a.x0 - b.x0)
  const size = median(ws.map((w) => w.size)) || 8
  const segments: Segment[] = []
  for (const w of ws) {
    const last = segments[segments.length - 1]
    const gap = last ? w.x0 - last.x1 : Infinity
    if (last && gap <= 0.6 * Math.max(size, w.size)) {
      last.text = gap > 0.12 * size || /\s$/.test(last.text) ? `${last.text} ${w.text.trim()}` : `${last.text}${w.text.trim()}`
      last.x1 = Math.max(last.x1, w.x1)
      last.words.push(w)
    } else {
      segments.push({ text: w.text.trim(), x0: w.x0, x1: w.x1, words: [w] })
    }
  }
  for (const s of segments) s.text = s.text.replace(/\s+/g, ' ').trim()
  const text = segments.map((s) => s.text).join('  ')
  return {
    words: ws,
    segments,
    y: median(ws.map((w) => (w.top + w.bottom) / 2)),
    top: Math.min(...ws.map((w) => w.top)),
    bottom: Math.max(...ws.map((w) => w.bottom)),
    size,
    text,
    key: normaliseKey(text),
    hasDate: segments.some((s) => isDateText(s.text) || s.words.some((w) => isDateText(w.text))),
    hasAmount: segments.some((s) => isAmountText(s.text) || s.words.some((w) => isAmountText(w.text)))
  }
}

// ───────────────────────── header detection ─────────────────────────

function isDataLine(l: Line): boolean {
  return l.hasDate || l.hasAmount
}

function headerLike(l: Line): boolean {
  if (l.segments.length < 2 || isDataLine(l)) return false
  const lettered = l.segments.filter((s) => /[A-Za-z]/.test(s.text)).length
  const avgLen = l.segments.reduce((n, s) => n + s.text.length, 0) / l.segments.length
  return lettered / l.segments.length >= 0.6 && avgLen <= 30 && !isPageNumberText(l.text)
}

function dataBelow(lines: Line[], i: number, look = 5): number {
  let n = 0
  for (let j = i + 1; j < lines.length && j <= i + look; j++) if (isDataLine(lines[j])) n++
  return n
}

/** Header line index for a page, or -1. Uses the shared header detector, checked against the layout. */
function findHeader(lines: Line[], from: number): number {
  const need = Math.min(2, lines.filter((l, i) => i > from && isDataLine(l)).length)
  if (need === 0) return -1
  const ok = (i: number): boolean => headerLike(lines[i]) && dataBelow(lines, i) >= need
  const slice = lines.slice(from, from + 30)
  const detected = detectHeaderRow(slice.map((l) => l.segments.map((s) => s.text)))
  const d = from + detected.index
  // Prefer the shared detector's pick (index -1 = "no header row"); otherwise the widest header-like line followed by data.
  let best = detected.index >= 0 && detected.confidence >= 0.4 && d < lines.length && ok(d) ? d : -1
  if (best < 0) {
    for (let i = from; i < Math.min(lines.length, from + 40); i++) {
      if (ok(i) && (best < 0 || lines[i].segments.length > lines[best].segments.length)) best = i
    }
  }
  return best
}

/** Two header lines stacked closely ("Txn" over "Date"): `lower` is directly below `upper`, both header-like. */
function stackedHeader(lines: Line[], upper: number, lower: number): boolean {
  const u = lines[upper]
  const l = lines[lower]
  if (!u || !l || upper < 0 || isDataLine(u) || isDataLine(l)) return false
  if (!headerLike(u) || !headerLike(l)) return false
  if (l.y - u.y > 1.7 * Math.max(u.size, l.size)) return false
  // Most upper labels sit above a lower label (a title line does not).
  const anchors = l.segments.map((s) => ({ x0: s.x0, x1: s.x1 }))
  const stacked = u.segments.filter((s) => bestAnchor(anchors, s.x0, s.x1, true) >= 0).length
  return stacked >= 2 && stacked / u.segments.length >= 0.5 && dataBelow(lines, lower) >= 1
}

/**
 * Two-line headers: returns the [upper, lower] line indexes when the chosen header line has a second header line
 * right below it (or right above it), else null.
 */
function twoLineHeader(lines: Line[], start: number): [number, number] | null {
  if (stackedHeader(lines, start, start + 1)) return [start, start + 1]
  if (stackedHeader(lines, start - 1, start)) return [start - 1, start]
  return null
}

/**
 * Column model from a two-line header: the lower line's segments are the columns; each upper label is joined in
 * front of the label below it ("Txn" + "Date" → "Txn Date"). An upper label spanning several lower columns
 * ("Amount" over "Debit" and "Credit") is joined to each of them.
 */
function modelFromTwoLines(upper: Line, lower: Line): ColumnModel {
  const anchors: Anchor[] = lower.segments.map((s) => ({ x0: s.x0, x1: s.x1 }))
  const tops: string[][] = anchors.map(() => [])
  for (const seg of upper.segments) {
    const hits = anchors.map((a, i) => (overlap(a, seg.x0, seg.x1) > 0 ? i : -1)).filter((i) => i >= 0)
    const targets = hits.length > 0 ? hits : [bestAnchor(anchors, seg.x0, seg.x1, false)]
    for (const i of targets) if (i >= 0) tops[i].push(seg.text)
    // An upper label over a single column widens that column to cover both lines.
    if (targets.length === 1 && targets[0] >= 0) {
      const a = anchors[targets[0]]
      anchors[targets[0]] = { x0: Math.min(a.x0, seg.x0), x1: Math.max(a.x1, seg.x1) }
    }
  }
  const header = lower.segments.map((s, i) => [...tops[i], s.text].join(' '))
  return { header, anchors }
}

// ───────────────────────── columns ─────────────────────────

function overlap(a: Anchor, x0: number, x1: number): number {
  return Math.max(0, Math.min(a.x1, x1) - Math.max(a.x0, x0))
}

function distance(a: Anchor, x0: number, x1: number): number {
  if (x1 < a.x0) return a.x0 - x1
  if (x0 > a.x1) return x0 - a.x1
  return 0
}

function bestAnchor(anchors: Anchor[], x0: number, x1: number, requireOverlap: boolean): number {
  let best = -1
  let bestOv = 0
  anchors.forEach((a, i) => {
    const ov = overlap(a, x0, x1)
    if (ov > bestOv) {
      bestOv = ov
      best = i
    }
  })
  if (best >= 0 || requireOverlap) return best
  let bestD = Infinity
  anchors.forEach((a, i) => {
    const d = distance(a, x0, x1)
    if (d < bestD) {
      bestD = d
      best = i
    }
  })
  return best
}

/** Splits a line into cells using the column anchors. Returns words per column. */
function assign(line: Line, anchors: Anchor[]): PdfWord[][] {
  const cells: PdfWord[][] = anchors.map(() => [])
  for (const seg of line.segments) {
    const perWord = seg.words.map((w) => bestAnchor(anchors, w.x0, w.x1, true))
    const distinct = new Set(perWord.filter((i) => i >= 0))
    if (seg.words.length > 1 && distinct.size >= 2) {
      // The segment runs across two header columns: split it word by word.
      let prev = perWord.find((i) => i >= 0) ?? 0
      seg.words.forEach((w, k) => {
        const i = perWord[k] >= 0 ? perWord[k] : prev
        cells[i].push(w)
        prev = i
      })
    } else {
      const i = bestAnchor(anchors, seg.x0, seg.x1, false)
      if (i >= 0) cells[i].push(...seg.words)
    }
  }
  return cells
}

/** Column anchors from x-clustering when no header is available: overlapping segment spans form one column. */
function clusterColumns(lines: Line[]): ColumnModel | null {
  const spans = lines
    .filter((l) => isDataLine(l) && l.segments.length >= 2)
    .flatMap((l) => l.segments.map((s) => ({ x0: s.x0, x1: s.x1 })))
    .sort((a, b) => a.x0 - b.x0)
  if (spans.length === 0) return null
  const anchors: Anchor[] = []
  for (const s of spans) {
    const last = anchors[anchors.length - 1]
    if (last && s.x0 <= last.x1) last.x1 = Math.max(last.x1, s.x1)
    else anchors.push({ ...s })
  }
  return { header: anchors.map(() => ''), anchors }
}

function joinWords(words: PdfWord[]): string {
  return words
    .map((w) => w.text.trim())
    .filter((t) => t !== '')
    .join(' ')
    .replace(/\s+/g, ' ')
    .trim()
}

function minConfidence(words: PdfWord[]): number | null {
  const c = words.map((w) => w.confidence).filter((x): x is number => typeof x === 'number')
  return c.length ? Math.round(Math.min(...c)) : null
}

// ───────────────────────── pages → fragments ─────────────────────────

export interface LayoutResult {
  fragments: PdfFragment[]
  excluded: PdfExcludedRow[]
}

/**
 * Rebuilds tables from the words of every processed page. Lines repeated on at least half of the pages
 * (and on 2+ pages) are page headers/footers. The model of the last header seen carries over to
 * continuation pages that have no header row.
 */
export function reconstruct(pages: PageWords[]): LayoutResult {
  const pageLines = pages.map((p) => ({ ...p, lines: buildLines(p.words) }))
  const fragments: PdfFragment[] = []
  const excluded: PdfExcludedRow[] = []

  // Lines repeated across pages.
  const seen = new Map<string, Set<number>>()
  for (const p of pageLines) {
    for (const l of p.lines) {
      if (l.key.length < 3) continue
      const s = seen.get(l.key) ?? new Set<number>()
      s.add(p.page)
      seen.set(l.key, s)
    }
  }
  const minRepeat = Math.max(2, Math.ceil(pageLines.length / 2))
  const isRepeated = (l: Line): boolean => (seen.get(l.key)?.size ?? 0) >= minRepeat

  let model: ColumnModel | null = null
  // Last row of the previous page: a row split by a page break continues right under the next page's header.
  let previousRow: PdfFragmentRow | null = null
  for (const p of pageLines) {
    const { lines } = p
    const exclude = (l: Line, reason: PdfExcludedRow['reason'], detail: string): void => {
      excluded.push({ page: p.page, text: l.text, reason, detail })
    }
    const excludeOutside = (l: Line): void => {
      if (isPageNumberText(l.text)) exclude(l, 'page-number', 'Page number')
      else if (isRepeated(l)) exclude(l, 'page-header-footer', 'Repeated on most pages')
      else exclude(l, 'outside-table', 'Text outside the table')
    }

    let start = findHeader(lines, 0)
    let headerTop = start
    if (start >= 0) {
      const pair = twoLineHeader(lines, start)
      if (pair) {
        model = modelFromTwoLines(lines[pair[0]], lines[pair[1]])
        headerTop = pair[0]
        start = pair[1]
      } else model = modelFromHeader(lines[start])
    } else if (!model) model = clusterColumns(lines)
    if (!model) {
      lines.forEach(excludeOutside)
      continue
    }
    const firstRow = start >= 0 ? start + 1 : 0
    for (let i = 0; i < (start >= 0 ? headerTop : 0); i++) excludeOutside(lines[i])

    let frag: PdfFragment = newFragment(p.page, p.method, model, start >= 0)
    fragments.push(frag)
    let current: { row: PdfFragmentRow; words: PdfWord[][]; last: Line } | null = null
    const flush = (): void => {
      if (!current) return
      current.row.cells = current.words.map(joinWords)
      current.row.confidence = current.words.map(minConfidence)
      current = null
    }
    const headerKey = start >= 0 ? lines[start].key : normaliseKey(model.header.join(''))

    for (let i = firstRow; i < lines.length; i++) {
      const l = lines[i]
      if (isPageNumberText(l.text)) {
        exclude(l, 'page-number', 'Page number')
        continue
      }
      if (!isDataLine(l) && l.key === headerKey && headerKey !== '') {
        // The header printed again on the same page: keep it as a flagged row so shaping can drop it.
        flush()
        const words = assign(l, model.anchors)
        frag.rows.push({ page: p.page, cells: words.map(joinWords), confidence: words.map(minConfidence), ocr: p.method === 'ocr', lines: 1, repeatedHeader: true })
        continue
      }
      const gapAbove = current ? l.y - current.last.y : Infinity
      const wrapped = current !== null && !isDataLine(l) && gapAbove <= 1.7 * Math.max(l.size, current.last.size)
      const minCells = Math.max(2, Math.ceil(model.anchors.length / 2))
      if (current === null && frag.rows.length === 0 && i === firstRow && start >= 0 && !isDataLine(l) && previousRow?.cells.length === model.anchors.length) {
        const words = assign(l, model.anchors)
        if (words.filter((w) => w.length > 0).length < minCells) {
          // Continuation of the previous page's last row (the row was split by the page break).
          const prev: PdfFragmentRow = previousRow
          words.forEach((w, c) => {
            const add = joinWords(w)
            if (add === '') return
            prev.cells[c] = prev.cells[c] ? `${prev.cells[c]} ${add}` : add
            const conf = minConfidence(w)
            if (conf !== null) prev.confidence[c] = prev.confidence[c] === null ? conf : Math.min(prev.confidence[c] as number, conf)
          })
          prev.lines++
          continue
        }
      }
      // Wrapped text is checked before the repeated-line rule: short continuations ("LLC") recur on many pages.
      if (!wrapped && !isDataLine(l) && isRepeated(l)) {
        exclude(l, 'page-header-footer', 'Repeated on most pages')
        continue
      }
      // A different header further down the page starts a new table.
      if (!isDataLine(l) && l.segments.length >= 3 && gapAbove > 1.7 * l.size && headerLike(l) && dataBelow(lines, i) >= 2) {
        flush()
        model = modelFromHeader(l)
        frag = newFragment(p.page, p.method, model, true)
        fragments.push(frag)
        continue
      }
      const words = assign(l, model.anchors)
      const filled = words.filter((w) => w.length > 0).length
      const starts = isDataLine(l) || filled >= minCells
      if (starts) {
        flush()
        current = { row: { page: p.page, cells: [], confidence: [], ocr: p.method === 'ocr', lines: 1 }, words, last: l }
        frag.rows.push(current.row)
      } else if (current && wrapped) {
        // Wrapped text (no date/amount) right under a row belongs to that row.
        words.forEach((w, c) => current?.words[c].push(...w))
        current.last = l
        current.row.lines++
      } else {
        flush()
        excludeOutside(l)
      }
    }
    flush()
    const lastFrag = fragments[fragments.length - 1]
    const lastRows = lastFrag && lastFrag.page === p.page ? lastFrag.rows.filter((r) => !r.repeatedHeader) : []
    previousRow = lastRows.length ? lastRows[lastRows.length - 1] : null
  }
  return { fragments: fragments.filter((f) => f.rows.length > 0), excluded }
}

function modelFromHeader(l: Line): ColumnModel {
  return { header: l.segments.map((s) => s.text), anchors: l.segments.map((s) => ({ x0: s.x0, x1: s.x1 })) }
}

function newFragment(page: number, method: 'text' | 'ocr', model: ColumnModel, hasHeader: boolean): PdfFragment {
  return { page, method, header: [...model.header], hasHeader, rows: [] }
}
