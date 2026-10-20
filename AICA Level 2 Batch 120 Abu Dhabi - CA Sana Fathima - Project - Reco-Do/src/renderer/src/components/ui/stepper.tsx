import { Check } from 'lucide-react'
import { cn } from '@/lib/cn'

export interface StepItem {
  title: string
  /** Second line, e.g. "Pick columns to match" or "Both files read". */
  subtitle?: string
  disabled?: boolean
}

export interface StepperProps {
  steps: StepItem[]
  /** 0-based index of the current step. */
  current: number
  /** Indices of finished steps (default: every step before `current`). */
  completed?: number[]
  /** When given, finished and current steps become buttons. */
  onStepClick?: (index: number) => void
  className?: string
}

/** The five-card wizard header from the mockups: "1. Upload ✓ | 2. Map & rules | …". */
export function Stepper({ steps, current, completed, onStepClick, className }: StepperProps): React.JSX.Element {
  const done = new Set(completed ?? steps.map((_, i) => i).filter((i) => i < current))
  return (
    <ol className={cn('mb-5 grid gap-2 @mid/main:gap-3', className)} style={{ gridTemplateColumns: `repeat(${steps.length}, minmax(0, 1fr))` }}>
      {steps.map((s, i) => {
        const isCurrent = i === current
        const isDone = done.has(i) && !isCurrent
        const clickable = !!onStepClick && !s.disabled && (isDone || isCurrent)
        const body = (
          <>
            <div className="flex items-center gap-1 text-[13.5px] leading-snug font-bold text-ink @mid/main:text-[15px]">
              {i + 1}. {s.title}
              {isDone && <Check size={15} strokeWidth={3} className="shrink-0 text-ink" aria-label="done" />}
            </div>
            {s.subtitle && <div className="mt-0.5 truncate text-[12.5px] text-muted @mid/main:text-[13px]">{s.subtitle}</div>}
          </>
        )
        const classes = cn(
          'block h-full w-full rounded-xl border bg-white px-3 py-2.5 text-left transition-colors @mid/main:px-4 @mid/main:py-3',
          isCurrent && 'border-2 border-primary bg-[#EEF4FD] px-[11px] py-[9px] @mid/main:px-[15px] @mid/main:py-[11px]',
          isDone && 'border-[#A9DCCB]',
          !isCurrent && !isDone && 'border-line',
          s.disabled && 'opacity-60',
          clickable && 'cursor-pointer outline-none hover:border-primary/60 focus-visible:ring-2 focus-visible:ring-primary/40'
        )
        return (
          <li key={i} aria-current={isCurrent ? 'step' : undefined}>
            {clickable ? (
              <button type="button" className={classes} onClick={() => onStepClick(i)}>
                {body}
              </button>
            ) : (
              <div className={classes}>{body}</div>
            )}
          </li>
        )
      })}
    </ol>
  )
}
