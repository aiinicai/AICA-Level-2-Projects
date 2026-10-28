import { useEffect, useMemo, useRef, useState } from 'react'
import type { ColumnType, OpenedFile, ParsedTable, WorkbookData } from '@shared/contracts'
import { inferColumnType, parseTable, readWorkbook } from '@shared/parsing'
import { baseName, offscreenCanvasFactory, renderThumbnail } from '@tools/common'
import { sheetToPdfDetailed, type ExcelToPdfOptions, type ExcelToPdfResult } from '@tools/excel-to-pdf'
import { Checkbox, DropZone, Field, Input, Select, SegmentedControl, Spinner } from '@/components/ui'
import { ColumnChips, EXCEL_IN, OutputBar, PDF_OUT, SampleFiles, Section, TaskStatus, ToolLayout } from './shared/components'
import { pdfRuntime } from './shared/pdf'
import { nextFrame, toolErrorMessage, useToolTask } from './shared/useToolTask'

interface Loaded {
  name: string
  size: number
  wb: WorkbookData
}

const SAMPLES = [{ label: 'Trial balance', files: ['Sheet_to_print.xlsx'] }]

const DEFAULTS: ExcelToPdfOptions = {
  orientation: 'auto',
  pageSize: 'a4',
  fitToWidth: true,
  repeatHeader: true,
  pageNumbers: true,
  gridlines: true,
  keepFormatting: true
}

/** First text found above the header row (often the report title, e.g. "Trial balance as at 30-Sep-2026"). */
function titleAbove(wb: WorkbookData, sheet: string, table: ParsedTable): string {
  const rows = wb.sheets.find((s) => s.name === sheet)?.rows ?? []
  for (let r = 0; r < table.headerRowIndex; r++) {
    const v = rows[r]?.find((c) => typeof c === 'string' && c.trim() !== '')
    if (typeof v === 'string') return v.trim()
  }
  return ''
}

export function ExcelToPdfScreen(): React.JSX.Element {
  const task = useToolTask()
  const [file, setFile] = useState<Loaded | null>(null)
  const [sheet, setSheet] = useState('')
  const [columns, setColumns] = useState<string[]>([])
  const [totals, setTotals] = useState<string[]>([])
  const [opts, setOpts] = useState<ExcelToPdfOptions>(DEFAULTS)
  const [title, setTitle] = useState('')
  const [subtitle, setSubtitle] = useState('')
  const [preview, setPreview] = useState<{ url: string; result: ExcelToPdfResult } | null>(null)
  const [previewError, setPreviewError] = useState<string | null>(null)
  const [rendering, setRendering] = useState(false)
  const seq = useRef(0)
  const urlRef = useRef<string | null>(null)

  const table = useMemo<ParsedTable | null>(() => {
    if (!file || !sheet) return null
    const s = file.wb.sheets.find((x) => x.name === sheet)
    return s ? parseTable(s, { fileName: file.name }) : null
  }, [file, sheet])

  const types = useMemo<Record<string, ColumnType>>(() => {
    if (!table) return {}
    return Object.fromEntries(table.columns.map((c) => [c, inferColumnType(c, table.rows.map((r) => r.values[c] ?? null))]))
  }, [table])
  const numericColumns = table ? table.columns.filter((c) => types[c] === 'amount' || types[c] === 'number') : []

  const pickSheet = (wb: WorkbookData, name: string, fileName: string): void => {
    const s = wb.sheets.find((x) => x.name === name)
    if (!s) return
    const t = parseTable(s, { fileName })
    setSheet(name)
    setColumns(t.columns)
    setTotals([])
    setTitle(titleAbove(wb, name, t))
    setSubtitle('')
  }

  const loadSeq = useRef(0)
  const load = async (files: OpenedFile[]): Promise<void> => {
    const f = files[0]
    if (!f) return
    const id = ++loadSeq.current
    const wb = await task.run('Reading the workbook', async () => readWorkbook(f.data, f.name))
    // A newer file was dropped while this one was being read: ignore this result.
    if (!wb || id !== loadSeq.current) return
    const first = wb.sheets.find((s) => s.rows.some((r) => r.some((v) => v !== null))) ?? wb.sheets[0]
    if (!first) {
      task.setError('This workbook has no sheets with data.')
      return
    }
    setFile({ name: f.name, size: f.data.byteLength, wb })
    pickSheet(wb, first.name, f.name)
  }

  const fullOptions = useMemo<ExcelToPdfOptions>(
    () => ({
      ...opts,
      title: title.trim() || undefined,
      subtitle: subtitle.trim() || undefined,
      columns: table ? table.columns.filter((c) => columns.includes(c)) : undefined,
      totals: totals.filter((t) => columns.includes(t)),
      columnTypes: types
    }),
    [opts, title, subtitle, columns, totals, types, table]
  )

  /** Drops the current preview and frees its image. */
  const clearPreview = (): void => {
    setPreview((old) => {
      if (old) URL.revokeObjectURL(old.url)
      return null
    })
    urlRef.current = null
  }

  // Live first-page preview: build the PDF, then draw its page 1 with pdf.js.
  useEffect(() => {
    if (!table) {
      seq.current++
      clearPreview()
      setPreviewError(null)
      setRendering(false)
      return
    }
    const id = ++seq.current
    setRendering(true)
    const timer = window.setTimeout(() => {
      void (async () => {
        try {
          await nextFrame()
          const result = sheetToPdfDetailed(table, fullOptions)
          const rt = await pdfRuntime()
          const thumb = await renderThumbnail<OffscreenCanvas>(result.data, 0, 1000, { ...rt, canvasFactory: offscreenCanvasFactory })
          const blob = await thumb.canvas.convertToBlob({ type: 'image/png' })
          if (id !== seq.current) return
          const url = URL.createObjectURL(blob)
          urlRef.current = url
          setPreview((old) => {
            if (old) URL.revokeObjectURL(old.url)
            return { url, result }
          })
          setPreviewError(null)
        } catch (e) {
          if (id === seq.current) {
            // Never leave the previous sheet's PDF behind a failed preview: Download would save it.
            clearPreview()
            setPreviewError(toolErrorMessage(e))
          }
        } finally {
          if (id === seq.current) setRendering(false)
        }
      })()
    }, 250)
    return () => window.clearTimeout(timer)
  }, [table, fullOptions])

  useEffect(
    () => () => {
      if (urlRef.current) URL.revokeObjectURL(urlRef.current)
    },
    []
  )

  const set = <K extends keyof ExcelToPdfOptions>(k: K, v: ExcelToPdfOptions[K]): void => setOpts((o) => ({ ...o, [k]: v }))

  const left = (
    <>
      <Section title="Source sheet">
        <DropZone
          accept={[EXCEL_IN]}
          onFiles={(f) => void load(f)}
          file={file ? { name: file.name, size: file.size } : null}
          info={
            table
              ? `${table.rows.length.toLocaleString('en-US')} rows · ${table.headerRowIndex < 0 ? 'no header row' : `header on row ${table.headerRowIndex + 1}`} · ${table.columns.length} columns`
              : undefined
          }
          busy={task.running}
          title="Drop an Excel or CSV file here"
          dialogTitle="Choose a sheet to print"
        />
        <SampleFiles samples={SAMPLES} onLoad={(f) => void load(f)} disabled={task.running} />
        <TaskStatus task={task} />
        {file && file.wb.sheets.length > 1 && (
          <Field label="Sheet" className="mt-3">
            <Select
              aria-label="Sheet"
              value={sheet}
              onValueChange={(v) => pickSheet(file.wb, v, file.name)}
              options={file.wb.sheets.map((s) => ({ value: s.name, label: s.name }))}
            />
          </Field>
        )}
      </Section>

      {table && (
        <>
          <Section title="Columns to print" right={`${columns.length} of ${table.columns.length}`}>
            <ColumnChips columns={table.columns} value={columns} onChange={setColumns} />
          </Section>

          <Section title="Page">
            <SegmentedControl
              size="sm"
              aria-label="Orientation"
              value={opts.orientation ?? 'auto'}
              onValueChange={(v) => set('orientation', v)}
              options={[
                { value: 'auto', label: 'Auto' },
                { value: 'portrait', label: 'Portrait' },
                { value: 'landscape', label: 'Landscape' }
              ]}
            />
            <div className="mt-2.5 grid grid-cols-[1fr_120px] items-center gap-3">
              <span className="text-[13px] text-ink">Paper size</span>
              <Select
                size="sm"
                aria-label="Paper size"
                value={opts.pageSize ?? 'a4'}
                onValueChange={(v) => set('pageSize', v as ExcelToPdfOptions['pageSize'])}
                options={[
                  { value: 'a4', label: 'A4' },
                  { value: 'letter', label: 'Letter' },
                  { value: 'legal', label: 'Legal' }
                ]}
              />
            </div>
            <div className="mt-3 flex flex-col gap-2.5">
              <Checkbox label="Fit all columns to the page width" checked={opts.fitToWidth ?? true} onCheckedChange={(v) => set('fitToWidth', v === true)} />
              <Checkbox label="Repeat the header row on every page" checked={opts.repeatHeader ?? true} onCheckedChange={(v) => set('repeatHeader', v === true)} />
              <Checkbox label='Page numbers "Page x of y"' checked={opts.pageNumbers ?? true} onCheckedChange={(v) => set('pageNumbers', v === true)} />
              <Checkbox label="Gridlines" checked={opts.gridlines ?? true} onCheckedChange={(v) => set('gridlines', v === true)} />
              <Checkbox
                label="Keep number and date formatting"
                description="1,234.50 and 03-Sep-2026"
                checked={opts.keepFormatting ?? true}
                onCheckedChange={(v) => set('keepFormatting', v === true)}
              />
            </div>
          </Section>

          {preview && preview.result.ambiguousDateColumns.length > 0 && (
            <Section title="Date format">
              <p className="mb-2 text-[12.5px] text-muted" data-testid="date-order-note">
                Dates in {preview.result.ambiguousDateColumns.join(', ')} can be read both ways (e.g. 03/09/2026). How are they written?
              </p>
              <SegmentedControl
                size="sm"
                aria-label="Date order"
                value={opts.dateOrder ?? 'DMY'}
                onValueChange={(v) => set('dateOrder', v)}
                options={[
                  { value: 'DMY', label: 'DD/MM/YYYY' },
                  { value: 'MDY', label: 'MM/DD/YYYY' }
                ]}
              />
            </Section>
          )}

          <Section title="Title">
            <div className="flex flex-col gap-2">
              <Input aria-label="Title" placeholder="Title, e.g. Desert Pearl Trading LLC" value={title} onChange={(e) => setTitle(e.target.value)} />
              <Input aria-label="Subtitle" placeholder="Subtitle, e.g. Trial balance as at 30-Sep-2026" value={subtitle} onChange={(e) => setSubtitle(e.target.value)} />
            </div>
          </Section>

          {numericColumns.length > 0 && (
            <Section title="Totals row">
              <p className="mb-2 text-[12.5px] text-muted">Add a final “Total” row for these columns:</p>
              <ColumnChips columns={numericColumns.filter((c) => columns.includes(c))} value={totals} onChange={setTotals} />
            </Section>
          )}
        </>
      )}

      <OutputBar
        defaultName={file ? `${baseName(file.name)}${file.wb.sheets.length > 1 ? `_${sheet}` : ''}.pdf` : 'Sheet.pdf'}
        extension="pdf"
        filter={PDF_OUT}
        label="Download PDF"
        disabled={!table || columns.length === 0 || previewError !== null}
        build={async () => {
          if (!table) return undefined
          if (preview && !rendering) return preview.result.data
          return task.run('Building the PDF', async () => sheetToPdfDetailed(table, fullOptions).data)
        }}
      />
    </>
  )

  const right = (
    <>
      <div className="flex items-baseline justify-between gap-4">
        <div className="text-[11.5px] font-bold tracking-[1.2px] text-muted uppercase" data-testid="preview-title">
          {preview && table
            ? `Preview: page 1 of ${preview.result.pages} · ${preview.result.orientation} · ${preview.result.fontSize} pt`
            : 'Preview of the first page'}
        </div>
        {rendering && <Spinner size={16} />}
      </div>
      <div className="mt-3 grid min-h-[520px] place-items-center rounded-lg border border-line bg-[#EEF1F5] p-5">
        {previewError ? (
          <p className="max-w-sm text-center text-[13px] text-unmatched">{previewError}</p>
        ) : preview && table ? (
          <img
            src={preview.url}
            alt="First page of the PDF"
            data-testid="pdf-preview"
            className="max-h-[720px] w-auto max-w-full bg-white shadow-[0_4px_18px_rgba(15,42,68,0.18)]"
          />
        ) : (
          <p className="text-center text-[13px] text-muted">Drop a sheet on the left, or try the sample file. The first page of the PDF appears here.</p>
        )}
      </div>
      {preview && table && (
        <p className="mt-3 text-[12.5px] text-muted">
          {table.rows.length.toLocaleString('en-US')} rows on {preview.result.pages} page{preview.result.pages === 1 ? '' : 's'}
          {opts.repeatHeader ?? true ? ', header repeated on every page' : ''}. Rows excluded from the sheet (blank, total, opening/closing): {table.excluded.length}.
        </p>
      )}
    </>
  )

  return <ToolLayout left={left} right={right} />
}
