import { useMemo, useRef, useState } from 'react'
import { ArrowDown, ArrowLeft, ArrowRight, ArrowUp, Plus, X } from 'lucide-react'
import type { OpenedFile } from '@shared/contracts'
import { baseName } from '@tools/common'
import {
  loadMergeSources,
  mappingFromRecipe,
  mergeSources,
  mergeToWorkbook,
  moveOutputColumn,
  recipeFromMapping,
  renameOutputColumn,
  setColumnTarget,
  suggestMapping,
  type MergeFilesRecipeOptions,
  type MergeMapping,
  type MergeResult,
  type MergeRow,
  type MergeSource
} from '@tools/merge-files'
import { extractPdf } from '@tools/pdf-to-excel'
import {
  Button,
  Checkbox,
  DataTable,
  DropZone,
  FileTile,
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
import { asMergeFilesRecipe } from './recipes'
import { Callout, EXCEL_OUT, MERGE_IN, OutputBar, SampleFiles, Section, TaskStatus, ToolLayout } from './shared/components'
import { OCR_OPTIONS, pdfRuntime } from './shared/pdf'
import { RecipeBar } from './shared/RecipeBar'
import { toolErrorMessage, useToolTask } from './shared/useToolTask'

const SAMPLES = [
  { label: '3 monthly statements', files: ['Statement_Jul2026.xlsx', 'Statement_Aug2026.xlsx', 'Statement_Sep2026.xlsx'] },
  { label: 'PDF + Excel statement', files: ['Bank_Statement_6_pages_digital.pdf', 'Statement_Sep2026.xlsx'] }
]
const NONE = '__none'
const KEEP = '__keep'

let batch = 0

/** Gives sources from a new batch of files ids that cannot clash with sources already loaded. */
function rekey(sources: MergeSource[]): MergeSource[] {
  batch++
  return sources.map((s) => {
    const id = `${batch}.${s.id}`
    return { ...s, id, excluded: s.excluded.map((e) => ({ ...e, sourceId: id })) }
  })
}

export function MergeFilesScreen(): React.JSX.Element {
  const task = useToolTask()
  const toast = useToast()
  const [sources, setSources] = useState<MergeSource[]>([])
  const [mapping, setMapping] = useState<MergeMapping>({ columns: [], sources: {} })
  const [sortBy, setSortBy] = useState<string | null>(null)
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc')
  const [addSource, setAddSource] = useState(true)
  const [dateOrder, setDateOrder] = useState<'DMY' | 'MDY' | undefined>(undefined)
  const [recipe, setRecipe] = useState<MergeFilesRecipeOptions | null>(null)
  const [tab, setTab] = useState('columns')
  /** Always the latest source list, so a load that finishes later never overwrites files added meanwhile. */
  const sourcesRef = useRef<MergeSource[]>([])
  const updateSources = (next: MergeSource[]): void => {
    sourcesRef.current = next
    setSources(next)
  }

  const merged = useMemo<{ result: MergeResult | null; error: string | null }>(() => {
    if (sources.length === 0) return { result: null, error: null }
    try {
      return { result: mergeSources(sources, { mapping, sortBy, sortDirection, addSourceColumns: addSource, dateOrder }), error: null }
    } catch (e) {
      return { result: null, error: toolErrorMessage(e) }
    }
  }, [sources, mapping, sortBy, sortDirection, addSource, dateOrder])
  const result = merged.result

  const remap = (all: MergeSource[], r: MergeFilesRecipeOptions | null): void => {
    const m = r ? mappingFromRecipe(all, r) : suggestMapping(all)
    setMapping(m)
    if (sortBy && !m.columns.includes(sortBy)) setSortBy(null)
  }

  const add = async (files: OpenedFile[]): Promise<void> => {
    const loaded = await task.run('Reading files', async (signal, report) => {
      const rt = await pdfRuntime()
      return loadMergeSources(files, {
        signal,
        onProgress: (p) => report({ label: `Reading ${p.name}`, value: ((p.file - 1) / p.files) * 100, detail: `File ${p.file} of ${p.files}` }),
        extractPdf: (data, fileName, s) => extractPdf(data, { ...rt, ocr: OCR_OPTIONS, fileName }, undefined, s)
      })
    })
    if (!loaded) return
    const all = [...sourcesRef.current, ...rekey(loaded)]
    updateSources(all)
    remap(all, recipe)
    setTab('columns')
  }

  const removeSource = (id: string): void => {
    const all = sourcesRef.current.filter((s) => s.id !== id)
    updateSources(all)
    const rest = { ...mapping.sources }
    delete rest[id]
    const used = new Set(Object.values(rest).flatMap((m) => Object.values(m).filter((t): t is string => !!t)))
    setMapping({ columns: mapping.columns.filter((c) => used.has(c)), sources: rest })
  }

  const moveSource = (i: number, d: -1 | 1): void => {
    const j = i + d
    if (j < 0 || j >= sources.length) return
    const next = [...sourcesRef.current]
    ;[next[i], next[j]] = [next[j], next[i]]
    updateSources(next)
  }

  const applyRecipe = (options: unknown): void => {
    const r = asMergeFilesRecipe(options)
    if (!r) {
      task.setError('This recipe could not be read. Save it again from this screen.')
      return
    }
    setRecipe(r)
    setSortDirection(r.sortDirection)
    setAddSource(r.addSourceColumns)
    setDateOrder(r.dateOrder)
    if (sources.length) {
      const m = mappingFromRecipe(sources, r)
      setMapping(m)
      setSortBy(r.sortBy && m.columns.includes(r.sortBy) ? r.sortBy : null)
    } else setSortBy(r.sortBy)
    toast.info('Recipe applied', sources.length ? 'Columns were matched by the recipe.' : 'Add the files; their columns will be matched by the recipe.')
  }

  const edit = (fn: (m: MergeMapping) => MergeMapping): void => {
    try {
      setMapping(fn(mapping))
    } catch (e) {
      toast.error('Not changed', toolErrorMessage(e))
    }
  }

  const summaryOf = (id: string): MergeResult['summary'][number] | undefined => result?.summary.find((s) => s.sourceId === id)

  const left = (
    <>
      <RecipeBar
        tool="merge-files"
        canSave={sources.length > 0 && mapping.columns.length > 0}
        current={() => recipeFromMapping(mapping, sources, { sortBy, sortDirection, addSourceColumns: addSource, convertValues: true, dateOrder })}
        onApply={applyRecipe}
      />
      <Section title="Files" right={sources.length ? `${sources.length} table${sources.length === 1 ? '' : 's'}` : undefined}>
        <DropZone
          accept={[MERGE_IN]}
          multiple
          onFiles={(f) => void add(f)}
          busy={task.running && !task.progress}
          disabled={task.running}
          title={sources.length ? 'Drop more files to add them' : 'Drop Excel, CSV or PDF files here'}
          dialogTitle="Choose files to merge"
        />
        <SampleFiles samples={SAMPLES} onLoad={(f) => void add(f)} disabled={task.running} />
        <TaskStatus task={task} />
        {sources.length > 0 && (
          <ul className="mt-3 flex flex-col gap-2" data-testid="merge-sources">
            {sources.map((s, i) => {
              const sum = summaryOf(s.id)
              return (
                <li key={s.id} className="flex items-center gap-2.5 rounded-lg border border-line px-2.5 py-2">
                  <FileTile name={s.fileName} size={32} />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-[13px] font-semibold" title={`${s.fileName} · ${s.sheetName}`}>
                      {s.fileName}
                    </div>
                    <div className="truncate text-[12px] text-muted">
                      {s.sheetName}
                      {s.headerRow ? ` · header row ${s.headerRow}` : ''} ·{' '}
                      <span className="text-matched">{(sum?.rowsTaken ?? s.rows.length).toLocaleString('en-US')} rows taken</span>
                      {s.excluded.length > 0 && <span className="text-doubtful"> · {s.excluded.length} excluded</span>}
                    </div>
                  </div>
                  <div className="flex shrink-0 items-center">
                    <Button variant="ghost" size="icon-sm" aria-label="Move up" disabled={task.running || i === 0} onClick={() => moveSource(i, -1)}>
                      <ArrowUp size={14} />
                    </Button>
                    <Button variant="ghost" size="icon-sm" aria-label="Move down" disabled={task.running || i === sources.length - 1} onClick={() => moveSource(i, 1)}>
                      <ArrowDown size={14} />
                    </Button>
                    <Button variant="ghost" size="icon-sm" aria-label={`Remove ${s.fileName}`} disabled={task.running} onClick={() => removeSource(s.id)}>
                      <X size={14} />
                    </Button>
                  </div>
                </li>
              )
            })}
          </ul>
        )}
      </Section>

      {sources.length > 0 && (
        <Section title="Options">
          <div className="flex flex-col gap-2">
            <Select
              aria-label="Sort by"
              size="sm"
              value={sortBy ?? NONE}
              onValueChange={(v) => setSortBy(v === NONE ? null : v)}
              options={[{ value: NONE, label: 'Keep file order (no sorting)' }, ...mapping.columns.map((c) => ({ value: c, label: `Sort by ${c}` }))]}
            />
            <SegmentedControl
              size="sm"
              aria-label="Sort direction"
              disabled={!sortBy}
              value={sortDirection}
              onValueChange={setSortDirection}
              options={[
                { value: 'asc', label: 'Oldest first' },
                { value: 'desc', label: 'Newest first' }
              ]}
            />
          </div>
          <div className="mt-3">
            <Checkbox label='Add "Source file" and "Sheet / Page" columns' checked={addSource} onCheckedChange={(v) => setAddSource(v === true)} />
          </div>
          {result && (result.needsDateOrder || dateOrder) && (
            <Callout className="mt-3" tone={result.needsDateOrder ? 'doubtful' : 'info'}>
              <div className="mb-2">{result.needsDateOrder ? 'Some dates could be read either way (e.g. 03/09/2026). How are they written?' : 'Day/month order of text dates:'}</div>
              <SegmentedControl
                size="sm"
                aria-label="Date order"
                value={dateOrder ?? ''}
                onValueChange={(v) => setDateOrder(v as 'DMY' | 'MDY')}
                options={[
                  { value: 'DMY', label: 'DD/MM/YYYY' },
                  { value: 'MDY', label: 'MM/DD/YYYY' }
                ]}
              />
            </Callout>
          )}
        </Section>
      )}

      {result && (
        <div className="mt-4 rounded-lg bg-[#F6F8FB] px-3 py-2.5 text-[12.5px] text-ink" data-testid="merge-summary">
          <span className="font-semibold">{result.rows.length.toLocaleString('en-US')} rows</span> from {result.summary.length} table
          {result.summary.length === 1 ? '' : 's'} · {result.columns.length} columns · {result.excluded.length} rows excluded and listed
        </div>
      )}

      <OutputBar
        defaultName={sources[0] ? `${baseName(sources[0].fileName)}_merged.xlsx` : 'Merged.xlsx'}
        extension="xlsx"
        filter={EXCEL_OUT}
        label="Download Excel"
        disabled={!result || task.running}
        build={async () => (result ? mergeToWorkbook(result) : undefined)}
      />
    </>
  )

  const right = (
    <>
      <div className="text-[11.5px] font-bold tracking-[1.2px] text-muted uppercase" data-testid="preview-title">
        {result ? `Merged: ${result.rows.length.toLocaleString('en-US')} rows · ${result.columns.length} columns` : 'Merged table'}
      </div>
      {sources.length === 0 ? (
        <div className="mt-3 grid h-[420px] place-items-center rounded-lg border border-dashed border-line text-center text-[13px] text-muted">
          Add the files to combine (for example three monthly statements). Their columns are matched here, then stacked into one sheet.
        </div>
      ) : (
        <Tabs value={tab} onValueChange={setTab} className="mt-2">
          <TabsList>
            <TabsTrigger value="columns">Column matching</TabsTrigger>
            <TabsTrigger value="preview" count={result ? result.rows.length.toLocaleString('en-US') : undefined}>
              Preview
            </TabsTrigger>
            <TabsTrigger value="excluded" count={`(${result?.excluded.length ?? 0})`}>
              Excluded rows
            </TabsTrigger>
          </TabsList>
          <TabsContent value="columns">
            {merged.error && (
              <p role="alert" className="mb-3 text-[13px] text-unmatched">
                {merged.error}
              </p>
            )}
            <MappingGrid sources={sources} mapping={mapping} onEdit={edit} />
          </TabsContent>
          <TabsContent value="preview">{result && <MergePreview result={result} />}</TabsContent>
          <TabsContent value="excluded">
            <DataTable
              aria-label="Excluded rows"
              rows={result?.excluded ?? []}
              rowKey={(_, i) => String(i)}
              height={440}
              empty="No rows were excluded."
              columns={[
                { id: 'file', header: 'File', minWidth: 170, value: (r) => r.fileName },
                { id: 'where', header: 'Where', width: 90, value: (r) => r.location },
                { id: 'reason', header: 'Reason', width: 170, value: (r) => r.reason },
                { id: 'text', header: 'Row content', minWidth: 240, value: (r) => r.text }
              ]}
            />
          </TabsContent>
        </Tabs>
      )}
    </>
  )

  return <ToolLayout left={left} right={right} />
}

function MappingGrid({ sources, mapping, onEdit }: { sources: MergeSource[]; mapping: MergeMapping; onEdit: (fn: (m: MergeMapping) => MergeMapping) => void }): React.JSX.Element {
  const sourceFor = (id: string, target: string): string | null => {
    const m = mapping.sources[id] ?? {}
    return Object.keys(m).find((c) => m[c] === target) ?? null
  }
  return (
    <div>
      <p className="mb-3 text-[12.5px] text-muted">
        Each row is one column of the merged sheet. Pick which column of each file goes there, rename it, or move it. Columns not used are listed under the grid.
      </p>
      <div className="overflow-x-auto rounded-lg border border-line">
        <table className="w-full border-collapse text-[12.5px]" data-testid="mapping-grid">
          <thead>
            <tr className="bg-[#F6F8FB] text-left">
              <th className="w-[220px] border-b border-line px-3 py-2 font-semibold">Merged column</th>
              {sources.map((s) => (
                <th key={s.id} className="min-w-[170px] border-b border-l border-line px-3 py-2 font-semibold">
                  <div className="truncate" title={`${s.fileName} · ${s.sheetName}`}>
                    {baseName(s.fileName)}
                  </div>
                  <div className="truncate text-[11px] font-normal text-muted">{s.sheetName}</div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {mapping.columns.map((col, ci) => (
              <tr key={col} className="border-b border-line last:border-b-0">
                <td className="px-2 py-1.5 align-middle">
                  <div className="flex items-center gap-1">
                    <RenameInput value={col} onCommit={(to) => onEdit((m) => renameOutputColumn(m, col, to))} />
                    <Button variant="ghost" size="icon-sm" aria-label={`Move ${col} left`} disabled={ci === 0} onClick={() => onEdit((m) => moveOutputColumn(m, col, -1))}>
                      <ArrowLeft size={13} />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      aria-label={`Move ${col} right`}
                      disabled={ci === mapping.columns.length - 1}
                      onClick={() => onEdit((m) => moveOutputColumn(m, col, 1))}
                    >
                      <ArrowRight size={13} />
                    </Button>
                  </div>
                </td>
                {sources.map((s) => {
                  const current = sourceFor(s.id, col)
                  return (
                    <td key={s.id} className={cn('border-l border-line px-2 py-1.5', !current && 'bg-[#FBFBFC]')}>
                      <Select
                        size="sm"
                        aria-label={`${s.fileName} column for ${col}`}
                        value={current ?? NONE}
                        onValueChange={(v) => {
                          if (v === NONE) {
                            if (current) onEdit((m) => setColumnTarget(m, s.id, current, null))
                          } else onEdit((m) => setColumnTarget(m, s.id, v, col))
                        }}
                        options={[{ value: NONE, label: '— not in this file —' }, ...s.columns.map((c) => ({ value: c, label: c }))]}
                      />
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mt-3 flex flex-col gap-1.5">
        {sources.map((s) => {
          const dropped = s.columns.filter((c) => !mapping.sources[s.id]?.[c])
          if (dropped.length === 0) return null
          return (
            <div key={s.id} className="flex flex-wrap items-center gap-1.5 text-[12.5px]">
              <span className="text-muted">Not used from {baseName(s.fileName)}:</span>
              {dropped.map((c) => (
                <span key={c} className="inline-flex items-center gap-1 rounded-md border border-line bg-white py-0.5 pr-1 pl-2">
                  {c}
                  <Select
                    size="sm"
                    aria-label={`Use ${c}`}
                    value=""
                    placeholder="Use…"
                    className="h-6 w-[130px] text-[11.5px]"
                    onValueChange={(v) => onEdit((m) => setColumnTarget(m, s.id, c, v === KEEP ? { separate: true } : v))}
                    options={[{ value: KEEP, label: 'Keep as separate column' }, ...mapping.columns.map((t) => ({ value: t, label: `Put under ${t}` }))]}
                  />
                </span>
              ))}
            </div>
          )
        })}
      </div>
      <div className="mt-2 text-[12px] text-muted">
        <Plus size={12} className="mr-1 inline" />
        Choosing “— not in this file —” drops that file&apos;s column; it then appears in the “Not used” list above.
      </div>
    </div>
  )
}

function RenameInput({ value, onCommit }: { value: string; onCommit: (v: string) => void }): React.JSX.Element {
  const [text, setText] = useState(value)
  const [last, setLast] = useState(value)
  if (value !== last) {
    setLast(value)
    setText(value)
  }
  const commit = (): void => {
    if (text.trim() && text.trim() !== value) onCommit(text)
    else setText(value)
  }
  return (
    <Input
      aria-label={`Rename ${value}`}
      className="h-8 min-w-0 flex-1 px-2 text-[12.5px] font-semibold"
      value={text}
      onChange={(e) => setText(e.target.value)}
      onBlur={commit}
      onKeyDown={(e) => {
        if (e.key === 'Enter') (e.target as HTMLInputElement).blur()
        if (e.key === 'Escape') setText(value)
      }}
    />
  )
}

function MergePreview({ result }: { result: MergeResult }): React.JSX.Element {
  const columns = useMemo<DataColumn<MergeRow>[]>(
    () =>
      result.columns.map((c, i) => {
        const numeric = c.type === 'amount' || c.type === 'number'
        return {
          id: `c${i}`,
          header: c.name,
          subHeader: c.added ? 'added' : c.type === 'id' ? 'reference' : c.type,
          minWidth: c.added ? 150 : c.type === 'text' ? 220 : 110,
          numeric,
          value: (r: MergeRow) => r.values[i]
        }
      }),
    [result]
  )
  return <DataTable aria-label="Merged rows" rows={result.rows} rowKey={(_, i) => String(i)} columns={columns} height={460} />
}
