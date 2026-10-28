// Building blocks shared by the six tool screens (two-panel layout as in mockup 5).

import { useEffect, useState } from 'react'
import { AlertCircle, Download, FlaskConical, X } from 'lucide-react'
import type { FileFilter, OpenedFile } from '@shared/contracts'
import { Button, Card, Input, Progress, SectionTitle, useToast } from '@/components/ui'
import { cn } from '@/lib/cn'
import { errorMessage } from '@/lib/useAsync'
import type { ToolTask } from './useToolTask'

/** Options card on the left, live preview card on the right; stacked (options first) when the window is narrow. */
export function ToolLayout({ left, right }: { left: React.ReactNode; right: React.ReactNode }): React.JSX.Element {
  return (
    <div className="flex flex-col gap-5 @mid/main:flex-row @mid/main:items-start">
      <Card className="p-5 @mid/main:w-[340px] @mid/main:shrink-0 @wide/main:w-[390px]">{left}</Card>
      <Card className="min-w-0 p-5 @mid/main:flex-1">{right}</Card>
    </div>
  )
}

/** A titled block inside a panel. */
export function Section({
  title,
  right,
  className,
  children
}: {
  title: React.ReactNode
  right?: React.ReactNode
  className?: string
  children: React.ReactNode
}): React.JSX.Element {
  return (
    <section className={cn('mt-5 first:mt-0', className)}>
      <SectionTitle right={right} className="mb-2.5">
        {title}
      </SectionTitle>
      {children}
    </section>
  )
}

/** "Try with sample file(s)": loads bundled files from sample-data/tools in one click. */
export function SampleFiles({
  samples,
  onLoad,
  disabled
}: {
  /** Each button loads one or more files from sample-data/tools. */
  samples: Array<{ label: string; files: string[] }>
  onLoad: (files: OpenedFile[]) => void
  disabled?: boolean
}): React.JSX.Element {
  const toast = useToast()
  const [busy, setBusy] = useState<string | null>(null)
  const load = async (label: string, files: string[]): Promise<void> => {
    setBusy(label)
    try {
      const list = await window.recoDo.samples.list()
      const out: OpenedFile[] = []
      for (const name of files) {
        const entry = list.find((s) => s.folder === 'tools' && s.name === name)
        if (!entry) throw new Error(`The sample file "${name}" is missing from this installation.`)
        out.push({ name, data: await window.recoDo.samples.read(entry.path) })
      }
      onLoad(out)
    } catch (e) {
      toast.error('Sample file not loaded', errorMessage(e))
    } finally {
      setBusy(null)
    }
  }
  return (
    <div className="mt-2.5 flex flex-wrap items-center gap-1.5 text-[12.5px] text-muted">
      <span className="inline-flex items-center gap-1">
        <FlaskConical size={13} /> Try with sample {samples.length === 1 && samples[0].files.length === 1 ? 'file' : 'files'}:
      </span>
      {samples.map((s) => (
        <button
          key={s.label}
          type="button"
          data-sample={s.files.join('+')}
          disabled={disabled || busy !== null}
          onClick={() => void load(s.label, s.files)}
          className="rounded-full border border-[#CFE0F7] bg-[#F3F8FE] px-2.5 py-0.5 font-medium text-primary transition-colors hover:bg-[#E6F0FC] disabled:opacity-50"
        >
          {busy === s.label ? 'Loading…' : s.label}
        </button>
      ))}
    </div>
  )
}

/** Progress bar with Cancel (after the grace period) and the last plain-English error. */
export function TaskStatus({ task, className }: { task: ToolTask; className?: string }): React.JSX.Element | null {
  if (task.progress) {
    return (
      <div className={cn('mt-4 rounded-lg border border-line bg-[#F8FAFC] p-3', className)} role="status" aria-live="polite">
        <div className="flex items-center gap-3">
          <Progress className="flex-1" value={task.progress.value} label={task.progress.label} detail={task.progress.detail} />
          <Button variant="secondary" size="sm" onClick={task.cancel} data-action="cancel">
            Cancel
          </Button>
        </div>
      </div>
    )
  }
  if (task.error) {
    return (
      <div role="alert" className={cn('mt-4 flex items-start gap-2 rounded-lg border border-[#F3C7C7] bg-[#FDF3F3] p-3 text-[13px] text-unmatched', className)}>
        <AlertCircle size={16} className="mt-[1px] shrink-0" />
        <div className="min-w-0 flex-1 leading-snug">
          <span>{task.error}</span>
          {task.errorDetail && (
            <details className="mt-1.5 text-[12px] text-muted">
              <summary className="cursor-pointer select-none">Technical details</summary>
              <code className="mt-1 block font-mono text-[11.5px] break-words whitespace-pre-wrap">{task.errorDetail}</code>
            </details>
          )}
        </div>
        <button type="button" aria-label="Dismiss" onClick={() => task.setError(null)} className="rounded p-0.5 hover:bg-[#F8DCDC]">
          <X size={14} />
        </button>
      </div>
    )
  }
  return null
}

/** Editable output file name + primary "Download …" button; saves through the Windows "Save as" dialog. */
export function OutputBar({
  defaultName,
  extension,
  filter,
  label,
  build,
  disabled,
  extra
}: {
  /** Suggested name (without folder); the user can edit it. */
  defaultName: string
  /** e.g. "xlsx", "pdf", "zip". */
  extension: string
  filter: FileFilter
  label: string
  /** Produces the bytes when the button is pressed; return undefined to stop (e.g. cancelled). */
  build: () => Promise<Uint8Array | undefined>
  disabled?: boolean
  /** Extra buttons on the left of the primary button. */
  extra?: React.ReactNode
}): React.JSX.Element {
  const toast = useToast()
  const [name, setName] = useState(defaultName)
  const [saving, setSaving] = useState(false)
  useEffect(() => setName(defaultName), [defaultName])

  const save = async (): Promise<void> => {
    setSaving(true)
    try {
      const data = await build()
      if (!data) return
      let file = name.trim() || defaultName
      if (!file.toLowerCase().endsWith(`.${extension}`)) file = `${file}.${extension}`
      const res = await window.recoDo.files.save({ defaultName: file, filters: [filter], data })
      if (res.saved) toast.success('File saved', res.path)
    } catch (e) {
      toast.error('The file was not saved', errorMessage(e))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="mt-5 border-t border-line pt-4">
      <label className="mb-1.5 block text-[12.5px] font-semibold text-ink" htmlFor="tool-output-name">
        File name
      </label>
      <Input id="tool-output-name" value={name} onChange={(e) => setName(e.target.value)} disabled={disabled} spellCheck={false} />
      <div className="mt-3 flex flex-wrap gap-2.5">
        {extra}
        <Button onClick={() => void save()} disabled={disabled} loading={saving} data-action="download">
          <Download size={15} /> {label}
        </Button>
      </div>
    </div>
  )
}

/** Toggle chips for choosing columns. */
export function ColumnChips({
  columns,
  value,
  onChange,
  disabled
}: {
  columns: string[]
  value: string[]
  onChange: (next: string[]) => void
  disabled?: boolean
}): React.JSX.Element {
  return (
    <div className="flex flex-wrap gap-1.5">
      {columns.map((c) => {
        const on = value.includes(c)
        return (
          <button
            key={c}
            type="button"
            aria-pressed={on}
            disabled={disabled}
            onClick={() => onChange(on ? value.filter((v) => v !== c) : [...value, c])}
            className={cn(
              'max-w-[160px] truncate rounded-md border px-2 py-0.5 text-[12px] transition-colors disabled:opacity-50',
              on ? 'border-primary bg-[#EEF4FD] font-semibold text-primary' : 'border-[#D5DCE5] bg-white text-muted hover:border-[#B9C3D0]'
            )}
            title={c}
          >
            {c}
          </button>
        )
      })}
    </div>
  )
}

/** Small amber box for questions such as DD/MM vs MM/DD. */
export function Callout({ tone = 'doubtful', children, className }: { tone?: 'doubtful' | 'info'; children: React.ReactNode; className?: string }): React.JSX.Element {
  return (
    <div
      className={cn(
        'rounded-lg border p-3 text-[13px] leading-snug',
        tone === 'doubtful' ? 'border-[#F1D9A6] bg-[#FFF8EA] text-[#7A4E00]' : 'border-[#CFE0F7] bg-[#F3F8FE] text-ink',
        className
      )}
    >
      {children}
    </div>
  )
}

/** Count pill shown next to an action ("37 cells"). */
export function CountPill({ count, unit, muted }: { count: number; unit: string; muted?: boolean }): React.JSX.Element {
  return (
    <span
      className={cn(
        'num ml-auto shrink-0 rounded-full px-2 py-[1px] text-[11.5px] font-semibold',
        count === 0 || muted ? 'bg-[#EEF1F5] text-muted' : 'bg-[#E6F0FC] text-primary'
      )}
    >
      {count.toLocaleString('en-US')} {unit}
    </span>
  )
}

export const EXCEL_OUT: FileFilter = { name: 'Excel workbook', extensions: ['xlsx'] }
export const PDF_OUT: FileFilter = { name: 'PDF document', extensions: ['pdf'] }
export const ZIP_OUT: FileFilter = { name: 'Zip archive', extensions: ['zip'] }
export const EXCEL_IN: FileFilter = { name: 'Excel or CSV', extensions: ['xlsx', 'xls', 'xlsm', 'csv'] }
export const PDF_IN: FileFilter = { name: 'PDF document', extensions: ['pdf'] }
export const MERGE_IN: FileFilter = { name: 'Excel, CSV or PDF', extensions: ['xlsx', 'xls', 'xlsm', 'csv', 'pdf'] }
