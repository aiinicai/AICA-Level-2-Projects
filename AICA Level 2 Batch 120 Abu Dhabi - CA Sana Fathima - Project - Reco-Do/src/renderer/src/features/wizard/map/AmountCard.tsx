import { forwardRef, useMemo } from 'react'
import { Info } from 'lucide-react'
import type { AmountLayout, ParsedTable, ReconConfig, Side } from '@shared/contracts'
import { detectNegativeCreditColumn } from '@engine/index'
import { Card, SectionTitle, SegmentedControl, Select, type SelectOption } from '@/components/ui'
import { convertLayout, syncAmountKey } from '../keys'

const KINDS: { value: AmountLayout['kind']; label: string }[] = [
  { value: 'signed', label: 'One signed column' },
  { value: 'debit-credit', label: 'Debit + Credit' },
  { value: 'amount-indicator', label: 'Amount + Dr/Cr' }
]

const HINT: Record<AmountLayout['kind'], string> = {
  signed: 'One column; negative numbers, brackets or a CR suffix mean credit.',
  'debit-credit': 'Two columns; the amount is Debit minus Credit.',
  'amount-indicator': 'An amount column and a column saying Dr or Cr.'
}

function SideLayout({
  side,
  name,
  layout,
  columns,
  table,
  onChange
}: {
  side: Side
  name: string
  layout: AmountLayout | undefined
  columns: string[]
  table?: ParsedTable
  onChange: (l: AmountLayout) => void
}): React.JSX.Element {
  // Debit + Credit files sometimes write credits as negative numbers; say so, so the user is not left guessing.
  const negativeCredit = useMemo(() => (table ? detectNegativeCreditColumn(table, layout) : null), [table, layout])
  const opts: SelectOption[] = columns.map((c) => ({ value: c, label: c }))
  const kind = layout?.kind ?? 'signed'
  const pick = (label: string, value: string, set: (v: string) => void): React.JSX.Element => (
    <label className="flex min-w-0 flex-1 flex-col gap-1 text-[12px] font-semibold text-muted">
      {label}
      <Select size="sm" aria-label={`${label} column in ${name}`} value={value || undefined} placeholder="Choose column" options={opts} onValueChange={set} />
    </label>
  )
  return (
    <div className="min-w-0 flex-1">
      <div className="mb-2 truncate text-[13px] font-semibold" title={name}>
        {name}
      </div>
      <SegmentedControl
        size="sm"
        aria-label={`How ${name} shows amounts`}
        value={kind}
        onValueChange={(k) => onChange(convertLayout(layout, k))}
        options={KINDS}
      />
      <p className="mt-1.5 text-[12px] text-muted">{HINT[kind]}</p>
      <div className="mt-2 flex gap-2">
        {layout?.kind === 'debit-credit' ? (
          <>
            {pick('Debit', layout.debit, (v) => onChange({ ...layout, debit: v }))}
            {pick('Credit', layout.credit, (v) => onChange({ ...layout, credit: v }))}
          </>
        ) : layout?.kind === 'amount-indicator' ? (
          <>
            {pick('Amount', layout.amount, (v) => onChange({ ...layout, amount: v }))}
            {pick('Dr / Cr', layout.indicator, (v) => onChange({ ...layout, indicator: v }))}
          </>
        ) : (
          pick('Amount', layout?.kind === 'signed' ? layout.column : '', (v) => onChange({ kind: 'signed', column: v }))
        )}
      </div>
      {negativeCredit && (
        <p className="mt-2 flex gap-1.5 rounded-md bg-[#EEF4FD] px-2.5 py-2 text-[12.5px] text-[#1F4E8C]" data-testid={`negative-credit-${side}`}>
          <Info size={14} className="mt-0.5 shrink-0" aria-hidden />
          <span>Credits in this file are written as negative numbers. Reco-Do treats them as credits.</span>
        </p>
      )}
      <span className="sr-only">Side {side}</span>
    </div>
  )
}

/** Amount layout pickers per side (signed / debit-credit / amount + indicator). */
export const AmountCard = forwardRef<
  HTMLDivElement,
  { config: ReconConfig; columnsA: string[]; columnsB: string[]; tableA?: ParsedTable; tableB?: ParsedTable; onChange: (c: ReconConfig) => void }
>(function AmountCard({ config, columnsA, columnsB, tableA, tableB, onChange }, ref) {
  return (
    <Card ref={ref} className="p-5" tabIndex={-1}>
      <SectionTitle className="mb-3">Amount columns</SectionTitle>
      <div className="flex flex-col gap-5 md:flex-row">
        <SideLayout side="A" name={config.sideAName} layout={config.amountA} columns={columnsA} table={tableA} onChange={(l) => onChange(syncAmountKey({ ...config, amountA: l }))} />
        <SideLayout side="B" name={config.sideBName} layout={config.amountB} columns={columnsB} table={tableB} onChange={(l) => onChange(syncAmountKey({ ...config, amountB: l }))} />
      </div>
    </Card>
  )
})
