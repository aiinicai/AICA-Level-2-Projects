import { useMemo, useRef } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'
import type { CellValue } from '@shared/contracts'
import { formatAmount, formatDate } from '@shared/format'
import { cn } from '@/lib/cn'
import { Checkbox } from './checkbox'

export interface DataColumn<T> {
  id: string
  header: React.ReactNode
  /** Small second header line, e.g. the column type ("amount", "date"). */
  subHeader?: React.ReactNode
  /** Fixed width in px. Without it the column shares the free space (min `minWidth`, default 110). */
  width?: number
  minWidth?: number
  /** Right-aligned with tabular figures; plain numbers are shown with 2 decimals and thousand separators. */
  numeric?: boolean
  align?: 'left' | 'right' | 'center'
  /** Raw value; formatted automatically (numbers → 1,234.50, dates → 03-Sep-2026). */
  value?: (row: T) => CellValue | undefined
  /** Custom cell renderer; takes precedence over `value`. */
  cell?: (row: T, index: number) => React.ReactNode
  /** Tooltip text for truncated cells (defaults to the formatted value). */
  title?: (row: T) => string | undefined
  className?: string
  headerClassName?: string
}

export interface DataTableProps<T> {
  rows: T[]
  columns: DataColumn<T>[]
  /** Stable key per row (also used for selection). */
  rowKey: (row: T, index: number) => string
  /** Row height in px (fixed, for smooth virtual scrolling). Default 36. */
  rowHeight?: number
  /** Height of the scroll area. Default 460 px. */
  height?: number | string
  /** Shows a checkbox column. */
  selectable?: boolean
  selected?: ReadonlySet<string>
  onSelectedChange?: (next: Set<string>) => void
  onRowClick?: (row: T, index: number) => void
  rowClassName?: (row: T, index: number) => string | undefined
  /** Shown when there are no rows. */
  empty?: React.ReactNode
  className?: string
  'aria-label'?: string
}

export function formatCell(v: CellValue | undefined, numeric?: boolean): string {
  if (v === null || v === undefined) return ''
  if (v instanceof Date) return Number.isNaN(v.getTime()) ? '' : formatDate(v)
  if (typeof v === 'number') return numeric === false ? String(v) : Number.isFinite(v) ? formatAmount(v) : ''
  return v
}

const CHECK_COL = 40

/** Virtualised table: sticky header, right-aligned numbers, optional row checkboxes. Smooth with 50,000+ rows. */
export function DataTable<T>({
  rows,
  columns,
  rowKey,
  rowHeight = 36,
  height = 460,
  selectable,
  selected,
  onSelectedChange,
  onRowClick,
  rowClassName,
  empty,
  className,
  ...aria
}: DataTableProps<T>): React.JSX.Element {
  const scrollRef = useRef<HTMLDivElement>(null)
  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => rowHeight,
    overscan: 14
  })

  const template = useMemo(() => {
    const cols = columns.map((c) => (c.width ? `${c.width}px` : `minmax(${c.minWidth ?? 110}px, 1fr)`))
    return (selectable ? [`${CHECK_COL}px`, ...cols] : cols).join(' ')
  }, [columns, selectable])
  const minWidth = useMemo(
    () => columns.reduce((sum, c) => sum + (c.width ?? c.minWidth ?? 110), selectable ? CHECK_COL : 0),
    [columns, selectable]
  )

  const keys = useMemo(() => (selectable ? rows.map((r, i) => rowKey(r, i)) : []), [rows, rowKey, selectable])
  const selectedCount = selectable && selected ? keys.reduce((n, k) => n + (selected.has(k) ? 1 : 0), 0) : 0
  const allState: boolean | 'indeterminate' = selectedCount === 0 ? false : selectedCount === keys.length ? true : 'indeterminate'

  const toggleAll = (): void => {
    if (!onSelectedChange) return
    const next = new Set(selected ?? [])
    if (allState === true) keys.forEach((k) => next.delete(k))
    else keys.forEach((k) => next.add(k))
    onSelectedChange(next)
  }
  const toggleOne = (key: string): void => {
    if (!onSelectedChange) return
    const next = new Set(selected ?? [])
    if (next.has(key)) next.delete(key)
    else next.add(key)
    onSelectedChange(next)
  }

  const alignOf = (c: DataColumn<T>): string =>
    (c.align ?? (c.numeric ? 'right' : 'left')) === 'right' ? 'justify-end text-right' : c.align === 'center' ? 'justify-center text-center' : 'justify-start text-left'

  return (
    <div
      ref={scrollRef}
      role="table"
      aria-label={aria['aria-label']}
      aria-rowcount={rows.length + 1}
      className={cn('relative overflow-auto rounded-lg border border-line bg-white', className)}
      style={{ height }}
    >
      <div style={{ minWidth }}>
        <div
          role="row"
          aria-rowindex={1}
          className="sticky top-0 z-10 grid border-b border-line bg-[#F6F8FB] text-[12.5px] font-semibold text-ink"
          style={{ gridTemplateColumns: template }}
        >
          {selectable && (
            <div role="columnheader" className="flex items-center justify-center px-2 py-2">
              <Checkbox
                aria-label={allState === true ? 'Clear selection' : 'Select all rows'}
                checked={allState}
                onCheckedChange={toggleAll}
                disabled={!rows.length}
              />
            </div>
          )}
          {columns.map((c) => (
            <div key={c.id} role="columnheader" className={cn('flex flex-col px-3 py-2 whitespace-nowrap', c.headerClassName)}>
              <span className={cn('flex leading-tight', alignOf(c))}>{c.header}</span>
              {c.subHeader && <span className={cn('flex text-[11px] font-normal text-primary', alignOf(c))}>{c.subHeader}</span>}
            </div>
          ))}
        </div>

        {rows.length === 0 ? (
          <div className="px-4 py-10 text-center text-[13px] text-muted">{empty ?? 'No rows to show.'}</div>
        ) : (
          <div role="rowgroup" className="relative" style={{ height: virtualizer.getTotalSize() }}>
            {virtualizer.getVirtualItems().map((v) => {
              const row = rows[v.index]
              const key = selectable ? keys[v.index] : rowKey(row, v.index)
              const isSelected = !!selectable && !!selected?.has(key)
              return (
                <div
                  key={key}
                  role="row"
                  aria-rowindex={v.index + 2}
                  aria-selected={selectable ? isSelected : undefined}
                  onClick={onRowClick ? () => onRowClick(row, v.index) : undefined}
                  className={cn(
                    'absolute top-0 left-0 grid w-full items-center border-b border-[#EEF1F5] text-[13px] text-ink',
                    onRowClick && 'cursor-pointer hover:bg-[#F7FAFE]',
                    isSelected && 'bg-[#EEF4FD] hover:bg-[#E6EFFC]',
                    rowClassName?.(row, v.index)
                  )}
                  style={{ gridTemplateColumns: template, height: rowHeight, transform: `translateY(${v.start}px)` }}
                >
                  {selectable && (
                    <div role="cell" className="flex items-center justify-center px-2" onClick={(e) => e.stopPropagation()}>
                      <Checkbox aria-label="Select row" checked={isSelected} onCheckedChange={() => toggleOne(key)} />
                    </div>
                  )}
                  {columns.map((c) => {
                    const raw = c.value?.(row)
                    const text = c.cell ? undefined : formatCell(raw, c.numeric ? true : typeof raw === 'number' ? false : undefined)
                    return (
                      <div
                        key={c.id}
                        role="cell"
                        title={c.title?.(row) ?? text}
                        className={cn('flex min-w-0 items-center overflow-hidden px-3', alignOf(c), c.numeric && 'num', c.className)}
                      >
                        {c.cell ? c.cell(row, v.index) : <span className="truncate">{text}</span>}
                      </div>
                    )
                  })}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
