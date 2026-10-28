// Header-name similarity used to auto-suggest column pairs (Map & Rules).

/** Synonym groups from the master prompt. Terms are compared after header normalisation. */
const SYNONYM_GROUPS: Record<string, string[]> = {
  date: ['date', 'txn date', 'value date', 'posting date', 'transaction date', 'pay date', 'trans date', 'doc date', 'invoice date', 'entry date', 'book date'],
  reference: [
    'reference', 'ref', 'reference no', 'ref no', 'doc no', 'document no', 'remarks', 'narration', 'description',
    'particulars', 'cheque no', 'chq no', 'invoice no', 'inv no', 'details', 'voucher no', 'invoice ref'
  ],
  amount: ['amount', 'debit', 'credit', 'dr', 'cr', 'withdrawals', 'withdrawal', 'deposits', 'deposit', 'net pay', 'net amount', 'value', 'amt'],
  party: ['party', 'customer', 'supplier', 'vendor', 'name', 'employee name', 'customer name', 'supplier name', 'vendor name', 'party name', 'counterparty', 'payee', 'beneficiary'],
  id: ['emp id', 'employee no', 'employee id', 'staff no', 'emp no', 'staff id', 'employee code', 'emp code', 'employee number', 'staff number']
}

/** Words that, inside a longer header, point to a group ("Supplier Inv / Ref" → reference). */
const GROUP_TOKENS: Record<string, string[]> = {
  date: ['date', 'dated'],
  reference: ['reference', 'ref', 'narration', 'description', 'particulars', 'remarks', 'cheque', 'chq', 'invoice', 'inv', 'details'],
  amount: ['amount', 'amt', 'debit', 'credit', 'dr', 'cr', 'withdrawal', 'withdrawals', 'deposit', 'deposits'],
  party: ['party', 'customer', 'supplier', 'vendor', 'payee', 'beneficiary', 'counterparty'],
  id: []
}

const ABBREVIATIONS: Record<string, string> = {
  txn: 'transaction',
  trx: 'transaction',
  trans: 'transaction',
  ref: 'reference',
  refs: 'reference',
  no: 'number',
  num: 'number',
  nbr: 'number',
  amt: 'amount',
  emp: 'employee',
  inv: 'invoice',
  doc: 'document',
  desc: 'description',
  qty: 'quantity',
  acct: 'account',
  acc: 'account',
  ac: 'account',
  chq: 'cheque',
  check: 'cheque',
  dt: 'date',
  bal: 'balance',
  cust: 'customer',
  supp: 'supplier',
  vend: 'vendor',
  dept: 'department'
}

/** Currency codes and similar noise dropped from headers ("Debit (AED)" → "debit"). */
const NOISE_TOKENS = new Set(['aed', 'usd', 'eur', 'gbp', 'sar', 'inr', 'omr', 'qar', 'kwd', 'bhd', 'the', 'of'])

function cleanHeader(h: string): string {
  return String(h ?? '')
    .toLowerCase()
    .replace(/a\/c/g, 'account')
    .replace(/[^a-z0-9]+/g, ' ')
    .split(' ')
    .filter((t) => t !== '' && !NOISE_TOKENS.has(t))
    .join(' ')
}

function tokens(h: string): string[] {
  return cleanHeader(h)
    .split(' ')
    .filter((t) => t !== '')
    .map((t) => ABBREVIATIONS[t] ?? t)
}

/** Levenshtein distance with an early exit when it exceeds `max`. */
export function levenshtein(a: string, b: string, max = Infinity): number {
  if (a === b) return 0
  if (a.length === 0) return b.length
  if (b.length === 0) return a.length
  if (Math.abs(a.length - b.length) > max) return max + 1
  let prev = new Array<number>(b.length + 1)
  let cur = new Array<number>(b.length + 1)
  for (let j = 0; j <= b.length; j++) prev[j] = j
  for (let i = 1; i <= a.length; i++) {
    cur[0] = i
    let rowMin = cur[0]
    const ca = a.charCodeAt(i - 1)
    for (let j = 1; j <= b.length; j++) {
      const cost = ca === b.charCodeAt(j - 1) ? 0 : 1
      cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
      if (cur[j] < rowMin) rowMin = cur[j]
    }
    if (rowMin > max) return max + 1
    ;[prev, cur] = [cur, prev]
  }
  return prev[b.length]
}

function ratio(a: string, b: string): number {
  const len = Math.max(a.length, b.length)
  if (len === 0) return 1
  return 1 - levenshtein(a, b) / len
}

function tokenSimilarity(a: string, b: string): number {
  if (a === b) return 1
  if (a.length >= 3 && b.length >= 3 && (a.startsWith(b) || b.startsWith(a))) return 0.85
  const r = ratio(a, b)
  return r >= 0.75 ? r : 0
}

/** Soft Dice coefficient over tokens: each token pairs with its best match on the other side. */
function tokenScore(ta: string[], tb: string[]): number {
  if (ta.length === 0 || tb.length === 0) return 0
  const used = new Array<boolean>(tb.length).fill(false)
  let total = 0
  for (const x of ta) {
    let best = 0
    let bestJ = -1
    for (let j = 0; j < tb.length; j++) {
      if (used[j]) continue
      const s = tokenSimilarity(x, tb[j])
      if (s > best) {
        best = s
        bestJ = j
      }
    }
    if (bestJ >= 0) {
      used[bestJ] = true
      total += best
    }
  }
  return (2 * total) / (ta.length + tb.length)
}

const NORMALISED_GROUPS: Array<{ group: string; terms: Set<string> }> = Object.entries(SYNONYM_GROUPS).map(
  ([group, terms]) => ({ group, terms: new Set(terms.map((t) => tokens(t).join(' '))) })
)

/** Group membership: strength 1 for an exact synonym, 0.75 for a header that contains a group word. */
function groupsOf(h: string): Map<string, number> {
  const out = new Map<string, number>()
  const tk = tokens(h)
  const joined = tk.join(' ')
  for (const { group, terms } of NORMALISED_GROUPS) {
    if (terms.has(joined)) out.set(group, 1)
  }
  if (out.size > 0) return out
  const rawTokens = new Set(cleanHeader(h).split(' '))
  for (const t of tk) rawTokens.add(t)
  for (const [group, words] of Object.entries(GROUP_TOKENS)) {
    if (words.some((w) => rawTokens.has(w))) out.set(group, 0.75)
  }
  return out
}

/**
 * Similarity (0..1) between two column headers: the better of a token/Levenshtein score and the synonym
 * groups (date, reference, amount, party, id). Identical headers score 1; two synonyms of one group 0.9.
 */
export function headerSimilarity(a: string, b: string): number {
  const ca = cleanHeader(a)
  const cb = cleanHeader(b)
  if (ca === '' || cb === '') return 0
  if (ca === cb) return 1
  const ta = tokens(a)
  const tb = tokens(b)
  if (ta.join(' ') === tb.join(' ')) return 0.97

  const lexical = Math.max(tokenScore(ta, tb), ratio(ta.join(''), tb.join('')) * 0.9)

  let synonym = 0
  const ga = groupsOf(a)
  const gb = groupsOf(b)
  for (const [group, sa] of ga) {
    const sb = gb.get(group)
    if (sb === undefined) continue
    const s = sa === 1 && sb === 1 ? 0.9 : sa === 1 || sb === 1 ? 0.8 : 0.7
    if (s > synonym) synonym = s
  }
  return Math.min(1, Math.max(lexical, synonym))
}
