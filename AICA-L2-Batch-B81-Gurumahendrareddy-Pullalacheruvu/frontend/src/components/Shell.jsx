// The frame every tab sits in: the fixed top strip, the confidence banner, the
// tab rail, and the drill-down drawer.
import React, { useState } from 'react'
import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import { useApp } from '../lib/store'
import { cls, d as fmtDate, inr, pct, st, ts } from '../lib/format'
import { Dot, Drawer, Empty, Icon, Loading, StatusPill, Table, TD, TH } from './ui'
import SyncBanner from './SyncBanner'
import BoardNotice from './BoardNotice'

const TABS = [
  { to: '/',              label: 'Today',           icon: 'grid',         q: 'Am I fine, and what needs me this week?' },
  { to: '/runway-burn',   label: 'Runway & Burn',   icon: 'trend',        q: 'How fast am I spending, on what, and how long does that leave me?' },
  { to: '/liquidity',     label: 'Liquidity',       icon: 'drop',         q: 'Is my cash actually available, and is my position healthy?' },
  { to: '/money-in',      label: 'Money Coming In',  icon: 'inbox',       q: "What's owed to me, will it arrive, and how exposed am I?" },
  { to: '/money-out',     label: 'Money Going Out',  icon: 'out',         q: 'What must I pay, what can wait, what have I committed to?' },
  { to: '/cash-calendar', label: 'Cash Calendar',   icon: 'calendar',     q: 'Which specific week do I have a problem in?' },
  { to: '/plan-vs-actual',label: 'Plan vs Actual',  icon: 'target',       q: 'Are we tracking to what we told ourselves and the board?' },
  { to: '/scenarios',     label: 'Scenarios',       icon: 'sliders',      q: 'What happens if, and which lever should I pull?' },
  { to: '/capital-debt',  label: 'Capital & Debt',  icon: 'bank',         q: 'What do I owe, what can I draw, am I about to breach?' },
  { to: '/board-pack',    label: 'Board Pack',      icon: 'presentation', q: 'Can I produce the cash story in ten minutes?' },
  { to: '/alerts',        label: 'Alerts',          icon: 'bell',         q: 'What has the tool told me, and did anyone act on it?' },
  { to: '/setup',         label: 'Setup',           icon: 'cog',          q: 'Sources, plans, rules, people and definitions.', apart: true },
]

export default function Shell({ children }) {
  const { strip, entities, entityId, setEntityId, asOn, setAsOn, user, signOut,
          trace, closeTrace, toast } = useApp()
  const loc = useLocation()
  const nav = useNavigate()
  const [menu, setMenu] = useState(false)
  const active = TABS.find((t) => t.to === loc.pathname) || TABS[0]
  const conf = strip?.confidence

  return (
    <div className="min-h-full flex flex-col">
      {/* ---- Top strip: fixed, on every tab -------------------------- */}
      <header className="sticky top-0 z-30 bg-white border-b border-line">
        <div className="flex items-stretch h-14">
          <div className="w-[236px] shrink-0 flex items-center gap-2.5 px-4 border-r border-line">
            <span className="w-7 h-7 rounded-lg bg-navy-700 grid place-items-center shrink-0">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="white"
                   strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 17l6-6 4 4 8-8" /><path d="M15 6h6v6" />
              </svg>
            </span>
            <span className="font-semibold text-[15px] tracking-tight">Cash Runway</span>
          </div>

          <div className="flex-1 min-w-0 flex items-center gap-0 overflow-x-auto">
            {/* Entity */}
            <StripCell label="Entity" className="min-w-[180px]">
              <select value={entityId ?? ''} onChange={(e) => setEntityId(Number(e.target.value))}
                      className="w-full bg-transparent text-[13px] font-semibold text-ink outline-none cursor-pointer -ml-0.5">
                {entities.map((e) => <option key={e.id} value={e.id}>{e.name}</option>)}
              </select>
            </StripCell>

            {/* As on */}
            <StripCell label="As on" className="min-w-[132px]">
              <input type="date" value={asOn ?? strip?.as_on ?? ''}
                     max={strip?.today}
                     onChange={(e) => setAsOn(e.target.value || null)}
                     className="w-full bg-transparent text-[13px] font-semibold text-ink outline-none cursor-pointer tnum" />
            </StripCell>

            <StripCell label="Books position" className="min-w-[112px]">
              <span className="text-[13px] font-semibold tnum">{inr(strip?.books_position)}</span>
            </StripCell>

            <StripCell label="Bank position" className="min-w-[112px]">
              <span className="text-[13px] font-semibold tnum">{inr(strip?.bank_position)}</span>
            </StripCell>

            <StripCell label="Difference" className="min-w-[146px]">
              {strip ? (
                <span className="flex items-center gap-1.5">
                  <span className="text-[13px] font-semibold tnum">{inr(strip.difference)}</span>
                  <StatusPill status={strip.difference_status}
                              label={pct(strip.difference_pct, { decimals: 2 })}
                              className="!py-0" />
                </span>
              ) : <span className="text-[13px] text-ink-faint">—</span>}
            </StripCell>

            <StripCell label="Data updated" className="min-w-[168px]">
              <span className="text-[13px] font-semibold">{ts(strip?.data_updated)}</span>
              <span className="text-2xs text-ink-muted ml-1.5">Books: {strip?.books_status ?? '—'}</span>
            </StripCell>
          </div>

          {/* Alerts + user */}
          <div className="shrink-0 flex items-center gap-1 px-3 border-l border-line">
            <button onClick={() => nav('/alerts')}
                    className="relative p-2 rounded-lg text-ink-muted hover:text-ink hover:bg-navy-50"
                    aria-label="Alerts">
              <Icon name="bell" size={18} />
              {strip?.unacknowledged_alerts > 0 && (
                <span className="absolute -top-0.5 -right-0.5 min-w-[17px] h-[17px] px-1 rounded-full
                                 bg-red text-white text-[10px] font-bold grid place-items-center">
                  {strip.unacknowledged_alerts}
                </span>
              )}
            </button>

            <div className="relative">
              <button onClick={() => setMenu((m) => !m)}
                      className="flex items-center gap-2 pl-2 pr-1.5 py-1.5 rounded-lg hover:bg-navy-50">
                <span className="w-7 h-7 rounded-full bg-navy-100 text-navy-700 grid place-items-center
                                 text-2xs font-bold shrink-0">
                  {(user?.name || '?').split(' ').map((w) => w[0]).slice(0, 2).join('')}
                </span>
                <span className="text-left hidden lg:block">
                  <span className="block text-2xs font-semibold text-ink leading-tight">{user?.name}</span>
                  <span className="block text-[10px] text-ink-muted leading-tight">{user?.role}</span>
                </span>
                <Icon name="chevron" size={14} className="text-ink-faint" />
              </button>
              {menu && (
                <>
                  <div className="fixed inset-0 z-10" onClick={() => setMenu(false)} />
                  <div className="absolute right-0 top-full mt-1 z-20 w-56 card shadow-pop py-1 animate-in">
                    <div className="px-3 py-2 border-b border-line-soft">
                      <p className="text-[13px] font-semibold">{user?.name}</p>
                      <p className="text-2xs text-ink-muted">{user?.email}</p>
                      <p className="text-2xs text-ink-muted mt-1">{user?.role}</p>
                    </div>
                    <button onClick={signOut}
                            className="w-full flex items-center gap-2 px-3 py-2 text-[13px] text-ink-soft hover:bg-navy-50">
                      <Icon name="logout" size={15} /> Sign out
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>

        {/* ---- Confidence banner: only when needed ------------------- */}
        {conf?.show_banner && (
          <div className={cls('flex items-start gap-2.5 px-4 py-2 border-t text-[13px]',
                              conf.level === 'Low' ? 'bg-grey-bg border-grey-line text-grey'
                                                   : 'bg-amber-bg border-amber-line text-amber')}>
            <Icon name="alert" size={15} className="mt-0.5 shrink-0" />
            <p className="min-w-0">
              <span className="font-semibold">{conf.message}</span>
              <span className="opacity-80"> Every headline number below carries a grey dot until this clears.</span>
            </p>
          </div>
        )}
      </header>

      <div className="flex-1 flex min-h-0">
        {/* ---- Tab rail ---------------------------------------------- */}
        <nav className="w-[236px] shrink-0 border-r border-line bg-white/60 py-3 overflow-y-auto">
          {TABS.map((t) => (
            <div key={t.to} className={cls(t.apart && 'mt-3 pt-3 border-t border-line-soft mx-3')}>
              <NavLink to={t.to} end={t.to === '/'} title={t.q}
                       className={({ isActive }) => cls(
                         'flex items-center gap-2.5 mx-3 px-3 py-2 rounded-lg text-[13px] font-medium transition-colors',
                         isActive ? 'bg-navy-700 text-white shadow-card'
                                  : 'text-ink-soft hover:bg-navy-50 hover:text-navy-700')}>
                <Icon name={t.icon} size={16} />
                <span className="truncate">{t.label}</span>
              </NavLink>
            </div>
          ))}
          <p className="basis mx-6 mt-4 pt-3 border-t border-line-soft">
            One question per tab. If it can't be said in a sentence, it isn't a tab.
          </p>
        </nav>

        {/* ---- Page -------------------------------------------------- */}
        <main className="flex-1 min-w-0 overflow-y-auto">
          <div className="px-6 py-5 max-w-[1560px]">
            <div className="mb-5">
              <h1 className="text-[19px] font-semibold text-ink tracking-tight">{active.label}</h1>
              <p className="text-[13px] text-ink-muted mt-0.5">{active.q}</p>
            </div>
            <SyncBanner />
            <BoardNotice />
            {children}
            <div className="h-10" />
          </div>
        </main>
      </div>

      <TraceDrawer trace={trace} onClose={closeTrace} />

      {toast && (
        <div className="fixed bottom-5 left-1/2 -translate-x-1/2 z-50 animate-in">
          <div className={cls('flex items-center gap-2 rounded-lg px-4 py-2.5 shadow-pop text-[13px] font-medium',
                              toast.tone === 'error' ? 'bg-red text-white' : 'bg-ink text-white')}>
            <Icon name={toast.tone === 'error' ? 'alert' : 'check'} size={15} />
            {toast.message}
          </div>
        </div>
      )}
    </div>
  )
}

function StripCell({ label, children, className }) {
  return (
    <div className={cls('px-4 py-2 border-r border-line-soft h-full flex flex-col justify-center shrink-0', className)}>
      <span className="text-[10px] font-semibold uppercase tracking-wide text-ink-faint leading-none mb-1">{label}</span>
      <div className="leading-none">{children}</div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// The drill-down. Every clickable number lands here.
// ---------------------------------------------------------------------------
function TraceDrawer({ trace, onClose }) {
  if (!trace) return null
  const { data, loading, error, title } = trace
  const rows = data?.rows ?? []

  return (
    <Drawer open onClose={onClose} width="max-w-4xl"
            title={data?.title || title || 'Behind this number'}
            sub={data?.formula || (data?.count !== undefined ? `${data.count} entries` : undefined)}>
      {loading && <Loading label="Pulling the entries behind this figure…" />}
      {error && <p className="text-[13px] text-red">{error}</p>}

      {data && (
        <>
          {data.total !== undefined && (
            <div className="card card-pad mb-4 flex items-baseline justify-between">
              <span className="label">Total</span>
              <span className="text-[19px] font-semibold tnum">{inr(data.total)}</span>
            </div>
          )}
          {data.value !== undefined && data.value !== null && (
            <div className="card card-pad mb-4 flex items-baseline justify-between">
              <span className="label">Value</span>
              <span className="text-[19px] font-semibold tnum">{data.value}</span>
            </div>
          )}

          {rows.length === 0 && <Empty>Nothing sits behind this figure for the period selected.</Empty>}

          {rows.length > 0 && <GenericTable rows={rows} />}

          {data.basis && (
            <p className="basis mt-4 pt-3 border-t border-line-soft">{data.basis}</p>
          )}
        </>
      )}
    </Drawer>
  )
}

const HIDE = new Set(['trace', 'id', 'status'])
const MONEY_KEYS = /amount|balance|cash|outstanding|total|value|burn|cost|contribution/i
const DATE_KEYS = /date|as_on|month|_on$/

function GenericTable({ rows }) {
  const keys = Object.keys(rows[0]).filter((k) => !HIDE.has(k) && typeof rows[0][k] !== 'object')
  return (
    <Table>
      <thead><tr>
        {keys.map((k, i) => <TH key={k} left={i === 0}>{human(k)}</TH>)}
      </tr></thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i} className="tr-hover">
            {keys.map((k, j) => (
              <TD key={k} left={j === 0}>{cell(k, r[k])}</TD>
            ))}
          </tr>
        ))}
      </tbody>
    </Table>
  )
}

const human = (k) => k.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase())

function cell(key, v) {
  if (v === null || v === undefined || v === '') return <span className="text-ink-faint">—</span>
  if (typeof v === 'boolean') return v ? 'Yes' : 'No'
  if (typeof v === 'number' && MONEY_KEYS.test(key)) return inr(v)
  if (typeof v === 'string' && DATE_KEYS.test(key) && /^\d{4}-\d{2}-\d{2}/.test(v)) return fmtDate(v)
  if (typeof v === 'string' && v.length > 90) return <span title={v}>{v.slice(0, 88)}…</span>
  return String(v)
}
