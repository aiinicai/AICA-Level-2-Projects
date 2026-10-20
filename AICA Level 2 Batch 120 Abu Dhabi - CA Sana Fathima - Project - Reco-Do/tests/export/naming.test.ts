import { describe, expect, it } from 'vitest'
import {
  ageBucket,
  exportFileName,
  periodEndDate,
  periodFileTag,
  sanitiseSheetName,
  toReconcileSheetName,
  uniqueSheetName
} from '@export/index'
import { bankFixture, generalNoAmountFixture } from './fixtures'

describe('exportFileName', () => {
  it('builds the documented example', () => {
    expect(exportFileName(bankFixture().session, 'xlsx')).toBe('Reco-Do_Bank_ENBD-Current-Ac_Sep-2026.xlsx')
    expect(exportFileName(bankFixture().session, '.pdf')).toBe('Reco-Do_Bank_ENBD-Current-Ac_Sep-2026.pdf')
  })

  it('handles date-range periods and General recons', () => {
    expect(exportFileName(generalNoAmountFixture().session, 'xlsx')).toBe('Reco-Do_General_Payroll-vs-WPS_Sep-2026.xlsx')
  })

  it('strips characters that are illegal in Windows file names', () => {
    const { session } = bankFixture()
    session.meta.accountLabel = 'A<>:"/\\|?* B'
    session.meta.period = 'Q3: Jul–Sep?'
    const name = exportFileName(session, 'xlsx')
    expect(name).not.toMatch(/[<>:"/\\|?*\s]/)
    expect(name.startsWith('Reco-Do_Bank_A-B_')).toBe(true)
  })
})

describe('period helpers', () => {
  it('derives file tags', () => {
    expect(periodFileTag('September 2026')).toBe('Sep-2026')
    expect(periodFileTag('Sep-26')).toBe('Sep-2026')
    expect(periodFileTag('2026-09')).toBe('Sep-2026')
    expect(periodFileTag('01-Aug-2026 to 30-Sep-2026')).toBe('Aug-2026_to_Sep-2026')
    expect(periodFileTag('Year end')).toBe('Year-end')
  })

  it('derives period end dates', () => {
    const fmt = (d: Date | null): string | null => (d ? `${d.getFullYear()}-${d.getMonth() + 1}-${d.getDate()}` : null)
    expect(fmt(periodEndDate('September 2026'))).toBe('2026-9-30')
    expect(fmt(periodEndDate('Feb 2028'))).toBe('2028-2-29')
    expect(fmt(periodEndDate('01-Sep-2026 to 15-Sep-2026'))).toBe('2026-9-15')
    expect(fmt(periodEndDate('2026-09-01 to 2026-09-20'))).toBe('2026-9-20')
    expect(periodEndDate('Year end')).toBeNull()
  })

  it('rejects impossible dates instead of rolling them over into the next month', () => {
    const fmt = (d: Date | null): string | null => (d ? `${d.getFullYear()}-${d.getMonth() + 1}-${d.getDate()}` : null)
    // 31 Feb is not a date: the period is read from its month and year instead of becoming 3 March.
    expect(fmt(periodEndDate('31 Feb 2026'))).toBe('2026-2-28')
    expect(fmt(periodEndDate('01-Feb-2026 to 31-Feb-2026'))).toBe('2026-2-28')
    expect(fmt(periodEndDate('2026-02-30'))).toBe('2026-2-28')
    expect(fmt(periodEndDate('29 Feb 2028'))).toBe('2028-2-29')
  })
})

describe('sheet names', () => {
  it('sanitises and limits to 31 characters', () => {
    expect(sanitiseSheetName('A[b]:c*d?e/f\\g')).toBe('Abcdefg')
    expect(sanitiseSheetName('x'.repeat(40))).toHaveLength(31)
    expect(sanitiseSheetName("''")).toBe('Sheet')
    expect(toReconcileSheetName('General ledger extract')).toBe('To Reconcile — General ledger…')
    expect(toReconcileSheetName('Our AR ledger (customer account)').length).toBeLessThanOrEqual(31)
    expect(toReconcileSheetName('GL')).toBe('To Reconcile — GL')
  })

  it('keeps names unique', () => {
    const taken = new Set<string>()
    expect(uniqueSheetName('Data', taken)).toBe('Data')
    expect(uniqueSheetName('data', taken)).toBe('data (2)')
    const long = 'y'.repeat(31)
    expect(uniqueSheetName(long, taken)).toBe(long)
    const second = uniqueSheetName(long, taken)
    expect(second).toHaveLength(31)
    expect(second.endsWith(' (2)')).toBe(true)
  })
})

describe('ageBucket', () => {
  it('uses 0-30 / 31-60 / 61-90 / 90+', () => {
    expect(ageBucket(0)).toBe('0-30')
    expect(ageBucket(30)).toBe('0-30')
    expect(ageBucket(31)).toBe('31-60')
    expect(ageBucket(60)).toBe('31-60')
    expect(ageBucket(61)).toBe('61-90')
    expect(ageBucket(90)).toBe('61-90')
    expect(ageBucket(91)).toBe('90+')
  })
})
