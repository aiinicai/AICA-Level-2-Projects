// Map & Rules helpers: key suggestions, amount layout detection, the sign-convention check and the live preview.

import type { AmountLayout, CellValue, ColumnType, EngineLine, MatchKey, ParsedTable, ReconConfig } from '@shared/contracts'
import { getModule, type ModuleId } from '@shared/modules'
import { headerSimilarity, inferColumnType, parseDate, valueOverlap } from '@shared/parsing'
import { buildCandidateSources, prepareKeys } from './keys'
import { buildLines } from './lines'
import { validateConfig } from './validate'
import { amountKeyOf, dayNumber, toCents } from './util'

const SAMPLE_ROWS = 500
const BALANCE_HEADER = /\b(balance|running|bal)\b/i
const DEBIT_HEADER = /\b(debit|debits|dr|withdrawal|withdrawals|payment|payments|paid out|money out)\b/i
const CREDIT_HEADER = /\b(credit|credits|cr|deposit|deposits|receipt|receipts|paid in|money in)\b/i
const PARTY_HEADER = /\b(party|customer|supplier|vendor|counterparty|payee|beneficiary|client)\b/i
const NOT_PARTY_HEADER = /\b(inv|invoice|ref|reference|no|number|code|id|doc|document|account|a\/c)\b/i
const INDICATOR_VALUE = /^(dr|cr|d|c|debit|credit)\.?$/i

function columnValues(table: ParsedTable, col: string, limit = SAMPLE_ROWS): CellValue[] {
  const out: CellValue[] = []
  const rows = table.rows
  const step = rows.length > limit ? rows.length / limit : 1
  for (let k = 0; k < rows.length && out.length < limit; k++) {
    const row = rows[Math.floor(k * step)]
    if (!row) break
    out.push(row.values[col] ?? null)
  }
  return out
}

/** Date column values as calendar dates (text dates parsed), so overlap compares days. */
function dateValues(values: CellValue[]): CellValue[] {
  return values.map((v) => parseDate(v) ?? null)
}

function columnTypes(table: ParsedTable): Map<string, ColumnType> {
  const m = new Map<string, ColumnType>()
  for (const c of table.columns) m.set(c, inferColumnType(c, columnValues(table, c)))
  return m
}

function isIndicatorColumn(table: ParsedTable, col: string): boolean {
  const vals = columnValues(table, col).filter((v) => v !== null && String(v).trim() !== '')
  if (vals.length === 0) return false
  const hits = vals.filter((v) => typeof v === 'string' && INDICATOR_VALUE.test(v.trim())).length
  return hits / vals.length >= 0.8
}

/** Detects how a file shows money: Debit + Credit columns, amount + Dr/Cr column, or one signed column. */
export function detectAmountLayout(table: ParsedTable, types = columnTypes(table)): AmountLayout | undefined {
  const money = table.columns.filter((c) => types.get(c) === 'amount' && !BALANCE_HEADER.test(c))
  const debit = money.find((c) => DEBIT_HEADER.test(c) && !CREDIT_HEADER.test(c))
  const credit = money.find((c) => CREDIT_HEADER.test(c) && !DEBIT_HEADER.test(c))
  if (debit && credit) return { kind: 'debit-credit', debit, credit }
  const indicator = table.columns.find((c) => types.get(c) !== 'amount' && isIndicatorColumn(table, c))
  const amountCols = money.filter((c) => c !== indicator)
  const best = amountCols
    .map((c, idx) => ({ c, score: headerSimilarity(c, 'Amount') - idx * 0.001 }))
    .sort((x, y) => y.score - x.score)[0]?.c
  if (!best) return undefined
  if (indicator) return { kind: 'amount-indicator', amount: best, indicator }
  return { kind: 'signed', column: best }
}

function detectParty(table: ParsedTable, types: Map<string, ColumnType>): string | undefined {
  return table.columns.find((c) => PARTY_HEADER.test(c) && !NOT_PARTY_HEADER.test(c) && types.get(c) === 'text')
}

function layoutColumns(l: AmountLayout | undefined): string[] {
  if (!l) return []
  if (l.kind === 'signed') return [l.column]
  if (l.kind === 'debit-credit') return [l.debit, l.credit]
  return [l.amount, l.indicator]
}

function layoutLabel(l: AmountLayout | undefined): string {
  if (!l) return ''
  if (l.kind === 'signed') return l.column
  if (l.kind === 'debit-credit') return `${l.debit} / ${l.credit}`
  return `${l.amount} (${l.indicator})`
}

interface Scored {
  a: string
  b: string
  header: number
  overlap: number
  score: number
}

export function suggestKeys(
  moduleId: ModuleId,
  tableA: ParsedTable,
  tableB: ParsedTable
): { keys: MatchKey[]; amountA?: AmountLayout; amountB?: AmountLayout; partyColumnA?: string; partyColumnB?: string } {
  const mod = getModule(moduleId)
  const dateTol = mod?.dateToleranceDays ?? 3
  const typesA = columnTypes(tableA)
  const typesB = columnTypes(tableB)
  const amountA = detectAmountLayout(tableA, typesA)
  const amountB = detectAmountLayout(tableB, typesB)
  const partyColumnA = detectParty(tableA, typesA)
  const partyColumnB = detectParty(tableB, typesB)
  const moneyA = new Set([...layoutColumns(amountA), ...tableA.columns.filter((c) => BALANCE_HEADER.test(c) && typesA.get(c) === 'amount')])
  const moneyB = new Set([...layoutColumns(amountB), ...tableB.columns.filter((c) => BALANCE_HEADER.test(c) && typesB.get(c) === 'amount')])
  const valuesA = new Map(tableA.columns.map((c) => [c, columnValues(tableA, c)]))
  const valuesB = new Map(tableB.columns.map((c) => [c, columnValues(tableB, c)]))
  const score = (a: string, b: string): Scored => {
    const header = headerSimilarity(a, b)
    const overlap = valueOverlap(valuesA.get(a) ?? [], valuesB.get(b) ?? [])
    return { a, b, header, overlap, score: 0 }
  }
  // General date pairs must coincide in both directions, row-weighted: one side repeating a single date (a payroll
  // pay date) that happens to appear on the other side is not a match key.
  const dateScore = (a: string, b: string): Scored => {
    const header = headerSimilarity(a, b)
    const overlap = valueOverlap(dateValues(valuesA.get(a) ?? []), dateValues(valuesB.get(b) ?? []), { mutual: true })
    return { a, b, header, overlap, score: 0 }
  }
  const keys: MatchKey[] = []

  if (moduleId !== 'general') {
    // Reference: the text/ID pair whose values overlap most, helped by reference-like header names.
    const refA = tableA.columns.filter((c) => !moneyA.has(c) && typesA.get(c) !== 'date' && typesA.get(c) !== 'amount')
    const refB = tableB.columns.filter((c) => !moneyB.has(c) && typesB.get(c) !== 'date' && typesB.get(c) !== 'amount')
    let bestRef: Scored | undefined
    for (const a of refA) {
      for (const b of refB) {
        const s = score(a, b)
        const refLike = Math.max(headerSimilarity(a, 'Reference'), headerSimilarity(b, 'Reference'))
        s.score = 0.65 * s.overlap + 0.2 * s.header + 0.15 * refLike
        if (!bestRef || s.score > bestRef.score) bestRef = s
      }
    }
    if (bestRef) {
      keys.push({ id: 'reference', name: 'Reference', type: 'text', use: true, columnA: bestRef.a, columnB: bestRef.b, identifying: true, textRule: 'normalised' })
    }
    const datesA = tableA.columns.filter((c) => typesA.get(c) === 'date')
    const datesB = tableB.columns.filter((c) => typesB.get(c) === 'date')
    let bestDate: Scored | undefined
    datesA.forEach((a, ia) =>
      datesB.forEach((b, ib) => {
        const s = score(a, b)
        s.score = s.header + 0.5 * s.overlap - 0.01 * (ia + ib)
        if (!bestDate || s.score > bestDate.score) bestDate = s
      })
    )
    if (bestDate) {
      keys.push({ id: 'date', name: 'Date', type: 'date', use: true, columnA: bestDate.a, columnB: bestDate.b, identifying: false, dateToleranceDays: dateTol })
    }
    if (amountA || amountB) {
      keys.push({ id: 'amount', name: 'Amount', type: 'amount', use: !!(amountA && amountB), columnA: layoutLabel(amountA), columnB: layoutLabel(amountB), identifying: true, tolerance: { mode: 'exact' } })
    }
    return { keys, amountA, amountB, partyColumnA, partyColumnB }
  }

  // General: any column ↔ any column, proposed by header similarity and value overlap. A pair is ticked "use"
  // only when the values actually agree (overlap); header-only resemblances are proposed unticked.
  const candidates: Scored[] = []
  for (const a of tableA.columns) {
    if (BALANCE_HEADER.test(a) && typesA.get(a) === 'amount') continue
    for (const b of tableB.columns) {
      if (BALANCE_HEADER.test(b) && typesB.get(b) === 'amount') continue
      const ta = typesA.get(a) ?? 'text'
      const tb = typesB.get(b) ?? 'text'
      if ((ta === 'date') !== (tb === 'date')) continue
      if ((ta === 'amount') !== (tb === 'amount')) continue
      const s = ta === 'date' ? dateScore(a, b) : score(a, b)
      s.score = Math.max(s.header, s.overlap) + 0.25 * Math.min(s.header, s.overlap)
      if (s.header >= 0.7 || s.overlap >= 0.5) candidates.push(s)
    }
  }
  candidates.sort((x, y) => y.score - x.score || tableA.columns.indexOf(x.a) - tableA.columns.indexOf(y.a))
  const takenA = new Set<string>()
  const takenB = new Set<string>()
  let n = 0
  let amountUsed = false
  let generalAmountA: AmountLayout | undefined
  let generalAmountB: AmountLayout | undefined
  for (const c of candidates) {
    if (takenA.has(c.a) || takenB.has(c.b)) continue
    takenA.add(c.a)
    takenB.add(c.b)
    const ta = typesA.get(c.a) ?? 'text'
    const tb = typesB.get(c.b) ?? 'text'
    const agree = c.overlap >= 0.3
    if (ta === 'amount') {
      if (amountUsed) continue // only one Amount key; further money columns are left for the user
      amountUsed = true
      generalAmountA = { kind: 'signed', column: c.a }
      generalAmountB = { kind: 'signed', column: c.b }
      keys.push({ id: 'amount', name: 'Amount', type: 'amount', use: true, columnA: c.a, columnB: c.b, identifying: true, tolerance: { mode: 'exact' } })
      continue
    }
    n++
    const type: ColumnType = ta === 'date' ? 'date' : ta === 'id' || tb === 'id' ? 'id' : ta === 'number' && tb === 'number' ? 'number' : 'text'
    const name = c.a === c.b ? c.a : `${c.a} ↔ ${c.b}`
    const base = { id: `key-${n}`, name, type, use: agree, columnA: c.a, columnB: c.b }
    if (type === 'date') keys.push({ ...base, identifying: false, dateToleranceDays: dateTol })
    else if (type === 'number') keys.push({ ...base, identifying: true, tolerance: { mode: 'exact' } })
    else keys.push({ ...base, identifying: type === 'id', textRule: 'normalised' })
  }
  // Prefer the file's own amount layout (e.g. Debit/Credit) when the proposed amount column belongs to it.
  const finalA = generalAmountA && amountA && layoutColumns(amountA).includes((generalAmountA as { column: string }).column) ? amountA : generalAmountA
  const finalB = generalAmountB && amountB && layoutColumns(amountB).includes((generalAmountB as { column: string }).column) ? amountB : generalAmountB
  return { keys, amountA: finalA, amountB: finalB, partyColumnA, partyColumnB }
}

/**
 * Sign-convention check: for each File A amount, does an equal File B amount exist with the chosen setting
 * ("same"), or only with the opposite setting ("opposite")? Warn when more than 80% match only the opposite way.
 */
export function detectSignMismatch(tableA: ParsedTable, tableB: ParsedTable, cfg: ReconConfig): { opposite: number; same: number; warn: boolean } {
  if (!amountKeyOf(cfg) || !cfg.amountA || !cfg.amountB) return { opposite: 0, same: 0, warn: false }
  const linesA = buildLines(tableA, 'A', cfg)
  const linesB = buildLines(tableB, 'B', cfg)
  const inB = new Set<number>()
  for (const l of linesB) if (l.comparableAmount !== null) inB.add(toCents(l.comparableAmount))
  let same = 0
  let opposite = 0
  for (const l of linesA) {
    if (l.comparableAmount === null) continue
    const c = toCents(l.comparableAmount)
    if (c === 0) continue
    if (inB.has(c)) same++
    else if (inB.has(-c)) opposite++
  }
  const total = same + opposite
  return { opposite, same, warn: total > 0 && opposite / total > 0.8 }
}

/**
 * The first plausible pair in File A order, so the user can see whether the sign setting looks right.
 * Found through the non-amount identifying keys (e.g. Reference); without those, through equal absolute amounts.
 */
export function previewFirstPair(tableA: ParsedTable, tableB: ParsedTable, cfg: ReconConfig): { a: EngineLine; b: EngineLine } | null {
  const errors = validateConfig(cfg, tableA, tableB)
  if (errors.length > 0) return null
  const linesA = buildLines(tableA, 'A', cfg)
  const linesB = buildLines(tableB, 'B', cfg)
  if (linesA.length === 0 || linesB.length === 0) return null
  const keys = prepareKeys(cfg, linesA, linesB).filter((k) => k.kind !== 'amount')
  const sources = buildCandidateSources(keys)
  const absIndex = new Map<number, number[]>()
  for (let j = 0; j < linesB.length; j++) {
    const v = linesB[j].amount
    if (v === null || v === 0) continue
    const k = Math.abs(toCents(v))
    const list = absIndex.get(k)
    if (list) list.push(j)
    else absIndex.set(k, [j])
  }
  for (let i = 0; i < linesA.length; i++) {
    const found = new Set<number>()
    for (const s of sources) s.collect(i, (j) => found.add(j))
    if (found.size === 0 && sources.length === 0) {
      const v = linesA[i].amount
      if (v !== null && v !== 0) for (const j of absIndex.get(Math.abs(toCents(v))) ?? []) found.add(j)
    }
    if (found.size === 0) continue
    const a = linesA[i]
    const rank = (j: number): [number, number, number] => {
      const b = linesB[j]
      const absEq = a.amount !== null && b.amount !== null && Math.abs(toCents(a.amount)) === Math.abs(toCents(b.amount)) ? 0 : 1
      const dd = a.date && b.date ? Math.abs(dayNumber(a.date) - dayNumber(b.date)) : Number.MAX_SAFE_INTEGER
      return [absEq, dd, j]
    }
    const best = Array.from(found).sort((x, y) => {
      const rx = rank(x)
      const ry = rank(y)
      return rx[0] - ry[0] || rx[1] - ry[1] || rx[2] - ry[2]
    })[0]
    return { a, b: linesB[best] }
  }
  return null
}

