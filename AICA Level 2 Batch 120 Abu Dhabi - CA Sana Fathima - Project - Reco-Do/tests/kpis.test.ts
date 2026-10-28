import { describe, expect, it } from 'vitest'
import { computeKpis, type HistoryEntry } from '@shared/kpis'

const entry = (over: Partial<HistoryEntry>): HistoryEntry => ({
  id: 'x',
  moduleId: 'bank',
  accountLabel: 'ENBD Current A/c',
  finishedAt: '2026-10-05T09:40:00',
  totalLines: 100,
  autoMatchedLines: 80,
  openItemCount: 0,
  openItemAmount: 0,
  oldestOpenItemDate: null,
  ...over
})

describe('dashboard KPIs', () => {
  const now = new Date('2026-10-18T12:00:00')

  it('shows empty values when there is no history', () => {
    expect(computeKpis([], now)).toEqual({
      reconsThisMonth: 0,
      reconsLastMonth: 0,
      avgAutoMatchRate: null,
      openItemCount: 0,
      openItemAmount: 0,
      oldestOpenItem: null
    })
  })

  it('counts recons this month and last month', () => {
    const k = computeKpis(
      [entry({}), entry({ finishedAt: '2026-10-01T08:00:00' }), entry({ finishedAt: '2026-09-30T18:00:00' })],
      now
    )
    expect(k.reconsThisMonth).toBe(2)
    expect(k.reconsLastMonth).toBe(1)
  })

  it('handles the January → December year boundary', () => {
    const k = computeKpis([entry({ finishedAt: '2025-12-31T10:00:00' })], new Date('2026-01-10T10:00:00'))
    expect(k.reconsLastMonth).toBe(1)
  })

  it('averages auto-match rate per recon and sums open items', () => {
    const k = computeKpis(
      [
        entry({ autoMatchedLines: 90, openItemCount: 10, openItemAmount: 1500.25 }),
        entry({ autoMatchedLines: 70, openItemCount: 30, openItemAmount: 499.75 })
      ],
      now
    )
    expect(k.avgAutoMatchRate).toBeCloseTo(0.8)
    expect(k.openItemCount).toBe(40)
    expect(k.openItemAmount).toBeCloseTo(2000)
  })

  it('finds the oldest open item and its account', () => {
    const k = computeKpis(
      [
        entry({ accountLabel: 'ADCB Payroll A/c', oldestOpenItemDate: '2026-09-20T12:00:00' }),
        entry({ accountLabel: 'ENBD Current A/c', oldestOpenItemDate: '2026-09-01T12:00:00' })
      ],
      now
    )
    expect(k.oldestOpenItem).toEqual({ days: 47, account: 'ENBD Current A/c' })
  })
})
