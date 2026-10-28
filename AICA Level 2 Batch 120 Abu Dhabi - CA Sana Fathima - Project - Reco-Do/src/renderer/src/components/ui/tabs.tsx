import { Tabs as TabsPrimitive } from 'radix-ui'
import { cn } from '@/lib/cn'

/** Underlined tabs as in the Results screen ("Matched 331 | Doubtful 29 | …"). */
export const Tabs = TabsPrimitive.Root

export function TabsList({ className, ...props }: React.ComponentProps<typeof TabsPrimitive.List>): React.JSX.Element {
  return <TabsPrimitive.List className={cn('flex flex-wrap items-end gap-1 border-b border-line', className)} {...props} />
}

export interface TabsTriggerProps extends React.ComponentProps<typeof TabsPrimitive.Trigger> {
  /** Optional count shown after the label. */
  count?: number | string
  /** Colour of the active underline and text; defaults to primary blue. */
  tone?: 'primary' | 'matched' | 'doubtful' | 'likely' | 'unmatched' | 'ai'
}

const ACTIVE: Record<NonNullable<TabsTriggerProps['tone']>, string> = {
  primary: 'data-[state=active]:border-primary data-[state=active]:text-primary',
  matched: 'data-[state=active]:border-matched data-[state=active]:text-matched',
  doubtful: 'data-[state=active]:border-doubtful data-[state=active]:text-doubtful',
  likely: 'data-[state=active]:border-likely data-[state=active]:text-likely',
  unmatched: 'data-[state=active]:border-unmatched data-[state=active]:text-unmatched',
  ai: 'data-[state=active]:border-ai data-[state=active]:text-ai'
}

export function TabsTrigger({ className, count, tone = 'primary', children, ...props }: TabsTriggerProps): React.JSX.Element {
  return (
    <TabsPrimitive.Trigger
      className={cn(
        '-mb-px inline-flex items-center gap-1.5 border-b-2 border-transparent px-4 pt-1 pb-2.5 text-[14px] whitespace-nowrap text-muted outline-none transition-colors hover:text-ink focus-visible:rounded-t focus-visible:bg-[#EEF4FD] disabled:opacity-50 data-[state=active]:font-semibold',
        ACTIVE[tone],
        className
      )}
      {...props}
    >
      {children}
      {count !== undefined && <span className="num">{count}</span>}
    </TabsPrimitive.Trigger>
  )
}

export function TabsContent({ className, ...props }: React.ComponentProps<typeof TabsPrimitive.Content>): React.JSX.Element {
  return <TabsPrimitive.Content className={cn('pt-4 outline-none', className)} {...props} />
}
