import { useId, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { AlertTriangle, ChevronDown, ChevronRight, FileWarning } from 'lucide-react'
import type { Side, TableRow } from '@shared/contracts'
import { formatAmount } from '@shared/format'
import { Badge, Button, Card, DataTable, DropZone, EXCEL_FILTER, Input, PDF_FILTER, SectionTitle, Select, type DataColumn } from '@/components/ui'
import { cn } from '@/lib/cn'
import { useWizard } from '../WizardContext'
import { columnTypes, EXCLUSION_LABELS } from '../helpers'
import { TYPE_LABELS } from '../keys'
import { cellText } from '../review/model'
import { NO_HEADER_ROW } from '@shared/parsing'
import { PDF_MESSAGE } from './loadFile'

const PREVIEW_ROWS = 10

function HeaderRowControl({ side }: { side: Side }): React.JSX.Element | null {
  const { state, changeHeaderRow } = useWizard()
  const f = state.files[side]
  const [editing, setEditing] = useState(false)
  const [value, setValue] = useState('')
  const id = useId()
  if (!f) return null
  const noHeader = f.table.headerRowIndex < 0
  const detectedNone = f.detectedHeaderRow < 0
  const current = f.table.headerRowIndex + 1
  const detectedText = detectedNone ? 'no header row' : `row ${f.detectedHeaderRow + 1}`
  const maxRow = Math.max(1, f.workbook.sheets[f.sheetIndex]?.rows.length ?? 1)
  const n = Number(value)
  // Same convention as the Data Cleaner: row 0 means the file has no header row.
  const valid = value.trim() !== '' && Number.isInteger(n) && n >= 0 && n <= maxRow
  if (!editing) {
    return (
      <div className="flex items-center gap-2 text-[13px]">
        <span data-testid={`header-row-${side}`}>
          {noHeader ? (
            <>
              <strong>{detectedNone ? 'No header row detected' : 'No header row'}</strong>, columns named Column 1, 2, …
            </>
          ) : (
            <>
              Header found on <strong>row {current}</strong>
            </>
          )}
          {f.table.headerRowIndex !== f.detectedHeaderRow && <span className="text-muted"> (changed; detected {detectedText})</span>}
        </span>
        <Button
          variant="link"
          size="sm"
          onClick={() => {
            setValue(String(noHeader ? 0 : current))
            setEditing(true)
          }}
        >
          Change
        </Button>
      </div>
    )
  }
  return (
    <form
      className="flex flex-wrap items-center gap-2 text-[13px]"
      onSubmit={(e) => {
        e.preventDefault()
        if (!valid) return
        changeHeaderRow(side, n === 0 ? NO_HEADER_ROW : n - 1)
        setEditing(false)
      }}
    >
      <label htmlFor={id}>Header is on row</label>
      <Input id={id} type="number" min={0} max={maxRow} value={value} onChange={(e) => setValue(e.target.value)} className="h-8 w-20" aria-invalid={!valid} autoFocus />
      <span className="text-[12px] text-muted">(0 = no header row)</span>
      <Button type="submit" size="sm" disabled={!valid}>
        Re-read
      </Button>
      <Button
        size="sm"
        variant="ghost"
        onClick={() => {
          changeHeaderRow(side, NO_HEADER_ROW)
          setEditing(false)
        }}
      >
        No header row
      </Button>
      <Button
        size="sm"
        variant="ghost"
        onClick={() => {
          changeHeaderRow(side, null)
          setEditing(false)
        }}
      >
        Use detected ({detectedText})
      </Button>
      <Button size="sm" variant="ghost" onClick={() => setEditing(false)}>
        Cancel
      </Button>
    </form>
  )
}

function ExcludedRows({ side }: { side: Side }): React.JSX.Element | null {
  const { state } = useWizard()
  const [open, setOpen] = useState(false)
  const f = state.files[side]
  if (!f) return null
  const ex = f.table.excluded
  if (ex.length === 0) return <div className="text-[13px] text-muted">No rows excluded</div>
  return (
    <div className="text-[13px]">
      <button
        type="button"
        className="inline-flex items-center gap-1 font-semibold text-doubtful outline-none hover:underline focus-visible:ring-2 focus-visible:ring-primary/40"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
      >
        {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        {ex.length} row{ex.length === 1 ? '' : 's'} excluded
      </button>
      {open && (
        <ul className="mt-2 max-h-48 overflow-y-auto rounded-lg border border-line bg-[#FAFBFC] text-[12.5px]">
          {ex.map((r) => (
            <li key={r.sourceRow} className="flex gap-3 border-b border-line px-3 py-1.5 last:border-b-0">
              <span className="num w-14 shrink-0 text-muted">Row {r.sourceRow + 1}</span>
              <Badge tone="neutral" size="sm" className="shrink-0">
                {EXCLUSION_LABELS[r.reason]}
              </Badge>
              <span className="truncate text-muted" title={r.values.map((v) => cellText(v)).filter(Boolean).join(' · ')}>
                {r.values
                  .map((v) => cellText(v))
                  .filter(Boolean)
                  .join(' · ') || '(empty)'}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function Preview({ side }: { side: Side }): React.JSX.Element | null {
  const { state } = useWizard()
  const f = state.files[side]
  const columns = useMemo<DataColumn<TableRow>[]>(() => {
    if (!f) return []
    const types = columnTypes(f.table)
    return f.table.columns.map((c) => ({
      id: c,
      header: c,
      subHeader: TYPE_LABELS[types[c]],
      numeric: types[c] === 'amount' || types[c] === 'number',
      minWidth: types[c] === 'date' ? 118 : 104,
      value: (r: TableRow) => r.values[c] ?? null
    }))
  }, [f])
  if (!f) return null
  const rows = f.table.rows.slice(0, PREVIEW_ROWS)
  return (
    <DataTable
      aria-label={`First ${PREVIEW_ROWS} rows of ${f.fileName}`}
      rows={rows}
      columns={columns}
      rowKey={(r) => r.id}
      rowHeight={30}
      height={Math.min(PREVIEW_ROWS, Math.max(rows.length, 1)) * 30 + 50}
      empty="No data rows under this header row."
    />
  )
}

export function FilePanel({ side }: { side: Side }): React.JSX.Element {
  const { state, module, dispatch, busy, fileErrors, loadFile, clearFile, changeSheet } = useWizard()
  const f = state.files[side]
  const name = side === 'A' ? state.sideAName : state.sideBName
  const nameId = useId()
  const error = fileErrors[side]
  const [showPreview, setShowPreview] = useState(true)
  const t = f?.table

  return (
    <Card className="flex min-w-0 flex-col gap-3.5 p-5">
      {module.editableSideNames ? (
        <div className="flex items-center justify-between gap-4">
          <label htmlFor={nameId} className="text-[11.5px] font-bold tracking-[1.2px] whitespace-nowrap text-muted uppercase">
            File {side} name
          </label>
          <Input
            id={nameId}
            value={name}
            maxLength={60}
            onChange={(e) => dispatch({ type: 'sideName', side, name: e.target.value })}
            onBlur={(e) => {
              if (!e.target.value.trim()) dispatch({ type: 'sideName', side, name: `File ${side}` })
            }}
            className="max-w-[300px]"
            aria-label={`Name for file ${side}`}
          />
        </div>
      ) : (
        <SectionTitle>{name}</SectionTitle>
      )}

      <DropZone
        accept={[EXCEL_FILTER, PDF_FILTER]}
        hint=".xlsx · .xls · .csv"
        title={`Drop the ${name.toLowerCase()} here or click to browse`}
        dialogTitle={`Choose the ${name.toLowerCase()}`}
        file={f ? { name: f.fileName, size: f.size } : null}
        info={t ? `${t.rows.length.toLocaleString('en-US')} rows · ${t.headerRowIndex < 0 ? 'no header row' : `header on row ${t.headerRowIndex + 1}`} · ${t.columns.length} columns identified` : undefined}
        busy={busy[side]}
        onFiles={(files) => void loadFile(side, files[0])}
        onClear={f ? () => clearFile(side) : undefined}
        error={error && error !== PDF_MESSAGE ? error : null}
      />

      {f?.workbook.warnings && f.workbook.warnings.length > 0 && (
        <div role="status" className="flex gap-3 rounded-lg border border-[#F2D7A6] bg-[#FFF8EB] p-3 text-[13px] leading-relaxed" data-testid={`file-warnings-${side}`}>
          <AlertTriangle size={17} className="mt-0.5 shrink-0 text-doubtful" aria-hidden />
          <div className="min-w-0">
            <div className="font-semibold text-ink">Check this file: Reco-Do had to repair something while reading it</div>
            <ul className="mt-0.5 list-disc pl-5 text-muted">
              {f.workbook.warnings.slice(0, 5).map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
            {f.workbook.warnings.length > 5 && <div className="text-muted">…and {f.workbook.warnings.length - 5} more.</div>}
          </div>
        </div>
      )}

      {error === PDF_MESSAGE && (
        <div role="alert" className="flex gap-3 rounded-lg border border-[#F2D7A6] bg-[#FFF8EB] p-3 text-[13px] leading-relaxed">
          <FileWarning size={18} className="mt-0.5 shrink-0 text-doubtful" />
          <div>
            <div className="font-semibold text-ink">PDF files need converting first</div>
            <div className="text-muted">
              The wizard reads Excel and CSV files. Use{' '}
              <Link to="/tools/pdf-to-excel" className="font-semibold text-primary hover:underline">
                Tools → PDF → Excel
              </Link>{' '}
              to turn the PDF into an Excel file, then upload that file here.
            </div>
          </div>
        </div>
      )}

      {f && t && (
        <>
          <div className="flex flex-col gap-2 rounded-lg bg-[#F7F9FB] px-3.5 py-3">
            {f.workbook.sheets.length > 1 && (
              <div className="flex items-center gap-2 text-[13px]">
                <span className="shrink-0">Sheet</span>
                <Select
                  size="sm"
                  className="max-w-[260px]"
                  aria-label={`Sheet in ${f.fileName}`}
                  value={String(f.sheetIndex)}
                  onValueChange={(v) => changeSheet(side, Number(v))}
                  options={f.workbook.sheets.map((s, i) => ({ value: String(i), label: `${s.name} (${s.rows.length} rows)` }))}
                />
              </div>
            )}
            <HeaderRowControl side={side} />
            <ExcludedRows side={side} />
            <div className="text-[13px]">
              {t.openingBalance === null && t.closingBalance === null ? (
                <span className="text-muted">No opening or closing balance rows found</span>
              ) : (
                <span>
                  Opening balance <strong className="num">{t.openingBalance === null ? '—' : formatAmount(t.openingBalance)}</strong>
                  <span className="text-muted"> · </span>
                  Closing balance <strong className="num">{t.closingBalance === null ? '—' : formatAmount(t.closingBalance)}</strong>
                </span>
              )}
            </div>
            {t.rows.length === 0 && (
              <div role="alert" className="text-[13px] font-semibold text-unmatched">
                No data rows found under this header. Choose another sheet or header row.
              </div>
            )}
          </div>

          <div>
            <div className="mb-2 text-[12.5px] font-semibold text-muted">
              {t.columns.length} columns identified · {t.rows.length.toLocaleString('en-US')} rows
            </div>
            <ul className="flex flex-wrap gap-1.5" aria-label="Columns">
              {t.columns.map((c) => (
                <li key={c} className="rounded-md border border-line bg-[#F4F6F9] px-2.5 py-1 text-[12.5px] text-ink">
                  {c}
                </li>
              ))}
            </ul>
          </div>

          <div>
            <button
              type="button"
              className={cn('mb-2 inline-flex items-center gap-1 text-[12.5px] font-semibold text-primary outline-none hover:underline focus-visible:ring-2 focus-visible:ring-primary/40')}
              aria-expanded={showPreview}
              onClick={() => setShowPreview((v) => !v)}
            >
              {showPreview ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
              Preview (first {Math.min(PREVIEW_ROWS, t.rows.length)} rows)
            </button>
            {showPreview && <Preview side={side} />}
          </div>
        </>
      )}
    </Card>
  )
}
