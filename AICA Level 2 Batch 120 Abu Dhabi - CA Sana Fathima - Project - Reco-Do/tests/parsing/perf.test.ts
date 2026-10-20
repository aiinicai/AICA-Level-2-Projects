import { describe, expect, it } from 'vitest'
import type { CellValue } from '@shared/contracts'
import { detectHeaderRow, inferColumnType, parseTable } from '@shared/parsing'

function generate(rows: number): CellValue[][] {
  const out: CellValue[][] = [
    ['Bank name', null, null, null, null, null, null, null, null, null],
    ['Txn Date', 'Value Date', 'Description', 'Reference', 'Debit', 'Credit', 'Balance', 'Party', 'Text Amount', 'Text Date']
  ]
  let balance = 1_000_000
  for (let i = 0; i < rows; i++) {
    const debit = i % 3 === 0 ? Math.round(i * 13.37) / 100 : null
    const credit = debit === null ? Math.round(i * 7.11) / 100 : null
    balance += (credit ?? 0) - (debit ?? 0)
    const day = 1 + (i % 28)
    out.push([
      new Date(2026, 8, day),
      new Date(2026, 8, day),
      `PAYMENT TO SUPPLIER NUMBER ${i % 500}`,
      `FT26${String(i).padStart(6, '0')}`,
      debit,
      credit,
      Math.round(balance * 100) / 100,
      `Party ${i % 97}`,
      `${(i * 1.5).toFixed(2)} CR`,
      `${String(day).padStart(2, '0')}/09/2026`
    ])
  }
  return out
}

describe('performance', () => {
  it('parses 50,000 rows × 10 columns well under 2 seconds', () => {
    const rows = generate(50_000)
    const t0 = performance.now()
    const header = detectHeaderRow(rows)
    const t = parseTable({ name: 'Big', rows }, { fileName: 'big.xlsx' })
    const elapsed = performance.now() - t0
    expect(header.index).toBe(1)
    expect(t.rows).toHaveLength(50_000)
    expect(t.columns).toHaveLength(10)
    expect(elapsed).toBeLessThan(2000)
  })

  it('infers column types on large columns quickly', () => {
    const rows = generate(50_000).slice(2)
    const t0 = performance.now()
    expect(inferColumnType('Reference', rows.map((r) => r[3]))).toBe('id')
    expect(inferColumnType('Debit', rows.map((r) => r[4]))).toBe('amount')
    expect(inferColumnType('Text Date', rows.map((r) => r[9]))).toBe('date')
    expect(performance.now() - t0).toBeLessThan(500)
  })
})
