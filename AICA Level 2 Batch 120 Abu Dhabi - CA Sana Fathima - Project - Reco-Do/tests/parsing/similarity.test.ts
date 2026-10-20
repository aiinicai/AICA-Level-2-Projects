import { describe, expect, it } from 'vitest'
import { headerSimilarity, levenshtein } from '@shared/parsing'

describe('levenshtein', () => {
  it('computes edit distance', () => {
    expect(levenshtein('kitten', 'sitting')).toBe(3)
    expect(levenshtein('', 'abc')).toBe(3)
    expect(levenshtein('same', 'same')).toBe(0)
  })
})

describe('headerSimilarity', () => {
  it('scores identical headers 1 regardless of case, punctuation and currency', () => {
    expect(headerSimilarity('Debit', 'debit')).toBe(1)
    expect(headerSimilarity('Debit (AED)', 'Debit')).toBe(1)
    expect(headerSimilarity('Reference No.', 'reference no')).toBe(1)
  })

  it('treats abbreviations as the same words', () => {
    expect(headerSimilarity('Txn Date', 'Transaction Date')).toBeGreaterThanOrEqual(0.9)
    expect(headerSimilarity('Ref No', 'Reference Number')).toBeGreaterThanOrEqual(0.9)
  })

  it('uses the synonym groups', () => {
    const pairs: Array<[string, string]> = [
      ['Value Date', 'Posting Date'],
      ['Txn Date', 'Pay Date'],
      ['Reference', 'Narration'],
      ['Remarks', 'Description'],
      ['Cheque No', 'Reference No'],
      ['Invoice No', 'Doc No'],
      ['Debit', 'Credit'],
      ['Withdrawals', 'Dr'],
      ['Net Pay', 'Amount'],
      ['Customer', 'Party'],
      ['Supplier', 'Vendor'],
      ['Employee Name', 'Name'],
      ['Emp ID', 'Employee No'],
      ['Staff No', 'Employee ID']
    ]
    for (const [a, b] of pairs) expect(headerSimilarity(a, b), `${a} ~ ${b}`).toBeGreaterThanOrEqual(0.8)
  })

  it('gives partial credit when a longer header contains a group word', () => {
    expect(headerSimilarity('Supplier Inv / Ref', 'Reference')).toBeGreaterThanOrEqual(0.7)
    expect(headerSimilarity('Join Date', 'Date')).toBeGreaterThanOrEqual(0.7)
  })

  it('prefers the exact header over a synonym', () => {
    expect(headerSimilarity('Debit', 'Debit')).toBeGreaterThan(headerSimilarity('Debit', 'Credit'))
  })

  it('scores unrelated headers low', () => {
    expect(headerSimilarity('Department', 'IBAN')).toBeLessThan(0.4)
    expect(headerSimilarity('Status', 'Posting Date')).toBeLessThan(0.4)
    expect(headerSimilarity('Debit', 'Posting Date')).toBeLessThan(0.4)
    expect(headerSimilarity('Employee No', 'Employee Name')).toBeLessThan(0.8)
  })

  it('returns 0 for blank headers and stays within 0..1', () => {
    expect(headerSimilarity('', 'Date')).toBe(0)
    expect(headerSimilarity('  ', '')).toBe(0)
    const s = headerSimilarity('Amount', 'Amt')
    expect(s).toBeGreaterThan(0.8)
    expect(s).toBeLessThanOrEqual(1)
  })

  it('is symmetric', () => {
    expect(headerSimilarity('Emp ID', 'Employee No')).toBe(headerSimilarity('Employee No', 'Emp ID'))
    expect(headerSimilarity('Supplier Inv / Ref', 'Remarks')).toBe(headerSimilarity('Remarks', 'Supplier Inv / Ref'))
  })
})
