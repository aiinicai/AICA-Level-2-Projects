import { useMemo } from 'react'
import { Check, CornerDownRight, X } from 'lucide-react'
import type { ReconResult, Suggestion } from '@shared/contracts'
import { formatAmount, formatDate } from '@shared/format'
import { Badge, Button } from '@/components/ui'
import { cn } from '@/lib/cn'
import { lineIndex, lineLabel, shortSide } from './sides'

const SOURCE_TITLE: Record<Suggestion['source'], string> = {
  ai: 'AI suggestion',
  'code-group': 'Sum match',
  'code-partial-ref': 'Partial reference'
}

export interface SuggestionCardProps {
  suggestion: Suggestion
  /** The current result (session.result), used to show each line. */
  result: ReconResult
  onApprove?: (suggestion: Suggestion) => void
  onReject?: (suggestion: Suggestion) => void
  /** Disables the buttons (e.g. while saving, or once the recon is finalised). */
  disabled?: boolean
  className?: string
}

/** The white suggestion card from the Results mockup: header, the lines involved, reasoning, confidence, actions. */
export function SuggestionCard({ suggestion, result, onApprove, onReject, disabled, className }: SuggestionCardProps): React.JSX.Element {
  const cfg = result.config
  const lines = useMemo(() => lineIndex(result), [result])
  const a = shortSide(cfg, 'A')
  const b = shortSide(cfg, 'B')
  const nA = suggestion.aIds.length
  const nB = suggestion.bIds.length
  const shape = `${nA === 1 ? '1' : nA} ${a} : ${nB === 1 ? '1' : nB} ${b}`
  // The single line goes first ("Bank … then ↳ GL, GL, GL"), as in the mockup.
  const [headIds, tailIds] = nA === 1 || nA <= nB ? [suggestion.aIds, suggestion.bIds] : [suggestion.bIds, suggestion.aIds]
  const isAi = suggestion.source === 'ai'
  const tone = suggestion.status === 'accepted' ? 'matched' : suggestion.status === 'rejected' ? 'unmatched' : null

  const row = (id: string, nested: boolean): React.JSX.Element => {
    const l = lines.get(id)
    if (!l) {
      return (
        <li key={id} className="text-[12.5px] text-muted">
          {id} (no longer in this reconciliation)
        </li>
      )
    }
    const { text, party } = lineLabel(cfg, l)
    return (
      <li key={id} className={cn('flex items-baseline gap-1.5 text-[13px] leading-snug', nested ? 'pl-0.5 text-ink' : 'font-semibold text-ink')}>
        {nested && <CornerDownRight size={13} className="shrink-0 translate-y-[2px] text-muted" aria-hidden />}
        <span className="min-w-0 flex-1 truncate" title={[text, party].filter(Boolean).join(' · ')}>
          {shortSide(cfg, l.side)}
          {l.date && <> {formatDate(l.date)}</>}
          {text && <> {text}</>}
          {party && <span className="font-normal text-muted"> · {party}</span>}
        </span>
        {l.amount !== null && <span className="num shrink-0 tabular-nums">{formatAmount(l.amount)}</span>}
      </li>
    )
  }

  return (
    <div className={cn('rounded-xl border border-line bg-white p-4 shadow-sm', className)}>
      <div className="flex items-center justify-between gap-3">
        <div className={cn('text-[11.5px] font-bold tracking-[1.1px] uppercase', isAi ? 'text-ai' : 'text-muted')}>
          {SOURCE_TITLE[suggestion.source]} · {shape}
        </div>
        {tone && (
          <Badge tone={tone} size="sm">
            {suggestion.status === 'accepted' ? 'Approved' : 'Rejected'}
          </Badge>
        )}
      </div>
      <ul className="mt-2.5 space-y-1">
        {headIds.map((id) => row(id, false))}
        {tailIds.map((id) => row(id, true))}
      </ul>
      <p className="mt-2.5 text-[12.5px] leading-relaxed text-ai">
        {suggestion.reason} · confidence {suggestion.confidence}%
      </p>
      {suggestion.status === 'open' && (onApprove || onReject) && (
        <div className="mt-3 flex gap-2">
          {onApprove && (
            <Button size="sm" variant="secondary" className="border-[#BFE5D3] bg-[#E3F4EC] text-matched hover:bg-[#d3eee1]" disabled={disabled} onClick={() => onApprove(suggestion)}>
              <Check size={14} />
              Approve
            </Button>
          )}
          {onReject && (
            <Button size="sm" variant="secondary" className="border-[#F5CACA] bg-[#FDECEC] text-unmatched hover:bg-[#fadcdc]" disabled={disabled} onClick={() => onReject(suggestion)}>
              <X size={14} />
              Reject
            </Button>
          )}
        </div>
      )}
    </div>
  )
}
