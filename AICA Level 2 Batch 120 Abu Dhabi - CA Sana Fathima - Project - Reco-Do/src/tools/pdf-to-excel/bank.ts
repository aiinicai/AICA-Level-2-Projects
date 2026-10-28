// Bank statement layout: suggest which PDF column feeds Date · Value Date · Description · Reference · Debit · Credit · Balance.

import { headerSimilarity } from '@shared/parsing'
import { BANK_FIELDS, type BankField, type BankMapping } from './types'

const PATTERNS: Record<BankField, RegExp[]> = {
  'Value Date': [/\bvalue\s*date\b/, /\bval(ue)?\.?\s*dt\b/, /\beffective\s*date\b/],
  Date: [/\b(txn|transaction|posting|post|booking|entry|trans)?\s*date\b/, /\bdt\b/],
  Description: [/\b(description|narration|details?|particulars|remarks?|transaction\s*details|memo|narrative)\b/],
  Reference: [/\b(ref(erence)?|cheque|chq|check|instrument|doc(ument)?\s*no|voucher)\b/],
  Debit: [/\b(debit|withdrawals?|dr|payments?|paid\s*out|money\s*out|outflow)\b/],
  Credit: [/\b(credit|deposits?|cr|receipts?|paid\s*in|money\s*in|inflow)\b/],
  Balance: [/\b(balance|bal|running\s*balance|closing\s*balance)\b/]
}

function clean(h: string): string {
  return h.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim()
}

/**
 * Suggests a bank mapping from the PDF's column headers. Each source column is used at most once;
 * fields with no plausible column stay null (they become empty columns).
 */
export function suggestBankMapping(columns: string[]): BankMapping {
  const mapping = Object.fromEntries(BANK_FIELDS.map((f) => [f, null])) as BankMapping
  const used = new Set<number>()
  // Value Date first so "Value Date" is not taken by Date.
  const order: BankField[] = ['Value Date', 'Date', 'Balance', 'Debit', 'Credit', 'Reference', 'Description']
  for (const field of order) {
    let best = -1
    let bestScore = 0
    columns.forEach((col, i) => {
      if (used.has(i)) return
      const h = clean(col)
      if (field === 'Date' && /\bvalue\b/.test(h)) return
      const byPattern = PATTERNS[field].some((re) => re.test(h)) ? 1 : 0
      // Similarity groups treat every "… Date" alike, so Value Date relies on its own patterns only.
      const similar = field !== 'Value Date' && headerSimilarity(col, field) >= 0.8 ? 0.9 : 0
      const score = Math.max(byPattern, similar)
      if (score > bestScore) {
        bestScore = score
        best = i
      }
    })
    if (best >= 0) {
      mapping[field] = columns[best]
      used.add(best)
    }
  }
  return mapping
}

/** Suggestion with the user's overrides applied (only known source columns are accepted). */
export function resolveBankMapping(columns: string[], overrides?: Partial<BankMapping>): BankMapping {
  const m = suggestBankMapping(columns)
  if (!overrides) return m
  for (const f of BANK_FIELDS) {
    if (!(f in overrides)) continue
    const v = overrides[f]
    m[f] = v === null || v === undefined || !columns.includes(v) ? null : v
  }
  return m
}
