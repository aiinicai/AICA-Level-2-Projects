import { useMemo } from 'react'
import { Plus, Trash2 } from 'lucide-react'
import type { ColumnType, MatchKey, ReconConfig, TextRule, Tolerance } from '@shared/contracts'
import { Button, Checkbox, Input, Select, Tooltip, type SelectOption } from '@/components/ui'
import { cn } from '@/lib/cn'
import { addKey, changeKeyType, layoutLabel, removeKey, syncAmountKey, TYPE_LABELS, updateKey } from '../keys'

const GRID = 'grid grid-cols-[30px_minmax(96px,1.1fr)_minmax(100px,1fr)_minmax(100px,1fr)_112px_minmax(118px,0.9fr)_28px] items-center gap-x-2'

const TYPE_OPTIONS: SelectOption[] = (Object.keys(TYPE_LABELS) as ColumnType[]).map((t) => ({ value: t, label: TYPE_LABELS[t] }))
const TEXT_RULES: SelectOption[] = [
  { value: 'exact', label: 'Exact text' },
  { value: 'contains', label: 'Contains' },
  { value: 'normalised', label: 'Normalised' }
]
const DAY_CHOICES = [0, 1, 2, 3, 4, 5, 7, 10, 14, 30]

const TYPE_TONE: Record<ColumnType, string> = {
  id: 'bg-[#E6F0FC] text-primary',
  text: 'bg-[#EEF1F5] text-muted',
  amount: 'bg-[#E3F4EC] text-matched',
  number: 'bg-[#E2F6F1] text-[#1E8E72]',
  date: 'bg-[#FDF1DC] text-doubtful'
}

function RuleCell({ k, currency, onChange, disabled }: { k: MatchKey; currency: string; onChange: (patch: Partial<MatchKey>) => void; disabled?: boolean }): React.JSX.Element {
  if (k.type === 'id' || k.type === 'text') {
    return (
      <Select
        size="sm"
        aria-label={`Rule for ${k.name}`}
        value={k.textRule ?? 'normalised'}
        onValueChange={(v) => onChange({ textRule: v as TextRule })}
        options={TEXT_RULES}
        disabled={disabled}
      />
    )
  }
  if (k.type === 'date') {
    const days = k.dateToleranceDays ?? 0
    const choices = DAY_CHOICES.includes(days) ? DAY_CHOICES : [...DAY_CHOICES, days].sort((a, b) => a - b)
    return (
      <Select
        size="sm"
        aria-label={`Date tolerance for ${k.name}`}
        value={String(days)}
        onValueChange={(v) => onChange({ dateToleranceDays: Number(v) })}
        options={choices.map((d) => ({ value: String(d), label: d === 0 ? 'Exact date' : `± ${d} day${d === 1 ? '' : 's'}` }))}
        disabled={disabled}
      />
    )
  }
  const t: Tolerance = k.tolerance ?? { mode: 'exact' }
  return (
    <div className="flex gap-1.5">
      <Select
        size="sm"
        className="min-w-0 flex-1"
        aria-label={`Tolerance for ${k.name}`}
        value={t.mode}
        onValueChange={(mode) => onChange({ tolerance: mode === 'exact' ? { mode: 'exact' } : { mode: mode as 'fixed' | 'percent', value: t.mode === 'exact' ? 0 : t.value } })}
        options={[
          { value: 'exact', label: 'Exact' },
          { value: 'fixed', label: `± ${currency}` },
          { value: 'percent', label: '± %' }
        ]}
        disabled={disabled}
      />
      {t.mode !== 'exact' && (
        <Input
          type="number"
          min={0}
          step={t.mode === 'percent' ? 0.1 : 0.01}
          aria-label={t.mode === 'percent' ? `Tolerance percent for ${k.name}` : `Tolerance amount for ${k.name}`}
          className="h-8 w-[62px] px-2 text-[12.5px]"
          value={Number.isFinite(t.value) ? t.value : ''}
          onChange={(e) => onChange({ tolerance: { mode: t.mode, value: e.target.value === '' ? Number.NaN : Number(e.target.value) } })}
          disabled={disabled}
        />
      )}
    </div>
  )
}

export function KeyTable({
  config,
  columnsA,
  columnsB,
  sideAName,
  sideBName,
  onChange,
  onEditAmount
}: {
  config: ReconConfig
  columnsA: string[]
  columnsB: string[]
  sideAName: string
  sideBName: string
  onChange: (next: ReconConfig) => void
  /** Scrolls to the amount layout card. */
  onEditAmount: () => void
}): React.JSX.Element {
  const optsA = useMemo<SelectOption[]>(() => columnsA.map((c) => ({ value: c, label: c })), [columnsA])
  const optsB = useMemo<SelectOption[]>(() => columnsB.map((c) => ({ value: c, label: c })), [columnsB])

  const amountCell = (side: 'A' | 'B', k: MatchKey): React.ReactNode => {
    const layout = side === 'A' ? config.amountA : config.amountB
    if (!layout || layout.kind === 'signed') {
      return (
        <Select
          size="sm"
          aria-label={`${k.name} column in ${side === 'A' ? sideAName : sideBName}`}
          value={layout?.kind === 'signed' && layout.column ? layout.column : undefined}
          placeholder="Choose column"
          options={side === 'A' ? optsA : optsB}
          onValueChange={(v) =>
            onChange(syncAmountKey({ ...config, [side === 'A' ? 'amountA' : 'amountB']: { kind: 'signed', column: v } }))
          }
        />
      )
    }
    return (
      <button
        type="button"
        onClick={onEditAmount}
        className="flex h-8 w-full items-center truncate rounded-lg border border-dashed border-[#C9D2DE] bg-[#FAFBFC] px-3 text-left text-[12.5px] text-ink outline-none hover:border-primary focus-visible:ring-2 focus-visible:ring-primary/40"
        title="Change in Amount columns below"
      >
        <span className="truncate">{layoutLabel(layout)}</span>
      </button>
    )
  }

  return (
    <div role="table" aria-label="Match keys" className="text-[13px]">
      <div role="row" className={cn(GRID, 'rounded-t-lg bg-[#F6F8FB] px-2.5 py-2 text-[12.5px] font-semibold text-ink')}>
        <span role="columnheader">Use</span>
        <span role="columnheader">Key name</span>
        <span role="columnheader" className="truncate" title={sideAName}>
          {sideAName}
        </span>
        <span role="columnheader" className="truncate" title={sideBName}>
          {sideBName}
        </span>
        <span role="columnheader">Type</span>
        <span role="columnheader">Rule / tolerance</span>
        <span role="columnheader">
          <span className="sr-only">Remove</span>
        </span>
      </div>
      {config.keys.length === 0 && <div className="border-b border-line px-3 py-6 text-center text-muted">No keys yet. Add a key to choose which columns to match.</div>}
      {config.keys.map((k) => {
        const set = (patch: Partial<MatchKey>): void => onChange(updateKey(config, k.id, patch))
        return (
          <div role="row" key={k.id} className={cn(GRID, 'border-b border-line px-2.5 py-2', !k.use && 'bg-[#FBFCFD]')}>
            <div role="cell">
              <Checkbox aria-label={`Use ${k.name}`} checked={k.use} onCheckedChange={(v) => set({ use: v === true })} />
            </div>
            <div role="cell" className="min-w-0">
              <Input
                aria-label="Key name"
                value={k.name}
                maxLength={40}
                onChange={(e) => set({ name: e.target.value })}
                onBlur={(e) => !e.target.value.trim() && set({ name: TYPE_LABELS[k.type] })}
                className={cn('h-8 px-2 text-[13px] font-semibold', !k.use && 'font-normal text-muted')}
              />
              {k.type === 'text' && (
                <div className="mt-1">
                  <Checkbox
                    className="h-[15px] w-[15px]"
                    label={<span className="text-[11.5px] font-semibold text-ai">ID key</span>}
                    checked={k.identifying}
                    onCheckedChange={(v) => set({ identifying: v === true })}
                  />
                </div>
              )}
              {k.type === 'id' && (
                <Tooltip content="ID / code keys can identify a record on their own.">
                  <span tabIndex={0} className="mt-1 inline-block text-[11px] font-semibold text-ai outline-none">
                    • ID KEY
                  </span>
                </Tooltip>
              )}
            </div>
            <div role="cell" className="min-w-0">
              {k.type === 'amount' ? (
                amountCell('A', k)
              ) : (
                <Select
                  size="sm"
                  aria-label={`${k.name} column in ${sideAName}`}
                  value={k.columnA || undefined}
                  placeholder="Choose column"
                  options={optsA}
                  onValueChange={(v) => set({ columnA: v })}
                  aria-invalid={k.use && !!k.columnA && !columnsA.includes(k.columnA)}
                />
              )}
            </div>
            <div role="cell" className="min-w-0">
              {k.type === 'amount' ? (
                amountCell('B', k)
              ) : (
                <Select
                  size="sm"
                  aria-label={`${k.name} column in ${sideBName}`}
                  value={k.columnB || undefined}
                  placeholder="Choose column"
                  options={optsB}
                  onValueChange={(v) => set({ columnB: v })}
                  aria-invalid={k.use && !!k.columnB && !columnsB.includes(k.columnB)}
                />
              )}
            </div>
            <div role="cell" className="min-w-0">
              <Select
                size="sm"
                aria-label={`Type of ${k.name}`}
                value={k.type}
                onValueChange={(v) => onChange(syncAmountKey(changeKeyType(config, k.id, v as ColumnType)))}
                options={TYPE_OPTIONS}
                className={cn('border-transparent font-semibold', TYPE_TONE[k.type])}
              />
            </div>
            <div role="cell" className="min-w-0">
              <RuleCell k={k} currency={config.currency} onChange={set} />
            </div>
            <div role="cell">
              <Tooltip content={`Remove ${k.name}`}>
                <Button variant="ghost" size="icon-sm" aria-label={`Remove ${k.name}`} onClick={() => onChange(removeKey(config, k.id))}>
                  <Trash2 size={14} />
                </Button>
              </Tooltip>
            </div>
          </div>
        )
      })}
      <div className="px-2.5 pt-2.5">
        <Button variant="ghost" size="sm" onClick={() => onChange(addKey(config))} className="text-primary">
          <Plus size={15} /> Add key {config.moduleId === 'general' ? `(any column in ${sideAName} ↔ any column in ${sideBName})` : '(e.g. Cheque No, Invoice No, Party)'}
        </Button>
      </div>
    </div>
  )
}
