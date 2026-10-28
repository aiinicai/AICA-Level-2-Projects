import { describe, expect, it } from 'vitest'
import type { CellValue } from '@shared/contracts'
import { DEFAULT_REFERENCE_PREFIXES, normaliseText, valueOverlap } from '@shared/parsing'

describe('normaliseText', () => {
  it('handles the master prompt examples', () => {
    expect(normaliseText('INV-00123')).toBe('123')
    expect(normaliseText('123')).toBe('123')
    expect(normaliseText('CHQ 004512')).toBe('4512')
    expect(normaliseText('004493')).toBe(normaliseText('4493'))
  })

  it('lower-cases and strips spaces, dashes, slashes and dots', () => {
    expect(normaliseText('  AB-12/34.56 ')).toBe('ab123456')
    expect(normaliseText('IC-2608-0001')).toBe('ic26080001')
    expect(normaliseText('Al Noor   Trading')).toBe('alnoortrading')
    expect(normaliseText('GS–INV–5520')).toBe('gs5520')
  })

  it('strips leading zeros of every numeric run but keeps inner zeros', () => {
    expect(normaliseText('A-0012-0300')).toBe('a120300')
    expect(normaliseText('1000')).toBe('1000')
    expect(normaliseText('000')).toBe('0')
    expect(normaliseText('00174')).toBe(normaliseText('174'))
  })

  it('joins digit groups split by separators before removing leading zeros', () => {
    expect(normaliseText('AE07 0331 2345 6789 0123 456')).toBe(normaliseText('AE070331234567890123456'))
    expect(normaliseText('AE07 0331 2345 6789 0123 456')).toBe('ae70331234567890123456')
    expect(normaliseText('1012-0458-0001')).toBe('101204580001')
    expect(normaliseText('0045-0012')).toBe('450012')
    expect(normaliseText('00 12/05')).toBe('1205')
    expect(normaliseText('IC-2608-0001')).toBe(normaliseText('IC26080001'))
    expect(normaliseText('INV-00123')).toBe('123')
    expect(normaliseText('INV 00123')).toBe('123')
    expect(normaliseText('CHQ 004512')).toBe('4512')
    expect(normaliseText('CHQ-004512')).toBe('4512')
  })

  it('strips prefixes only at word starts', () => {
    expect(normaliseText('FT2609ABC')).toBe('2609abc')
    expect(normaliseText('TT26091310')).toBe('26091310')
    expect(normaliseText('Cheque No. 004512')).toBe('4512')
    expect(normaliseText('REF: CHQ 123')).toBe('123')
    expect(normaliseText('POS 652755191601')).toBe('652755191601')
    expect(normaliseText('RCPT-77')).toBe('77')
    expect(normaliseText('REFUND 55')).toBe('refund55')
    expect(normaliseText('POSITION')).toBe('position')
    expect(normaliseText('Rcpt FT2609ABC - Al Noor')).toBe('2609abcalnoor')
  })

  it('uses configured prefixes', () => {
    expect(normaliseText('DEP-0907', ['DEP'])).toBe('907')
    expect(normaliseText('INV-00123', [])).toBe('inv123')
    expect(normaliseText('CHQ 004512', ['chq'])).toBe('4512')
    expect(DEFAULT_REFERENCE_PREFIXES).toEqual(
      expect.arrayContaining(['CHQ', 'CHEQUE', 'FT', 'TT', 'INV', 'REF', 'POS', 'RCPT', 'DD'])
    )
  })

  it('keeps the result non-empty when possible', () => {
    expect(normaliseText('INV')).toBe('inv')
    expect(normaliseText('REF - ')).toBe('ref')
    expect(normaliseText('---')).toBe('---')
    expect(normaliseText('')).toBe('')
    expect(normaliseText('   ')).toBe('')
  })
})

describe('valueOverlap', () => {
  it('measures the share of the smaller column found in the other', () => {
    expect(valueOverlap(['A1', 'A2', 'A3', 'A4'], ['a1', 'A2', 'X', 'Y', 'Z', 'A3'])).toBeCloseTo(0.75)
    expect(valueOverlap(['00102', '00103', 108], ['102', '00108', '00103', '00999'])).toBe(1)
  })

  it('ignores blanks and returns 0 for empty columns', () => {
    expect(valueOverlap([null, '', '  '], ['a'])).toBe(0)
    expect(valueOverlap([], [])).toBe(0)
    expect(valueOverlap(['x', null], ['y'])).toBe(0)
  })

  it('compares numbers to 2 decimals and dates by calendar day', () => {
    expect(valueOverlap([1234.5, 10], [1234.499999, 10])).toBe(1)
    expect(valueOverlap([new Date(2026, 8, 3, 10)], [new Date(2026, 8, 3)])).toBe(1)
  })

  it('mutual mode weights by rows in both directions, so a single repeated value does not count', () => {
    const join: CellValue[] = [new Date(2020, 0, 1), new Date(2021, 1, 2), new Date(2026, 8, 28), new Date(2022, 2, 3)]
    const pay: CellValue[] = [new Date(2026, 8, 28), new Date(2026, 8, 28), new Date(2026, 8, 28), new Date(2026, 8, 28)]
    expect(valueOverlap(join, pay)).toBe(1)
    expect(valueOverlap(join, pay, { mutual: true })).toBeCloseTo(0.25)
    expect(valueOverlap(pay, join, { mutual: true })).toBeCloseTo(0.25)
    expect(valueOverlap(['A1', 'A2', 'A3'], ['a3', 'a2', 'a1', null], { mutual: true })).toBe(1)
    expect(valueOverlap([], ['x'], { mutual: true })).toBe(0)
  })

  it('applies reference normalisation', () => {
    expect(valueOverlap(['CHQ 004512', 'INV-00123'], ['4512', '123', 'zzz'])).toBe(1)
  })

  it('is fast on large columns', () => {
    const a: CellValue[] = Array.from({ length: 60000 }, (_, i) => `EMP-${String(i).padStart(6, '0')}`)
    const b: CellValue[] = Array.from({ length: 60000 }, (_, i) =>
      i % 2 === 0 ? `EMP-${String(i).padStart(6, '0')}` : `X${i}`
    )
    const t0 = performance.now()
    const r = valueOverlap(a, b)
    expect(performance.now() - t0).toBeLessThan(1500)
    expect(r).toBeGreaterThan(0.4)
    expect(r).toBeLessThan(0.6)
  })
})
