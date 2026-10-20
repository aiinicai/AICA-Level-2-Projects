import type { Statement } from '@shared/contracts'
import { formatAmount } from '@shared/format'
import { Card, SectionTitle } from '@/components/ui'
import { cn } from '@/lib/cn'

/** The reconciliation statement with the unexplained difference highlighted. */
export function StatementCard({ statement, currency }: { statement: Statement; currency: string }): React.JSX.Element {
  const counts = statement.kind === 'record-count'
  const fmt = (n: number): string => (counts ? n.toLocaleString('en-US') : formatAmount(n))
  const zero = Math.abs(statement.unexplainedDifference) < 0.005
  return (
    <Card className="p-5">
      <SectionTitle className="mb-1" right={counts ? 'Records' : currency}>
        Reconciliation statement
      </SectionTitle>
      <div className="mb-2 text-[13px] font-semibold text-ink">{statement.title}</div>
      <dl className="text-[12.5px]">
        {statement.lines.map((l, i) => (
          <div
            key={i}
            className={cn('flex items-baseline justify-between gap-3 border-b border-line py-1.5 last:border-b-0', l.isTotal && 'border-t-[1.5px] border-t-ink font-bold')}
          >
            <dt className={cn('min-w-0 [overflow-wrap:anywhere]', l.isTotal ? 'text-ink' : 'text-muted', l.label.startsWith('  ') && 'pl-3')}>{l.label.trim()}</dt>
            <dd className="num shrink-0 text-right whitespace-nowrap text-ink">{fmt(l.value)}</dd>
          </div>
        ))}
      </dl>
      <div
        role="status"
        className={cn(
          'mt-3 flex items-baseline justify-between gap-3 rounded-lg px-3 py-2 text-[13px] font-bold',
          zero ? 'bg-[#E3F4EC] text-matched' : 'bg-[#FDECEC] text-unmatched'
        )}
      >
        <span>{counts ? 'Unexplained count difference' : 'Unexplained difference'}</span>
        <span className="num">{fmt(statement.unexplainedDifference)}</span>
      </div>
    </Card>
  )
}
