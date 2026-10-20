import { cn } from '@/lib/cn'

export function Card({ className, ...props }: React.ComponentProps<'div'>): React.JSX.Element {
  return <div className={cn('rounded-xl border border-line bg-white', className)} {...props} />
}

/** Page title style: slightly smaller when the content area is narrow. */
export const PAGE_TITLE = 'text-[22px] font-bold tracking-tight @wide/main:text-[25px]'

/** Small uppercase section heading ("SOURCE PDF", "MATCH KEYS"). */
export function SectionTitle({ className, children, right }: { className?: string; children: React.ReactNode; right?: React.ReactNode }): React.JSX.Element {
  const title = <div className={cn('text-[11.5px] font-bold tracking-[1.2px] text-muted uppercase', !right && className)}>{children}</div>
  if (!right) return title
  return (
    <div className={cn('flex items-baseline justify-between gap-4', className)}>
      {title}
      <div className="text-[12.5px] text-muted">{right}</div>
    </div>
  )
}

export function PageHeader({
  title,
  subtitle,
  right,
  className
}: {
  title: React.ReactNode
  subtitle?: React.ReactNode
  right?: React.ReactNode
  className?: string
}): React.JSX.Element {
  return (
    // In a narrow window the right-hand actions move below the title instead of squeezing it.
    <div className={cn('mb-5 flex flex-wrap items-start justify-between gap-x-6 gap-y-3', className)}>
      <div className="min-w-0 flex-[1_1_24rem]">
        <h1 className={PAGE_TITLE}>{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-muted">{subtitle}</p>}
      </div>
      {right && <div className="ml-auto flex shrink-0 flex-wrap items-center justify-end gap-2.5">{right}</div>}
    </div>
  )
}

export interface KeyValueItem {
  label: React.ReactNode
  value: React.ReactNode
  /** Right-align and use tabular figures (for amounts and counts). */
  numeric?: boolean
  /** Bold, with a top rule (totals). */
  total?: boolean
  tone?: 'default' | 'matched' | 'doubtful' | 'likely' | 'unmatched' | 'ai' | 'muted'
}

const KV_TONE: Record<NonNullable<KeyValueItem['tone']>, string> = {
  default: 'text-ink',
  matched: 'text-matched',
  doubtful: 'text-doubtful',
  likely: 'text-likely',
  unmatched: 'text-unmatched',
  ai: 'text-ai',
  muted: 'text-muted'
}

/** Label / value rows (summaries, statements, file details). */
export function KeyValue({ items, className, dense }: { items: KeyValueItem[]; className?: string; dense?: boolean }): React.JSX.Element {
  return (
    <dl className={cn('text-[13.5px]', className)}>
      {items.map((it, i) => (
        <div
          key={i}
          className={cn(
            'flex items-baseline justify-between gap-6 border-b border-line last:border-b-0',
            dense ? 'py-1.5' : 'py-2.5',
            it.total && 'border-t-[1.5px] border-t-ink font-bold'
          )}
        >
          <dt className={cn('min-w-0 [overflow-wrap:anywhere]', it.total ? 'text-ink' : 'text-muted')}>{it.label}</dt>
          <dd className={cn('min-w-0 text-right', it.numeric && 'num whitespace-nowrap', KV_TONE[it.tone ?? 'default'])}>{it.value}</dd>
        </div>
      ))}
    </dl>
  )
}
