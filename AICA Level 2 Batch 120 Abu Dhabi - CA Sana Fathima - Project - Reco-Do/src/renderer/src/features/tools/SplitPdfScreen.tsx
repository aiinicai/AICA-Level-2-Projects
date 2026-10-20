import { useEffect, useMemo, useRef, useState } from 'react'
import { Check } from 'lucide-react'
import type { OpenedFile } from '@shared/contracts'
import { baseName, pdfInfo, protectedPdfError, zipFiles } from '@tools/common'
import { planGroups, splitFileName, splitPdf, type SplitPlan } from '@tools/split-pdf'
import { Button, DropZone, formatBytes, Input, RadioGroup } from '@/components/ui'
import { cn } from '@/lib/cn'
import { newId } from '@/lib/db'
import { OutputBar, PDF_IN, PDF_OUT, SampleFiles, Section, TaskStatus, ToolLayout, ZIP_OUT } from './shared/components'
import { PageThumb } from './shared/PageThumb'
import { pdfRuntime, releaseThumbnails } from './shared/pdf'
import { toolErrorMessage, useToolTask } from './shared/useToolTask'

interface LoadedPdf {
  key: string
  name: string
  data: ArrayBuffer
  size: number
  pageCount: number
}

type Mode = SplitPlan['mode']

const SAMPLES = [{ label: 'Split_Me_12_pages', files: ['Split_Me_12_pages.pdf'] }]
/** Soft colours that tell the output files apart in the page grid. */
const GROUP_COLOURS = ['#1D6FD8', '#11865F', '#A86B00', '#5A43D6', '#C25500', '#1E8E72', '#C0292B', '#0F2A44']

export function SplitPdfScreen(): React.JSX.Element {
  const task = useToolTask()
  const [file, setFile] = useState<LoadedPdf | null>(null)
  const [mode, setMode] = useState<Mode>('every')
  const [every, setEvery] = useState('3')
  const [ranges, setRanges] = useState('')
  const [selected, setSelected] = useState<number[]>([])
  const keyRef = useRef<string | null>(null)
  useEffect(() => () => void (keyRef.current && releaseThumbnails(keyRef.current)), [])

  const loadSeq = useRef(0)
  const load = async (files: OpenedFile[]): Promise<void> => {
    const f = files[0]
    if (!f) return
    const id = ++loadSeq.current
    task.cancel()
    task.setError(null)
    try {
      const info = await pdfInfo(f.data)
      if (info.encrypted) throw await protectedPdfError(f.data, (await pdfRuntime()).pdfjs)
      if (info.pages === 0) throw new Error('This PDF has no pages.')
      // A newer file was dropped while this one was being checked.
      if (id !== loadSeq.current) return
      if (keyRef.current) releaseThumbnails(keyRef.current)
      const key = newId()
      keyRef.current = key
      setFile({ key, name: f.name, data: f.data, size: f.data.byteLength, pageCount: info.pages })
      setSelected([])
      setRanges(info.pages >= 4 ? `1-${Math.ceil(info.pages / 2)}, ${Math.ceil(info.pages / 2) + 1}-${info.pages}` : '1')
    } catch (e) {
      if (id === loadSeq.current) task.setError(toolErrorMessage(e))
    }
  }

  const plan = useMemo<SplitPlan>(() => {
    switch (mode) {
      case 'every':
        return { mode, pages: Number(every) }
      case 'ranges':
        return { mode, ranges }
      case 'select':
        return { mode, pages: selected }
      case 'single':
        return { mode }
    }
  }, [mode, every, ranges, selected])

  const planned = useMemo<{ groups: number[][]; error: string | null }>(() => {
    if (!file) return { groups: [], error: null }
    try {
      return { groups: planGroups(plan, file.pageCount), error: null }
    } catch (e) {
      return { groups: [], error: toolErrorMessage(e) }
    }
  }, [plan, file])

  const groupOf = useMemo(() => {
    const m = new Map<number, number>()
    planned.groups.forEach((g, gi) => g.forEach((p) => m.has(p) || m.set(p, gi)))
    return m
  }, [planned])

  const base = file ? baseName(file.name) : 'document'
  const many = planned.groups.length > 1
  const outName = !file ? 'Split.pdf' : many ? `${base}_split.zip` : planned.groups[0] ? splitFileName(base, planned.groups[0]) : `${base}_split.pdf`

  const left = (
    <>
      <Section title="Source PDF">
        <DropZone
          accept={[PDF_IN]}
          onFiles={(f) => void load(f)}
          file={file ? { name: file.name, size: file.size } : null}
          info={file ? `${file.pageCount} pages · ${formatBytes(file.size)}` : undefined}
          title="Drop a PDF here or click to browse"
          dialogTitle="Choose a PDF to split"
        />
        <SampleFiles samples={SAMPLES} onLoad={(f) => void load(f)} disabled={task.running} />
        <TaskStatus task={task} />
      </Section>

      <Section title="How to split">
        <RadioGroup<Mode>
          aria-label="Split mode"
          value={mode}
          onValueChange={setMode}
          options={[
            { value: 'every', label: 'Every N pages', description: 'A new file every few pages; the last file holds the rest.' },
            { value: 'ranges', label: 'Custom ranges', description: 'One file per range, e.g. 1-3, 4-6, 7.' },
            { value: 'select', label: 'Extract selected pages', description: 'Click pages on the right; they go into one new file.' },
            { value: 'single', label: 'One file per page' }
          ]}
        />
        {mode === 'every' && (
          <div className="mt-3 flex items-center gap-2 text-[13px]">
            <span>A new file every</span>
            <Input aria-label="Pages per file" type="number" min={1} className="h-8 w-20" value={every} onChange={(e) => setEvery(e.target.value)} />
            <span>pages</span>
          </div>
        )}
        {mode === 'ranges' && (
          <Input aria-label="Page ranges" className="mt-3" placeholder="e.g. 1-3, 4-6, 7" value={ranges} onChange={(e) => setRanges(e.target.value)} />
        )}
        {mode === 'select' && file && (
          <div className="mt-3 flex items-center gap-2 text-[12.5px] text-muted">
            <span>{selected.length ? `${selected.length} page${selected.length === 1 ? '' : 's'} selected` : 'No pages selected yet.'}</span>
            {selected.length > 0 && (
              <Button variant="link" size="sm" onClick={() => setSelected([])}>
                Clear
              </Button>
            )}
            <Button variant="link" size="sm" onClick={() => setSelected(Array.from({ length: file.pageCount }, (_, i) => i + 1))}>
              Select all
            </Button>
          </div>
        )}
      </Section>

      {file && (
        <Section title="Result" right={planned.groups.length ? `${planned.groups.length} file${many ? 's' : ''}` : undefined}>
          {planned.error ? (
            <p className="text-[13px] text-unmatched" role="alert">
              {planned.error}
            </p>
          ) : (
            <ul className="max-h-[220px] overflow-y-auto rounded-lg border border-line text-[12.5px]" data-testid="split-plan">
              {planned.groups.map((g, gi) => (
                <li key={gi} className="flex items-center gap-2 border-b border-line px-3 py-1.5 last:border-b-0">
                  <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: GROUP_COLOURS[gi % GROUP_COLOURS.length] }} />
                  <span className="min-w-0 flex-1 truncate font-medium">{splitFileName(base, g)}</span>
                  <span className="num text-muted">
                    {g.length} page{g.length === 1 ? '' : 's'}
                  </span>
                </li>
              ))}
            </ul>
          )}
          {many && <p className="mt-2 text-[12px] text-muted">Several files are produced, so they are saved together in one .zip.</p>}
        </Section>
      )}

      <OutputBar
        defaultName={outName}
        extension={many ? 'zip' : 'pdf'}
        filter={many ? ZIP_OUT : PDF_OUT}
        label={many ? 'Download .zip' : 'Download PDF'}
        disabled={!file || !!planned.error || planned.groups.length === 0 || task.running}
        build={() =>
          task.run('Splitting the PDF', async (signal, report) => {
            if (!file) return undefined
            const out = await splitPdf(file.data, plan, {
              fileName: file.name,
              signal,
              onProgress: (p) => report({ value: (p.file / p.files) * 100, detail: `File ${p.file} of ${p.files}` })
            })
            return out.length > 1 ? zipFiles(out) : out[0].data
          })
        }
      />
    </>
  )

  const right = (
    <>
      <div className="flex items-baseline justify-between gap-4">
        <div className="text-[11.5px] font-bold tracking-[1.2px] text-muted uppercase" data-testid="preview-title">
          {file ? `${file.pageCount} pages${planned.groups.length ? ` → ${planned.groups.length} file${many ? 's' : ''}` : ''}` : 'Pages'}
        </div>
        {mode === 'select' && file && <div className="text-[12.5px] text-muted">Click pages to select them</div>}
      </div>
      {!file ? (
        <div className="mt-3 grid h-[420px] place-items-center rounded-lg border border-dashed border-line text-center text-[13px] text-muted">
          Drop a PDF on the left, or try the sample file. Its pages appear here, coloured by output file.
        </div>
      ) : (
        <div className="mt-3 flex flex-wrap gap-3" data-testid="split-pages">
          {Array.from({ length: file.pageCount }, (_, i) => {
            const page = i + 1
            const gi = groupOf.get(page)
            const isSel = selected.includes(page)
            const colour = gi !== undefined ? GROUP_COLOURS[gi % GROUP_COLOURS.length] : undefined
            return (
              <div key={i} className="relative">
                <PageThumb
                  fileKey={file.key}
                  data={file.data}
                  page={i}
                  width={96}
                  selected={mode === 'select' && isSel}
                  tone={gi === undefined ? 'dim' : 'default'}
                  onClick={mode === 'select' ? () => setSelected((s) => (s.includes(page) ? s.filter((p) => p !== page) : [...s, page].sort((a, b) => a - b))) : undefined}
                  label={
                    <span className="inline-flex items-center gap-1">
                      {colour && <span className="h-2 w-2 rounded-full" style={{ background: colour }} />}
                      Page {page}
                      {gi !== undefined && many ? ` · file ${gi + 1}` : ''}
                    </span>
                  }
                  overlay={
                    mode === 'select' && isSel ? (
                      <span className="absolute top-1 right-1 grid h-5 w-5 place-items-center rounded-full bg-primary text-white">
                        <Check size={12} strokeWidth={3} />
                      </span>
                    ) : colour ? (
                      <span className={cn('absolute inset-x-0 top-0 h-1')} style={{ background: colour }} />
                    ) : undefined
                  }
                />
              </div>
            )
          })}
        </div>
      )}
    </>
  )

  return <ToolLayout left={left} right={right} />
}
