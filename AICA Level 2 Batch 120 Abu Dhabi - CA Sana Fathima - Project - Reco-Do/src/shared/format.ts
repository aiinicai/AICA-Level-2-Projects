const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

/** 1234567.5 → "1,234,567.50" */
export function formatAmount(n: number): string {
  return n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

/** 1280000 → "1.28M", 45200 → "45.2K" for compact KPI lines. */
export function formatCompact(n: number): string {
  const abs = Math.abs(n)
  if (abs >= 1e6) return `${+(n / 1e6).toFixed(2)}M`
  if (abs >= 1e3) return `${+(n / 1e3).toFixed(1)}K`
  return formatAmount(n)
}

/** Date → "03-Sep-2026" */
export function formatDate(d: Date): string {
  return `${String(d.getDate()).padStart(2, '0')}-${MONTHS[d.getMonth()]}-${d.getFullYear()}`
}
