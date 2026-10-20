// Derives everything the workbook and the PDF summary show from a ReconSession.
// Pure and independent of the engine: it reads only the shared contract types.

import type {
  CellValue,
  EngineLine,
  MatchKey,
  MatchPair,
  PairOrigin,
  ReconSession,
  Side,
  Suggestion,
  SuggestionSource,
  Tier
} from '../shared/contracts'
import { getModule, type ModuleId } from '../shared/modules'
import { formatDate } from '../shared/format'
import { periodEndDate } from './naming'

export type AgeBucket = '0-30' | '31-60' | '61-90' | '90+'
export const AGE_BUCKETS: AgeBucket[] = ['0-30', '31-60', '61-90', '90+']

/** Display tier used for colours: the four engine tiers plus AI assisted. */
export type DisplayTier = Tier | 'ai'

export const TIER_LABELS: Record<DisplayTier, string> = {
  matched: 'Matched',
  doubtful: 'Doubtful',
  likely: 'Likely',
  unmatched: 'Unmatched',
  ai: 'AI assisted'
}

export const TIER_COLOURS: Record<DisplayTier, string> = {
  matched: '#11865F',
  doubtful: '#A86B00',
  likely: '#C25500',
  unmatched: '#C0292B',
  ai: '#5A43D6'
}

export const ORIGIN_LABELS: Record<PairOrigin, string> = {
  engine: 'Engine',
  manual: 'Manual match',
  'code-group': 'Smart Recon: group sum',
  'code-partial-ref': 'Smart Recon: partial reference',
  ai: 'Smart Recon: AI'
}

const SOURCE_LABELS: Record<SuggestionSource, string> = {
  'code-group': ORIGIN_LABELS['code-group'],
  'code-partial-ref': ORIGIN_LABELS['code-partial-ref'],
  ai: ORIGIN_LABELS.ai
}

const ASSISTED_ORIGINS: ReadonlySet<PairOrigin> = new Set<PairOrigin>(['ai', 'code-group', 'code-partial-ref'])

const DAY_MS = 86_400_000

/** A text/id/number key column shown for each side (amount and date keys have dedicated columns). */
export interface KeyColumn {
  keyId: string
  name: string
  column: string
}

/** One side of a pair, aggregated across its lines. */
export interface PairSideView {
  lines: EngineLine[]
  /** Excel row numbers of the source rows, e.g. "12" or "12, 15". */
  sourceRows: string
  /** Earliest date among the lines. */
  date: Date | null
  /** Raw value for a single line, joined text for several. */
  keyValues: CellValue[]
  /** Sum of the lines' own-terms amounts (null without amounts). */
  amount: number | null
}

export interface PairView {
  pair: MatchPair
  a: PairSideView
  b: PairSideView
  displayTier: DisplayTier
}

export type OpenStatus = 'unmatched' | 'rejected' | 'doubtful' | 'likely'

export const OPEN_STATUS_LABELS: Record<OpenStatus, string> = {
  unmatched: 'Unmatched',
  rejected: 'Unmatched (pair rejected)',
  doubtful: 'Pending review (Doubtful)',
  likely: 'Pending review (Likely)'
}

export interface OpenItem {
  line: EngineLine
  status: OpenStatus
  ageDays: number | null
  bucket: AgeBucket | null
  /** Auto label, e.g. "Probable bank charge – post JV". Empty when nothing applies. */
  comment: string
}

export interface AssistedRow {
  id: string
  source: string
  confidence: number | null
  reason: string
  label: string
  status: string
  a: PairSideView
  b: PairSideView
  difference: number | null
}

export interface TierTotals {
  pairs: number
  linesA: number
  linesB: number
  /**
   * Absolute sum of the tier's amounts: Σ |amount| of the File A lines for pair tiers, of the side's own lines
   * for Unmatched. This is the same definition as the on-screen KPI cards (stats.matchedAmount and the review
   * KPIs sum absolute File A amounts), so a mix of receipts and payments never nets towards zero.
   * null without an amount key.
   */
  amount: number | null
}

export interface ExportModel {
  session: ReconSession
  moduleId: ModuleId
  moduleName: string
  sideAName: string
  sideBName: string
  currency: string
  hasAmount: boolean
  hasDateA: boolean
  hasDateB: boolean
  keys: MatchKey[]
  keyColumnsA: KeyColumn[]
  keyColumnsB: KeyColumn[]
  lineById: Map<string, EngineLine>
  matched: PairView[]
  review: PairView[]
  assisted: AssistedRow[]
  openA: OpenItem[]
  openB: OpenItem[]
  asOf: Date | null
  asOfSource: 'period-end' | 'latest-date' | null
  totals: {
    matched: TierTotals
    doubtful: TierTotals
    likely: TierTotals
    unmatchedA: TierTotals
    unmatchedB: TierTotals
    assisted: TierTotals
    aiPending: number
  }
  generatedAt: Date
}

/** Whole days between two dates, compared on calendar days (time of day ignored). */
export function daysBetween(from: Date, to: Date): number {
  const a = Date.UTC(from.getFullYear(), from.getMonth(), from.getDate())
  const b = Date.UTC(to.getFullYear(), to.getMonth(), to.getDate())
  return Math.round((b - a) / DAY_MS)
}

export function ageBucket(ageDays: number): AgeBucket {
  if (ageDays <= 30) return '0-30'
  if (ageDays <= 60) return '31-60'
  if (ageDays <= 90) return '61-90'
  return '90+'
}

/** "r12" → 12. Falls back to the raw id when it is not in the engine's row-id format. */
export function excelRowOf(rowId: string): string {
  const m = /^r(\d+)$/.exec(rowId)
  return m ? m[1] : rowId
}

export function cellToText(v: CellValue): string {
  if (v === null || v === undefined) return ''
  if (v instanceof Date) return Number.isNaN(v.getTime()) ? '' : formatDate(v)
  return String(v)
}

function isValidDate(d: Date | null | undefined): d is Date {
  return d instanceof Date && !Number.isNaN(d.getTime())
}

function sumAmounts(lines: EngineLine[], field: 'amount' | 'comparableAmount'): number | null {
  let total = 0
  let any = false
  for (const l of lines) {
    const v = l[field]
    if (typeof v === 'number' && Number.isFinite(v)) {
      total += v
      any = true
    }
  }
  return any ? round2(total) : null
}

export function round2(n: number): number {
  return Math.round((n + Number.EPSILON) * 100) / 100
}

function keyColumnsFor(keys: MatchKey[], side: Side): KeyColumn[] {
  const out: KeyColumn[] = []
  const seen = new Set<string>()
  for (const k of keys) {
    if (!k.use || k.type === 'amount' || k.type === 'date') continue
    const column = side === 'A' ? k.columnA : k.columnB
    if (!column || seen.has(column)) continue
    seen.add(column)
    out.push({ keyId: k.id, name: k.name, column })
  }
  return out
}

function sideView(ids: string[], lineById: Map<string, EngineLine>, cols: KeyColumn[]): PairSideView {
  const lines: EngineLine[] = []
  for (const id of ids) {
    const l = lineById.get(id)
    if (l) lines.push(l)
  }
  let date: Date | null = null
  for (const l of lines) if (isValidDate(l.date) && (!date || l.date < date)) date = l.date
  const keyValues: CellValue[] = cols.map((c) => {
    if (lines.length === 1) return lines[0].values[c.column] ?? null
    const parts = lines.map((l) => cellToText(l.values[c.column] ?? null)).filter((t) => t !== '')
    return parts.length ? parts.join(', ') : null
  })
  return {
    lines,
    sourceRows: lines.map((l) => excelRowOf(l.rowId)).join(', '),
    date,
    keyValues,
    amount: sumAmounts(lines, 'amount')
  }
}

function idsKey(aIds: string[], bIds: string[]): string {
  return `${[...aIds].sort().join(',')}|${[...bIds].sort().join(',')}`
}

/** Matched means accepted, or an engine "matched" pair that was never rejected. */
function isMatchedPair(p: MatchPair): boolean {
  return p.status === 'accepted' || (p.tier === 'matched' && p.status === 'open')
}

function isOpenReviewPair(p: MatchPair): boolean {
  return p.status === 'open' && (p.tier === 'doubtful' || p.tier === 'likely')
}

const BANK_CHARGE = /\b(charges?|fees?|commission|vat on|service chg|chg)\b/i
const BANK_INTEREST = /\binterest\b|\bint\.? (cr|credit|paid)\b/i
const INVOICE = /\b(inv|invoice|bill|tax invoice)\b/i

/** Auto label for an unmatched line, e.g. "Probable bank charge – post JV". Shared by the export and the Review screen. */
export function autoComment(moduleId: ModuleId, side: Side, line: EngineLine): string {
  if (moduleId !== 'bank' && moduleId !== 'ap') return ''
  let text = ''
  for (const v of Object.values(line.values)) if (typeof v === 'string') text += ` ${v}`
  if (moduleId === 'bank' && side === 'A') {
    if (BANK_CHARGE.test(text)) return 'Probable bank charge – post JV'
    if (BANK_INTEREST.test(text)) return 'Probable bank interest – post JV'
    return ''
  }
  if (moduleId === 'ap' && side === 'B' && INVOICE.test(text)) return 'Possible unrecorded liability'
  return ''
}

function latestDate(lines: EngineLine[], current: Date | null): Date | null {
  let best = current
  for (const l of lines) if (isValidDate(l.date) && (!best || l.date > best)) best = l.date
  return best
}

function emptyTotals(hasAmount: boolean): TierTotals {
  return { pairs: 0, linesA: 0, linesB: 0, amount: hasAmount ? 0 : null }
}

/** Σ |amount| of a set of lines (see TierTotals.amount). */
function absSum(lines: EngineLine[]): number {
  let t = 0
  for (const l of lines) t += Math.abs(l.amount ?? 0)
  return t
}

function addPairTotals(t: TierTotals, v: { a: PairSideView; b: PairSideView }): void {
  t.pairs++
  t.linesA += v.a.lines.length
  t.linesB += v.b.lines.length
  if (t.amount !== null) t.amount = round2(t.amount + absSum(v.a.lines))
}

export interface BuildModelOptions {
  generatedAt?: Date
}

export function buildExportModel(session: ReconSession, opts: BuildModelOptions = {}): ExportModel {
  const { result, meta } = session
  const cfg = result.config
  const mod = getModule(cfg.moduleId)
  const lineById = new Map<string, EngineLine>()
  for (const l of result.linesA) lineById.set(l.id, l)
  for (const l of result.linesB) lineById.set(l.id, l)

  const hasAmount =
    cfg.keys.some((k) => k.use && k.type === 'amount') ||
    result.linesA.some((l) => l.amount !== null) ||
    result.linesB.some((l) => l.amount !== null)
  const hasDateA = result.linesA.some((l) => isValidDate(l.date))
  const hasDateB = result.linesB.some((l) => isValidDate(l.date))
  const keyColumnsA = keyColumnsFor(cfg.keys, 'A')
  const keyColumnsB = keyColumnsFor(cfg.keys, 'B')

  const view = (p: MatchPair): PairView => {
    const assisted = ASSISTED_ORIGINS.has(p.origin)
    const matched = isMatchedPair(p)
    return {
      pair: p,
      a: sideView(p.aIds, lineById, keyColumnsA),
      b: sideView(p.bIds, lineById, keyColumnsB),
      displayTier: matched ? (assisted ? 'ai' : 'matched') : p.status === 'rejected' ? 'unmatched' : p.tier
    }
  }

  const matched: PairView[] = []
  const review: PairView[] = []
  const covered = new Set<string>()
  const openStatus = new Map<string, OpenStatus>()
  const totals = {
    matched: emptyTotals(hasAmount),
    doubtful: emptyTotals(hasAmount),
    likely: emptyTotals(hasAmount),
    unmatchedA: emptyTotals(hasAmount),
    unmatchedB: emptyTotals(hasAmount),
    assisted: emptyTotals(hasAmount),
    aiPending: 0
  }

  const assisted: AssistedRow[] = []
  const assistedKeys = new Set<string>()

  for (const p of result.pairs) {
    if (isMatchedPair(p)) {
      const v = view(p)
      matched.push(v)
      addPairTotals(totals.matched, v)
      for (const id of p.aIds) covered.add(id)
      for (const id of p.bIds) covered.add(id)
      if (ASSISTED_ORIGINS.has(p.origin)) {
        addPairTotals(totals.assisted, v)
        assistedKeys.add(idsKey(p.aIds, p.bIds))
        assisted.push({
          id: p.id,
          source: ORIGIN_LABELS[p.origin],
          confidence: typeof p.confidence === 'number' ? p.confidence : null,
          reason: p.reason,
          label: p.label ?? '',
          status: 'Approved',
          a: v.a,
          b: v.b,
          difference: p.amountDifference
        })
      }
    }
    if (p.tier === 'doubtful' || p.tier === 'likely') {
      const v = view(p)
      review.push(v)
      if (isOpenReviewPair(p)) {
        addPairTotals(p.tier === 'doubtful' ? totals.doubtful : totals.likely, v)
      }
    }
  }

  // Open review pairs and rejected pairs keep their lines on the "to reconcile" lists, with a status.
  for (const p of result.pairs) {
    if (isMatchedPair(p)) continue
    const status: OpenStatus | null = isOpenReviewPair(p)
      ? p.tier === 'doubtful'
        ? 'doubtful'
        : 'likely'
      : p.status === 'rejected'
        ? 'rejected'
        : null
    if (!status) continue
    for (const id of [...p.aIds, ...p.bIds]) {
      if (covered.has(id)) continue
      const prev = openStatus.get(id)
      // A line in an open pair outranks a stale rejected pair.
      if (!prev || prev === 'rejected') openStatus.set(id, status)
    }
  }

  // Approved suggestions that the engine did not (yet) turn into a pair are still shown.
  for (const s of session.suggestions) {
    if (s.status === 'open') totals.aiPending++
    if (s.status !== 'accepted') continue
    const key = idsKey(s.aIds, s.bIds)
    if (assistedKeys.has(key)) continue
    assistedKeys.add(key)
    assisted.push(suggestionRow(s, lineById, keyColumnsA, keyColumnsB))
  }

  // As-of date for ageing: period end when recognisable, otherwise the latest date in the data.
  const periodEnd = periodEndDate(meta.period)
  const latest = latestDate(result.linesB, latestDate(result.linesA, null))
  const asOf = periodEnd ?? latest
  const asOfSource: ExportModel['asOfSource'] = periodEnd ? 'period-end' : latest ? 'latest-date' : null

  const openItems = (lines: EngineLine[], side: Side): OpenItem[] => {
    const out: OpenItem[] = []
    for (const line of lines) {
      if (covered.has(line.id)) continue
      const status = openStatus.get(line.id) ?? 'unmatched'
      const ageDays = asOf && isValidDate(line.date) ? Math.max(0, daysBetween(line.date, asOf)) : null
      out.push({
        line,
        status,
        ageDays,
        bucket: ageDays === null ? null : ageBucket(ageDays),
        comment: autoComment(cfg.moduleId, side, line)
      })
    }
    return out
  }
  const openA = openItems(result.linesA, 'A')
  const openB = openItems(result.linesB, 'B')

  for (const item of openA) {
    if (item.status === 'unmatched' || item.status === 'rejected') {
      totals.unmatchedA.linesA++
      if (totals.unmatchedA.amount !== null) totals.unmatchedA.amount = round2(totals.unmatchedA.amount + Math.abs(item.line.amount ?? 0))
    }
  }
  for (const item of openB) {
    if (item.status === 'unmatched' || item.status === 'rejected') {
      totals.unmatchedB.linesB++
      if (totals.unmatchedB.amount !== null) totals.unmatchedB.amount = round2(totals.unmatchedB.amount + Math.abs(item.line.amount ?? 0))
    }
  }

  return {
    session,
    moduleId: cfg.moduleId,
    moduleName: mod?.name ?? 'Reconciliation',
    sideAName: cfg.sideAName || mod?.sideA || 'File A',
    sideBName: cfg.sideBName || mod?.sideB || 'File B',
    currency: meta.currency || cfg.currency,
    hasAmount,
    hasDateA,
    hasDateB,
    keys: cfg.keys,
    keyColumnsA,
    keyColumnsB,
    lineById,
    matched,
    review,
    assisted,
    openA,
    openB,
    asOf,
    asOfSource,
    totals,
    generatedAt: opts.generatedAt ?? new Date()
  }
}

function suggestionRow(
  s: Suggestion,
  lineById: Map<string, EngineLine>,
  colsA: KeyColumn[],
  colsB: KeyColumn[]
): AssistedRow {
  const a = sideView(s.aIds, lineById, colsA)
  const b = sideView(s.bIds, lineById, colsB)
  const ca = sumAmounts(a.lines, 'comparableAmount')
  const cb = sumAmounts(b.lines, 'comparableAmount')
  return {
    id: s.id,
    source: SOURCE_LABELS[s.source],
    confidence: s.confidence,
    reason: s.reason,
    label: '',
    status: 'Approved',
    a,
    b,
    difference: ca !== null && cb !== null ? round2(ca - cb) : null
  }
}

/** "Reference ✓ · Date ✗ (differs by 5 days)" style mark for one key of a pair. */
export function keyMark(pair: MatchPair, keyId: string): string {
  const r = pair.keyResults.find((k) => k.keyId === keyId)
  if (!r) return ''
  return r.pass ? '✓' : r.detail ? `✗ ${r.detail}` : '✗'
}

export const FLAG_LABELS: Record<MatchPair['flags'][number], string> = {
  transposition: 'Possible transposition',
  'bank-charge': 'Bank charge style difference',
  rounding: 'Rounding',
  'multiple-candidates': 'Multiple identical candidates'
}

export function decisionLabel(pair: MatchPair): string {
  if (pair.status === 'accepted') return 'Accepted'
  if (pair.status === 'rejected') return 'Rejected'
  return 'Open'
}

/** Local wall-clock date rewritten as UTC so spreadsheet cells show the same calendar date in any time zone. */
export function toSheetDate(d: Date): Date {
  return new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()))
}

/** Local wall-clock date and time rewritten as UTC (for timestamps). */
export function toSheetDateTime(d: Date): Date {
  return new Date(
    Date.UTC(d.getFullYear(), d.getMonth(), d.getDate(), d.getHours(), d.getMinutes(), d.getSeconds())
  )
}

export function formatDateTime(d: Date): string {
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  return `${formatDate(d)} ${hh}:${mm}`
}

export function parseIso(s: string | undefined | null): Date | null {
  if (!s) return null
  const d = new Date(s)
  return Number.isNaN(d.getTime()) ? null : d
}
