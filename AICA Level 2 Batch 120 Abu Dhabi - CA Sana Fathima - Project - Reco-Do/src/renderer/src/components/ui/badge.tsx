import { cn } from '@/lib/cn'

export type BadgeTone =
  | 'matched'
  | 'doubtful'
  | 'likely'
  | 'unmatched'
  | 'ai'
  | 'live'
  | 'phase2'
  | 'info'
  | 'neutral'
  | 'teal'

const TONES: Record<BadgeTone, string> = {
  matched: 'bg-[#E3F4EC] text-matched',
  live: 'bg-[#E3F4EC] text-matched',
  doubtful: 'bg-[#FDF1DC] text-doubtful',
  phase2: 'bg-[#FDF1DC] text-doubtful',
  likely: 'bg-[#FDEBDD] text-likely',
  unmatched: 'bg-[#FDECEC] text-unmatched',
  ai: 'bg-[#ECE8FC] text-ai',
  info: 'bg-[#E6F0FC] text-primary',
  neutral: 'bg-[#EEF1F5] text-muted',
  teal: 'bg-[#E2F6F1] text-[#1E8E72]'
}

export interface BadgeProps extends React.ComponentProps<'span'> {
  tone?: BadgeTone
  size?: 'sm' | 'md'
  /** Small leading dot in the tone colour. */
  dot?: boolean
}

/** Pill label. Status tones (matched/doubtful/likely/unmatched/ai) use the same colours everywhere. */
export function Badge({ tone = 'neutral', size = 'md', dot, className, children, ...props }: BadgeProps): React.JSX.Element {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full font-semibold whitespace-nowrap',
        size === 'sm' ? 'px-2 py-[1px] text-[10.5px]' : 'px-2.5 py-0.5 text-[11.5px]',
        TONES[tone],
        className
      )}
      {...props}
    >
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current" />}
      {children}
    </span>
  )
}

/** Text labels for the four match tiers, matching the Results tabs. */
export const TIER_LABEL = { matched: 'Matched', doubtful: 'Doubtful', likely: 'Likely', unmatched: 'Unmatched' } as const
