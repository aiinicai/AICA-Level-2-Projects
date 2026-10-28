import { useState } from 'react'
import { CheckCircle2, UploadCloud, X } from 'lucide-react'
import type { FileFilter, OpenedFile } from '@shared/contracts'
import { cn } from '@/lib/cn'
import { errorMessage } from '@/lib/useAsync'
import { Spinner } from './spinner'

const TILE: Record<string, string> = {
  xlsx: 'bg-[#1F7A4D]',
  xlsm: 'bg-[#1F7A4D]',
  xls: 'bg-[#1F7A4D]',
  csv: 'bg-[#2F6F5E]',
  pdf: 'bg-unmatched',
  zip: 'bg-[#5B6676]'
}

export function fileExtension(name: string): string {
  const dot = name.lastIndexOf('.')
  return dot > 0 ? name.slice(dot + 1).toLowerCase() : ''
}

/** Coloured file-type tile: green XLSX, red PDF… */
export function FileTile({ name, size = 44 }: { name: string; size?: number }): React.JSX.Element {
  const ext = fileExtension(name)
  return (
    <div
      className={cn('grid shrink-0 place-items-center rounded-lg font-bold text-white', TILE[ext] ?? 'bg-[#5B6676]')}
      style={{ width: size, height: size, fontSize: size * 0.3 }}
      aria-hidden
    >
      {(ext || 'FILE').toUpperCase().slice(0, 4)}
    </div>
  )
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export const EXCEL_FILTER: FileFilter = { name: 'Excel or CSV', extensions: ['xlsx', 'xls', 'xlsm', 'csv'] }
export const PDF_FILTER: FileFilter = { name: 'PDF document', extensions: ['pdf'] }

export interface DropZoneProps {
  /** Allowed file types; used for the Open dialog and to check dropped files. */
  accept: FileFilter[]
  /** Called with the chosen or dropped files (already read into memory). */
  onFiles: (files: OpenedFile[]) => void
  multiple?: boolean
  /** File currently loaded; shows the file chip instead of the empty prompt. */
  file?: { name: string; size?: number } | null
  /** Second line under the file name, e.g. "186 rows · header on row 2 · 7 columns identified". */
  info?: React.ReactNode
  /** Right side of the chip; defaults to a green "✓ Read". Pass null to hide. */
  status?: React.ReactNode
  /** Shows a remove button on the chip. */
  onClear?: () => void
  /** Prompt text when empty. */
  title?: React.ReactNode
  hint?: React.ReactNode
  dialogTitle?: string
  busy?: boolean
  disabled?: boolean
  /** Error from reading the file (shown in red under the zone). */
  error?: string | null
  className?: string
}

/** Drag a file in, or click to browse with the Windows Open dialog. */
export function DropZone({
  accept,
  onFiles,
  multiple,
  file,
  info,
  status,
  onClear,
  title = 'Drop a file here or click to browse',
  hint,
  dialogTitle,
  busy,
  disabled,
  error,
  className
}: DropZoneProps): React.JSX.Element {
  const [dragging, setDragging] = useState(false)
  const [localError, setLocalError] = useState<string | null>(null)
  const allowed = new Set(accept.flatMap((f) => f.extensions.map((e) => e.toLowerCase())))
  const allowAll = allowed.has('*')
  const inactive = disabled || busy

  const browse = async (): Promise<void> => {
    if (inactive) return
    setLocalError(null)
    try {
      const files = await window.recoDo.files.open({ title: dialogTitle, filters: accept, multiple })
      if (files.length) onFiles(files)
    } catch (err) {
      setLocalError(errorMessage(err, 'The file could not be opened.'))
    }
  }

  const onDrop = async (e: React.DragEvent): Promise<void> => {
    e.preventDefault()
    setDragging(false)
    if (inactive) return
    setLocalError(null)
    const dropped = Array.from(e.dataTransfer.files).slice(0, multiple ? undefined : 1)
    if (!dropped.length) return
    const wrong = dropped.find((f) => !allowAll && !allowed.has(fileExtension(f.name)))
    if (wrong) {
      const list = [...allowed].map((x) => `.${x}`).join(', ')
      setLocalError(`"${wrong.name}" is not a supported file. Use ${list}.`)
      return
    }
    try {
      onFiles(await Promise.all(dropped.map(async (f) => ({ name: f.name, data: await f.arrayBuffer() }))))
    } catch {
      setLocalError('The dropped file could not be read. Try the Browse option instead.')
    }
  }

  const shownError = error ?? localError
  const showClear = !!file && !!onClear && !busy

  // The Remove button sits beside (not inside) the clickable zone: a button may not contain another button.
  return (
    <div className={className}>
      <div
        className="relative"
        onDragOver={(e) => {
          e.preventDefault()
          if (!inactive) setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => void onDrop(e)}
      >
        <div
          role="button"
          tabIndex={inactive ? -1 : 0}
          aria-disabled={inactive || undefined}
          aria-label={file ? `Replace ${file.name}` : typeof title === 'string' ? title : 'Choose a file'}
          onClick={() => void browse()}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault()
              void browse()
            }
          }}
          className={cn(
            'rounded-xl border-[1.5px] border-dashed border-[#C9D2DE] bg-white outline-none transition-colors focus-visible:ring-2 focus-visible:ring-primary/40',
            !inactive && 'cursor-pointer hover:border-primary/70 hover:bg-[#FAFCFF]',
            dragging && 'border-primary bg-[#EEF4FD]',
            inactive && 'cursor-not-allowed opacity-70',
            shownError && 'border-unmatched/60'
          )}
        >
          {file ? (
            <div className={cn('flex items-center gap-3.5 py-3 pl-4', showClear ? 'pr-14' : 'pr-4')}>
              <FileTile name={file.name} />
              <div className="min-w-0 flex-1">
                <div className="truncate text-[15px] font-bold text-ink" title={file.name}>
                  {file.name}
                </div>
                <div className="truncate text-[13px] text-muted">
                  {info ?? (file.size !== undefined ? formatBytes(file.size) : 'Click to choose a different file')}
                </div>
              </div>
              {busy ? (
                <Spinner size={18} />
              ) : status === undefined ? (
                <span className="inline-flex items-center gap-1 text-[14px] font-semibold text-matched">
                  <CheckCircle2 size={16} /> Read
                </span>
              ) : (
                status
              )}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center gap-1.5 px-6 py-7 text-center">
              {busy ? <Spinner size={26} /> : <UploadCloud size={28} className="text-primary" strokeWidth={1.8} />}
              <div className="text-[14px] font-semibold text-ink">{busy ? 'Reading file…' : title}</div>
              <div className="text-[12.5px] text-muted">{hint ?? accept.map((f) => f.extensions.map((x) => `.${x}`).join(' ')).join(' · ')}</div>
            </div>
          )}
        </div>
        {showClear && file && onClear && (
          <button
            type="button"
            aria-label={`Remove ${file.name}`}
            className="absolute top-1/2 right-4 grid h-7 w-7 -translate-y-1/2 place-items-center rounded-md text-muted hover:bg-[#EEF1F5] hover:text-ink focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:outline-none"
            onClick={onClear}
          >
            <X size={15} />
          </button>
        )}
      </div>
      {shownError && (
        <p role="alert" className="mt-1.5 text-[12.5px] text-unmatched">
          {shownError}
        </p>
      )}
    </div>
  )
}
