import { describe, expect, it } from 'vitest'
import { sheetValue } from '@export/workbook'

describe('long whole numbers in non-amount columns (P5)', () => {
  it('are written as text so Excel keeps every digit', () => {
    expect(sheetValue(4111111111111111)).toBe('4111111111111111')
    expect(sheetValue(123456789012)).toBe('123456789012')
    expect(sheetValue(-123456789012)).toBe('-123456789012')
  })

  it('leaves shorter numbers, decimals, text and dates alone', () => {
    expect(sheetValue(12345678901)).toBe(12345678901)
    expect(sheetValue(123456789012.5)).toBe(123456789012.5)
    expect(sheetValue('INV-1')).toBe('INV-1')
    expect(sheetValue(null)).toBeNull()
    expect(sheetValue(new Date(2026, 8, 1))).toBeInstanceOf(Date)
  })
})
