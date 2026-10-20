import { formatAmount } from '@shared/format'

/** Amount in its own file's terms as accountants read it: 24,208.56 Dr / 24,208.56 Cr (debit-positive). */
export function Money({ n }: { n: number | null }): React.JSX.Element {
  if (n === null) return <span className="text-muted">—</span>
  if (n === 0) return <span>0.00</span>
  return (
    <span className="whitespace-nowrap">
      {formatAmount(Math.abs(n))}
      <span className="ml-1 text-[10.5px] font-semibold text-muted">{n < 0 ? 'Cr' : 'Dr'}</span>
    </span>
  )
}
