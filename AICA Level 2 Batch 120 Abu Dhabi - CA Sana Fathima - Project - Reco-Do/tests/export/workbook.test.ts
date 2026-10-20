import { describe, expect, it } from 'vitest'
import ExcelJS from 'exceljs'
import { buildReconWorkbook, NUM_FMT_AMOUNT, NUM_FMT_COUNT, NUM_FMT_DATE } from '@export/index'
import { bankFixture, generalNoAmountFixture } from './fixtures'

const GENERATED = new Date(2026, 9, 3, 14, 30)

async function load(bytes: Uint8Array): Promise<ExcelJS.Workbook> {
  const wb = new ExcelJS.Workbook()
  await wb.xlsx.load(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) as ArrayBuffer)
  return wb
}

function sheet(wb: ExcelJS.Workbook, name: string): ExcelJS.Worksheet {
  const ws = wb.getWorksheet(name)
  if (!ws) throw new Error(`Missing sheet ${name}`)
  return ws
}

function headers(ws: ExcelJS.Worksheet, row = 1): string[] {
  const out: string[] = []
  ws.getRow(row).eachCell({ includeEmpty: true }, (c, col) => {
    out[col - 1] = c.value === null || c.value === undefined ? '' : String(c.value)
  })
  return out
}

function col(ws: ExcelJS.Worksheet, header: string, row = 1): number {
  const idx = headers(ws, row).indexOf(header)
  if (idx < 0) throw new Error(`Missing header "${header}" in ${ws.name}: ${headers(ws, row).join(' | ')}`)
  return idx + 1
}

/** First row (from 2) whose first cell equals or starts with `label`. */
function findRow(ws: ExcelJS.Worksheet, label: string, column = 1): ExcelJS.Row {
  for (let r = 1; r <= ws.rowCount; r++) {
    const v = ws.getRow(r).getCell(column).value
    if (typeof v === 'string' && v.startsWith(label)) return ws.getRow(r)
  }
  throw new Error(`Row "${label}" not found in ${ws.name}`)
}

function rowWhere(ws: ExcelJS.Worksheet, column: number, value: string): ExcelJS.Row {
  for (let r = 2; r <= ws.rowCount; r++) {
    if (ws.getRow(r).getCell(column).value === value) return ws.getRow(r)
  }
  throw new Error(`No row with "${value}" in ${ws.name}`)
}

function num(c: ExcelJS.Cell): number {
  if (typeof c.value !== 'number') throw new Error(`Cell ${c.address} is not a number: ${String(c.value)}`)
  return c.value
}

function frozenY(ws: ExcelJS.Worksheet): number | undefined {
  const v = ws.views[0]
  return v && v.state === 'frozen' ? v.ySplit : undefined
}

function fillArgb(c: ExcelJS.Cell): string | undefined {
  const f = c.fill
  return f && f.type === 'pattern' ? f.fgColor?.argb : undefined
}

describe('buildReconWorkbook (bank)', async () => {
  const { session, statement } = bankFixture()
  const bytes = await buildReconWorkbook(session, statement, { generatedAt: GENERATED })
  const wb = await load(bytes)

  it('returns xlsx bytes with workbook properties', () => {
    expect(bytes).toBeInstanceOf(Uint8Array)
    expect(bytes[0]).toBe(0x50) // "PK" zip signature
    expect(bytes[1]).toBe(0x4b)
    expect(wb.creator).toBe('Reco-Do')
  })

  it('has the eight sheets in order with sanitised names', () => {
    const names = wb.worksheets.map((w) => w.name)
    expect(names).toEqual([
      'Summary',
      'Reconciliation Statement',
      'Matched (100%)',
      'To Reconcile — Bank statement',
      'To Reconcile — General ledger…',
      'Doubtful & Likely',
      'AI Assisted',
      'Audit Log'
    ])
    for (const n of names) {
      expect(n.length).toBeLessThanOrEqual(31)
      expect(n).not.toMatch(/[[\]:*?/\\]/)
    }
  })

  it('freezes and bolds header rows and adds autofilters', () => {
    for (const name of ['Matched (100%)', 'To Reconcile — Bank statement', 'Doubtful & Likely', 'AI Assisted', 'Audit Log']) {
      const ws = sheet(wb, name)
      expect(frozenY(ws), name).toBe(1)
      expect(ws.getRow(1).getCell(1).font?.bold, name).toBe(true)
      expect(ws.autoFilter, name).toBeTruthy()
    }
    expect(frozenY(sheet(wb, 'Summary'))).toBe(1)
    expect(frozenY(sheet(wb, 'Reconciliation Statement'))).toBe(4)
  })

  it('writes the summary with tier counts, amounts and draft status', () => {
    const ws = sheet(wb, 'Summary')
    expect(headers(ws).slice(0, 2)).toEqual(['Item', 'Value'])
    expect(findRow(ws, 'Module').getCell(2).value).toBe('Bank Reconciliation')
    expect(findRow(ws, 'Account').getCell(2).value).toBe('ENBD Current A/c')
    expect(findRow(ws, 'Period').getCell(2).value).toBe('September 2026')
    expect(findRow(ws, 'Side A').getCell(2).value).toBe('Bank statement')
    expect(String(findRow(ws, 'File used – Bank statement').getCell(2).value)).toContain('ENBD_Current_Statement_Sep2026.xlsx')
    expect(findRow(ws, 'Mapping / template used').getCell(2).value).toBe('ENBD Current A/c ↔ GL 101200')
    expect(findRow(ws, 'Preparer').getCell(2).value).toBe('Sana Fathima')
    expect(findRow(ws, 'Status').getCell(2).value).toBe('Draft, not finalised')
    expect(findRow(ws, 'Currency').getCell(2).value).toBe('AED')
    const gen = findRow(ws, 'Generated').getCell(2).value
    expect(gen).toBeInstanceOf(Date)
    expect((gen as Date).getUTCHours()).toBe(14)

    const matched = findRow(ws, 'Matched')
    expect(num(matched.getCell(2))).toBe(3)
    // Tier amounts are absolute sums, the same definition as the on-screen KPIs (8,450 + 25,000 + 14,700).
    expect(num(matched.getCell(5))).toBe(48150)
    expect(matched.getCell(5).numFmt).toBe(NUM_FMT_AMOUNT)
    expect(fillArgb(matched.getCell(1))).toBeDefined()
    expect(num(findRow(ws, 'Doubtful').getCell(2))).toBe(1)
    expect(num(findRow(ws, 'Doubtful').getCell(5))).toBe(8540)
    expect(num(findRow(ws, 'Likely').getCell(2))).toBe(1)
    const ua = findRow(ws, 'Unmatched – Bank statement')
    expect(num(ua.getCell(3))).toBe(4)
    expect(num(ua.getCell(5))).toBeCloseTo(1862.75, 2) // 500 + 52.50 + 310.25 + 1,000
    const ub = findRow(ws, 'Unmatched – General ledger extract')
    expect(num(ub.getCell(4))).toBe(3)
    expect(num(ub.getCell(5))).toBe(10400) // 400 + 3,000 + 7,000
    const ai = findRow(ws, 'AI assisted')
    expect(num(ai.getCell(2))).toBe(1)
    expect(num(ai.getCell(5))).toBe(14700)
    expect(num(findRow(ws, 'Smart Recon suggestions pending').getCell(2))).toBe(1)
  })

  it('renders the statement lines with totals and a green nil difference', () => {
    const ws = sheet(wb, 'Reconciliation Statement')
    expect(ws.getCell('A1').value).toBe('Bank reconciliation statement')
    expect(headers(ws, 4).slice(0, 2)).toEqual(['Item', 'Amount (AED)'])
    const labels: string[] = []
    const values: number[] = []
    for (let r = 5; r < 5 + statement.lines.length; r++) {
      labels.push(String(ws.getCell(r, 1).value))
      values.push(num(ws.getCell(r, 2)))
      expect(ws.getCell(r, 2).numFmt).toBe(NUM_FMT_AMOUNT)
    }
    expect(labels).toEqual(statement.lines.map((l) => l.label))
    expect(values).toEqual(statement.lines.map((l) => l.value))
    const adjusted = findRow(ws, 'Adjusted balance')
    expect(adjusted.getCell(1).font?.bold).toBe(true)
    expect(adjusted.getCell(2).border?.top?.style).toBe('thin')
    const diff = findRow(ws, 'Unexplained difference')
    expect(num(diff.getCell(2))).toBe(0)
    expect(fillArgb(diff.getCell(2))).toMatch(/^FF[D-F]/) // light green tint
    const fg = diff.getCell(2).font?.color?.argb ?? ''
    expect(parseInt(fg.slice(4, 6), 16)).toBeGreaterThan(parseInt(fg.slice(2, 4), 16)) // dark green text
    // the difference appears once, not appended again
    let count = 0
    ws.eachRow((r) => {
      if (r.getCell(1).value === 'Unexplained difference') count++
    })
    expect(count).toBe(1)
    // count of underlying lines shown for drill-down lines
    expect(findRow(ws, '± Bank items not in GL').getCell(3).value).toBe(2)
  })

  it('lists matched pairs side by side with real dates and amounts', () => {
    const ws = sheet(wb, 'Matched (100%)')
    const h = headers(ws)
    expect(h).toEqual([
      'Pair ID',
      'Tier',
      'Bank statement – Row',
      'Bank statement – Date',
      'Bank statement – Reference No',
      'Bank statement – Amount',
      'General ledger extract – Row',
      'General ledger extract – Date',
      'General ledger extract – Cheque No',
      'General ledger extract – Amount',
      'Difference',
      'Reason',
      'Origin',
      'Label',
      'Note'
    ])
    const p1 = rowWhere(ws, 1, 'P1')
    const date = p1.getCell(col(ws, 'Bank statement – Date')).value
    expect(date).toBeInstanceOf(Date)
    expect((date as Date).getUTCFullYear()).toBe(2026)
    expect((date as Date).getUTCMonth()).toBe(8)
    expect((date as Date).getUTCDate()).toBe(3)
    expect(p1.getCell(col(ws, 'Bank statement – Date')).numFmt).toBe(NUM_FMT_DATE)
    expect(p1.getCell(col(ws, 'Bank statement – Amount')).value).toBe(-8450)
    expect(p1.getCell(col(ws, 'Bank statement – Amount')).numFmt).toBe(NUM_FMT_AMOUNT)
    expect(p1.getCell(col(ws, 'General ledger extract – Amount')).value).toBe(8450)
    expect(p1.getCell(col(ws, 'Bank statement – Row')).value).toBe('8')
    expect(p1.getCell(col(ws, 'Bank statement – Reference No')).value).toBe('CHQ 100234')
    expect(p1.getCell(2).value).toBe('Matched')
    expect(fillArgb(p1.getCell(2))).toBe('FFDBEDE7')
    const p5 = rowWhere(ws, 1, 'P5')
    expect(p5.getCell(2).value).toBe('AI assisted')
    expect(p5.getCell(col(ws, 'Label')).value).toBe('Matched — AI assisted (approved by Sana Fathima)')
    expect(p5.getCell(col(ws, 'Origin')).value).toBe('Smart Recon: AI')
    // open / rejected pairs are not on the matched sheet
    expect(() => rowWhere(ws, 1, 'P3')).toThrow()
    expect(() => rowWhere(ws, 1, 'P6')).toThrow()
    const total = findRow(ws, 'Total (3 pairs)')
    expect(num(total.getCell(col(ws, 'Bank statement – Amount')))).toBe(31250)
    expect(total.getCell(1).font?.bold).toBe(true)
  })

  it('lists open items on side A with ageing buckets and totals', () => {
    const ws = sheet(wb, 'To Reconcile — Bank statement')
    const h = headers(ws)
    expect(h.slice(0, 3)).toEqual(['Row', 'Date', 'Reference No'])
    expect(h).toContain('Description')
    expect(h).not.toContain('Debit')
    expect(h).not.toContain('Txn Date')
    expect(h.slice(-5)).toEqual(['Age (days)', '0-30 days', '31-60 days', '61-90 days', '90+ days'])
    const rowsCol = col(ws, 'Row')
    const rowIds: string[] = []
    for (let r = 2; r <= 7; r++) rowIds.push(String(ws.getCell(r, rowsCol).value))
    expect(rowIds).toEqual(['10', '11', '13', '14', '15', '16'])

    const charge = rowWhere(ws, rowsCol, '14')
    expect(charge.getCell(col(ws, 'Comment')).value).toBe('Probable bank charge – post JV')
    expect(charge.getCell(col(ws, 'Status')).value).toBe('Unmatched')
    expect(charge.getCell(col(ws, '0-30 days')).value).toBe(-52.5)
    const doubtful = rowWhere(ws, rowsCol, '10')
    expect(doubtful.getCell(col(ws, 'Status')).value).toBe('Pending review (Doubtful)')
    const rejected = rowWhere(ws, rowsCol, '13')
    expect(rejected.getCell(col(ws, 'Status')).value).toBe('Unmatched (pair rejected)')
    expect(rejected.getCell(col(ws, 'Age (days)')).value).toBe(72)
    expect(rejected.getCell(col(ws, '61-90 days')).value).toBe(500)
    const old = rowWhere(ws, rowsCol, '16')
    expect(old.getCell(col(ws, 'Age (days)')).value).toBe(107)
    expect(old.getCell(col(ws, '90+ days')).value).toBe(-1000)
    expect(old.getCell(col(ws, 'Date')).value).toBeInstanceOf(Date)
    expect(old.getCell(col(ws, 'Date')).numFmt).toBe(NUM_FMT_DATE)

    const total = findRow(ws, 'Total (6 items)')
    expect(num(total.getCell(col(ws, 'Amount (AED)')))).toBeCloseTo(-9982.25, 2)
    expect(num(total.getCell(col(ws, '0-30 days')))).toBeCloseTo(-9482.25, 2)
    expect(total.getCell(col(ws, '31-60 days')).value).toBe(0)
    expect(num(total.getCell(col(ws, '61-90 days')))).toBe(500)
    expect(num(total.getCell(col(ws, '90+ days')))).toBe(-1000)
    expect(String(findRow(ws, 'Ageing as of').getCell(1).value)).toContain('30-Sep-2026 (period end)')
  })

  it('lists open items on side B with ageing', () => {
    const ws = sheet(wb, 'To Reconcile — General ledger…')
    const total = findRow(ws, 'Total (5 items)')
    expect(num(total.getCell(col(ws, 'Amount (AED)')))).toBe(5300)
    expect(num(total.getCell(col(ws, '0-30 days')))).toBe(5700)
    expect(num(total.getCell(col(ws, '31-60 days')))).toBe(-400)
    expect(headers(ws)).toContain('Cheque No')
    expect(headers(ws)).toContain('Remarks')
  })

  it('shows doubtful and likely pairs with per-key ticks and decisions', () => {
    const ws = sheet(wb, 'Doubtful & Likely')
    const h = headers(ws)
    expect(h).toContain('Reference ✓/✗')
    expect(h).toContain('Date ✓/✗')
    expect(h).toContain('Amount ✓/✗')
    expect(h).toContain('Decision')
    const p3 = rowWhere(ws, 1, 'P3')
    expect(p3.getCell(2).value).toBe('Doubtful')
    expect(p3.getCell(col(ws, 'Reference ✓/✗')).value).toBe('✓')
    expect(p3.getCell(col(ws, 'Amount ✓/✗')).value).toBe('✗ 90.00 difference')
    expect(p3.getCell(col(ws, 'Difference')).value).toBe(-90)
    expect(p3.getCell(col(ws, 'Flags')).value).toBe('Possible transposition')
    expect(String(p3.getCell(col(ws, 'Reason')).value)).toContain('transposition 8,450 vs 8,540')
    expect(p3.getCell(col(ws, 'Decision')).value).toBe('Open')
    const p4 = rowWhere(ws, 1, 'P4')
    expect(p4.getCell(2).value).toBe('Likely')
    expect(p4.getCell(col(ws, 'Note')).value).toBe('Asked treasury for the remittance advice')
    expect(rowWhere(ws, 1, 'P6').getCell(col(ws, 'Decision')).value).toBe('Rejected')
    expect(fillArgb(p3.getCell(2))).toBeDefined()
  })

  it('lists approved AI assisted matches once', () => {
    const ws = sheet(wb, 'AI Assisted')
    expect(headers(ws).slice(0, 4)).toEqual(['ID', 'Tier', 'Source', 'Confidence (%)'])
    const p5 = rowWhere(ws, 1, 'P5')
    expect(p5.getCell(4).value).toBe(88)
    expect(p5.getCell(col(ws, 'Status')).value).toBe('Approved')
    expect(fillArgb(p5.getCell(2))).toBeDefined()
    expect(() => rowWhere(ws, 1, 'S1')).toThrow() // same ids as P5: not duplicated
    expect(() => rowWhere(ws, 1, 'S2')).toThrow() // pending
  })

  it('writes the audit log in time order with real timestamps', () => {
    const ws = sheet(wb, 'Audit Log')
    expect(headers(ws)).toEqual(['Timestamp', 'User', 'Action', 'Pair', 'Suggestion', 'Before', 'After', 'Note'])
    expect(ws.getCell('C2').value).toBe('Approved suggestion')
    expect(ws.getCell('E2').value).toBe('S1')
    expect(ws.getCell('C3').value).toBe('Rejected pair')
    expect(ws.getCell('H3').value).toBe('Different transactions')
    expect(ws.getCell('C4').value).toBe('Added note')
    const ts = ws.getCell('A2').value
    expect(ts).toBeInstanceOf(Date)
    const local = new Date('2026-10-01T09:15:00.000Z')
    expect((ts as Date).getUTCHours()).toBe(local.getHours())
    expect((ts as Date).getUTCMinutes()).toBe(local.getMinutes())
  })

  it('uses consistent widths (no zero-width or huge columns)', () => {
    for (const ws of wb.worksheets) {
      ws.columns.forEach((c) => {
        if (c.width !== undefined) {
          expect(c.width).toBeGreaterThanOrEqual(8)
          expect(c.width).toBeLessThanOrEqual(62)
        }
      })
    }
  })
})

describe('buildReconWorkbook (General, no amount)', async () => {
  const { session, statement } = generalNoAmountFixture()
  const wb = await load(await buildReconWorkbook(session, statement, { generatedAt: GENERATED }))

  it('names the to-reconcile sheets after the user side names', () => {
    expect(wb.worksheets.map((w) => w.name)).toContain('To Reconcile — HR master')
    expect(wb.worksheets.map((w) => w.name)).toContain('To Reconcile — WPS payroll')
  })

  it('omits amount columns everywhere and shows counts', () => {
    for (const ws of wb.worksheets) {
      const row = ws.name === 'Reconciliation Statement' ? 4 : 1
      for (const h of headers(ws, row)) expect(h, ws.name).not.toMatch(/Amount|Difference$/)
    }
    const summary = sheet(wb, 'Summary')
    const tierHeader = findRow(summary, 'Tier')
    expect(tierHeader.getCell(5).value).toBeNull()
    const matched = findRow(summary, 'Matched')
    expect(num(matched.getCell(2))).toBe(4)
    expect(matched.getCell(2).numFmt).toBe(NUM_FMT_COUNT)
    expect(num(findRow(summary, 'Unmatched – HR master').getCell(3))).toBe(1)
  })

  it('shows the finalised status', () => {
    const summary = sheet(wb, 'Summary')
    expect(String(findRow(summary, 'Status').getCell(2).value)).toMatch(/^Finalised by Sana Fathima on \d{2}-Oct-2026/)
    expect(findRow(summary, 'Finalised by').getCell(2).value).toBe('Sana Fathima')
    expect(findRow(summary, 'Finalised at').getCell(2).value).toBeInstanceOf(Date)
  })

  it('renders a record-count statement without decimals', () => {
    const ws = sheet(wb, 'Reconciliation Statement')
    expect(headers(ws, 4).slice(0, 2)).toEqual(['Item', 'Records'])
    const first = findRow(ws, 'Records in HR master')
    expect(num(first.getCell(2))).toBe(5)
    expect(first.getCell(2).numFmt).toBe(NUM_FMT_COUNT)
    const diff = findRow(ws, 'Count difference')
    expect(num(diff.getCell(2))).toBe(0)
    expect(diff.getCell(2).numFmt).toBe(NUM_FMT_COUNT)
    expect(fillArgb(diff.getCell(1))).toBeDefined()
  })

  it('has no date or ageing columns when the data has no dates', () => {
    const ws = sheet(wb, 'To Reconcile — HR master')
    const h = headers(ws)
    expect(h).not.toContain('Date')
    expect(h).not.toContain('0-30 days')
    expect(h.slice(0, 3)).toEqual(['Row', 'Employee ID', 'Employee Name'])
    expect(findRow(ws, 'Total (1 items)')).toBeTruthy()
  })

  it('shows key ticks for the 2-key likely pair', () => {
    const ws = sheet(wb, 'Doubtful & Likely')
    const g2 = rowWhere(ws, 1, 'G2')
    expect(g2.getCell(col(ws, 'Employee ID ✓/✗')).value).toBe('✓')
    expect(g2.getCell(col(ws, 'Name ✓/✗')).value).toBe("✗ 'Mohd Rafi' vs 'Mohammed Rafi'")
    expect(g2.getCell(col(ws, 'Decision')).value).toBe('Accepted')
  })
})
