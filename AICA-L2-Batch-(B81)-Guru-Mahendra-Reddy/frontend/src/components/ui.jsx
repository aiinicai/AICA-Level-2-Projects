import React, { useEffect, useRef, useState } from 'react'
import { cls, st } from '../lib/format'

// ---------------------------------------------------------------------------
// Surfaces
// ---------------------------------------------------------------------------
export function Card({ title, sub, right, children, className, pad = true, basis }) {
  return (
    <section className={cls('card flex flex-col min-w-0', className)}>
      {(title || right) && (
        <header className="flex items-start justify-between gap-4 px-5 pt-4 pb-3">
          <div className="min-w-0">
            {title && <h2 className="card-title">{title}</h2>}
            {sub && <p className="card-sub">{sub}</p>}
          </div>
          {right && <div className="shrink-0 flex items-center gap-2">{right}</div>}
        </header>
      )}
      <div className={cls('flex-1 min-w-0', pad ? 'px-5 pb-4' : '', !title && pad ? 'pt-4' : '')}>
        {children}
      </div>
      {basis && (
        <footer className="px-5 pb-4 pt-1">
          <p className="basis border-t border-line-soft pt-2.5">{basis}</p>
        </footer>
      )}
    </section>
  )
}

export function Section({ title, sub, right, children, className }) {
  return (
    <div className={cls('min-w-0', className)}>
      <div className="flex items-end justify-between gap-4 mb-3">
        <div>
          <h2 className="text-[15px] font-semibold text-ink tracking-tight">{title}</h2>
          {sub && <p className="text-2xs text-ink-muted mt-0.5">{sub}</p>}
        </div>
        {right}
      </div>
      {children}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Status — never colour alone. Always a word, and a dot beside it.
// ---------------------------------------------------------------------------
export function StatusPill({ status, label, className, title }) {
  const s = st(status)
  return (
    <span className={cls('chip', s.bg, s.border, s.text, className)} title={title || s.word}>
      <span className={cls('w-1.5 h-1.5 rounded-full shrink-0', s.dot)} />
      {label || status}
    </span>
  )
}

export function Dot({ status, className, title }) {
  const s = st(status)
  return <span className={cls('inline-block w-2 h-2 rounded-full shrink-0', s.dot, className)}
               title={title || `${status} — ${s.word}`} />
}

/** The grey staleness dot the spec requires on every headline number while the
 *  confidence banner is showing. */
export function StaleDot({ show, reason }) {
  if (!show) return null
  return (
    <span title={reason || 'Data is incomplete — treat this figure as indicative.'}
          className="inline-block w-1.5 h-1.5 rounded-full bg-grey align-super ml-1.5 shrink-0" />
  )
}

// ---------------------------------------------------------------------------
// Tables
// ---------------------------------------------------------------------------
export function Table({ children, className }) {
  return (
    <div className={cls('-mx-1 overflow-x-auto', className)}>
      <table className="w-full border-collapse">{children}</table>
    </div>
  )
}
export const TH = ({ children, left, className, ...p }) =>
  <th className={cls('th', left && 'th-l', className)} {...p}>{children}</th>
export const TD = ({ children, left, className, ...p }) =>
  <td className={cls('td', left && 'text-left', className)} {...p}>{children}</td>

// ---------------------------------------------------------------------------
// States
// ---------------------------------------------------------------------------
export function Loading({ label = 'Working that out…', rows = 3 }) {
  return (
    <div className="animate-in">
      <p className="text-2xs text-ink-faint mb-3">{label}</p>
      <div className="space-y-2">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="h-9 rounded-lg bg-line-soft animate-pulse"
               style={{ animationDelay: `${i * 90}ms` }} />
        ))}
      </div>
    </div>
  )
}

export function ErrorNote({ error, onRetry }) {
  if (!error) return null
  return (
    <div className="rounded-lg border border-red-line bg-red-bg px-4 py-3 flex items-start gap-3">
      <Dot status="Red" className="mt-1.5" />
      <div className="min-w-0 flex-1">
        <p className="text-[13px] text-red font-medium">{error}</p>
        {onRetry && <button onClick={onRetry} className="text-2xs text-red underline mt-1">Try again</button>}
      </div>
    </div>
  )
}

export function Empty({ children, className }) {
  return (
    <div className={cls('text-center py-10 px-4', className)}>
      <p className="text-[13px] text-ink-muted">{children}</p>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Overlays
// ---------------------------------------------------------------------------
export function Drawer({ open, onClose, title, sub, children, width = 'max-w-2xl' }) {
  useEffect(() => {
    if (!open) return
    const onKey = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-ink/25 backdrop-blur-[1px]" onClick={onClose} />
      <aside className={cls('relative bg-white h-full w-full shadow-pop flex flex-col animate-slide', width)}>
        <header className="px-5 py-4 border-b border-line flex items-start justify-between gap-4">
          <div className="min-w-0">
            <h3 className="text-[15px] font-semibold text-ink tracking-tight">{title}</h3>
            {sub && <p className="text-2xs text-ink-muted mt-1">{sub}</p>}
          </div>
          <button onClick={onClose} aria-label="Close"
                  className="text-ink-faint hover:text-ink shrink-0 rounded p-1 hover:bg-line-soft">
            <Icon name="x" />
          </button>
        </header>
        <div className="flex-1 overflow-y-auto px-5 py-4">{children}</div>
      </aside>
    </div>
  )
}

export function Modal({ open, onClose, title, sub, children, footer, width = 'max-w-lg' }) {
  useEffect(() => {
    if (!open) return
    const onKey = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-ink/25 backdrop-blur-[1px]" onClick={onClose} />
      <div className={cls('relative bg-white rounded-xl shadow-pop w-full flex flex-col max-h-[88vh] animate-in', width)}>
        <header className="px-5 py-4 border-b border-line">
          <h3 className="text-[15px] font-semibold text-ink tracking-tight">{title}</h3>
          {sub && <p className="text-2xs text-ink-muted mt-1">{sub}</p>}
        </header>
        <div className="flex-1 overflow-y-auto px-5 py-4">{children}</div>
        {footer && <footer className="px-5 py-3 border-t border-line flex justify-end gap-2">{footer}</footer>}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Small pieces
// ---------------------------------------------------------------------------
export function Toggle({ options, value, onChange, size = 'sm' }) {
  return (
    <div className="inline-flex rounded-lg border border-line bg-white p-0.5">
      {options.map((o) => {
        const v = typeof o === 'string' ? o : o.value
        const l = typeof o === 'string' ? o : o.label
        return (
          <button key={v} onClick={() => onChange(v)}
                  className={cls('rounded-md font-semibold transition-colors',
                    size === 'sm' ? 'px-2.5 py-1 text-2xs' : 'px-3 py-1.5 text-[13px]',
                    v === value ? 'bg-navy-700 text-white' : 'text-ink-muted hover:text-ink hover:bg-navy-50')}>
            {l}
          </button>
        )
      })}
    </div>
  )
}

export function Field({ label, hint, children, className }) {
  return (
    <label className={cls('block', className)}>
      <span className="label block mb-1.5">{label}</span>
      {children}
      {hint && <span className="basis block mt-1">{hint}</span>}
    </label>
  )
}

export function Bar({ value, max, status = 'Green', className }) {
  const w = max ? Math.max(Math.min((value / max) * 100, 100), 0) : 0
  return (
    <div className={cls('h-1.5 rounded-full bg-line-soft overflow-hidden', className)}>
      <div className={cls('h-full rounded-full', st(status).dot)} style={{ width: `${w}%` }} />
    </div>
  )
}

/** Info tooltip for the "basis" of a number — hover, not a modal. */
export function Why({ children }) {
  const [open, setOpen] = useState(false)
  return (
    <span className="relative inline-flex" onMouseEnter={() => setOpen(true)}
          onMouseLeave={() => setOpen(false)}>
      <button className="text-ink-faint hover:text-navy-600 ml-1 align-middle" aria-label="How this is worked out">
        <Icon name="info" size={13} />
      </button>
      {open && (
        <span className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 z-40 w-64
                         rounded-lg bg-ink text-white text-2xs leading-relaxed px-3 py-2 shadow-pop">
          {children}
        </span>
      )}
    </span>
  )
}

// ---------------------------------------------------------------------------
// Icons — inline, no icon library
// ---------------------------------------------------------------------------
const PATHS = {
  x: 'M18 6 6 18M6 6l12 12',
  info: 'M12 16v-4M12 8h.01M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z',
  bell: 'M6 8a6 6 0 1 1 12 0c0 7 3 9 3 9H3s3-2 3-9M10.3 21a1.94 1.94 0 0 0 3.4 0',
  chevron: 'm6 9 6 6 6-6',
  chevronRight: 'm9 18 6-6-6-6',
  arrowUp: 'M12 19V5M5 12l7-7 7 7',
  arrowDown: 'M12 5v14M19 12l-7 7-7-7',
  external: 'M15 3h6v6M10 14 21 3M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6',
  grid: 'M3 3h7v9H3zM14 3h7v5h-7zM14 12h7v9h-7zM3 16h7v5H3z',
  trend: 'M3 17l6-6 4 4 8-8M15 6h6v6',
  drop: 'M12 2C8 6 8 9 8 12a4 4 0 0 0 8 0c0-3 0-6-4-10M9 15c0 3 1.5 5 3 5s3-2 3-5',
  inbox: 'M22 12h-6l-2 3h-4l-2-3H2M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z',
  out: 'M12 2v20M17 7l-5-5-5 5M17 17l-5 5-5-5',
  calendar: 'M8 2v4M16 2v4M3 10h18M5 4h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z',
  target: 'M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20ZM12 18a6 6 0 1 0 0-12 6 6 0 0 0 0 12ZM12 14a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z',
  sliders: 'M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6',
  bank: 'M3 21h18M5 21V10M9 21V10M15 21V10M19 21V10M2 10l10-7 10 7',
  file: 'M14 2v6h6M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7z',
  cog: 'M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6ZM19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.6 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.6a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9v0a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z',
  check: 'm20 6-11 11-5-5',
  plus: 'M12 5v14M5 12h14',
  search: 'M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16ZM21 21l-4.3-4.3',
  download: 'M12 3v13M7 11l5 5 5-5M4 19v2h16v-2',
  upload: 'M12 17V4M7 9l5-5 5 5M4 19v2h16v-2',
  refresh: 'M21 12a9 9 0 1 1-3-6.7M21 3v6h-6',
  lock: 'M7 11V7a5 5 0 0 1 10 0v4M5 11h14v10H5z',
  users: 'M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75',
  book: 'M4 19.5A2.5 2.5 0 0 1 6.5 17H20M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z',
  clock: 'M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20ZM12 6v6l4 2',
  logout: 'M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9',
  alert: 'M12 9v4M12 17h.01M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z',
  briefcase: 'M20 7H4a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2ZM16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16',
  presentation: 'M2 3h20M4 3v11a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V3M9 21l3-5 3 5',
  scale: 'm3 7 3 9 3-9M15 7l3 9 3-9M12 3v18M6 7h12',
  eye: 'M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7-10-7-10-7ZM12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z',
  eyeoff: 'M9.9 4.24A9.1 9.1 0 0 1 12 4c6.4 0 10 7 10 7a17.6 17.6 0 0 1-3.2 4.19M6.6 6.6A17.6 17.6 0 0 0 2 11s3.6 7 10 7a9.1 9.1 0 0 0 4.1-.94M1 1l22 22M9.9 9.9a3 3 0 0 0 4.2 4.2',
  plug: 'M9 2v6M15 2v6M6 8h12v3a6 6 0 0 1-12 0zM12 17v5',
  building: 'M4 21V5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v16M16 9h2a2 2 0 0 1 2 2v10M2 21h20M8 7h2M8 11h2M8 15h2',
  link: 'M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7',
  wand: 'M15 4V2M15 16v-2M8 9h2M20 9h2M17.8 11.8 19 13M15 9h0M17.8 6.2 19 5M3 21l9-9M12.2 6.2 11 5',
}

export function Icon({ name, size = 16, className, strokeWidth = 1.9 }) {
  const d = PATHS[name]
  if (!d) return null
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
         strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round"
         className={cls('shrink-0', className)} aria-hidden="true">
      <path d={d} />
    </svg>
  )
}
