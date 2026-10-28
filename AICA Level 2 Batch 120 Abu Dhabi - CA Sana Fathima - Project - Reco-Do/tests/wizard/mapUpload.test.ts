import { describe, expect, it } from 'vitest'
import type { MatchKey, ReconConfig, WorkbookData } from '@shared/contracts'
import { dateOrderState } from '@/features/wizard/map/dateOrder'
import { parseSheet } from '@/features/wizard/upload/loadFile'

const dateKey: MatchKey = { id: 'date', name: 'Date', type: 'date', use: true, columnA: 'Date', columnB: 'Date', identifying: false, dateToleranceDays: 3 }
const cfg = (over: Partial<ReconConfig> = {}): ReconConfig => ({
  moduleId: 'bank',
  sideAName: 'Bank statement',
  sideBName: 'GL',
  keys: [dateKey],
  sign: 'inverse',
  referencePrefixes: [],
  currency: 'AED',
  ...over
})

describe('date order control (W1)', () => {
  it('stays hidden when both sides are clear and agree', () => {
    expect(dateOrderState(cfg(), { a: 'DMY', b: 'DMY' }).show).toBe(false)
    expect(dateOrderState(cfg({ keys: [{ ...dateKey, use: false }] }), { a: 'ambiguous', b: 'DMY' }).show).toBe(false)
  })

  it('shows when a side is ambiguous or the sides disagree, and reads ambiguous dates as DD/MM/YYYY', () => {
    const amb = dateOrderState(cfg(), { a: 'ambiguous', b: 'DMY' })
    expect(amb).toMatchObject({ show: true, a: 'DMY', b: 'DMY', ambiguous: { A: true, B: false } })
    expect(dateOrderState(cfg(), { a: 'DMY', b: 'MDY' })).toMatchObject({ show: true, a: 'DMY', b: 'MDY' })
  })

  it('uses the stored choice and keeps the control visible to change it back', () => {
    const st = dateOrderState(cfg({ dateOrderA: 'MDY' }), { a: 'DMY', b: 'DMY' })
    expect(st).toMatchObject({ show: true, a: 'MDY', b: 'DMY' })
  })
})

describe('file without a header row', () => {
  const wb: WorkbookData = {
    fileName: 'noheader.csv',
    sheets: [
      {
        name: 'Sheet1',
        rows: [
          [new Date(2026, 8, 1), 'FT1001', 1500.25],
          [new Date(2026, 8, 2), 'FT1002', 220.1],
          [new Date(2026, 8, 3), 'FT1003', 75.5]
        ]
      }
    ]
  } as WorkbookData

  it('can be read with "No header row": every row is data and columns are Column 1, 2, …', () => {
    const f = parseSheet(wb, 'noheader.csv', 100, 0, -1)
    expect(f.table.headerRowIndex).toBe(-1)
    expect(f.table.columns.slice(0, 3)).toEqual(['Column 1', 'Column 2', 'Column 3'])
    expect(f.table.rows).toHaveLength(3)
  })
})
