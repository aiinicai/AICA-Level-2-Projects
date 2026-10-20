import { readFileSync } from 'fs'
import { describe, expect, it } from 'vitest'
import {
  detectDateOrder,
  headerSimilarity,
  inferColumnType,
  normaliseText,
  parseAmount,
  parseTable,
  valueOverlap
} from '@shared/parsing'
import type { ParsedTable } from '@shared/contracts'
import { d, loadSample } from './helpers'

const expected = JSON.parse(readFileSync('sample-data/expected-results.json', 'utf8')) as {
  bank: { rowsA: number; rowsB: number; opening: number; closeA: number; closeB: number }
  ar: { rowsA: number; rowsB: number; opening: number; closeA: number; closeB: number }
  ap: { rowsA: number; rowsB: number; opening: number; closeA: number; closeB: number }
  hrWps?: unknown
  intercompany: { rowsA: number; rowsB: number; opening: number; closeA: number; closeB: number }
  tools: {
    monthly: { jul: number; aug: number; sep: number; julClose: number; augClose: number; sepClose: number }
    tb: { accounts: number; total: number }
    messy: { dataRows: number; blankRows: number; subtotalRows: number; grandTotal: number }
  }
}

const table = (file: string): ParsedTable => {
  const wb = loadSample(file)
  return parseTable(wb.sheets[0], { fileName: file })
}

const col = (t: ParsedTable, name: string): Array<ParsedTable['rows'][number]['values'][string]> =>
  t.rows.map((r) => r.values[name])

describe('sample files: reconciliation pairs', () => {
  const pairs: Array<[keyof typeof expected, string, string]> = [
    ['bank', 'bank/ENBD_Current_Statement_Sep2026.xlsx', 'bank/GL_101200_Cash_Sep2026.xlsx'],
    ['ar', 'ar/Our_AR_Ledger_AlNoor_Trading.xlsx', 'ar/AlNoor_Trading_SOA.xlsx'],
    ['ap', 'ap/Our_AP_Ledger_Gulf_Supplies.xlsx', 'ap/Gulf_Supplies_SOA.xlsx'],
    ['intercompany', 'general/Intercompany_EntityA_Dubai.xlsx', 'general/Intercompany_EntityB_AbuDhabi.xlsx']
  ]
  for (const [key, fileA, fileB] of pairs) {
    it(`${key}: row counts and balances match expected-results.json`, () => {
      const exp = expected[key] as { rowsA: number; rowsB: number; opening: number; closeA: number; closeB: number }
      const a = table(fileA)
      const b = table(fileB)
      expect(a.rows).toHaveLength(exp.rowsA)
      expect(b.rows).toHaveLength(exp.rowsB)
      expect(a.openingBalance).toBeCloseTo(exp.opening, 2)
      expect(b.openingBalance).toBeCloseTo(exp.opening, 2)
      expect(a.closingBalance).toBeCloseTo(exp.closeA, 2)
      expect(b.closingBalance).toBeCloseTo(exp.closeB, 2)
      for (const t of [a, b]) {
        expect(t.excluded.map((e) => e.reason)).toEqual(['opening-balance', 'closing-balance'])
      }
    })
  }

  it('bank: columns, Date cells, types and reference normalisation', () => {
    const bank = table('bank/ENBD_Current_Statement_Sep2026.xlsx')
    const gl = table('bank/GL_101200_Cash_Sep2026.xlsx')
    expect(bank.columns).toEqual(['Txn Date', 'Value Date', 'Description', 'Reference No', 'Debit', 'Credit', 'Balance'])
    expect(gl.columns).toEqual(['Posting Date', 'Doc No', 'Voucher Type', 'Remarks', 'Party', 'Debit', 'Credit', 'Cheque No'])
    expect(bank.rows[0].id).toBe('r9')
    expect(bank.rows[0].values['Txn Date']).toEqual(d(2026, 9, 1))
    expect(gl.rows[0].values['Posting Date']).toEqual(d(2026, 9, 1))

    const types = bank.columns.map((c) => inferColumnType(c, col(bank, c)))
    expect(types).toEqual(['date', 'date', 'text', 'id', 'amount', 'amount', 'amount'])
    const glTypes = gl.columns.map((c) => inferColumnType(c, col(gl, c)))
    expect(glTypes).toEqual(['date', 'id', 'text', 'text', 'text', 'amount', 'amount', 'id'])

    // Cheques written without leading zeros in the GL normalise to the bank form.
    expect(normaliseText('004493')).toBe(normaliseText('4493'))
    expect(valueOverlap(col(bank, 'Reference No'), col(gl, 'Cheque No'))).toBeGreaterThan(0.8)
    expect(headerSimilarity('Txn Date', 'Posting Date')).toBeGreaterThanOrEqual(0.8)
    expect(headerSimilarity('Reference No', 'Cheque No')).toBeGreaterThanOrEqual(0.8)
  })

  it('general: HR master vs WPS register (Emp ID ↔ Employee No)', () => {
    const hr = table('general/HR_Employee_Master.xlsx')
    const wps = table('general/WPS_Payroll_Register_Sep2026.xlsx')
    expect(hr.headerRowIndex).toBe(1)
    expect(hr.rows).toHaveLength(180)
    expect(wps.rows).toHaveLength(175)
    expect(hr.openingBalance).toBeNull()
    expect(inferColumnType('Emp ID', col(hr, 'Emp ID'))).toBe('id')
    expect(inferColumnType('Employee No', col(wps, 'Employee No'))).toBe('id')
    expect(inferColumnType('IBAN', col(wps, 'IBAN'))).toBe('id')
    expect(inferColumnType('Net Pay', col(wps, 'Net Pay'))).toBe('amount')
    expect(inferColumnType('Pay Date', col(wps, 'Pay Date'))).toBe('date')
    expect(headerSimilarity('Emp ID', 'Employee No')).toBeGreaterThanOrEqual(0.8)
    // 15 payroll rows hold the number as 174 instead of "00174"; normalisation still pairs them.
    expect(valueOverlap(col(hr, 'Emp ID'), col(wps, 'Employee No'))).toBeGreaterThan(0.9)
    expect(valueOverlap(col(hr, 'IBAN'), col(wps, 'IBAN'))).toBeGreaterThan(0.9)
  })
})

describe('sample files: tools', () => {
  it('monthly statements: rows, repeated header, totals and closing balances', () => {
    const m = expected.tools.monthly
    const jul = table('tools/Statement_Jul2026.xlsx')
    const aug = table('tools/Statement_Aug2026.xlsx')
    const sep = table('tools/Statement_Sep2026.xlsx')
    expect(jul.rows).toHaveLength(m.jul)
    expect(aug.rows).toHaveLength(m.aug)
    expect(sep.rows).toHaveLength(m.sep)
    expect(Math.round((jul.closingBalance ?? 0) * 100)).toBe(m.julClose)
    expect(Math.round((aug.closingBalance ?? 0) * 100)).toBe(m.augClose)
    expect(Math.round((sep.closingBalance ?? 0) * 100)).toBe(m.sepClose)
    expect(aug.excluded.map((e) => [e.sourceRow, e.reason])).toContainEqual([28, 'repeated-header'])
    expect(sep.excluded.map((e) => e.reason)).toEqual(['opening-balance', 'total', 'closing-balance'])
    expect(sep.openingBalance).toBe(315276.29)
  })

  it('trial balance: 121 accounts, total row excluded', () => {
    const tb = table('tools/Sheet_to_print.xlsx')
    expect(tb.rows).toHaveLength(expected.tools.tb.accounts)
    expect(tb.excluded.map((e) => e.reason)).toEqual(['total'])
    const totalRow = tb.excluded[0].values
    expect(Math.round((totalRow[3] as number) * 100)).toBe(expected.tools.tb.total)
    expect(inferColumnType('Account Code', col(tb, 'Account Code'))).toBe('id')
  })

  it('messy data: blanks, subtotals, grand total, merged categories, text amounts and dates', () => {
    const exp = expected.tools.messy
    const wb = loadSample('tools/Messy_Data_for_Cleaner.xlsx')
    const t = parseTable(wb.sheets[0], { fileName: 'Messy_Data_for_Cleaner.xlsx' })
    expect(t.rows).toHaveLength(exp.dataRows)
    const reasons = t.excluded.map((e) => e.reason)
    expect(reasons.filter((r) => r === 'blank')).toHaveLength(exp.blankRows)
    expect(reasons.filter((r) => r === 'subtotal')).toHaveLength(exp.subtotalRows)
    expect(reasons.filter((r) => r === 'total')).toHaveLength(1)
    const grand = t.excluded.find((e) => e.reason === 'total')
    expect(Math.round((parseAmount(grand?.values[4] ?? null)?.value ?? 0) * 100)).toBe(exp.grandTotal)

    // Merged category cells: value only on the first row of each block.
    expect(t.rows[0].values.Category).toBe('Travel')
    expect(t.rows[1].values.Category).toBeNull()

    expect(inferColumnType('Amount', col(t, 'Amount'))).toBe('amount')
    expect(inferColumnType('Txn Date', col(t, 'Txn Date'))).toBe('date')
    expect(inferColumnType('Ref', col(t, 'Ref'))).toBe('id')
    expect(detectDateOrder(col(t, 'Txn Date'))).toBe('DMY')
    expect(parseAmount(t.rows[1].values.Amount)).toEqual({ value: 1937.92, indicator: 'DR' })
  })
})
