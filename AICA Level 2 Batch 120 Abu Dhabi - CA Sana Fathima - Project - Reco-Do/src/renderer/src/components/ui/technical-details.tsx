import { cn } from '@/lib/cn'

/** A collapsed "Technical details" toggle under a plain-English error, for support. Renders nothing without details. */
export function TechnicalDetails({ details, className }: { details: string | null | undefined; className?: string }): React.JSX.Element | null {
  if (!details) return null
  return (
    <details className={cn('mt-2 text-left text-[12px] text-muted', className)}>
      <summary className="cursor-pointer select-none font-semibold hover:text-ink">Technical details</summary>
      <pre className="mt-1.5 max-h-40 overflow-auto rounded-md border border-line bg-[#F7F9FB] p-2 font-mono text-[11.5px] break-all whitespace-pre-wrap">{details}</pre>
    </details>
  )
}
