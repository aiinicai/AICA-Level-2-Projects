// Formatting, to the convention the spec fixes:
//   ₹ in Lakh / Crore with Indian digit grouping, dates DD-Mmm-YY, times IST.
// Every screen goes through here so no two numbers are ever formatted
// differently.

const CR = 1e7
const L = 1e5

/** ₹ 4,25,00,000 → "₹ 4.25 Cr". Never "M", never "K". */
export function inr(v, { decimals = 2, sign = false, blank = '—' } = {}) {
  if (v === null || v === undefined || Number.isNaN(v)) return blank
  const n = Number(v)
  const s = n < 0 ? '-' : sign && n > 0 ? '+' : ''
  const a = Math.abs(n)
  if (a >= CR) return `${s}₹ ${a / CR === Math.round(a / CR) ? (a / CR).toFixed(0) : (a / CR).toFixed(decimals)} Cr`
  if (a >= L) return `${s}₹ ${(a / L).toFixed(a / L >= 100 ? 0 : decimals)} L`
  if (a === 0) return '₹ 0'
  // Keep the lakh unit down to ₹ 10,000 so a column of figures reads as one
  // scale. Below that, plain rupees are clearer than "0.04 L".
  if (a >= 10_000) return `${s}₹ ${(a / L).toFixed(2)} L`
  return `${s}₹ ${group(Math.round(a))}`
}

/** Compact form for axis ticks and dense tables. */
export function inrShort(v, blank = '—') {
  if (v === null || v === undefined || Number.isNaN(v)) return blank
  const n = Number(v), a = Math.abs(n), s = n < 0 ? '-' : ''
  if (a >= CR) return `${s}${(a / CR).toFixed(a / CR >= 10 ? 1 : 2)}Cr`
  if (a >= L) return `${s}${(a / L).toFixed(a / L >= 10 ? 0 : 1)}L`
  if (a >= 10_000) return `${s}${(a / L).toFixed(2)}L`
  return `${s}${group(Math.round(a))}`
}

/** Indian digit grouping: 12,34,567 — not 1,234,567. */
export function group(n) {
  const s = String(Math.round(Math.abs(n)))
  if (s.length <= 3) return s
  const last3 = s.slice(-3)
  const rest = s.slice(0, -3).replace(/\B(?=(\d{2})+(?!\d))/g, ',')
  return `${rest},${last3}`
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

/** DD-Mmm-YY */
export function d(iso, blank = '—') {
  if (!iso) return blank
  const dt = typeof iso === 'string' ? new Date(iso.slice(0, 10) + 'T00:00:00') : iso
  if (Number.isNaN(dt?.getTime?.())) return blank
  return `${String(dt.getDate()).padStart(2, '0')}-${MONTHS[dt.getMonth()]}-${String(dt.getFullYear()).slice(2)}`
}

/** Mmm-YY */
export function mon(iso, blank = '—') {
  if (!iso) return blank
  const dt = new Date(String(iso).slice(0, 10) + 'T00:00:00')
  if (Number.isNaN(dt.getTime())) return blank
  return `${MONTHS[dt.getMonth()]}-${String(dt.getFullYear()).slice(2)}`
}

/** Timestamps are always IST — the spec says so. */
export function ts(iso, blank = '—') {
  if (!iso) return blank
  const dt = new Date(iso)
  if (Number.isNaN(dt.getTime())) return blank
  const s = dt.toLocaleString('en-IN', {
    timeZone: 'Asia/Kolkata', day: '2-digit', month: 'short',
    hour: '2-digit', minute: '2-digit', hour12: false,
  })
  return `${s} IST`
}

export function pct(v, { decimals = 1, sign = false, blank = '—' } = {}) {
  if (v === null || v === undefined || Number.isNaN(v)) return blank
  const s = sign && v > 0 ? '+' : ''
  return `${s}${Number(v).toFixed(decimals)}%`
}

export function num(v, decimals = 1, blank = '—') {
  if (v === null || v === undefined || Number.isNaN(v)) return blank
  return Number(v).toFixed(decimals)
}

export function months(v, blank = '—') {
  if (v === null || v === undefined) return blank
  return `${Number(v).toFixed(1)} mo`
}

export function days(v, blank = '—') {
  if (v === null || v === undefined) return blank
  return `${Math.round(v)}d`
}

// ---------------------------------------------------------------------------
// Colour. One meaning only:
//   Red = act this week · Amber = watch · Green = within tolerance
//   Grey = data incomplete, don't rely on it
// Never used decoratively. Every status is paired with a word or icon so the
// meaning never rests on hue alone.
// ---------------------------------------------------------------------------
export const STATUS = {
  Red:   { text: 'text-red',   bg: 'bg-red-bg',   border: 'border-red-line',   dot: 'bg-red',   hex: '#b3261e', word: 'Act this week' },
  Amber: { text: 'text-amber', bg: 'bg-amber-bg', border: 'border-amber-line', dot: 'bg-amber', hex: '#a87c00', word: 'Watch' },
  Green: { text: 'text-green', bg: 'bg-green-bg', border: 'border-green-line', dot: 'bg-green', hex: '#0f7a43', word: 'Within tolerance' },
  Grey:  { text: 'text-grey',  bg: 'bg-grey-bg',  border: 'border-grey-line',  dot: 'bg-grey',  hex: '#788699', word: 'Data incomplete' },
}
export const st = (s) => STATUS[s] || STATUS.Grey

/** The one navy hue every data mark uses, plus its ordinal steps. */
export const MARK = {
  main:  '#2c3690',
  light: '#8b98e2',
  pale:  '#dde2f9',
  deep:  '#1e2761',
  // Ordinal ramp for Fixed → Variable → Discretionary (ordered by how
  // controllable the cost is). Validated: monotone L, single hue.
  ordinal: ['#1e2761', '#5566d0', '#a8b3e8'],
  // Diverging poles for waterfalls. Polarity, not status.
  pos: '#0f766e',
  neg: '#6d3fa0',
  grid: '#eef2f7',
  axis: '#cbd5e1',
  floor: '#b3261e',
}

export const cls = (...a) => a.filter(Boolean).join(' ')
