import { describe, expect, it } from 'vitest'
import { detectDateOrder, excelSerialToDate, isDateLike, parseDate } from '@shared/parsing'
import { d } from './helpers'

describe('parseDate', () => {
  it('returns local midnight dates for Date cells', () => {
    const r = parseDate(new Date(2026, 8, 3, 15, 30))
    expect(r).toEqual(d(2026, 9, 3))
    expect(r?.getHours()).toBe(0)
    expect(parseDate(new Date(Number.NaN))).toBeNull()
  })

  it('converts Excel serial numbers only in a plausible range', () => {
    expect(parseDate(46268)).toEqual(d(2026, 9, 3))
    expect(parseDate(46268.75)).toEqual(d(2026, 9, 3))
    expect(parseDate(18264)).toEqual(d(1950, 1, 1))
    expect(parseDate(73050)).toEqual(d(2099, 12, 31))
    expect(parseDate(18263)).toBeNull()
    expect(parseDate(73051)).toBeNull()
    expect(parseDate(1234.5)).toBeNull()
    expect(parseDate(412332.91)).toBeNull()
    expect(excelSerialToDate(Number.NaN)).toBeNull()
  })

  it('reads the common text formats', () => {
    const sep3 = d(2026, 9, 3)
    const inputs = [
      '03/09/2026', '3/9/2026', '3-Sep-2026', '03-SEP-26', '2026-09-03', 'Sep 3, 2026', '03.09.2026',
      '3 September 2026', 'September 3 2026', '3rd Sep 2026', '2026/09/03', '20260903', 'Thu, 3 Sep 2026',
      '2026-09-03T00:00:00', '03/09/2026 14:25', '03-09-26', '  03/09/2026  ', 'Sept 3, 2026'
    ]
    for (const s of inputs) expect(parseDate(s), s).toEqual(sep3)
  })

  it('uses DMY by default and MDY when asked', () => {
    expect(parseDate('04/08/2026')).toEqual(d(2026, 8, 4))
    expect(parseDate('04/08/2026', 'MDY')).toEqual(d(2026, 4, 8))
    expect(parseDate('Sep 3, 2026', 'MDY')).toEqual(d(2026, 9, 3))
  })

  it('falls back to the other order only when the preferred one is impossible', () => {
    expect(parseDate('09/23/2026')).toEqual(d(2026, 9, 23))
    expect(parseDate('23/09/2026', 'MDY')).toEqual(d(2026, 9, 23))
  })

  it('expands two-digit years', () => {
    expect(parseDate('01-Jan-49')).toEqual(d(2049, 1, 1))
    expect(parseDate('01-Jan-50')).toEqual(d(1950, 1, 1))
  })

  it('returns null for invalid dates and non-dates', () => {
    const bad = [
      '31/02/2026', '13/13/2026', '29-Feb-2026', '2026-02-30', '00/01/2026', 'Foo 3, 2026', 'hello',
      '1,234.50', '123456', 'INV-2026-0811', '', '32-Jan-2026'
    ]
    for (const v of bad) expect(parseDate(v), v).toBeNull()
    expect(parseDate(null)).toBeNull()
    expect(parseDate('29-Feb-2028')).toEqual(d(2028, 2, 29))
  })
})

describe('detectDateOrder', () => {
  it('finds DMY when a day is above 12', () => {
    expect(detectDateOrder(['03/09/2026', '18/08/2026', null, 5])).toBe('DMY')
  })
  it('finds MDY when the second part is above 12', () => {
    expect(detectDateOrder(['03/09/2026', '08/18/2026'])).toBe('MDY')
  })
  it('is ambiguous when every value fits both orders', () => {
    expect(detectDateOrder(['03/09/2026', '07/08/2026', '11/08/2026'])).toBe('ambiguous')
  })
  it('is ambiguous on conflicting evidence, but accepts a clear majority', () => {
    expect(detectDateOrder(['18/08/2026', '08/18/2026'])).toBe('ambiguous')
    const many = Array.from({ length: 40 }, (_, i) => `${13 + (i % 15)}/08/2026`)
    expect(detectDateOrder([...many, '08/18/2026'])).toBe('DMY')
  })
  it('defaults to DMY when no value needs an order', () => {
    expect(detectDateOrder([new Date(2026, 8, 3), '3-Sep-2026', '2026-09-03'])).toBe('DMY')
    expect(detectDateOrder([])).toBe('DMY')
  })
})

describe('isDateLike', () => {
  it('recognises Date cells and date text but not numbers', () => {
    expect(isDateLike(new Date(2026, 0, 1))).toBe(true)
    expect(isDateLike('3-Sep-2026')).toBe(true)
    expect(isDateLike(46268)).toBe(false)
    expect(isDateLike('Opening balance')).toBe(false)
  })
})
