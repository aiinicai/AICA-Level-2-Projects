import { Progress as ProgressPrimitive } from 'radix-ui'
import { cn } from '@/lib/cn'

export function Spinner({ size = 18, className, label = 'Loading' }: { size?: number; className?: string; label?: string }): React.JSX.Element {
  return (
    <svg
      role="status"
      aria-label={label}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      className={cn('animate-spin text-primary', className)}
    >
      <circle cx="12" cy="12" r="9.5" stroke="currentColor" strokeOpacity="0.2" strokeWidth="3" />
      <path d="M21.5 12A9.5 9.5 0 0 0 12 2.5" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  )
}

export interface ProgressProps {
  /** 0–100. Omit for an indeterminate bar. */
  value?: number | null
  label?: React.ReactNode
  /** Text on the right, e.g. "Page 3 of 6". Defaults to the percentage. */
  detail?: React.ReactNode
  tone?: 'primary' | 'teal' | 'ai'
  className?: string
}

const BAR: Record<NonNullable<ProgressProps['tone']>, string> = { primary: 'bg-primary', teal: 'bg-teal', ai: 'bg-ai' }

export function Progress({ value, label, detail, tone = 'primary', className }: ProgressProps): React.JSX.Element {
  const known = typeof value === 'number' && Number.isFinite(value)
  const pct = known ? Math.max(0, Math.min(100, value)) : 0
  return (
    <div className={cn('w-full', className)}>
      {(label || detail || known) && (
        <div className="mb-1.5 flex items-baseline justify-between gap-3 text-[12.5px]">
          <span className="text-ink">{label}</span>
          <span className="num text-muted">{detail ?? (known ? `${Math.round(pct)}%` : '')}</span>
        </div>
      )}
      <ProgressPrimitive.Root value={known ? pct : null} className="relative h-2 w-full overflow-hidden rounded-full bg-[#E8ECF2]">
        <ProgressPrimitive.Indicator
          className={cn('h-full rounded-full transition-[width] duration-300', BAR[tone], !known && 'animate-[progress-indeterminate_1.4s_ease-in-out_infinite] w-1/3')}
          style={known ? { width: `${pct}%` } : undefined}
        />
      </ProgressPrimitive.Root>
    </div>
  )
}
