import type { ReconSession } from '@shared/contracts'
import { formatAmount, formatCompact } from '@shared/format'
import { cn } from '@/lib/cn'
import type { ReviewKpis, ReviewTab } from './model'

interface CardDef {
  tab: ReviewTab | 'unmatched'
  label: string
  value: string
  sub: string
  tone: string
}

function money(currency: string, n: number | null): string | null {
  return n === null ? null : `${currency} ${formatAmount(n)}`
}

/** Matched · Doubtful · Likely · Unmatched A/B · AI suggestions, with counts and amounts (counts only without an amount key). */
export function KpiCards({
  session,
  kpis,
  shortA,
  shortB,
  onPick,
  active
}: {
  session: ReconSession
  kpis: ReviewKpis
  shortA: string
  shortB: string
  onPick?: (tab: ReviewTab) => void
  active?: ReviewTab
}): React.JSX.Element {
  const c = session.meta.currency || session.result.config.currency
  const used = session.result.config.keys.filter((k) => k.use).length
  const fail = (n: number): string => (used >= 3 ? ` (${n}/${used})` : '')
  const cards: CardDef[] = [
    { tab: 'matched', label: `Matched${fail(used)}`, value: kpis.matched.count.toLocaleString('en-US'), sub: money(c, kpis.matched.amount) ?? 'No review needed', tone: 'text-matched' },
    { tab: 'doubtful', label: `Doubtful${fail(used - 1)}`, value: kpis.doubtful.count.toLocaleString('en-US'), sub: money(c, kpis.doubtful.amount) ?? 'Review required', tone: 'text-doubtful' },
    { tab: 'likely', label: `Likely${used >= 3 ? ` (1/${used})` : ''}`, value: kpis.likely.count.toLocaleString('en-US'), sub: money(c, kpis.likely.amount) ?? 'Low confidence', tone: 'text-likely' },
    {
      tab: 'unmatched',
      label: 'Unmatched',
      value: `${kpis.unmatchedA.count.toLocaleString('en-US')} / ${kpis.unmatchedB.count.toLocaleString('en-US')}`,
      sub: kpis.hasAmount ? `${shortA} ${formatCompact(kpis.unmatchedA.amount ?? 0)} / ${shortB} ${formatCompact(kpis.unmatchedB.amount ?? 0)}` : `${shortA} / ${shortB}`,
      tone: 'text-unmatched'
    },
    { tab: 'ai', label: 'AI suggestions', value: kpis.aiPending.count.toLocaleString('en-US'), sub: kpis.aiPending.count > 0 ? 'Pending approval' : 'None pending', tone: 'text-ai' }
  ]
  return (
    <div className="mb-5 grid grid-cols-2 gap-3.5 @2xl/main:grid-cols-3 @mid/main:grid-cols-5">
      {cards.map((card) => {
        const tab: ReviewTab = card.tab === 'unmatched' ? 'unmatchedA' : card.tab
        const isActive = active !== undefined && (active === tab || (card.tab === 'unmatched' && active === 'unmatchedB'))
        const body = (
          <>
            <div className="text-[11.5px] font-bold tracking-[1px] text-muted uppercase">{card.label}</div>
            <div data-kpi-value className={cn('num mt-1 text-[28px] leading-tight font-bold', card.tone)}>
              {card.value}
            </div>
            <div className="num mt-0.5 text-[12.5px] text-ink @wide/main:truncate" title={card.sub}>
              {card.sub}
            </div>
          </>
        )
        const cls = cn('rounded-xl border bg-white px-4 py-3.5 text-left', isActive ? 'border-primary ring-1 ring-primary/30' : 'border-line')
        return onPick ? (
          <button key={card.label} type="button" data-testid={`kpi-${card.tab}`} className={cn(cls, 'outline-none hover:border-primary/60 focus-visible:ring-2 focus-visible:ring-primary/40')} onClick={() => onPick(tab)}>
            {body}
          </button>
        ) : (
          <div key={card.label} className={cls} data-testid={`kpi-${card.tab}`}>
            {body}
          </div>
        )
      })}
    </div>
  )
}
