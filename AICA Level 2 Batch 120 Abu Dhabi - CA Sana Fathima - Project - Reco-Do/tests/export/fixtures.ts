// Hand-built ReconSession fixtures for the export tests (no engine code involved).

import type {
  CellValue,
  EngineLine,
  MatchKey,
  MatchPair,
  ReconConfig,
  ReconSession,
  Side,
  Statement
} from '../../src/shared/contracts'

const d = (y: number, m: number, day: number): Date => new Date(y, m - 1, day)

function bankLine(side: Side, row: number, date: Date, ref: string, text: string, amount: number, comparable: number): EngineLine {
  const values: Record<string, CellValue> =
    side === 'A'
      ? {
          'Txn Date': date,
          Description: text,
          'Reference No': ref,
          Debit: amount < 0 ? -amount : null,
          Credit: amount > 0 ? amount : null
        }
      : {
          'Posting Date': date,
          'Doc No': `JV-${row}`,
          Remarks: text,
          'Cheque No': ref,
          Debit: amount > 0 ? amount : null,
          Credit: amount < 0 ? -amount : null
        }
  return { id: `${side}:r${row}`, side, rowId: `r${row}`, amount, comparableAmount: comparable, date, values }
}

export const BANK_KEYS: MatchKey[] = [
  { id: 'k-ref', name: 'Reference', type: 'text', use: true, columnA: 'Reference No', columnB: 'Cheque No', identifying: true, textRule: 'normalised' },
  { id: 'k-date', name: 'Date', type: 'date', use: true, columnA: 'Txn Date', columnB: 'Posting Date', identifying: false, dateToleranceDays: 3 },
  { id: 'k-amt', name: 'Amount', type: 'amount', use: true, columnA: '', columnB: '', identifying: true, tolerance: { mode: 'exact' } }
]

export function bankFixture(): { session: ReconSession; statement: Statement } {
  const config: ReconConfig = {
    moduleId: 'bank',
    sideAName: 'Bank statement',
    sideBName: 'General ledger extract',
    keys: BANK_KEYS,
    amountA: { kind: 'debit-credit', debit: 'Debit', credit: 'Credit' },
    amountB: { kind: 'debit-credit', debit: 'Debit', credit: 'Credit' },
    sign: 'inverse',
    referencePrefixes: ['CHQ', 'FT', 'TT'],
    currency: 'AED'
  }
  // Bank amounts are credit − debit; GL amounts are debit − credit with the inverse convention,
  // so comparableAmount for B = −amount.
  const linesA: EngineLine[] = [
    bankLine('A', 8, d(2026, 9, 3), 'CHQ 100234', 'Cheque 100234 Gulf Supplies', -8450, -8450),
    bankLine('A', 9, d(2026, 9, 5), 'TT55821', 'TT inward Emirates Steel', 25000, 25000),
    bankLine('A', 10, d(2026, 9, 8), 'FT7781', 'FT outward Delta Logistics', -8540, -8540),
    bankLine('A', 11, d(2026, 9, 12), 'REF 9911', 'Payment ref 9911', -1200, -1200),
    bankLine('A', 12, d(2026, 9, 15), 'POS 4471', 'Al Noor Trdg', 14700, 14700),
    bankLine('A', 13, d(2026, 7, 20), 'DD 3321', 'Direct credit 3321', 500, 500),
    bankLine('A', 14, d(2026, 9, 30), '', 'BANK CHARGES SEP', -52.5, -52.5),
    bankLine('A', 15, d(2026, 9, 30), '', 'INTEREST CREDIT', 310.25, 310.25),
    bankLine('A', 16, d(2026, 6, 15), 'CHQ 099001', 'Old cheque 099001', -1000, -1000)
  ]
  const linesB: EngineLine[] = [
    bankLine('B', 2, d(2026, 9, 3), '100234', 'Gulf Supplies payment', 8450, -8450),
    bankLine('B', 3, d(2026, 9, 5), 'TT-55821', 'Receipt Emirates Steel', -25000, 25000),
    bankLine('B', 4, d(2026, 9, 8), 'FT 7781', 'Delta Logistics', 8450, -8450),
    bankLine('B', 5, d(2026, 9, 25), '9911', 'Payment 9911', 1250, -1250),
    bankLine('B', 6, d(2026, 9, 15), 'R-4471', 'AL NOOR TRADING LLC receipt', -14700, 14700),
    bankLine('B', 7, d(2026, 8, 15), '3321', 'Receipt 3321', -400, 400),
    bankLine('B', 8, d(2026, 9, 28), '100240', 'Cheque 100240 Star Prints', 3000, -3000),
    bankLine('B', 9, d(2026, 9, 29), 'DEP-77', 'Cash deposit', -7000, 7000)
  ]
  const pass = (keyId: string): { keyId: string; pass: true } => ({ keyId, pass: true })
  const pairs: MatchPair[] = [
    {
      id: 'P1', tier: 'matched', aIds: ['A:r8'], bIds: ['B:r2'],
      keyResults: [pass('k-ref'), pass('k-date'), pass('k-amt')],
      amountDifference: 0, dateDifferenceDays: 0, reason: 'Reference, date and amount agree', flags: [], origin: 'engine', status: 'accepted'
    },
    {
      id: 'P2', tier: 'matched', aIds: ['A:r9'], bIds: ['B:r3'],
      keyResults: [pass('k-ref'), pass('k-date'), pass('k-amt')],
      amountDifference: 0, dateDifferenceDays: 0, reason: 'Reference, date and amount agree', flags: [], origin: 'engine', status: 'accepted'
    },
    {
      id: 'P3', tier: 'doubtful', aIds: ['A:r10'], bIds: ['B:r4'],
      keyResults: [pass('k-ref'), pass('k-date'), { keyId: 'k-amt', pass: false, detail: '90.00 difference' }],
      amountDifference: -90, dateDifferenceDays: 0,
      reason: 'Reference and date agree; amount differs by 90.00 (possible transposition 8,450 vs 8,540)',
      flags: ['transposition'], origin: 'engine', status: 'open'
    },
    {
      id: 'P4', tier: 'likely', aIds: ['A:r11'], bIds: ['B:r5'],
      keyResults: [pass('k-ref'), { keyId: 'k-date', pass: false, detail: 'differs by 13 days' }, { keyId: 'k-amt', pass: false, detail: '50.00 difference' }],
      amountDifference: 50, dateDifferenceDays: 13, reason: 'Only the reference agrees', flags: [], origin: 'engine', status: 'open',
      note: 'Asked treasury for the remittance advice'
    },
    {
      id: 'P5', tier: 'matched', aIds: ['A:r12'], bIds: ['B:r6'],
      keyResults: [{ keyId: 'k-ref', pass: false }, pass('k-date'), pass('k-amt')],
      amountDifference: 0, dateDifferenceDays: 0, reason: 'Same customer (Al Noor Trading), same day and amount',
      flags: [], origin: 'ai', status: 'accepted', confidence: 88, label: 'Matched — AI assisted (approved by Sana Fathima)'
    },
    {
      id: 'P6', tier: 'likely', aIds: ['A:r13'], bIds: ['B:r7'],
      keyResults: [pass('k-ref'), { keyId: 'k-date', pass: false }, { keyId: 'k-amt', pass: false }],
      amountDifference: 100, dateDifferenceDays: 26, reason: 'Only the reference agrees', flags: [], origin: 'engine', status: 'rejected'
    }
  ]
  const session: ReconSession = {
    id: 'sess-bank-1',
    createdAt: '2026-10-01T08:00:00.000Z',
    updatedAt: '2026-10-01T10:00:00.000Z',
    meta: {
      accountLabel: 'ENBD Current A/c',
      period: 'September 2026',
      fileA: { name: 'ENBD_Current_Statement_Sep2026.xlsx', sheet: 'Statement', rows: 9 },
      fileB: { name: 'GL_101200_Cash_Sep2026.xlsx', sheet: 'GL', rows: 8 },
      mappingName: 'ENBD Current A/c ↔ GL 101200',
      preparer: 'Sana Fathima',
      currency: 'AED',
      balances: { openingA: 90000, closingA: 100000, openingB: 90000, closingB: 103742.25 }
    },
    result: {
      config,
      linesA,
      linesB,
      pairs,
      unmatchedA: ['A:r13', 'A:r14', 'A:r15', 'A:r16'],
      unmatchedB: ['B:r7', 'B:r8', 'B:r9'],
      stats: { linesA: 9, linesB: 8, matched: 3, doubtful: 1, likely: 1, unmatchedA: 4, unmatchedB: 3, matchedAmount: 48150 },
      durationMs: 12
    },
    suggestions: [
      { id: 'S1', aIds: ['A:r12'], bIds: ['B:r6'], confidence: 88, reason: 'Same customer (Al Noor Trading), same day and amount', source: 'ai', status: 'accepted' },
      { id: 'S2', aIds: ['A:r14'], bIds: ['B:r9'], confidence: 35, reason: 'Weak narration similarity', source: 'ai', status: 'open' },
      { id: 'S3', aIds: ['A:r15'], bIds: ['B:r8'], confidence: 20, reason: 'Unrelated', source: 'code-partial-ref', status: 'rejected' }
    ],
    audit: [
      { id: 'E1', at: '2026-10-01T09:15:00.000Z', user: 'Sana Fathima', action: 'approve-suggestion', suggestionId: 'S1', before: 'AI Suggested', after: 'Matched' },
      { id: 'E3', at: '2026-10-01T09:40:00.000Z', user: 'Sana Fathima', action: 'note', pairId: 'P4', note: 'Asked treasury for the remittance advice' },
      { id: 'E2', at: '2026-10-01T09:20:00.000Z', user: 'Sana Fathima', action: 'reject', pairId: 'P6', before: 'Likely', after: 'Unmatched', note: 'Different transactions' }
    ],
    finalised: null
  }
  const statement: Statement = {
    kind: 'bank',
    title: 'Bank reconciliation statement',
    lines: [
      { label: 'Balance as per bank statement', value: 100000, isTotal: true },
      { label: 'Less: unpresented payments (in GL, not in bank)', value: -3000, lineIds: ['B:r8'] },
      { label: 'Add: uncredited deposits (in GL, not in bank)', value: 7000, lineIds: ['B:r9'] },
      { label: '± Bank items not in GL (charges, interest, direct credits)', value: -257.75, lineIds: ['A:r14', 'A:r15'] },
      { label: 'Adjusted balance', value: 103742.25, isTotal: true },
      { label: 'Balance as per GL', value: 103742.25, isTotal: true },
      { label: 'Unexplained difference', value: 0 }
    ],
    unexplainedDifference: 0
  }
  return { session, statement }
}

function personLine(side: Side, row: number, empId: string, name: string): EngineLine {
  const values: Record<string, CellValue> =
    side === 'A' ? { 'Employee ID': empId, 'Employee Name': name, Department: 'Ops' } : { 'Emp No': empId, Name: name, Bank: 'ENBD' }
  return { id: `${side}:r${row}`, side, rowId: `r${row}`, amount: null, comparableAmount: null, date: null, values }
}

export function generalNoAmountFixture(): { session: ReconSession; statement: Statement } {
  const keys: MatchKey[] = [
    { id: 'g-id', name: 'Employee ID', type: 'id', use: true, columnA: 'Employee ID', columnB: 'Emp No', identifying: true },
    { id: 'g-name', name: 'Name', type: 'text', use: true, columnA: 'Employee Name', columnB: 'Name', identifying: false, textRule: 'normalised' }
  ]
  const config: ReconConfig = {
    moduleId: 'general',
    sideAName: 'HR master',
    sideBName: 'WPS payroll',
    keys,
    sign: 'same',
    referencePrefixes: [],
    currency: 'AED'
  }
  const linesA = [
    personLine('A', 2, 'E001', 'Aisha Khan'),
    personLine('A', 3, 'E002', 'Mohd Rafi'),
    personLine('A', 4, 'E003', 'John Mathew'),
    personLine('A', 5, 'E004', 'Priya Nair'),
    personLine('A', 6, 'E005', 'Omar Saeed')
  ]
  const linesB = [
    personLine('B', 2, 'E001', 'AISHA KHAN'),
    personLine('B', 3, 'E002', 'Mohammed Rafi'),
    personLine('B', 4, 'E003', 'John Mathew'),
    personLine('B', 5, 'E004', 'Priya Nair'),
    personLine('B', 6, 'E099', 'New Joiner')
  ]
  const ok = [{ keyId: 'g-id', pass: true }, { keyId: 'g-name', pass: true }]
  const pairs: MatchPair[] = [
    { id: 'G1', tier: 'matched', aIds: ['A:r2'], bIds: ['B:r2'], keyResults: ok, amountDifference: null, dateDifferenceDays: null, reason: 'Employee ID and name agree', flags: [], origin: 'engine', status: 'accepted' },
    {
      id: 'G2', tier: 'likely', aIds: ['A:r3'], bIds: ['B:r3'],
      keyResults: [{ keyId: 'g-id', pass: true }, { keyId: 'g-name', pass: false, detail: "'Mohd Rafi' vs 'Mohammed Rafi'" }],
      amountDifference: null, dateDifferenceDays: null, reason: "Employee ID agrees; name differs ('Mohd Rafi' vs 'Mohammed Rafi')", flags: [], origin: 'engine', status: 'accepted', note: 'Same person'
    },
    { id: 'G3', tier: 'matched', aIds: ['A:r4'], bIds: ['B:r4'], keyResults: ok, amountDifference: null, dateDifferenceDays: null, reason: 'Employee ID and name agree', flags: [], origin: 'engine', status: 'accepted' },
    { id: 'G4', tier: 'matched', aIds: ['A:r5'], bIds: ['B:r5'], keyResults: ok, amountDifference: null, dateDifferenceDays: null, reason: 'Employee ID and name agree', flags: [], origin: 'engine', status: 'accepted' }
  ]
  const session: ReconSession = {
    id: 'sess-gen-1',
    createdAt: '2026-10-02T07:00:00.000Z',
    updatedAt: '2026-10-02T11:00:00.000Z',
    meta: {
      accountLabel: 'Payroll vs WPS',
      period: '01-Sep-2026 to 30-Sep-2026',
      fileA: { name: 'HR_Master_Sep2026.xlsx', sheet: 'Employees', rows: 5 },
      fileB: { name: 'WPS_Sep2026.csv', sheet: 'WPS_Sep2026', rows: 5 },
      preparer: 'Sana Fathima',
      currency: 'AED',
      balances: { openingA: null, closingA: null, openingB: null, closingB: null }
    },
    result: {
      config,
      linesA,
      linesB,
      pairs,
      unmatchedA: ['A:r6'],
      unmatchedB: ['B:r6'],
      stats: { linesA: 5, linesB: 5, matched: 3, doubtful: 0, likely: 1, unmatchedA: 1, unmatchedB: 1, matchedAmount: 0 },
      durationMs: 3
    },
    suggestions: [],
    audit: [
      { id: 'GE1', at: '2026-10-02T10:30:00.000Z', user: 'Sana Fathima', action: 'accept', pairId: 'G2', before: 'Likely', after: 'Matched', note: 'Same person' },
      { id: 'GE2', at: '2026-10-02T11:00:00.000Z', user: 'Sana Fathima', action: 'finalise' }
    ],
    finalised: { by: 'Sana Fathima', at: '2026-10-02T11:00:00.000Z' }
  }
  const statement: Statement = {
    kind: 'record-count',
    title: 'Record-count statement',
    lines: [
      { label: 'Records in HR master', value: 5, isTotal: true },
      { label: 'Matched', value: 4 },
      { label: 'Doubtful / Likely pending', value: 0 },
      { label: 'Only in HR master', value: 1, lineIds: ['A:r6'] },
      { label: 'Records in WPS payroll', value: 5, isTotal: true },
      { label: 'Matched', value: 4 },
      { label: 'Doubtful / Likely pending', value: 0 },
      { label: 'Only in WPS payroll', value: 1, lineIds: ['B:r6'] },
      { label: 'Count difference', value: 0 }
    ],
    unexplainedDifference: 0
  }
  return { session, statement }
}

/** A large bank session: `n` lines per side, 80% matched one-to-one, the rest unmatched. */
export function largeFixture(n: number): { session: ReconSession; statement: Statement } {
  const base = bankFixture()
  const linesA: EngineLine[] = new Array<EngineLine>(n)
  const linesB: EngineLine[] = new Array<EngineLine>(n)
  const start = new Date(2026, 5, 1).getTime()
  for (let i = 0; i < n; i++) {
    const date = new Date(start + (i % 120) * 86_400_000)
    const amt = Math.round(((i * 7919) % 100000) + 1) / 100 * (i % 3 === 0 ? -1 : 1)
    linesA[i] = bankLine('A', i + 2, date, `FT${100000 + i}`, `Transfer ${i} narration text`, amt, amt)
    linesB[i] = bankLine('B', i + 2, date, `FT-${100000 + i}`, `GL remark ${i}`, -amt, amt)
  }
  const matchedCount = Math.floor(n * 0.8)
  const pairs: MatchPair[] = new Array<MatchPair>(matchedCount)
  const keyResults = [
    { keyId: 'k-ref', pass: true },
    { keyId: 'k-date', pass: true },
    { keyId: 'k-amt', pass: true }
  ]
  for (let i = 0; i < matchedCount; i++) {
    pairs[i] = {
      id: `P${i + 1}`, tier: 'matched', aIds: [linesA[i].id], bIds: [linesB[i].id], keyResults,
      amountDifference: 0, dateDifferenceDays: 0, reason: 'Reference, date and amount agree', flags: [], origin: 'engine', status: 'accepted'
    }
  }
  const session: ReconSession = {
    ...base.session,
    id: 'sess-large',
    result: {
      ...base.session.result,
      linesA,
      linesB,
      pairs,
      unmatchedA: linesA.slice(matchedCount).map((l) => l.id),
      unmatchedB: linesB.slice(matchedCount).map((l) => l.id),
      stats: { linesA: n, linesB: n, matched: matchedCount, doubtful: 0, likely: 0, unmatchedA: n - matchedCount, unmatchedB: n - matchedCount, matchedAmount: 0 }
    },
    suggestions: [],
    audit: []
  }
  return { session, statement: base.statement }
}
