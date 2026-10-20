// Reconciliation statements (master prompt §4 Step 5): bank, ledger (AR/AP), general with amount, record count.
//
// Arithmetic. Every amount is expressed in the "balance sign" of File A: the sign in which File A's closing balance
// is reported (closing = opening + Σ lines). Matched lines cancel out, so
//   closing A − Σ(unmatched A) + Σ(unmatched B) + Σ(pair differences B − A) = closing B
// and anything left over is the unexplained difference. Doubtful/Likely (and accepted) pairs whose amounts differ
// appear as explicit lines, so the statement ties even before they are reviewed.

import type { EngineLine, MatchPair, ReconConfig, ReconMeta, ReconResult, Statement, StatementLine } from '@shared/contracts'
import { amountKeyOf, fmtMoney, isIdentifying, plural, round2, usedKeys } from './util'
import { rawCellText } from './keys'

type Sign = 1 | -1

/** Which way File A's own amounts move its reported balance, judged from opening/closing balances. */
function balanceSign(open: number | null, close: number | null, sum: number): Sign | null {
  if (open === null || close === null || sum === 0) return null
  const plus = Math.abs(open + sum - close)
  const minus = Math.abs(open - sum - close)
  if (plus === minus) return null
  return plus < minus ? 1 : -1
}

/**
 * Default balance sign when the files carry no balances. Our amounts are debit-positive; bank statements
 * report a credit (customer-funds) balance and AP ledgers a credit (payable) balance, so with Debit/Credit or
 * Dr/Cr layouts their balance moves opposite to the debit-positive amount. A signed column is taken as written.
 */
function defaultSignA(cfg: ReconConfig): Sign {
  const signed = cfg.amountA?.kind === 'signed'
  if (signed) return 1
  if (cfg.moduleId === 'bank' || cfg.moduleId === 'cc' || cfg.moduleId === 'ap') return -1
  return 1
}

function sum(lines: Array<EngineLine | undefined>, pick: (l: EngineLine) => number | null): number {
  let s = 0
  for (const l of lines) if (l) s += pick(l) ?? 0
  return s
}

interface Ctx {
  result: ReconResult
  meta: ReconMeta
  cfg: ReconConfig
  sA: Sign
  byId: Map<string, EngineLine>
  /** Balance-sign value of a line (File A balance terms). */
  val: (l: EngineLine) => number
  closingA: number
  closingB: number
  closingANote: string
  closingBNote: string
}

/** A short reference for a line: the first identifying text/ID key value, else the row id. */
function lineRef(cfg: ReconConfig, l: EngineLine): string {
  const keys = usedKeys(cfg).filter((k) => (k.type === 'id' || k.type === 'text') && isIdentifying(k))
  for (const k of keys) {
    const t = rawCellText(l.values[l.side === 'A' ? k.columnA : k.columnB])
    if (t) return t
  }
  for (const k of usedKeys(cfg).filter((k) => k.type === 'id' || k.type === 'text')) {
    const t = rawCellText(l.values[l.side === 'A' ? k.columnA : k.columnB])
    if (t) return t
  }
  // Fall back to a document / voucher number column, which every ledger extract carries.
  for (const [col, v] of Object.entries(l.values)) {
    if (!/\b(doc|document|voucher|ref|reference|cheque|chq|invoice|inv)\b/i.test(col)) continue
    const t = rawCellText(v)
    if (t) return t
  }
  return `row ${l.rowId.replace(/^r/, '')}`
}

function pairRef(ctx: Ctx, p: MatchPair): string {
  const refs = [...p.aIds, ...p.bIds].map((id) => ctx.byId.get(id)).filter((l): l is EngineLine => !!l)
  for (const l of refs) {
    const r = lineRef(ctx.cfg, l)
    if (!r.startsWith('row ')) return r
  }
  return refs.length > 0 ? lineRef(ctx.cfg, refs[0]) : p.id
}

function refList(ctx: Ctx, lines: EngineLine[]): string {
  if (lines.length === 0) return ''
  const refs = lines.slice(0, 6).map((l) => lineRef(ctx.cfg, l))
  return `: ${refs.join(', ')}${lines.length > 6 ? ', …' : ''}`
}

function itemsLine(ctx: Ctx, verb: 'Less' | 'Add', what: string, lines: EngineLine[], negateSum: boolean): StatementLine {
  const s = sum(lines, ctx.val)
  return {
    label: `${verb}: ${what} — ${plural(lines.length, 'item')}${refList(ctx, lines)}`,
    value: round2(negateSum ? -s : s),
    lineIds: lines.map((l) => l.id)
  }
}

/** Explicit lines for every pair whose amounts differ (B − A in balance terms). */
function pairDifferenceLines(ctx: Ctx, wordA: string, wordB: string): StatementLine[] {
  const out: StatementLine[] = []
  for (const p of ctx.result.pairs) {
    const a = p.aIds.map((id) => ctx.byId.get(id))
    const b = p.bIds.map((id) => ctx.byId.get(id))
    const ta = sum(a, ctx.val)
    const tb = sum(b, ctx.val)
    const diff = round2(tb - ta)
    if (diff === 0) continue
    const verb = diff > 0 ? 'Add' : 'Less'
    const ref = pairRef(ctx, p)
    const amounts = `${wordA} ${p.aIds.length > 1 ? `${p.aIds.length} lines ` : ''}${fmtMoney(Math.abs(ta))} vs ${wordB} ${p.bIds.length > 1 ? `${p.bIds.length} lines ` : ''}${fmtMoney(Math.abs(tb))}`
    let what: string
    if (p.flags.includes('multiple-candidates')) what = `duplicate lines for ${ref}`
    else if (p.flags.includes('transposition')) what = `possible transposition error on ${ref}`
    else if (p.flags.includes('bank-charge') && (ctx.cfg.moduleId === 'bank' || ctx.cfg.moduleId === 'cc')) what = `possible bank charge deducted from ${ref}`
    else if (p.flags.includes('rounding')) what = `rounding difference on ${ref}`
    else what = `amount difference on ${ref}`
    const status = p.status === 'accepted' ? 'accepted' : p.tier === 'matched' ? 'matched' : `${p.tier}, pending review`
    out.push({ label: `${verb}: ${what} (${amounts}; ${status})`, value: diff, lineIds: [...p.aIds, ...p.bIds] })
  }
  return out
}

function total(label: string, value: number): StatementLine {
  return { label, value: round2(value), isTotal: true }
}

function addUp(lines: StatementLine[]): number {
  return round2(lines.reduce((s, l) => s + l.value, 0))
}

function context(result: ReconResult, meta: ReconMeta): Ctx {
  const cfg = result.config
  const byId = new Map<string, EngineLine>()
  for (const l of result.linesA) byId.set(l.id, l)
  for (const l of result.linesB) byId.set(l.id, l)
  const sumA = round2(sum(result.linesA, (l) => l.amount))
  const sumB = round2(sum(result.linesB, (l) => l.amount))
  const { openingA, closingA, openingB, closingB } = meta.balances
  const c: Sign = cfg.sign === 'inverse' ? -1 : 1
  const inferredA = balanceSign(openingA, closingA, sumA)
  const inferredB = balanceSign(openingB, closingB, sumB)
  const sA: Sign = inferredA ?? (inferredB ? ((inferredB * c) as Sign) : defaultSignA(cfg))
  const expectedSB = (sA * c) as Sign
  const val = (l: EngineLine): number => sA * (l.comparableAmount ?? 0)

  let cA: number
  let noteA = ''
  if (closingA !== null) cA = closingA
  else if (openingA !== null) {
    cA = openingA + sA * sumA
    noteA = ' (opening balance plus the lines; no closing balance in the file)'
  } else {
    cA = sA * sumA
    noteA = ' (sum of the lines; no balance in the file)'
  }
  // File B balances are reported in File B's own balance sign. When the file shows its balance moving the other
  // way from what the sign convention implies, the reported figures are flipped into File A's terms.
  const flipB = inferredB !== null && inferredB !== expectedSB ? -1 : 1
  let cB: number
  let noteB = ''
  if (closingB !== null) cB = flipB * closingB
  else if (openingB !== null) {
    cB = flipB * openingB + sA * sum(result.linesB, (l) => l.comparableAmount)
    noteB = ' (opening balance plus the lines; no closing balance in the file)'
  } else {
    cB = sA * sum(result.linesB, (l) => l.comparableAmount)
    noteB = ' (sum of the lines; no balance in the file)'
  }
  return { result, meta, cfg, sA, byId, val, closingA: round2(cA), closingB: round2(cB), closingANote: noteA, closingBNote: noteB }
}

function asOf(meta: ReconMeta): string {
  return meta.period ? ` (${meta.period})` : ''
}

function bankStatement(ctx: Ctx): Statement {
  const unA = ctx.result.unmatchedA.map((id) => ctx.byId.get(id)).filter((l): l is EngineLine => !!l)
  const unB = ctx.result.unmatchedB.map((id) => ctx.byId.get(id)).filter((l): l is EngineLine => !!l)
  const payments = unB.filter((l) => ctx.val(l) < 0)
  const deposits = unB.filter((l) => ctx.val(l) > 0)
  const bankCredits = unA.filter((l) => ctx.val(l) > 0)
  const bankDebits = unA.filter((l) => ctx.val(l) < 0)
  const opening: StatementLine = { label: `Balance as per bank statement${asOf(ctx.meta)}${ctx.closingANote}`, value: ctx.closingA }
  const items: StatementLine[] = [
    itemsLine(ctx, 'Less', 'unpresented payments (in GL, not in bank)', payments, false),
    itemsLine(ctx, 'Add', 'uncredited deposits (in GL, not in bank)', deposits, false),
    itemsLine(ctx, 'Less', 'bank credits not in GL (interest, direct credits)', bankCredits, true),
    itemsLine(ctx, 'Add', 'bank debits not in GL (charges, direct debits)', bankDebits, true),
    ...pairDifferenceLines(ctx, 'bank', 'GL')
  ]
  const adjusted = addUp([opening, ...items])
  const gl: StatementLine = { label: `Balance as per general ledger${asOf(ctx.meta)}${ctx.closingBNote}`, value: ctx.closingB }
  const unexplained = round2(adjusted - ctx.closingB)
  return {
    kind: 'bank',
    title: `Bank reconciliation statement — ${ctx.meta.accountLabel}`,
    lines: [opening, ...items, total('Adjusted balance', adjusted), gl, total('Unexplained difference', unexplained)],
    unexplainedDifference: unexplained
  }
}

function ledgerStatement(ctx: Ctx): Statement {
  const isAr = ctx.cfg.moduleId === 'ar'
  const them = isAr ? "customer's" : "supplier's"
  const unA = ctx.result.unmatchedA.map((id) => ctx.byId.get(id)).filter((l): l is EngineLine => !!l)
  const unB = ctx.result.unmatchedB.map((id) => ctx.byId.get(id)).filter((l): l is EngineLine => !!l)
  const opening: StatementLine = { label: `Balance as per our books${asOf(ctx.meta)}${ctx.closingANote}`, value: ctx.closingA }
  const items: StatementLine[] = [
    itemsLine(ctx, 'Less', 'items in our books, not in theirs, that increase our balance', unA.filter((l) => ctx.val(l) > 0), true),
    itemsLine(ctx, 'Add', 'items in our books, not in theirs, that reduce our balance', unA.filter((l) => ctx.val(l) < 0), true),
    itemsLine(ctx, 'Add', `items in the ${them} statement, not in our books, that increase their balance`, unB.filter((l) => ctx.val(l) > 0), false),
    itemsLine(ctx, 'Less', `items in the ${them} statement, not in our books, that reduce their balance`, unB.filter((l) => ctx.val(l) < 0), false),
    ...pairDifferenceLines(ctx, 'ours', 'theirs')
  ]
  const calculated = addUp([opening, ...items])
  const file: StatementLine = { label: `Balance per ${them} statement (file)${ctx.closingBNote}`, value: ctx.closingB }
  const unexplained = round2(calculated - ctx.closingB)
  return {
    kind: 'ledger',
    title: `${isAr ? 'Customer' : 'Supplier'} account reconciliation — ${ctx.meta.accountLabel}`,
    lines: [opening, ...items, total(`Balance as per ${them} statement (calculated)`, calculated), file, total('Unexplained difference', unexplained)],
    unexplainedDifference: unexplained
  }
}

function generalAmountStatement(ctx: Ctx): Statement {
  const nameA = ctx.cfg.sideAName || 'File A'
  const nameB = ctx.cfg.sideBName || 'File B'
  const unA = ctx.result.unmatchedA.map((id) => ctx.byId.get(id)).filter((l): l is EngineLine => !!l)
  const unB = ctx.result.unmatchedB.map((id) => ctx.byId.get(id)).filter((l): l is EngineLine => !!l)
  const opening: StatementLine = { label: `Balance per ${nameA}${asOf(ctx.meta)}${ctx.closingANote}`, value: ctx.closingA }
  const items: StatementLine[] = [
    itemsLine(ctx, 'Less', `items in ${nameA} not in ${nameB}`, unA, true),
    itemsLine(ctx, 'Add', `items in ${nameB} not in ${nameA} (signed)`, unB, false),
    ...pairDifferenceLines(ctx, nameA, nameB)
  ]
  const calculated = addUp([opening, ...items])
  const file: StatementLine = { label: `Balance per ${nameB} file${ctx.closingBNote}`, value: ctx.closingB }
  const unexplained = round2(calculated - ctx.closingB)
  return {
    kind: 'general-amount',
    title: `Reconciliation statement — ${nameA} vs ${nameB}`,
    lines: [opening, ...items, total(`= Balance per ${nameB} (calculated)`, calculated), file, total('Unexplained difference', unexplained)],
    unexplainedDifference: unexplained
  }
}

/**
 * Record-count statement (General without an amount key). "Records in" is the number of rows parsed from each
 * file (meta.fileA.rows / meta.fileB.rows), independent of the engine's own line list, so a line that is counted
 * twice (in two pairs, or in a pair and the unmatched list) or missing from every list shows a non-zero
 * difference. Without a usable row count in meta the engine's line count is used instead.
 */
function recordCountStatement(result: ReconResult, meta: ReconMeta): Statement {
  const cfg = result.config
  const nameA = cfg.sideAName || 'File A'
  const nameB = cfg.sideBName || 'File B'
  const count = (side: 'A' | 'B', pred: (p: MatchPair) => boolean): { n: number; ids: string[] } => {
    const ids: string[] = []
    for (const p of result.pairs) if (pred(p)) ids.push(...(side === 'A' ? p.aIds : p.bIds))
    return { n: ids.length, ids }
  }
  const isMatched = (p: MatchPair): boolean => p.tier === 'matched'
  const isPending = (p: MatchPair): boolean => p.tier !== 'matched'
  const mA = count('A', isMatched)
  const pA = count('A', isPending)
  const mB = count('B', isMatched)
  const pB = count('B', isPending)
  const rowsOf = (n: number | undefined, fallback: number): number => (typeof n === 'number' && Number.isFinite(n) && n >= 0 ? n : fallback)
  const recordsA = rowsOf(meta.fileA?.rows, result.linesA.length)
  const recordsB = rowsOf(meta.fileB?.rows, result.linesB.length)
  const diffA = recordsA - mA.n - pA.n - result.unmatchedA.length
  const diffB = recordsB - mB.n - pB.n - result.unmatchedB.length
  const lines: StatementLine[] = [
    { label: `Records in ${nameA}`, value: recordsA, isTotal: true },
    { label: '  = Matched', value: mA.n, lineIds: mA.ids },
    { label: '  + Doubtful / Likely pending', value: pA.n, lineIds: pA.ids },
    { label: `  + Only in ${nameA}`, value: result.unmatchedA.length, lineIds: [...result.unmatchedA] },
    { label: `Records in ${nameB}`, value: recordsB, isTotal: true },
    { label: '  = Matched', value: mB.n, lineIds: mB.ids },
    { label: '  + Doubtful / Likely pending', value: pB.n, lineIds: pB.ids },
    { label: `  + Only in ${nameB}`, value: result.unmatchedB.length, lineIds: [...result.unmatchedB] },
    { label: `Count difference (${nameA})`, value: diffA, isTotal: true },
    { label: `Count difference (${nameB})`, value: diffB, isTotal: true }
  ]
  return {
    kind: 'record-count',
    title: `Record-count statement — ${nameA} vs ${nameB}`,
    lines,
    unexplainedDifference: Math.abs(diffA) + Math.abs(diffB)
  }
}

export function buildStatement(result: ReconResult, meta: ReconMeta): Statement {
  const cfg = result.config
  if (!amountKeyOf(cfg)) return recordCountStatement(result, meta)
  const ctx = context(result, meta)
  if (cfg.moduleId === 'bank' || cfg.moduleId === 'cc') return bankStatement(ctx)
  if (cfg.moduleId === 'ar' || cfg.moduleId === 'ap') return ledgerStatement(ctx)
  return generalAmountStatement(ctx)
}
