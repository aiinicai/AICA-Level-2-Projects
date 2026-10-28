import { useEffect, useState } from 'react'
import { cn } from '@/lib/cn'
import { thumbnailUrl } from './pdf'

export interface PageThumbProps {
  /** Identifies the open file in the thumbnail cache. */
  fileKey: string
  data: ArrayBuffer | Uint8Array
  /** 0-based page index. */
  page: number
  /** Rendered width in px (the image is drawn at 2x for sharpness). */
  width?: number
  /** Extra clockwise rotation shown on screen. */
  rotate?: number
  label?: React.ReactNode
  selected?: boolean
  tone?: 'default' | 'ocr' | 'dim'
  onClick?: () => void
  /** Overlay content (buttons, badges) in the top corner. */
  overlay?: React.ReactNode
  className?: string
  title?: string
}

/** One PDF page thumbnail, rendered on demand with pdf.js and cached. */
export function PageThumb({ fileKey, data, page, width = 84, rotate = 0, label, selected, tone = 'default', onClick, overlay, className, title }: PageThumbProps): React.JSX.Element {
  const [url, setUrl] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)
  useEffect(() => {
    let live = true
    setUrl(null)
    setFailed(false)
    thumbnailUrl(fileKey, data, page, width * 2)
      .then((u) => live && setUrl(u))
      .catch(() => live && setFailed(true))
    return () => {
      live = false
    }
  }, [fileKey, data, page, width])

  const height = Math.round(width * 1.3)
  const Box = onClick ? 'button' : 'div'
  return (
    <div className={cn('flex flex-col items-center gap-1', className)} style={{ width }}>
      <Box
        type={onClick ? 'button' : undefined}
        onClick={onClick}
        title={title}
        aria-pressed={onClick ? !!selected : undefined}
        className={cn(
          'relative grid w-full place-items-center overflow-hidden rounded-md border bg-white outline-none transition-shadow',
          selected ? 'border-2 border-primary shadow-[0_0_0_2px_rgba(29,111,216,0.15)]' : 'border-line',
          tone === 'ocr' && 'bg-[#F4F1FE]',
          tone === 'dim' && 'opacity-40',
          onClick && 'cursor-pointer hover:border-primary/70 focus-visible:ring-2 focus-visible:ring-primary/40'
        )}
        style={{ height }}
      >
        {url ? (
          <img
            src={url}
            alt={`Page ${page + 1}`}
            draggable={false}
            className={cn('max-h-full max-w-full object-contain transition-transform', tone === 'ocr' && 'mix-blend-multiply')}
            style={rotate ? { transform: `rotate(${rotate}deg) scale(${rotate % 180 ? 0.77 : 1})` } : undefined}
          />
        ) : (
          <div className={cn('h-[70%] w-[70%] rounded-sm', failed ? 'bg-[#FDECEC]' : 'animate-pulse bg-[#EEF1F5]')} />
        )}
        {overlay}
      </Box>
      {label !== undefined && <div className="num text-[11.5px] leading-tight text-muted">{label}</div>}
    </div>
  )
}
