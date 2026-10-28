import { useMemo } from 'react'
import { CalendarDays } from 'lucide-react'
import type { ParsedTable, ReconConfig, Side } from '@shared/contracts'
import { detectConfigDateOrders } from '@engine/index'
import { Card, SectionTitle, Select } from '@/components/ui'
import { dateOrderState, type Order } from './dateOrder'

const LABEL: Record<Order, string> = { DMY: 'DD/MM/YYYY', MDY: 'MM/DD/YYYY' }
const OPTIONS = [
  { value: 'DMY', label: 'DD/MM/YYYY (day first)' },
  { value: 'MDY', label: 'MM/DD/YYYY (month first)' }
]

/**
 * "Dates in Bank statement are read as DD/MM/YYYY – change". Shown on Map & rules when a date column could be read
 * either way (every day is 12 or less) or the two files write dates differently. The choice is stored in
 * ReconConfig.dateOrderA / dateOrderB.
 */
export function DateOrderCard({
  config,
  tableA,
  tableB,
  onChange
}: {
  config: ReconConfig
  tableA: ParsedTable
  tableB: ParsedTable
  onChange: (c: ReconConfig) => void
}): React.JSX.Element | null {
  const dateKey = config.keys.find((k) => k.use && k.type === 'date')
  const colA = dateKey?.columnA
  const colB = dateKey?.columnB
  // Whole-column scan: only when the tables or the date columns change.
  const detected = useMemo(() => detectConfigDateOrders(tableA, tableB, config), [tableA, tableB, colA, colB])
  const st = dateOrderState(config, detected)
  if (!st.show) return null

  const row = (side: Side): React.JSX.Element => {
    const name = side === 'A' ? config.sideAName : config.sideBName
    const order = side === 'A' ? st.a : st.b
    const chosen = side === 'A' ? config.dateOrderA : config.dateOrderB
    return (
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0 text-[13.5px]">
          Dates in <strong className="font-semibold">{name}</strong> are read as <strong className="font-semibold">{LABEL[order]}</strong>
          {st.ambiguous[side] && !chosen && <span className="text-muted"> (every day in this file is 12 or less, so both readings are possible)</span>}
        </div>
        <Select
          size="sm"
          aria-label={`Change how dates in ${name} are read`}
          value={order}
          options={OPTIONS}
          onValueChange={(v) => onChange(side === 'A' ? { ...config, dateOrderA: v as Order } : { ...config, dateOrderB: v as Order })}
        />
      </div>
    )
  }

  return (
    <Card className="p-5" data-testid="date-order">
      <SectionTitle className="mb-3">
        <span className="inline-flex items-center gap-1.5">
          <CalendarDays size={15} aria-hidden /> Date format
        </span>
      </SectionTitle>
      <div className="flex flex-col gap-3">
        {row('A')}
        {row('B')}
      </div>
      <p className="mt-3 text-[12.5px] text-muted">Check one or two dates against the file. A wrong choice swaps day and month (5 March becomes 3 May).</p>
    </Card>
  )
}
