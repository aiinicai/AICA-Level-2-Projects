import { useEffect, useRef, useState } from 'react'
import { ArrowDown, ArrowUp, ChevronDown, ChevronLeft, ChevronRight, GripVertical, RotateCcw, RotateCw, Trash2, X } from 'lucide-react'
import type { OpenedFile } from '@shared/contracts'
import { baseName, pdfInfo, protectedPdfError } from '@tools/common'
import { mergePdfs, type MergePageSelection, type Rotation } from '@tools/merge-pdfs'
import { Button, DropZone, FileTile } from '@/components/ui'
import { cn } from '@/lib/cn'
import { newId } from '@/lib/db'
import { OutputBar, PDF_IN, PDF_OUT, SampleFiles, Section, TaskStatus, ToolLayout } from './shared/components'
import { PageThumb } from './shared/PageThumb'
import { pdfRuntime, releaseThumbnails } from './shared/pdf'
import { toolErrorMessage, useToolTask } from './shared/useToolTask'

interface PdfItem {
  key: string
  name: string
  data: ArrayBuffer
  pageCount: number
  pages: MergePageSelection[]
  expanded: boolean
}

const SAMPLES = [{ label: 'Merge_Part1 + Merge_Part2', files: ['Merge_Part1.pdf', 'Merge_Part2.pdf'] }]

function allPages(n: number): MergePageSelection[] {
  return Array.from({ length: n }, (_, index) => ({ index, rotate: 0 as Rotation }))
}

function move<T>(list: T[], from: number, to: number): T[] {
  const next = [...list]
  const [item] = next.splice(from, 1)
  next.splice(to, 0, item)
  return next
}

const rotateBy = (r: Rotation, d: 90 | -90): Rotation => ((((r + d) % 360) + 360) % 360) as Rotation

export function MergePdfsScreen(): React.JSX.Element {
  const task = useToolTask()
  const [items, setItems] = useState<PdfItem[]>([])
  const [loading, setLoading] = useState(false)
  const dragFile = useRef<number | null>(null)
  const dragPage = useRef<{ file: number; pos: number } | null>(null)
  const keys = useRef<string[]>([])

  useEffect(() => {
    keys.current = items.map((i) => i.key)
  }, [items])
  useEffect(() => () => keys.current.forEach(releaseThumbnails), [])

  const add = async (files: OpenedFile[]): Promise<void> => {
    setLoading(true)
    task.setError(null)
    const added: PdfItem[] = []
    const problems: string[] = []
    for (const f of files) {
      try {
        const info = await pdfInfo(f.data)
        if (info.encrypted) {
          const err = await protectedPdfError(f.data, (await pdfRuntime()).pdfjs)
          problems.push(`${f.name}: ${err.message}`)
          continue
        }
        if (info.pages === 0) {
          problems.push(`${f.name}: this PDF has no pages.`)
          continue
        }
        added.push({ key: newId(), name: f.name, data: f.data, pageCount: info.pages, pages: allPages(info.pages), expanded: false })
      } catch (e) {
        problems.push(`${f.name}: ${toolErrorMessage(e)}`)
      }
    }
    setItems((list) => [...list, ...added])
    if (problems.length) task.setError(problems.join(' '))
    setLoading(false)
  }

  const update = (i: number, fn: (item: PdfItem) => PdfItem): void => setItems((list) => list.map((it, k) => (k === i ? fn(it) : it)))
  const removeFile = (i: number): void => {
    releaseThumbnails(items[i].key)
    setItems((list) => list.filter((_, k) => k !== i))
  }

  const total = items.reduce((n, it) => n + it.pages.length, 0)
  const outputPages = items.flatMap((it) => it.pages.map((p, pos) => ({ item: it, p, pos })))

  const left = (
    <>
      <Section title="PDF files" right={items.length ? `${items.length} file${items.length === 1 ? '' : 's'} · ${total} page${total === 1 ? '' : 's'}` : undefined}>
        <DropZone accept={[PDF_IN]} multiple onFiles={(f) => void add(f)} busy={loading} disabled={loading} title="Drop PDFs here or click to browse" dialogTitle="Choose PDFs to merge" />
        <SampleFiles samples={SAMPLES} onLoad={(f) => void add(f)} disabled={loading || task.running} />
        <TaskStatus task={task} />
        {items.length > 0 && (
          <ul className="mt-3 flex flex-col gap-2" data-testid="merge-file-list">
            {items.map((it, i) => (
              <li
                key={it.key}
                draggable
                onDragStart={(e) => {
                  dragFile.current = i
                  e.dataTransfer.effectAllowed = 'move'
                }}
                onDragOver={(e) => {
                  if (dragFile.current !== null) e.preventDefault()
                }}
                onDrop={(e) => {
                  e.preventDefault()
                  const from = dragFile.current
                  dragFile.current = null
                  if (from !== null && from !== i) setItems((list) => move(list, from, i))
                }}
                className="rounded-lg border border-line bg-white"
              >
                <div className="flex items-center gap-2 px-2 py-2">
                  <GripVertical size={16} className="shrink-0 cursor-grab text-[#9AA4B2]" aria-label="Drag to reorder" />
                  <FileTile name={it.name} size={32} />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-[13px] font-semibold" title={it.name}>
                      {it.name}
                    </div>
                    <div className="text-[12px] text-muted">
                      {it.pages.length === it.pageCount ? `${it.pageCount} pages` : `${it.pages.length} of ${it.pageCount} pages`}
                      {it.pages.some((p) => p.rotate) ? ' · rotated' : ''}
                    </div>
                  </div>
                  {items.length > 1 && (
                    <>
                      <Button variant="ghost" size="icon-sm" aria-label={`Move ${it.name} up`} title="Move up" disabled={i === 0} onClick={() => setItems((list) => move(list, i, i - 1))}>
                        <ArrowUp size={15} />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        aria-label={`Move ${it.name} down`}
                        title="Move down"
                        disabled={i === items.length - 1}
                        onClick={() => setItems((list) => move(list, i, i + 1))}
                      >
                        <ArrowDown size={15} />
                      </Button>
                    </>
                  )}
                  <Button variant="ghost" size="icon-sm" aria-label={it.expanded ? 'Hide pages' : 'Show pages'} onClick={() => update(i, (x) => ({ ...x, expanded: !x.expanded }))}>
                    {it.expanded ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
                  </Button>
                  <Button variant="ghost" size="icon-sm" aria-label={`Remove ${it.name}`} onClick={() => removeFile(i)}>
                    <X size={15} />
                  </Button>
                </div>
                {it.expanded && (
                  <div className="border-t border-line px-2 pt-2 pb-2.5">
                    <div className="flex flex-wrap gap-2">
                      {it.pages.map((p, pos) => (
                        <div
                          key={`${p.index}-${pos}`}
                          draggable
                          onDragStart={(e) => {
                            e.stopPropagation()
                            dragPage.current = { file: i, pos }
                          }}
                          onDragOver={(e) => {
                            if (dragPage.current?.file === i) {
                              e.preventDefault()
                              e.stopPropagation()
                            }
                          }}
                          onDrop={(e) => {
                            const from = dragPage.current
                            if (!from || from.file !== i) return
                            e.preventDefault()
                            e.stopPropagation()
                            dragPage.current = null
                            update(i, (x) => ({ ...x, pages: move(x.pages, from.pos, pos) }))
                          }}
                        >
                          <PageThumb
                            fileKey={it.key}
                            data={it.data}
                            page={p.index}
                            width={64}
                            rotate={p.rotate}
                            label={`p${p.index + 1}`}
                            overlay={
                              <>
                                {it.pages.length > 1 && (
                                  <div className="absolute inset-x-0 top-0 flex justify-between bg-white/90 px-0.5 py-0.5">
                                    <IconBtn label={`Move page ${p.index + 1} earlier`} disabled={pos === 0} onClick={() => update(i, (x) => ({ ...x, pages: move(x.pages, pos, pos - 1) }))}>
                                      <ChevronLeft size={12} />
                                    </IconBtn>
                                    <IconBtn
                                      label={`Move page ${p.index + 1} later`}
                                      disabled={pos === it.pages.length - 1}
                                      onClick={() => update(i, (x) => ({ ...x, pages: move(x.pages, pos, pos + 1) }))}
                                    >
                                      <ChevronRight size={12} />
                                    </IconBtn>
                                  </div>
                                )}
                                <div className="absolute inset-x-0 bottom-0 flex justify-center gap-0.5 bg-white/90 py-0.5">
                                  <IconBtn label="Rotate left" onClick={() => update(i, (x) => ({ ...x, pages: x.pages.map((q, k) => (k === pos ? { ...q, rotate: rotateBy(q.rotate, -90) } : q)) }))}>
                                    <RotateCcw size={12} />
                                  </IconBtn>
                                  <IconBtn label="Rotate right" onClick={() => update(i, (x) => ({ ...x, pages: x.pages.map((q, k) => (k === pos ? { ...q, rotate: rotateBy(q.rotate, 90) } : q)) }))}>
                                    <RotateCw size={12} />
                                  </IconBtn>
                                  <IconBtn label="Remove page" onClick={() => update(i, (x) => ({ ...x, pages: x.pages.filter((_, k) => k !== pos) }))}>
                                    <Trash2 size={12} />
                                  </IconBtn>
                                </div>
                              </>
                            }
                          />
                        </div>
                      ))}
                    </div>
                    <div className="mt-2 flex items-center justify-between text-[12px] text-muted">
                      <span>Drag pages, or use the arrows, to reorder.</span>
                      {(it.pages.length !== it.pageCount || it.pages.some((p, k) => p.rotate || p.index !== k)) && (
                        <button type="button" className="font-semibold text-primary hover:underline" onClick={() => update(i, (x) => ({ ...x, pages: allPages(x.pageCount) }))}>
                          Reset pages
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
        {items.length > 1 && <p className="mt-2 text-[12px] text-muted">Drag files by the handle, or use the up and down arrows, to change their order.</p>}
      </Section>

      <OutputBar
        defaultName={items[0] ? `${baseName(items[0].name)}_merged.pdf` : 'Merged.pdf'}
        extension="pdf"
        filter={PDF_OUT}
        label="Download merged PDF"
        disabled={total === 0 || task.running}
        build={() =>
          task.run('Merging PDFs', (signal, report) =>
            mergePdfs(
              items.map((it) => ({ name: it.name, data: it.data, pages: it.pages })),
              { signal, onProgress: (p) => report({ value: (p.file / p.files) * 100, detail: `File ${p.file} of ${p.files}` }) }
            )
          )
        }
      />
    </>
  )

  const right = (
    <>
      <div className="text-[11.5px] font-bold tracking-[1.2px] text-muted uppercase" data-testid="preview-title">
        {total ? `Merged PDF: ${total} page${total === 1 ? '' : 's'}` : 'Merged PDF'}
      </div>
      {total === 0 ? (
        <div className="mt-3 grid h-[420px] place-items-center rounded-lg border border-dashed border-line text-center text-[13px] text-muted">
          Add two or more PDFs on the left (or try the sample files). The pages of the merged file appear here in order.
        </div>
      ) : (
        <div className="mt-3 flex flex-wrap gap-3" data-testid="merged-pages">
          {outputPages.map(({ item, p, pos }, n) => (
            <PageThumb
              key={`${item.key}-${pos}`}
              fileKey={item.key}
              data={item.data}
              page={p.index}
              width={96}
              rotate={p.rotate}
              label={
                <span className="block max-w-[96px] text-center" title={`${item.name}, page ${p.index + 1}`}>
                  <span className="font-semibold text-ink">{n + 1}</span>
                  <span className={cn('block truncate text-[11px]')}>
                    {baseName(item.name)} · p{p.index + 1}
                  </span>
                </span>
              }
            />
          ))}
        </div>
      )}
    </>
  )

  return <ToolLayout left={left} right={right} />
}

function IconBtn({ label, onClick, disabled, children }: { label: string; onClick: () => void; disabled?: boolean; children: React.ReactNode }): React.JSX.Element {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      disabled={disabled}
      onClick={(e) => {
        e.stopPropagation()
        onClick()
      }}
      className="grid h-5 w-5 place-items-center rounded text-muted outline-none hover:bg-[#EEF1F5] hover:text-ink focus-visible:ring-2 focus-visible:ring-primary/50 disabled:pointer-events-none disabled:opacity-35"
    >
      {children}
    </button>
  )
}
