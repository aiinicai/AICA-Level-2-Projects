import { useMemo, useRef, useState } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'
import { Check, ChevronDown, ChevronRight, StickyNote, Unlink, X } from 'lucide-react'
import type { EngineLine, MatchKey, MatchPair, ReconConfig } from '@shared/contracts'
import { formatAmount, formatCompact } from '@shared/format'
import { Badge, Button, Checkbox, Tooltip } from '@/components/ui'
import { cn } from '@/lib/cn'
import { cellText, rowLabel, type DisplayColumn } from './model'
import { Money } from './Money'

export interface PairActions {
  onAccept?: (p: MatchPair) => void
  onReject?: (p: MatchPair) => void
  onUnmatch?: (p: MatchPair) => void
  onNote?: (p: MatchPair) => void
}

const FLAG_TEXT: Record<MatchPair['flags'][number], string> = {
  transposition: 'Possible transposition',
  'bank-charge': 'Possible bank charge',
  rounding: 'Rounding',
  'multiple-candidates': 'Multiple identical candidates'
}

function keyShort(k: MatchKey): string {
  const n = k.name.trim()
  if (/^amount$/i.test(n)) return 'Amt'
  if (/^reference$/i.test(n)) return 'Ref'
  return n.length > 7 ? `${n.slice(0, 6)}…` : n
}

function SideCell({ lines, cols }: { lines: EngineLine[]; cols: DisplayColumn[] }): React.JSX.Element {
  const first = lines[0]
  if (!first) return <span className="text-muted">—</span>
  const keyCols = cols.filter((c) => c.kind !== 'date')
  const dateCol = cols.find((c) => c.kind === 'date')
  const main = keyCols.map((c) => cellText(first.values[c.column])).filter(Boolean)
  const primary = main[0] ?? ''
  const secondary = [dateCol ? cellText(first.values[dateCol.column]) : '', ...main.slice(1)].filter(Boolean).join(' · ')
  return (
    <div className="min-w-0 leading-tight">
      <div className="truncate font-medium text-ink" title={primary}>
        {primary || <span className="text-muted">(blank)</span>}
        {lines.length > 1 && <span className="ml-1 text-[11.5px] font-semibold text-primary">+{lines.length - 1} more</span>}
      </div>
      <div className="truncate text-[12px] text-muted" title={secondary}>
        {secondary}
      </div>
    </div>
  )
}

function amountOf(lines: EngineLine[]): number | null {
  let t = 0
  let any = false
  for (const l of lines) {
    if (l.amount !== null) {
      t += l.amount
      any = true
    }
  }
  return any ? Math.round(t * 100) / 100 : null
}

function KeyMark({ pair, k }: { pair: MatchPair; k: MatchKey }): React.JSX.Element {
  const r = pair.keyResults.find((x) => x.keyId === k.id)
  if (!r) return <span className="text-muted">·</span>
  let extra = ''
  if (!r.pass) {
    if (k.type === 'date' && pair.dateDifferenceDays !== null) extra = `${Math.abs(pair.dateDifferenceDays)}d`
    else if (k.type === 'amount' && pair.amountDifference !== null) extra = formatCompact(Math.abs(pair.amountDifference))
  }
  const label = `${k.name}: ${r.pass ? 'agrees' : 'differs'}${r.detail ? ` (${r.detail})` : ''}`
  return (
    <Tooltip content={label}>
      <span tabIndex={0} aria-label={label} className={cn('inline-flex flex-col items-center leading-none outline-none focus-visible:ring-2 focus-visible:ring-primary/40', r.pass ? 'text-matched' : 'text-unmatched')}>
        {r.pass ? <Check size={15} strokeWidth={2.6} /> : <X size={15} strokeWidth={2.6} />}
        {extra && <span className="num mt-0.5 text-[10.5px] font-semibold">{extra}</span>}
      </span>
    </Tooltip>
  )
}

function LineDetail({ title, lines, cols, hasAmount }: { title: string; lines: EngineLine[]; cols: DisplayColumn[]; hasAmount: boolean }): React.JSX.Element {
  return (
    <div className="min-w-0 flex-1">
      <div className="mb-1 truncate text-[11.5px] font-bold tracking-[0.8px] text-muted uppercase" title={title}>
        {title}
      </div>
      <table className="w-full table-fixed border-collapse text-[12px]">
        <thead>
          <tr className="text-left text-muted">
            <th className="w-[58px] py-0.5 pr-2 font-semibold">Row</th>
            {cols.map((c) => (
              <th key={c.column} className="truncate py-0.5 pr-2 font-semibold" title={c.label}>
                {c.label}
              </th>
            ))}
            {hasAmount && <th className="w-[96px] py-0.5 text-right font-semibold">Amount</th>}
          </tr>
        </thead>
        <tbody>
          {lines.map((l) => (
            <tr key={l.id} className="border-t border-line">
              <td className="num py-1 pr-2 text-muted">{rowLabel(l.id).replace('row ', '')}</td>
              {cols.map((c) => (
                <td key={c.column} className="truncate py-1 pr-2" title={cellText(l.values[c.column])}>
                  {cellText(l.values[c.column])}
                </td>
              ))}
              {hasAmount && (
                <td className="num py-1 text-right">
                  <Money n={l.amount} />
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/** Virtualised pair list: both sides side by side, ✓/✗ per key, difference, reason (hover and expandable), actions. */
export function PairTable({
  pairs,
  config,
  idx,
  colsA,
  colsB,
  nameA,
  nameB,
  shortA,
  shortB,
  hasAmount,
  selected,
  onSelectedChange,
  actions,
  locked,
  height,
  empty
}: {
  pairs: MatchPair[]
  config: ReconConfig
  idx: Map<string, EngineLine>
  colsA: DisplayColumn[]
  colsB: DisplayColumn[]
  nameA: string
  nameB: string
  shortA: string
  shortB: string
  hasAmount: boolean
  selected: ReadonlySet<string>
  onSelectedChange: (next: Set<string>) => void
  actions: PairActions
  locked: boolean
  height: number
  empty: React.ReactNode
}): React.JSX.Element {
  const keys = useMemo(() => config.keys.filter((k) => k.use), [config.keys])
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const scrollRef = useRef<HTMLDivElement>(null)
  const virtualizer = useVirtualizer({
    count: pairs.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: (i) => (expanded.has(pairs[i]?.id) ? 230 : 54),
    overscan: 10,
    getItemKey: (i) => pairs[i]?.id ?? i
  })
  const selectable = !locked
  const template = [
    selectable ? '34px' : null,
    '26px',
    'minmax(120px,1fr)',
    hasAmount ? '112px' : null,
    'minmax(120px,1fr)',
    hasAmount ? '112px' : null,
    ...keys.map(() => '46px'),
    hasAmount ? '82px' : null,
    locked ? '44px' : '112px'
  ]
    .filter(Boolean)
    .join(' ')

  const allSelected = pairs.length > 0 && pairs.every((p) => selected.has(p.id))
  const someSelected = pairs.some((p) => selected.has(p.id))
  const toggle = (id: string): void => {
    const next = new Set(selected)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    onSelectedChange(next)
  }
  const toggleExpand = (id: string): void =>
    setExpanded((s) => {
      const n = new Set(s)
      if (n.has(id)) n.delete(id)
      else n.add(id)
      return n
    })

  return (
    <div ref={scrollRef} className="relative overflow-auto rounded-lg border border-line bg-white" style={{ height }} role="table" aria-label="Matched pairs" aria-rowcount={pairs.length + 1}>
      <div className="min-w-[760px]">
        <div role="row" className="sticky top-0 z-10 grid items-center gap-x-2 border-b border-line bg-[#F6F8FB] px-2 py-2 text-[12px] font-semibold text-ink" style={{ gridTemplateColumns: template }}>
          {selectable && (
            <span role="columnheader" className="flex justify-center">
              <Checkbox
                aria-label={allSelected ? 'Clear selection' : 'Select all rows'}
                checked={allSelected ? true : someSelected ? 'indeterminate' : false}
                disabled={pairs.length === 0}
                onCheckedChange={() => onSelectedChange(allSelected ? new Set() : new Set(pairs.map((p) => p.id)))}
              />
            </span>
          )}
          <span role="columnheader">
            <span className="sr-only">Details</span>
          </span>
          <span role="columnheader" className="truncate" title={nameA}>
            {shortA}
          </span>
          {hasAmount && (
            <span role="columnheader" className="text-right">
              {shortA} amt
            </span>
          )}
          <span role="columnheader" className="truncate" title={nameB}>
            {shortB}
          </span>
          {hasAmount && (
            <span role="columnheader" className="text-right">
              {shortB} amt
            </span>
          )}
          {keys.map((k) => (
            <span key={k.id} role="columnheader" className="truncate text-center" title={k.name}>
              {keyShort(k)}
            </span>
          ))}
          {hasAmount && (
            <span role="columnheader" className="text-right">
              Diff.
            </span>
          )}
          <span role="columnheader" className="text-center">
            Action
          </span>
        </div>

        {pairs.length === 0 ? (
          <div className="px-4 py-12 text-center text-[13px] text-muted">{empty}</div>
        ) : (
          <div role="rowgroup" className="relative" style={{ height: virtualizer.getTotalSize() }}>
            {virtualizer.getVirtualItems().map((v) => {
              const p = pairs[v.index]
              const linesA = p.aIds.map((id) => idx.get(id)).filter((l): l is EngineLine => !!l)
              const linesB = p.bIds.map((id) => idx.get(id)).filter((l): l is EngineLine => !!l)
              const isOpen = expanded.has(p.id)
              const isSel = selected.has(p.id)
              const canDecide = !locked && p.status === 'open' && p.tier !== 'matched'
              return (
                <div
                  key={v.key}
                  data-index={v.index}
                  ref={virtualizer.measureElement}
                  role="row"
                  aria-rowindex={v.index + 2}
                  aria-selected={selectable ? isSel : undefined}
                  className={cn('absolute top-0 left-0 w-full border-b border-[#EEF1F5] text-[13px]', isSel && 'bg-[#EEF4FD]')}
                  style={{ transform: `translateY(${v.start}px)` }}
                >
                  <div className="grid min-h-[53px] items-center gap-x-2 px-2 py-1.5" style={{ gridTemplateColumns: template }} title={p.reason}>
                    {selectable && (
                      <span role="cell" className="flex justify-center">
                        <Checkbox aria-label="Select pair" checked={isSel} onCheckedChange={() => toggle(p.id)} />
                      </span>
                    )}
                    <span role="cell">
                      <button
                        type="button"
                        aria-expanded={isOpen}
                        aria-label={isOpen ? 'Hide details' : 'Show details and reason'}
                        onClick={() => toggleExpand(p.id)}
                        className="grid h-6 w-6 place-items-center rounded text-muted outline-none hover:bg-[#EEF1F5] hover:text-ink focus-visible:ring-2 focus-visible:ring-primary/40"
                      >
                        {isOpen ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
                      </button>
                    </span>
                    <span role="cell" className="min-w-0">
                      <SideCell lines={linesA} cols={colsA} />
                    </span>
                    {hasAmount && (
                      <span role="cell" className="num text-right">
                        <Money n={amountOf(linesA)} />
                      </span>
                    )}
                    <span role="cell" className="min-w-0">
                      <SideCell lines={linesB} cols={colsB} />
                    </span>
                    {hasAmount && (
                      <span role="cell" className="num text-right">
                        <Money n={amountOf(linesB)} />
                      </span>
                    )}
                    {keys.map((k) => (
                      <span key={k.id} role="cell" className="flex justify-center">
                        <KeyMark pair={p} k={k} />
                      </span>
                    ))}
                    {hasAmount && (
                      <span role="cell" className={cn('num text-right', p.amountDifference ? 'font-semibold text-unmatched' : 'text-muted')}>
                        {p.amountDifference === null ? '—' : formatAmount(p.amountDifference)}
                      </span>
                    )}
                    <span role="cell" className="flex items-center justify-end gap-1">
                      {canDecide && actions.onAccept && (
                        <Tooltip content="Accept: move to Matched">
                          <Button size="icon-sm" variant="secondary" className="border-[#BFE5D3] bg-[#E3F4EC] text-matched hover:bg-[#d3eee1]" aria-label="Accept" onClick={() => actions.onAccept?.(p)}>
                            <Check size={14} />
                          </Button>
                        </Tooltip>
                      )}
                      {canDecide && actions.onReject && (
                        <Tooltip content="Reject: split back to Unmatched">
                          <Button size="icon-sm" variant="secondary" className="border-[#F5CACA] bg-[#FDECEC] text-unmatched hover:bg-[#fadcdc]" aria-label="Reject" onClick={() => actions.onReject?.(p)}>
                            <X size={14} />
                          </Button>
                        </Tooltip>
                      )}
                      {!locked && p.tier === 'matched' && actions.onUnmatch && (
                        <Tooltip content="Unmatch: return both sides to Unmatched">
                          <Button size="icon-sm" variant="ghost" aria-label="Unmatch" onClick={() => actions.onUnmatch?.(p)}>
                            <Unlink size={14} />
                          </Button>
                        </Tooltip>
                      )}
                      {actions.onNote && (
                        <Tooltip content={p.note ? `Note: ${p.note}` : 'Add note'}>
                          <Button size="icon-sm" variant="ghost" aria-label={p.note ? 'Edit note' : 'Add note'} disabled={locked} onClick={() => actions.onNote?.(p)} className={cn(p.note && 'text-doubtful')}>
                            <StickyNote size={14} />
                          </Button>
                        </Tooltip>
                      )}
                    </span>
                  </div>
                  {isOpen && (
                    <div className="mx-2 mb-2.5 rounded-lg bg-[#F7F9FB] px-3.5 py-3">
                      <div className="mb-2 flex flex-wrap items-center gap-1.5 text-[12.5px]">
                        <span className="font-semibold text-ink">Reason:</span>
                        <span className="text-ink">{p.reason}</span>
                        {p.flags.map((f) => (
                          <Badge key={f} tone="doubtful" size="sm">
                            {FLAG_TEXT[f]}
                          </Badge>
                        ))}
                        {p.label && (
                          <Badge tone={p.origin === 'ai' ? 'ai' : 'matched'} size="sm">
                            {p.label}
                          </Badge>
                        )}
                        {p.confidence !== undefined && <span className="text-muted">confidence {p.confidence}%</span>}
                      </div>
                      {p.note && (
                        <div className="mb-2 text-[12.5px]">
                          <span className="font-semibold">Note:</span> {p.note}
                        </div>
                      )}
                      <div className="flex flex-col gap-4 lg:flex-row">
                        <LineDetail title={nameA} lines={linesA} cols={colsA} hasAmount={hasAmount} />
                        <LineDetail title={nameB} lines={linesB} cols={colsB} hasAmount={hasAmount} />
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
