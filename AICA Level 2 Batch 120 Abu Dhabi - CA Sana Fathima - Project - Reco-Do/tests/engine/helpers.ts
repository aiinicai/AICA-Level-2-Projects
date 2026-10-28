import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import type { AmountLayout, CellValue, MatchKey, ParsedTable, ReconConfig, ReconMeta, ReconResult } from '@shared/contracts'
import type { ModuleId, SignConvention } from '@shared/modules'
import { DEFAULT_REFERENCE_PREFIXES, parseTable, readWorkbook } from '@shared/parsing'

/** Builds a ParsedTable by hand. Row ids are r2, r3, … (header on row 1). */
export function table(columns: string[], rows: CellValue[][], name = 'test.xlsx'): ParsedTable {
  return {
    fileName: name,
    sheetName: 'Sheet1',
    headerRowIndex: 0,
    columns,
    rows: rows.map((r, k) => ({ id: `r${k + 2}`, sourceRow: k + 1, values: Object.fromEntries(columns.map((c, i) => [c, r[i] ?? null])) })),
    excluded: [],
    openingBalance: null,
    closingBalance: null
  }
}

export const d = (y: number, m: number, day: number): Date => new Date(y, m - 1, day)

export function refKey(columnA = 'Ref', columnB = 'Ref', over: Partial<MatchKey> = {}): MatchKey {
  return { id: 'reference', name: 'Reference', type: 'text', use: true, columnA, columnB, identifying: true, textRule: 'normalised', ...over }
}
export function dateKey(tol = 3, columnA = 'Date', columnB = 'Date', over: Partial<MatchKey> = {}): MatchKey {
  return { id: 'date', name: 'Date', type: 'date', use: true, columnA, columnB, identifying: false, dateToleranceDays: tol, ...over }
}
export function amountKey(over: Partial<MatchKey> = {}): MatchKey {
  return { id: 'amount', name: 'Amount', type: 'amount', use: true, columnA: 'Amount', columnB: 'Amount', identifying: true, tolerance: { mode: 'exact' }, ...over }
}

export function config(keys: MatchKey[], over: Partial<ReconConfig> = {}): ReconConfig {
  return {
    moduleId: 'general',
    sideAName: 'File A',
    sideBName: 'File B',
    keys,
    amountA: { kind: 'signed', column: 'Amount' },
    amountB: { kind: 'signed', column: 'Amount' },
    sign: 'same',
    referencePrefixes: DEFAULT_REFERENCE_PREFIXES,
    currency: 'AED',
    ...over
  }
}

export function meta(over: Partial<ReconMeta> = {}): ReconMeta {
  return {
    accountLabel: 'Test account',
    period: 'Sep 2026',
    fileA: { name: 'a.xlsx', sheet: 'Sheet1', rows: 0 },
    fileB: { name: 'b.xlsx', sheet: 'Sheet1', rows: 0 },
    preparer: 'Sana Fathima',
    currency: 'AED',
    balances: { openingA: null, closingA: null, openingB: null, closingB: null },
    ...over
  }
}

export function metaFor(a: ParsedTable, b: ParsedTable, over: Partial<ReconMeta> = {}): ReconMeta {
  return meta({
    fileA: { name: a.fileName, sheet: a.sheetName, rows: a.rows.length },
    fileB: { name: b.fileName, sheet: b.sheetName, rows: b.rows.length },
    balances: { openingA: a.openingBalance, closingA: a.closingBalance, openingB: b.openingBalance, closingB: b.closingBalance },
    ...over
  })
}

const SAMPLES = resolve(__dirname, '../../sample-data')

export function loadSample(path: string, headerRowIndex?: number): ParsedTable {
  const buf = readFileSync(resolve(SAMPLES, path))
  const ab = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength) as ArrayBuffer
  const wb = readWorkbook(ab, path.split('/').pop() ?? path)
  return parseTable(wb.sheets[0], { fileName: path, headerRowIndex })
}

export function expected(): Record<string, { tiers: Record<string, number>; statement?: Array<{ line: string; amount: number }> }> {
  return JSON.parse(readFileSync(resolve(SAMPLES, 'expected-results.json'), 'utf8')) as Record<string, { tiers: Record<string, number> }>
}

/** Tier counts in the README convention (File A lines; doubtfulB = File B lines in Doubtful pairs). */
export function tierCounts(r: ReconResult): Record<string, number> {
  const lines = (tier: string, side: 'a' | 'b'): number => r.pairs.filter((p) => p.tier === tier).reduce((s, p) => s + (side === 'a' ? p.aIds.length : p.bIds.length), 0)
  return {
    matched: lines('matched', 'a'),
    doubtful: lines('doubtful', 'a'),
    doubtfulB: lines('doubtful', 'b'),
    likely: lines('likely', 'a'),
    unmatchedA: r.unmatchedA.length,
    unmatchedB: r.unmatchedB.length
  }
}

export interface SampleSetup {
  moduleId: ModuleId
  sign: SignConvention
  sideAName: string
  sideBName: string
  keys: MatchKey[]
  amountA?: AmountLayout
  amountB?: AmountLayout
  partyColumnA?: string
  partyColumnB?: string
}

export function sampleConfig(s: SampleSetup): ReconConfig {
  return { ...s, referencePrefixes: DEFAULT_REFERENCE_PREFIXES, currency: 'AED' }
}
