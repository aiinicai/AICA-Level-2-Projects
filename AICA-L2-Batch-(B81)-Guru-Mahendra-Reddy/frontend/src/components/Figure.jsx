// A number, plus everything needed to defend it.
//
// Design principle 4 in the spec: no number appears without its as-on date and
// its basis. Principle 3: every number is clickable down to the entries behind
// it. Both live here, so no screen can accidentally show a bare figure.
import React from 'react'
import { useApp } from '../lib/store'
import { cls, d as fmtDate, st } from '../lib/format'
import { Dot, Icon, StaleDot, Why } from './ui'

/** The five headline numbers on Today. Large, one row, no scrolling. */
export function HeroFigure({ figure, onClick }) {
  const { openTrace, indicative } = useApp()
  const s = st(figure.status)
  const clickable = !!figure.trace
  const stale = indicative || figure.confident === false

  return (
    <button
      type="button"
      disabled={!clickable && !onClick}
      onClick={() => (onClick ? onClick() : openTrace(figure.trace, figure.label))}
      className={cls(
        'group text-left card px-4 py-4 min-w-0 flex flex-col justify-between',
        'transition-shadow', (clickable || onClick) && 'hover:shadow-pop cursor-pointer',
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="label truncate">{figure.label}</span>
        <span className="flex items-center gap-1.5 shrink-0">
          <Dot status={figure.status} />
          {(clickable || onClick) && (
            <Icon name="chevronRight" size={13}
                  className="text-ink-faint opacity-0 group-hover:opacity-100 transition-opacity" />
          )}
        </span>
      </div>

      <div className="mt-2.5 flex items-baseline min-w-0">
        <span className={cls('text-[26px] leading-none font-semibold tracking-tight truncate',
                             figure.status === 'Red' ? 'text-red' : 'text-ink')}>
          {figure.display}
        </span>
        <StaleDot show={stale} />
      </div>

      {figure.sub_line && (
        <p className="mt-2 text-2xs text-ink-muted leading-snug line-clamp-2">{figure.sub_line}</p>
      )}

      <p className="mt-2.5 pt-2 border-t border-line-soft basis line-clamp-2">
        {figure.basis}{figure.as_on ? ` · as on ${fmtDate(figure.as_on)}` : ''}
      </p>
    </button>
  )
}

/** A labelled figure inside a card — the workhorse for tiles and stat rows. */
export function Stat({ label, value, sub, status, basis, trace, traceTitle,
                       size = 'md', align = 'left', className }) {
  const { openTrace, indicative } = useApp()
  const clickable = !!trace
  const Wrap = clickable ? 'button' : 'div'
  return (
    <Wrap
      type={clickable ? 'button' : undefined}
      onClick={clickable ? () => openTrace(trace, traceTitle || label) : undefined}
      className={cls('group min-w-0 block w-full', align === 'right' && 'text-right',
                     clickable && 'cursor-pointer', className)}
    >
      <div className={cls('flex items-center gap-1.5', align === 'right' && 'justify-end')}>
        <span className="label truncate">{label}</span>
        {status && <Dot status={status} />}
        {basis && <Why>{basis}</Why>}
      </div>
      <div className={cls('mt-1 flex items-baseline', align === 'right' && 'justify-end')}>
        <span className={cls('font-semibold tracking-tight tnum',
          size === 'lg' ? 'text-[22px] leading-tight' : size === 'sm' ? 'text-[15px]' : 'text-[18px]',
          status === 'Red' ? 'text-red' : 'text-ink')}>
          {value}
        </span>
        <StaleDot show={indicative} />
        {clickable && <Icon name="chevronRight" size={12}
          className="ml-1 text-ink-faint opacity-0 group-hover:opacity-100 transition-opacity" />}
      </div>
      {sub && <p className="mt-1 text-2xs text-ink-muted leading-snug">{sub}</p>}
    </Wrap>
  )
}

/** A row of stats with hairline separators. */
export function StatRow({ children, cols = 4, className }) {
  return (
    <div className={cls('grid divide-x divide-line-soft', className)}
         style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}>
      {React.Children.map(children, (c, i) => (
        <div className={cls('min-w-0', i === 0 ? 'pr-4' : 'px-4', i === cols - 1 && 'pr-0')}>{c}</div>
      ))}
    </div>
  )
}

/** Delta beside a figure. Direction is an arrow + word, never colour alone. */
export function Delta({ value, suffix = '', goodIsUp = true, format }) {
  if (value === null || value === undefined) return null
  const up = value > 0
  const good = up === goodIsUp
  const s = value === 0 ? st('Grey') : good ? st('Green') : st('Amber')
  return (
    <span className={cls('inline-flex items-center gap-0.5 text-2xs font-semibold', s.text)}>
      {value !== 0 && <Icon name={up ? 'arrowUp' : 'arrowDown'} size={11} strokeWidth={2.4} />}
      {format ? format(Math.abs(value)) : `${Math.abs(value).toFixed(1)}${suffix}`}
    </span>
  )
}
