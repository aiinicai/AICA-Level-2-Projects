import { useMemo, useRef, useState } from 'react'
import type { CellValue, ColumnType, OpenedFile, WorkbookData } from '@shared/contracts'
import { inferColumnType, readWorkbook } from '@shared/parsing'
import { baseName } from '@tools/common'
import {
  ACTION_ORDER,
  cleanToWorkbook,
  dateInfo,
  isChanged,
  prepareSheet,
  REASON_LABEL,
  REMOVABLE_REASONS,
  runCleaner,
  suggestOptions,
  valueText,
  withDefaults,
  type ActionReport,
  type AmountOptions,
  type CleanerAction,
  type CleanerOptions,
  type CleanRow,
  type PreparedSheet,
  type RemovableReason,
  type RemovedRow
} from '@tools/data-cleaner'
import {
  Checkbox,
  DataTable,
  DropZone,
  Field,
  Input,
  Select,
  SegmentedControl,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  useToast,
  type DataColumn
} from '@/components/ui'
import { cn } from '@/lib/cn'
import { asDataCleanerRecipe, dataCleanerRecipe } from './recipes'
import { Callout, ColumnChips, CountPill, EXCEL_IN, EXCEL_OUT, OutputBar, SampleFiles, Section, TaskStatus, ToolLayout } from './shared/components'
import { cellText, isNumericCell } from './shared/cellText'
import { RecipeBar } from './shared/RecipeBar'
import { toolErrorMessage, useToolTask } from './shared/useToolTask'

interface Loaded {
  name: string
  size: number
  wb: WorkbookData
}

const SAMPLES = [{ label: 'Messy expense register', files: ['Messy_Data_for_Cleaner.xlsx'] }]

const ACTION_LABEL: Record<CleanerAction, string> = {
  removeRows: 'Remove blank, repeated header, subtotal, total, opening and closing rows',
  trim: 'Trim extra spaces and non-printing characters',
  fillDown: 'Fill down blank cells from merged-cell layouts',
  numbers: 'Convert text numbers to numbers',
  dates: 'Convert text dates to real dates',
  amount: 'Split amount into Debit / Credit, or combine them',
  textCase: 'Change text case',
  duplicates: 'Flag or remove exact duplicate rows'
}

const REASON_SHORT: Record<RemovableReason, string> = {
  blank: 'Blank',
  'repeated-header': 'Repeated header',
  subtotal: 'Subtotal',
  total: 'Total',
  'opening-balance': 'Opening balance',
  'closing-balance': 'Closing balance'
}

export function DataCleanerScreen(): React.JSX.Element {
  const task = useToolTask()
  const toast = useToast()
  const [file, setFile] = useState<Loaded | null>(null)
  const [sheet, setSheet] = useState('')
  const [headerRow, setHeaderRow] = useState<number | undefined>(undefined)
  const [options, setOptions] = useState<CleanerOptions | null>(null)
  const [pendingRecipe, setPendingRecipe] = useState<Partial<CleanerOptions> | null>(null)
  const [tab, setTab] = useState('after')

  const prepared = useMemo<{ value: PreparedSheet | null; error: string | null }>(() => {
    if (!file || !sheet) return { value: null, error: null }
    const s = file.wb.sheets.find((x) => x.name === sheet)
    if (!s) return { value: null, error: null }
    try {
      return { value: prepareSheet(s, file.name, headerRow), error: null }
    } catch (e) {
      return { value: null, error: toolErrorMessage(e) }
    }
  }, [file, sheet, headerRow])
  const p = prepared.value

  const result = useMemo(() => (p && options ? runCleaner(p, options) : null), [p, options])
  const reports = useMemo(() => Object.fromEntries((result?.reports ?? []).map((r) => [r.action, r])) as Partial<Record<CleanerAction, ActionReport>>, [result])
  const dates = useMemo(() => (p && options ? dateInfo(p, options.dates.columns) : null), [p, options])

  const choose = (wb: WorkbookData, name: string, fileName: string, header: number | undefined, recipe: Partial<CleanerOptions> | null): void => {
    setSheet(name)
    setHeaderRow(header)
    const s = wb.sheets.find((x) => x.name === name)
    if (!s) return
    try {
      const prep = prepareSheet(s, fileName, header)
      setOptions(recipe ? withDefaults(prep, recipe) : suggestOptions(prep))
    } catch {
      setOptions(null)
    }
  }

  const loadSeq = useRef(0)
  const load = async (files: OpenedFile[]): Promise<void> => {
    const f = files[0]
    if (!f) return
    const id = ++loadSeq.current
    const wb = await task.run('Reading the workbook', async () => readWorkbook(f.data, f.name))
    // A newer file was dropped while this one was being read: ignore this result.
    if (!wb || id !== loadSeq.current) return
    for (const w of wb.warnings ?? []) toast.info('Check the file', w)
    const first = wb.sheets.find((s) => s.rows.some((r) => r.some((v) => v !== null))) ?? wb.sheets[0]
    if (!first) {
      task.setError('This workbook has no sheets with data.')
      return
    }
    setFile({ name: f.name, size: f.data.byteLength, wb })
    setTab('after')
    choose(wb, first.name, f.name, undefined, pendingRecipe)
  }

  const applyRecipe = (raw: unknown): void => {
    const r = asDataCleanerRecipe(raw)
    if (!r) {
      task.setError('This recipe could not be read. Save it again from this screen.')
      return
    }
    setPendingRecipe(r.options)
    if (file) {
      const name = r.sheetName && file.wb.sheets.some((s) => s.name === r.sheetName) ? r.sheetName : sheet
      choose(file.wb, name, file.name, headerRow, r.options)
      toast.info('Recipe applied')
    } else toast.info('Recipe ready', 'Drop the file; the recipe is applied when it loads.')
  }

  const set = <K extends CleanerAction>(k: K, patch: Partial<CleanerOptions[K]>): void =>
    setOptions((o) => (o ? { ...o, [k]: { ...o[k], ...patch } as CleanerOptions[K] } : o))

  const columns = p?.table.columns ?? []

  const left = (
    <>
      <RecipeBar tool="data-cleaner" canSave={!!options} current={() => (options ? dataCleanerRecipe(options, sheet) : null)} onApply={applyRecipe} />
      <Section title="Source sheet">
        <DropZone
          accept={[EXCEL_IN]}
          onFiles={(f) => void load(f)}
          file={file ? { name: file.name, size: file.size } : null}
          info={p ? `${p.table.rows.length.toLocaleString('en-US')} rows below the header · ${p.table.columns.length} columns` : undefined}
          busy={task.running}
          title="Drop an Excel or CSV file here"
          dialogTitle="Choose a file to clean"
        />
        <SampleFiles samples={SAMPLES} onLoad={(f) => void load(f)} disabled={task.running} />
        <TaskStatus task={task} />
        {prepared.error && (
          <p className="mt-2 text-[13px] text-unmatched" role="alert">
            {prepared.error}
          </p>
        )}
        {file && (
          <div className="mt-3 grid grid-cols-[1fr_110px] gap-3">
            <Field label="Sheet">
              <Select
                aria-label="Sheet"
                size="sm"
                value={sheet}
                onValueChange={(v) => choose(file.wb, v, file.name, undefined, pendingRecipe)}
                options={file.wb.sheets.map((s) => ({ value: s.name, label: s.name }))}
              />
            </Field>
            <Field label="Header row">
              <Input
                aria-label="Header row"
                type="number"
                min={0}
                className="h-8"
                title="0 = the file has no header row"
                value={p ? p.headerRowIndex + 1 : ''}
                onChange={(e) => {
                  const n = Number(e.target.value)
                  // 0 means "no header row": every row is data and the columns are named Column 1, Column 2, ...
                  if (Number.isInteger(n) && n >= 0) choose(file.wb, sheet, file.name, n - 1, pendingRecipe)
                }}
              />
            </Field>
          </div>
        )}
      </Section>

      {options && p && (
        <Section title="Cleaning actions" right="ticked actions run in this order">
          <div className="flex flex-col gap-3" data-testid="cleaner-actions">
            {ACTION_ORDER.map((a) => (
              <ActionRow key={a} action={a} enabled={options[a].enabled} report={reports[a]} onToggle={(v) => set(a, { enabled: v } as Partial<CleanerOptions[typeof a]>)}>
                {a === 'removeRows' && (
                  <div className="flex flex-wrap gap-x-4 gap-y-1.5">
                    {REMOVABLE_REASONS.map((r) => {
                      const n = p.table.rows.filter((x) => x.junk === r).length
                      return (
                        <Checkbox
                          key={r}
                          label={
                            <span className="text-[12.5px]">
                              {REASON_SHORT[r]} <span className="num text-muted">({n})</span>
                            </span>
                          }
                          checked={options.removeRows.reasons.includes(r)}
                          onCheckedChange={(v) =>
                            set('removeRows', { reasons: v === true ? [...options.removeRows.reasons, r] : options.removeRows.reasons.filter((x) => x !== r) })
                          }
                        />
                      )
                    })}
                  </div>
                )}
                {a === 'fillDown' && <ColumnChips columns={columns} value={options.fillDown.columns} onChange={(c) => set('fillDown', { columns: c })} />}
                {a === 'numbers' && (
                  <>
                    <ColumnChips columns={columns} value={options.numbers.columns} onChange={(c) => set('numbers', { columns: c })} />
                    <SignChoice value={options.numbers.crNegative} onChange={(v) => set('numbers', { crNegative: v })} />
                  </>
                )}
                {a === 'dates' && (
                  <>
                    <ColumnChips columns={columns} value={options.dates.columns} onChange={(c) => set('dates', { columns: c })} />
                    {dates && (dates.ambiguous.length > 0 || dates.detected === 'ambiguous') && (
                      <Callout tone={dates.detected === 'ambiguous' ? 'doubtful' : 'info'} className="mt-2">
                        <div className="mb-2 text-[12.5px]">
                          {dates.ambiguous.length} date{dates.ambiguous.length === 1 ? '' : 's'} could be read either way (
                          {dates.ambiguous.slice(0, 3).join(', ')}
                          {dates.ambiguous.length > 3 ? ', …' : ''}).{' '}
                          {dates.detected === 'ambiguous'
                            ? 'Which order does this file use?'
                            : `The other dates in the file are ${dates.detected === 'MDY' ? 'MM/DD' : 'DD/MM'}, so that order is suggested.`}
                        </div>
                        <SegmentedControl
                          size="sm"
                          aria-label="Date order"
                          value={options.dates.order}
                          onValueChange={(v) => set('dates', { order: v })}
                          options={[
                            { value: 'DMY', label: 'DD/MM/YYYY' },
                            { value: 'MDY', label: 'MM/DD/YYYY' }
                          ]}
                        />
                      </Callout>
                    )}
                  </>
                )}
                {a === 'amount' && <AmountEditor value={options.amount} columns={columns} onChange={(v) => setOptions((o) => (o ? { ...o, amount: v } : o))} />}
                {a === 'textCase' && (
                  <>
                    <ColumnChips columns={columns} value={options.textCase.columns} onChange={(c) => set('textCase', { columns: c })} />
                    <SegmentedControl
                      size="sm"
                      className="mt-2"
                      aria-label="Text case"
                      value={options.textCase.mode}
                      onValueChange={(v) => set('textCase', { mode: v })}
                      options={[
                        { value: 'upper', label: 'UPPER' },
                        { value: 'proper', label: 'Proper' },
                        { value: 'lower', label: 'lower' }
                      ]}
                    />
                  </>
                )}
                {a === 'duplicates' && (
                  <SegmentedControl
                    size="sm"
                    aria-label="Duplicates"
                    value={options.duplicates.mode}
                    onValueChange={(v) => set('duplicates', { mode: v })}
                    options={[
                      { value: 'flag', label: 'Flag (add a column)' },
                      { value: 'remove', label: 'Remove copies' }
                    ]}
                  />
                )}
              </ActionRow>
            ))}
          </div>
        </Section>
      )}

      <OutputBar
        defaultName={file ? `${baseName(file.name)}_cleaned.xlsx` : 'Cleaned.xlsx'}
        extension="xlsx"
        filter={EXCEL_OUT}
        label="Download cleaned file"
        disabled={!result || !p}
        build={async () => (p && result ? task.run('Writing the cleaned workbook', () => cleanToWorkbook(p, result)) : undefined)}
      />
    </>
  )

  const right = (
    <>
      <div className="flex items-baseline justify-between gap-4">
        <div className="text-[11.5px] font-bold tracking-[1.2px] text-muted uppercase" data-testid="preview-title">
          {result
            ? `After cleaning: ${result.table.rows.length.toLocaleString('en-US')} rows · ${result.changedCells.toLocaleString('en-US')} cells changed · ${result.table.removed.length} rows removed`
            : 'Before / after preview'}
        </div>
        {result && (
          <div className="flex items-center gap-1.5 text-[12.5px] text-muted">
            <span className="inline-block h-3 w-3 rounded-sm bg-[#FFF2CC] ring-1 ring-[#F1D9A6]" /> changed
          </div>
        )}
      </div>
      {!p || !result ? (
        <div className="mt-3 grid h-[420px] place-items-center rounded-lg border border-dashed border-line text-center text-[13px] text-muted">
          Drop an Excel or CSV export on the left, or try the sample file. The cleaned table appears here with every change highlighted.
        </div>
      ) : (
        <Tabs value={tab} onValueChange={setTab} className="mt-2">
          <TabsList>
            <TabsTrigger value="after">After</TabsTrigger>
            <TabsTrigger value="before">Before</TabsTrigger>
            <TabsTrigger value="removed" count={`(${result.table.removed.length})`}>
              Removed rows
            </TabsTrigger>
          </TabsList>
          <TabsContent value="after">
            <AfterTable rows={result.table.rows} columns={result.table.columns} flagColumn={result.table.flagColumn} />
          </TabsContent>
          <TabsContent value="before">
            <BeforeTable prepared={p} />
          </TabsContent>
          <TabsContent value="removed">
            <RemovedTable rows={result.table.removed} prepared={p} />
          </TabsContent>
        </Tabs>
      )}
      {result && (
        <p className="mt-3 text-[12.5px] text-muted">
          The download keeps the original sheet as “Original” for audit and lists removed rows on their own sheet. Changed cells are shaded, with a note showing the value
          before cleaning.
        </p>
      )}
    </>
  )

  return <ToolLayout left={left} right={right} />
}

function ActionRow({
  action,
  enabled,
  report,
  onToggle,
  children
}: {
  action: CleanerAction
  enabled: boolean
  report: ActionReport | undefined
  onToggle: (v: boolean) => void
  children?: React.ReactNode
}): React.JSX.Element {
  return (
    <div className={cn('rounded-lg border px-3 py-2.5', enabled ? 'border-[#CFE0F7] bg-[#FAFCFF]' : 'border-line')} data-action-row={action}>
      <div className="flex items-start gap-2">
        <Checkbox label={<span className="text-[13px] font-medium">{ACTION_LABEL[action]}</span>} checked={enabled} onCheckedChange={(v) => onToggle(v === true)} />
        {report && <CountPill count={report.count} unit={report.unit} muted={!enabled} />}
      </div>
      {report && <div className="mt-1 pl-[28px] text-[12px] text-muted">{report.summary}</div>}
      {enabled && children && <div className="mt-2 pl-[28px]">{children}</div>}
    </div>
  )
}

function SignChoice({ value, onChange }: { value: boolean; onChange: (crNegative: boolean) => void }): React.JSX.Element {
  return (
    <SegmentedControl
      size="sm"
      className="mt-2"
      aria-label="CR / DR sign"
      value={value ? 'cr' : 'dr'}
      onValueChange={(v) => onChange(v === 'cr')}
      options={[
        { value: 'cr', label: 'CR amounts negative' },
        { value: 'dr', label: 'DR amounts negative' }
      ]}
    />
  )
}

function AmountEditor({ value, columns, onChange }: { value: AmountOptions; columns: string[]; onChange: (v: AmountOptions) => void }): React.JSX.Element {
  const opts = columns.map((c) => ({ value: c, label: c }))
  return (
    <div className="flex flex-col gap-2">
      <SegmentedControl
        size="sm"
        aria-label="Split or combine"
        value={value.mode}
        onValueChange={(mode) =>
          onChange(
            mode === 'split'
              ? { enabled: value.enabled, mode, column: columns[0] ?? '', debitName: 'Debit', creditName: 'Credit', positiveIs: 'debit', crNegative: value.crNegative }
              : { enabled: value.enabled, mode, debit: columns[0] ?? '', credit: columns[1] ?? '', name: 'Amount', positiveIs: 'debit', crNegative: value.crNegative }
          )
        }
        options={[
          { value: 'split', label: 'Split one amount' },
          { value: 'combine', label: 'Combine Debit / Credit' }
        ]}
      />
      {value.mode === 'split' ? (
        <>
          <Select size="sm" aria-label="Amount column" value={value.column} onValueChange={(column) => onChange({ ...value, column })} options={opts} />
          <div className="grid grid-cols-2 gap-2">
            <Input className="h-8 text-[12.5px]" aria-label="Debit column name" value={value.debitName} onChange={(e) => onChange({ ...value, debitName: e.target.value })} />
            <Input className="h-8 text-[12.5px]" aria-label="Credit column name" value={value.creditName} onChange={(e) => onChange({ ...value, creditName: e.target.value })} />
          </div>
          <SegmentedControl
            size="sm"
            aria-label="Positive amounts go to"
            value={value.positiveIs}
            onValueChange={(positiveIs) => onChange({ ...value, positiveIs })}
            options={[
              { value: 'debit', label: 'Positive → Debit' },
              { value: 'credit', label: 'Positive → Credit' }
            ]}
          />
        </>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-2">
            <Select size="sm" aria-label="Debit column" value={value.debit} onValueChange={(debit) => onChange({ ...value, debit })} options={opts} />
            <Select size="sm" aria-label="Credit column" value={value.credit} onValueChange={(credit) => onChange({ ...value, credit })} options={opts} />
          </div>
          <Input className="h-8 text-[12.5px]" aria-label="Combined column name" value={value.name} onChange={(e) => onChange({ ...value, name: e.target.value })} />
          <SegmentedControl
            size="sm"
            aria-label="Sign"
            value={value.positiveIs}
            onValueChange={(positiveIs) => onChange({ ...value, positiveIs })}
            options={[
              { value: 'debit', label: 'Debit − Credit' },
              { value: 'credit', label: 'Credit − Debit' }
            ]}
          />
        </>
      )}
    </div>
  )
}

/** Column types from the cell values (shared parser rules), used to format and align each column. */
function useColumnTypes(columns: string[], rows: CleanRow[], pick: (cell: CleanRow['cells'][number]) => CellValue | undefined): ColumnType[] {
  return useMemo(
    () => columns.map((name, c) => inferColumnType(name, rows.map((r) => pick(r.cells[c]) ?? null))),
    // `pick` is a fixed accessor chosen by the caller; the types change only with the data.
    [columns, rows]
  )
}

function AfterTable({ rows, columns, flagColumn }: { rows: CleanRow[]; columns: string[]; flagColumn?: number }): React.JSX.Element {
  const types = useColumnTypes(columns, rows, (cell) => cell.value)
  const cols = useMemo<DataColumn<CleanRow>[]>(
    () => [
      { id: 'row', header: 'Row', width: 58, numeric: false, value: (r) => r.sourceRow + 1, className: 'text-muted' },
      ...columns.map<DataColumn<CleanRow>>((name, c) => ({
        id: `c${c}`,
        header: name,
        minWidth: c === flagColumn ? 170 : 140,
        cell: (r) => {
          const cell = r.cells[c]
          const changed = isChanged(cell)
          const numeric = isNumericCell(cell.value, types[c])
          return (
            <span
              className={cn(
                '-mx-3 block w-[calc(100%+1.5rem)] truncate px-3 leading-[34px]',
                numeric && 'num text-right',
                changed && 'bg-[#FFF2CC]',
                c === flagColumn && r.duplicateOf !== undefined && 'bg-[#FDE3CF] font-medium text-likely'
              )}
              title={changed && cell.original !== undefined ? `Before: ${valueText(cell.original) || '(blank)'}` : undefined}
              data-changed={changed || undefined}
            >
              {cellText(cell.value, types[c])}
            </span>
          )
        }
      }))
    ],
    [columns, flagColumn, types]
  )
  return <DataTable aria-label="After cleaning" rows={rows} rowKey={(r) => String(r.sourceRow)} columns={cols} rowHeight={34} height={470} />
}

function BeforeTable({ prepared }: { prepared: PreparedSheet }): React.JSX.Element {
  const types = useColumnTypes(prepared.table.columns, prepared.table.rows, (cell) => cell.original)
  const cols = useMemo<DataColumn<CleanRow>[]>(
    () => [
      { id: 'row', header: 'Row', width: 58, numeric: false, value: (r) => r.sourceRow + 1, className: 'text-muted' },
      // Values exactly as stored in the file; numbers stay right-aligned so the columns line up.
      ...prepared.table.columns.map<DataColumn<CleanRow>>((name, c) => ({
        id: `c${c}`,
        header: name,
        minWidth: 120,
        cell: (r) => {
          const v = r.cells[c].original ?? null
          const numeric = isNumericCell(v, types[c])
          return (
            <span className={cn('block truncate', numeric && 'num text-right')}>
              {v instanceof Date ? cellText(v, types[c]) : v === null ? '' : String(v)}
            </span>
          )
        }
      })),
      { id: 'junk', header: 'Row type', width: 140, value: (r) => (r.junk ? REASON_LABEL[r.junk] : ''), className: 'text-unmatched' }
    ],
    [prepared, types]
  )
  return (
    <DataTable
      aria-label="Before cleaning"
      rows={prepared.table.rows}
      rowKey={(r) => String(r.sourceRow)}
      columns={cols}
      rowHeight={34}
      height={470}
      rowClassName={(r) => (r.junk ? 'bg-[#FDF5F5]' : undefined)}
    />
  )
}

function RemovedTable({ rows, prepared }: { rows: RemovedRow[]; prepared: PreparedSheet }): React.JSX.Element {
  const sorted = useMemo(() => [...rows].sort((a, b) => a.sourceRow - b.sourceRow), [rows])
  return (
    <DataTable
      aria-label="Removed rows"
      rows={sorted}
      rowKey={(r) => String(r.sourceRow)}
      height={470}
      empty="No rows are removed with the current settings."
      columns={[
        { id: 'row', header: 'Excel row', width: 90, numeric: false, value: (r) => r.sourceRow + 1 },
        { id: 'reason', header: 'Reason', width: 170, value: (r) => r.label },
        {
          id: 'content',
          header: 'Row content',
          minWidth: 300,
          value: (r) =>
            prepared.table.columns
              .map((_, c) => valueText(prepared.original[r.sourceRow]?.[c] ?? null))
              .filter((s) => s.trim() !== '')
              .join(' | ') || '(blank row)'
        }
      ]}
    />
  )
}
