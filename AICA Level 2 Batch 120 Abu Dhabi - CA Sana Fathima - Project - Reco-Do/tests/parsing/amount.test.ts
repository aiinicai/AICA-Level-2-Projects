import { describe, expect, it } from 'vitest'
import { parseAmount } from '@shared/parsing'

const val = (v: Parameters<typeof parseAmount>[0]): number | null => parseAmount(v)?.value ?? null

describe('parseAmount', () => {
  it('passes numbers through', () => {
    expect(parseAmount(1234.5)).toEqual({ value: 1234.5, indicator: null })
    expect(parseAmount(-20)).toEqual({ value: -20, indicator: null })
    expect(parseAmount(0)).toEqual({ value: 0, indicator: null })
    expect(Object.is(parseAmount(-0)?.value, 0)).toBe(true)
    expect(parseAmount(Number.NaN)).toBeNull()
    expect(parseAmount(Number.POSITIVE_INFINITY)).toBeNull()
  })

  it('returns null for blanks, dashes, dates and non-amounts', () => {
    for (const v of [null, '', '   ', '-', '–', '—', '--', 'abc', 'INV-00123', 'DR26080001', 'CR26080004',
      'EXP-03001', '03/09/2026', '2026-09-03', 'N/A', '1,23,4.5.6', '12a', '(12', '1..2', '.']) {
      expect(parseAmount(v as string | null), String(v)).toBeNull()
    }
    expect(parseAmount(new Date(2026, 8, 3))).toBeNull()
  })

  it('reads thousands separators and plain text numbers', () => {
    expect(val('1,234.50')).toBe(1234.5)
    expect(val('1,234,567.89')).toBe(1234567.89)
    expect(val('1234.5')).toBe(1234.5)
    expect(val('  3,791.00 ')).toBe(3791)
    expect(val('1,234')).toBe(1234)
    expect(val('0.75')).toBe(0.75)
    expect(val('.5')).toBe(0.5)
    expect(val('1 234.50')).toBe(1234.5)
    expect(val('+250')).toBe(250)
    expect(val('12,34,567.50')).toBe(1234567.5)
    expect(val('1,23,456')).toBe(123456)
  })

  it('reads European formats only when unambiguous', () => {
    expect(val('1.234,50')).toBe(1234.5)
    expect(val('1.234.567,89')).toBe(1234567.89)
    expect(val('12,5')).toBe(12.5)
    expect(val('1234,50')).toBe(1234.5)
    expect(val('1.234.567')).toBe(1234567)
    // "1,234" and "1.234" are read the UAE way (comma thousands, dot decimal)
    expect(val('1,234')).toBe(1234)
    expect(val('1.234')).toBe(1.234)
    expect(val('1.234,5.6')).toBeNull()
    expect(val('12,34,56')).toBeNull()
  })

  it('reads negatives: brackets, trailing and leading minus', () => {
    expect(val('(500.00)')).toBe(-500)
    expect(val('(2,881.00)')).toBe(-2881)
    expect(val('750.00-')).toBe(-750)
    expect(val('2,041.61-')).toBe(-2041.61)
    expect(val('-750.00')).toBe(-750)
    expect(val('−750.00')).toBe(-750)
    expect(val('-(5)')).toBeNull()
    expect(val('(5)-')).toBeNull()
  })

  it('returns the CR / DR indicator without changing the sign', () => {
    expect(parseAmount('1,234.50 CR')).toEqual({ value: 1234.5, indicator: 'CR' })
    expect(parseAmount('1,234.50 Dr')).toEqual({ value: 1234.5, indicator: 'DR' })
    expect(parseAmount('1,234.50cr')).toEqual({ value: 1234.5, indicator: 'CR' })
    expect(parseAmount('1,937.92 DR')).toEqual({ value: 1937.92, indicator: 'DR' })
    expect(parseAmount('500.00 Dr.')).toEqual({ value: 500, indicator: 'DR' })
    expect(parseAmount('CR 1,000')).toEqual({ value: 1000, indicator: 'CR' })
    expect(parseAmount('Dr. 25')).toEqual({ value: 25, indicator: 'DR' })
    expect(parseAmount('(100.00) CR')).toEqual({ value: -100, indicator: 'CR' })
    expect(parseAmount('CR')).toBeNull()
  })

  it('strips currency codes and symbols', () => {
    expect(parseAmount('AED 1,200.00')).toEqual({ value: 1200, indicator: null })
    expect(parseAmount('1,200.00 AED')).toEqual({ value: 1200, indicator: null })
    expect(val('AED1,200')).toBe(1200)
    expect(val('aed 1,200')).toBe(1200)
    expect(val('USD (45.10)')).toBe(-45.1)
    expect(val('$ 99.99')).toBe(99.99)
    expect(val('€12,50')).toBe(12.5)
    expect(parseAmount('AED 1,200.00 CR')).toEqual({ value: 1200, indicator: 'CR' })
    expect(val('AED')).toBeNull()
  })
})
