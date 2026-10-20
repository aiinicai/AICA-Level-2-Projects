import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { RefreshCw } from 'lucide-react'
import type { ColumnType, OpenedFile } from '@shared/contracts'
import { baseName, closePdfJsDocument, formatPageList, openPdfJsDocument, parsePageSelection } from '@tools/common'
import {
  BANK_FIELDS,
  extractPdf,
  reshapeResult,
  toWorkbook,
  type BankField,
  type PdfColumn,
  type PdfExtractResult,
  type PdfRow,
  type PdfShapeOptions,
  type PdfTable,
  type PdfWorkbookOptions
} from '@tools/pdf-to-excel'
import {
  Badge,
  Button,
  Checkbox,
  DataTable,
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DropZone,
  Field,
  formatBytes,
  formatCell,
  Input,
  Select,
  SegmentedControl,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  type DataColumn
} from '@/components/ui'
import { newId } from '@/lib/db'
import { cn } from '@/lib/cn'
import { asPdfToExcelRecipe } from './recipes'
import { Callout, EXCEL_OUT, OutputBar, PDF_IN, SampleFiles, Section, TaskStatus, ToolLayout } from './shared/components'
import { PageThumb } from './shared/PageThumb'
import { OCR_OPTIONS, pdfRuntime, releaseThumbnails } from './shared/pdf'
import { RecipeBar } from './shared/RecipeBar'
import { useToolTask } from './shared/useToolTask'

interface LoadedPdf {
  key: string
  name: string
  data: ArrayBuffer
  size: number
  pageCount: number
}

const DEFAULT_SHAPE: PdfShapeOptions = { layout: 'raw', joinAcrossPages: true, removeRepeatedHeaders: true, convertValues: true }
const DEFAULT_WB: Required<Pick<PdfWorkbookOptions, 'oneSheetPerTable' | 'addPageColumn'>> = { oneSheetPerTable: false, addPageColumn: true }
const TYPE_OPTIONS: Array<{ value: ColumnType; label: string }> = [
  { value: 'text', label: 'Text' },
  { value: 'number', label: 'Number' },
  { value: 'amount', label: 'Amount' },
  { value: 'date', label: 'Date' },
  { value: 'id', label: 'Reference / ID' }
]
const NONE = '__none'
const MAX_THUMBS = 40

const SAMPLES = [
  { label: 'Bank statement (6 pages)', files: ['Bank_Statement_6_pages_digital.pdf'] },
  { label: 'Price list', files: ['Price_List_digital.pdf'] },
  { label: 'Scanned page (OCR)', files: ['Statement_with_scanned_page.pdf'] },
  { label: 'Password-protected', files: ['Password_protected.pdf'] }
]

export function PdfToExcelScreen(): React.JSX.Element {
  const task = useToolTask()
  const [file, setFile] = useState<LoadedPdf | null>(null)
  const [base, setBase] = useState<PdfExtractResult | null>(null)
  const [shape, setShape] = useState<PdfShapeOptions>(DEFAULT_SHAPE)
  const [wbOpts, setWbOpts] = useState(DEFAULT_WB)
  const [pagesText, setPagesText] = useState('')
  const [tab, setTab] = useState('table-0')
  const [editing, setEditing] = useState<{ table: number; column: number } | null>(null)

  /** Key of the file currently on screen; results for any other file are stale and ignored. */
  const currentKey = useRef<string | null>(null)
  // Leaving the screen frees the open pdf.js document and the page thumbnails.
  useEffect(
    () => () => {
      if (currentKey.current) releaseThumbnails(currentKey.current)
      currentKey.current = null
    },
    []
  )

  const openEdit = useCallback((table: number, column: number) => setEditing({ table, column }), [])
  const result = useMemo(() => (base ? reshapeResult(base, shape) : null), [base, shape])
  const rawColumns = useMemo(
    () => (base ? (reshapeResult(base, { ...shape, layout: 'raw', columnEdits: undefined }).tables[0]?.columns.map((c) => c.key) ?? []) : []),
    [base, shape]
  )

  const extract = async (f: LoadedPdf, pages: string, current: PdfShapeOptions): Promise<void> => {
    let pagesOpt: string | undefined
    try {
      pagesOpt = pages.trim() ? formatPageList(parsePageSelection(pages, f.pageCount)) : undefined
    } catch (e) {
      task.setError(e instanceof Error ? e.message : 'Check the page range.')
      return
    }
    const r = await task.run('Reading the PDF', async (signal, report) => {
      const rt = await pdfRuntime()
      return extractPdf(
        f.data,
        { ...rt, ...current, ocr: OCR_OPTIONS, fileName: f.name, pages: pagesOpt },
        (p) =>
          report({
            label: p.stage === 'ocr' ? `OCR on page ${p.page}` : `Reading page ${p.page}`,
            value: ((p.index - 1) / p.pages) * 100,
            detail: `${p.index}/${p.pages}`
          }),
        signal
      )
    })
    // Another file was loaded while this one was being read: drop the stale result.
    if (r && currentKey.current === f.key) {
      setBase(r)
      setTab('table-0')
    }
  }

  const load = async (files: OpenedFile[]): Promise<void> => {
    const f = files[0]
    if (!f) return
    // Stop any extraction still running for the previous file and forget that file.
    task.cancel()
    if (currentKey.current) releaseThumbnails(currentKey.current)
    const key = newId()
    currentKey.current = key
    setBase(null)
    setFile(null)
    task.setError(null)
    // Open with pdf.js: a PDF that needs a password to open gets the password message, while one that is only
    // protected against editing (owner password) opens and converts normally.
    const pageCount = await task.run('Opening the PDF', async (signal) => {
      const rt = await pdfRuntime()
      const doc = await openPdfJsDocument(f.data, rt, signal)
      try {
        return doc.numPages
      } finally {
        await closePdfJsDocument(doc)
      }
    })
    if (pageCount === undefined || currentKey.current !== key) return
    const loaded: LoadedPdf = { key, name: f.name, data: f.data, size: f.data.byteLength, pageCount }
    setFile(loaded)
    await extract(loaded, pagesText, shape)
  }

  const applyRecipe = (options: unknown): void => {
    const r = asPdfToExcelRecipe(options)
    if (!r) {
      task.setError('This recipe could not be read. Save it again from this screen.')
      return
    }
    const { oneSheetPerTable, addPageColumn, includeExcludedSheet: _ignored, pages, ...rest } = r
    const nextShape: PdfShapeOptions = { ...DEFAULT_SHAPE, ...rest }
    setShape(nextShape)
    setWbOpts({ oneSheetPerTable: oneSheetPerTable ?? DEFAULT_WB.oneSheetPerTable, addPageColumn: addPageColumn ?? DEFAULT_WB.addPageColumn })
    const nextPages = pages ?? ''
    setPagesText(nextPages)
    if (file && nextPages !== pagesText) void extract(file, nextPages, nextShape)
  }

  const textPages = result?.pages.filter((p) => p.method === 'text').map((p) => p.page) ?? []
  const ocrPages = result?.ocrPages ?? []
  const skipped = result?.pages.filter((p) => p.method === 'scanned-skipped' || p.method === 'empty').map((p) => p.page) ?? []
  const lowConfidence = result?.tables.reduce((n, t) => n + t.rows.reduce((m, r) => m + r.cells.filter((c) => c.lowConfidence).length, 0), 0) ?? 0
  const totalRows = result?.tables.reduce((n, t) => n + t.rows.length, 0) ?? 0

  const editColumn = editing && result ? result.tables[editing.table]?.columns[editing.column] : undefined

  const left = (
    <>
      <RecipeBar
        tool="pdf-to-excel"
        canSave={!!result}
        current={() => ({ ...shape, ...wbOpts, pages: pagesText.trim() || undefined })}
        onApply={applyRecipe}
      />
      <Section title="Source PDF">
        <DropZone
          accept={[PDF_IN]}
          onFiles={(f) => void load(f)}
          file={file ? { name: file.name, size: file.size } : null}
          info={file ? `${file.pageCount} page${file.pageCount === 1 ? '' : 's'} · ${formatBytes(file.size)}` : undefined}
          busy={task.running && !task.progress}
          status={result ? undefined : null}
          title="Drop a PDF here or click to browse"
          dialogTitle="Choose a PDF"
        />
        <SampleFiles samples={SAMPLES} onLoad={(f) => void load(f)} disabled={task.running} />
        {result && (
          <div className="mt-2.5 flex flex-wrap gap-1.5" data-testid="page-methods">
            {textPages.length > 0 && (
              <Badge tone="matched">
                Digital text: page{textPages.length === 1 ? '' : 's'} {formatPageList(textPages)}
              </Badge>
            )}
            {ocrPages.length > 0 && (
              <Badge tone="ai" data-ocr-pages={ocrPages.join(',')}>
                Scanned: page{ocrPages.length === 1 ? '' : 's'} {formatPageList(ocrPages)} → OCR
              </Badge>
            )}
            {skipped.length > 0 && <Badge tone="unmatched">Not read: page{skipped.length === 1 ? '' : 's'} {formatPageList(skipped)}</Badge>}
          </div>
        )}
        <TaskStatus task={task} />
        {result && result.warnings.length > 0 && (
          <Callout className="mt-3">
            {result.warnings.map((w) => (
              <div key={w}>{w}</div>
            ))}
          </Callout>
        )}
      </Section>

      <Section title="Output layout">
        <SegmentedControl
          aria-label="Output layout"
          value={shape.layout ?? 'raw'}
          onValueChange={(layout) => setShape((s) => ({ ...s, layout, columnEdits: undefined }))}
          options={[
            { value: 'raw', label: 'Raw tables' },
            { value: 'bank', label: 'Bank statement' }
          ]}
        />
        <p className="mt-2 text-[12.5px] leading-snug text-muted">
          Raw tables keeps the PDF&apos;s own columns. Bank statement layout maps to Date · Value Date · Description · Reference · Debit · Credit · Balance.
        </p>
        {shape.layout === 'bank' && result?.bankMapping && (
          <div className="mt-3 rounded-lg border border-line bg-[#FAFBFD] p-3" data-testid="bank-mapping">
            <div className="mb-2 text-[12.5px] font-semibold text-ink">Column mapping (suggested, change if needed)</div>
            <div className="grid grid-cols-[96px_1fr] items-center gap-x-3 gap-y-1.5">
              {BANK_FIELDS.map((f: BankField) => (
                <BankRow
                  key={f}
                  field={f}
                  value={result.bankMapping?.[f] ?? null}
                  columns={rawColumns}
                  onChange={(v) => setShape((s) => ({ ...s, bankMapping: { ...s.bankMapping, [f]: v } }))}
                />
              ))}
            </div>
            {result.bankUnmapped.length > 0 && (
              <p className="mt-2 text-[12px] text-doubtful">Not used: {result.bankUnmapped.join(', ')}. Map them above if they hold data you need.</p>
            )}
          </div>
        )}
      </Section>

      <Section title="Pages">
        <div className="flex items-center gap-2">
          <Button variant={pagesText.trim() ? 'secondary' : 'outline'} size="sm" onClick={() => setPagesText('')}>
            All pages
          </Button>
          <span className="text-[13px] text-muted">or</span>
          <Input
            aria-label="Page range"
            className="h-8 flex-1 text-[13px]"
            placeholder="e.g. 1-3, 5"
            value={pagesText}
            onChange={(e) => setPagesText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && file) void extract(file, pagesText, shape)
            }}
          />
        </div>
      </Section>

      <Section title="Clean-up">
        <div className="flex flex-col gap-2.5">
          <Checkbox
            label="Join tables that continue across pages"
            checked={shape.joinAcrossPages ?? true}
            onCheckedChange={(v) => setShape((s) => ({ ...s, joinAcrossPages: v === true }))}
          />
          <Checkbox
            label="Remove repeated page headers & footers"
            checked={shape.removeRepeatedHeaders ?? true}
            onCheckedChange={(v) => setShape((s) => ({ ...s, removeRepeatedHeaders: v === true }))}
          />
          <Checkbox
            label="Convert text numbers & dates to real values"
            checked={shape.convertValues ?? true}
            onCheckedChange={(v) => setShape((s) => ({ ...s, convertValues: v === true }))}
          />
          <Checkbox
            label="One sheet per table (instead of one sheet)"
            checked={wbOpts.oneSheetPerTable}
            onCheckedChange={(v) => setWbOpts((s) => ({ ...s, oneSheetPerTable: v === true }))}
          />
          <Checkbox
            label='Add "Page" column for traceability'
            checked={wbOpts.addPageColumn}
            onCheckedChange={(v) => setWbOpts((s) => ({ ...s, addPageColumn: v === true }))}
          />
        </div>
        {result && (result.needsDateOrder || shape.dateOrder) && (
          <Callout className="mt-3" tone={result.needsDateOrder ? 'doubtful' : 'info'}>
            <div className="mb-2">
              {result.needsDateOrder
                ? 'Some dates could be read either way (for example 03/09/2026). How are dates written in this PDF?'
                : `Dates are read as ${shape.dateOrder === 'MDY' ? 'MM/DD/YYYY' : 'DD/MM/YYYY'}.`}
            </div>
            <SegmentedControl
              size="sm"
              aria-label="Date order"
              value={shape.dateOrder ?? ''}
              onValueChange={(dateOrder) => setShape((s) => ({ ...s, dateOrder: dateOrder as 'DMY' | 'MDY' }))}
              options={[
                { value: 'DMY', label: 'DD/MM/YYYY' },
                { value: 'MDY', label: 'MM/DD/YYYY' }
              ]}
            />
          </Callout>
        )}
      </Section>

      <OutputBar
        defaultName={file ? `${baseName(file.name)}.xlsx` : 'Converted.xlsx'}
        extension="xlsx"
        filter={EXCEL_OUT}
        label="Download Excel"
        disabled={!result || task.running}
        build={async () => (result ? toWorkbook(result, { ...wbOpts, includeExcludedSheet: true }) : undefined)}
        extra={
          <Button variant="outline" disabled={!file || task.running} onClick={() => file && void extract(file, pagesText, shape)}>
            <RefreshCw size={14} /> Convert again
          </Button>
        }
      />
    </>
  )

  const right = (
    <>
      <div className="flex items-baseline justify-between gap-4">
        <div className="text-[11.5px] font-bold tracking-[1.2px] text-muted uppercase" data-testid="preview-title">
          {result
            ? `Preview: ${result.tables.length} table${result.tables.length === 1 ? '' : 's'} · ${totalRows.toLocaleString('en-US')} rows · ${result.tables[0]?.columns.length ?? 0} columns${wbOpts.addPageColumn ? ' + page' : ''}`
            : 'Preview'}
        </div>
        {result && <div className="text-[12.5px] text-muted">Click a header to rename or set its type</div>}
      </div>

      {file && (
        <div className="mt-3 flex gap-2.5 overflow-x-auto pb-1">
          {Array.from({ length: Math.min(file.pageCount, MAX_THUMBS) }, (_, i) => {
            const ocr = ocrPages.includes(i + 1)
            return (
              <PageThumb
                key={i}
                fileKey={file.key}
                data={file.data}
                page={i}
                width={70}
                tone={ocr ? 'ocr' : 'default'}
                selected={i === 0}
                label={ocr ? `${i + 1} · OCR` : `${i + 1}`}
              />
            )
          })}
          {file.pageCount > MAX_THUMBS && <div className="self-center text-[12px] whitespace-nowrap text-muted">+{file.pageCount - MAX_THUMBS} more</div>}
        </div>
      )}

      {!result ? (
        <div className="mt-6 grid h-[360px] place-items-center rounded-lg border border-dashed border-line text-center text-[13px] text-muted">
          {task.running ? 'Reading the PDF…' : 'Drop a PDF on the left, or try a sample file. The extracted table appears here.'}
        </div>
      ) : (
        <Tabs value={tab} onValueChange={setTab} className="mt-3">
          <TabsList>
            {result.tables.map((t, i) => (
              <TabsTrigger key={t.name} value={`table-${i}`}>
                Sheet: {result.tables.length === 1 ? 'Data' : t.name}
              </TabsTrigger>
            ))}
            <TabsTrigger value="excluded" count={`(${result.excluded.length})`}>
              Excluded rows
            </TabsTrigger>
          </TabsList>
          {result.tables.map((t, i) => (
            <TabsContent key={t.name} value={`table-${i}`}>
              <PdfTablePreview table={t} tableIndex={i} addPage={wbOpts.addPageColumn} onEdit={openEdit} />
            </TabsContent>
          ))}
          <TabsContent value="excluded">
            <DataTable
              aria-label="Excluded rows"
              rows={result.excluded}
              rowKey={(_, i) => String(i)}
              height={420}
              empty="No rows were excluded."
              columns={[
                { id: 'page', header: 'Page', width: 64, value: (r) => r.page, numeric: false },
                { id: 'reason', header: 'Why', width: 230, value: (r) => r.detail },
                { id: 'text', header: 'Text', minWidth: 260, value: (r) => r.text }
              ]}
            />
          </TabsContent>
        </Tabs>
      )}

      {result && (
        <div className="mt-3 flex items-center justify-between gap-4 text-[12.5px] text-muted">
          <span>
            {lowConfidence > 0 ? (
              <>
                <span className="mr-1 inline-block h-3 w-3 rounded-sm bg-[#FFE08A] align-middle" /> Amber cells ({lowConfidence}) = OCR confidence below{' '}
                {result.lowConfidenceBelow}%. Check before using.
              </>
            ) : ocrPages.length > 0 ? (
              `OCR used on page${ocrPages.length === 1 ? '' : 's'} ${formatPageList(ocrPages)}; every cell read with confidence of ${result.lowConfidenceBelow}% or more.`
            ) : (
              'All pages had a text layer; no OCR was needed.'
            )}
          </span>
          <span className="whitespace-nowrap">Read in {(result.durationMs / 1000).toFixed(1)} s</span>
        </div>
      )}

      <ColumnDialog
        column={editColumn}
        onClose={() => setEditing(null)}
        onSave={(name, type) => {
          if (!editColumn) return
          setShape((s) => ({ ...s, columnEdits: { ...s.columnEdits, [editColumn.key]: { name, type } } }))
          setEditing(null)
        }}
      />
    </>
  )

  return <ToolLayout left={left} right={right} />
}

function BankRow({ field, value, columns, onChange }: { field: BankField; value: string | null; columns: string[]; onChange: (v: string | null) => void }): React.JSX.Element {
  return (
    <>
      <span className="text-[12.5px] text-ink">{field}</span>
      <Select
        size="sm"
        aria-label={`Source column for ${field}`}
        value={value ?? NONE}
        onValueChange={(v) => onChange(v === NONE ? null : v)}
        options={[{ value: NONE, label: '— leave empty —' }, ...columns.map((c) => ({ value: c, label: c }))]}
      />
    </>
  )
}

function PdfTablePreview({ table, tableIndex, addPage, onEdit }: { table: PdfTable; tableIndex: number; addPage: boolean; onEdit: (table: number, column: number) => void }): React.JSX.Element {
  const columns = useMemo<DataColumn<PdfRow>[]>(() => {
    const cols: DataColumn<PdfRow>[] = table.columns.map((c: PdfColumn, i) => {
      const numeric = c.type === 'amount' || c.type === 'number'
      return {
        id: `c${i}`,
        minWidth: c.type === 'text' ? 180 : 110,
        numeric,
        header: (
          <button type="button" className="font-semibold hover:text-primary hover:underline" onClick={() => onEdit(tableIndex, i)} title="Rename or change type">
            {c.name}
          </button>
        ),
        subHeader: c.type === 'id' ? 'reference' : c.type,
        cell: (row: PdfRow) => {
          const cell = row.cells[i]
          const text = cell ? formatCell(cell.value, numeric ? true : typeof cell.value === 'number' ? false : undefined) : ''
          return (
            <span
              className={cn('-mx-3 block w-[calc(100%+1.5rem)] truncate px-3 leading-[36px]', cell?.lowConfidence && 'bg-[#FFF1C2]')}
              title={cell?.lowConfidence ? `OCR confidence ${cell.confidence ?? 'low'}%. Read as "${cell.text}".` : text}
              data-low-confidence={cell?.lowConfidence || undefined}
            >
              {text}
            </span>
          )
        }
      }
    })
    if (addPage) cols.unshift({ id: 'page', header: 'Page', width: 64, value: (r) => r.page, numeric: false })
    return cols
  }, [table, tableIndex, addPage, onEdit])
  return <DataTable aria-label={table.name} rows={table.rows} rowKey={(_, i) => String(i)} columns={columns} height={440} />
}

function ColumnDialog({ column, onClose, onSave }: { column: PdfColumn | undefined; onClose: () => void; onSave: (name: string, type: ColumnType) => void }): React.JSX.Element {
  const [name, setName] = useState('')
  const [type, setType] = useState<ColumnType>('text')
  const [lastKey, setLastKey] = useState<string | null>(null)
  if (column && column.key !== lastKey) {
    setLastKey(column.key)
    setName(column.name)
    setType(column.type)
  }
  if (!column && lastKey !== null) setLastKey(null)
  return (
    <Dialog open={!!column} onOpenChange={(o) => !o && onClose()}>
      <DialogContent width={420}>
        <DialogHeader>
          <DialogTitle>Column “{column?.key}”</DialogTitle>
          <DialogDescription>Rename the column or change how its values are read. The change is kept in recipes.</DialogDescription>
        </DialogHeader>
        <DialogBody className="flex flex-col gap-4">
          <Field label="Column name" htmlFor="col-name">
            <Input id="col-name" value={name} onChange={(e) => setName(e.target.value)} autoFocus />
          </Field>
          <Field label="Type" hint="Amount and number columns become real numbers; date columns become real dates.">
            <Select value={type} onValueChange={(v) => setType(v as ColumnType)} options={TYPE_OPTIONS} aria-label="Column type" />
          </Field>
        </DialogBody>
        <DialogFooter>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button disabled={!name.trim()} onClick={() => onSave(name.trim(), type)}>
            Apply
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
