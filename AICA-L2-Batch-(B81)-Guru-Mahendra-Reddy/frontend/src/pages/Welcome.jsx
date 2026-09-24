// The first screen the application ever shows. Two doors, and no default —
// the two audiences want opposite things and guessing wrong wastes the first
// two minutes of either one.
import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { useApp } from '../lib/store'
import { Icon } from '../components/ui'

export default function Welcome({ onDone }) {
  const { user, notify } = useApp()
  const nav = useNavigate()
  const [busy, setBusy] = useState(null)
  const [error, setError] = useState(null)

  const mayDecide = user && ['Admin', 'CFO'].includes(user.role)

  async function loadDemo() {
    setBusy('demo'); setError(null)
    try {
      const r = await api.post('/api/onboarding/demo', { confirm: true }, {})
      notify(r.message)
      window.location.href = '/'
    } catch (e) { setError(e.message); setBusy(null) }
  }

  return (
    <div className="min-h-full grid place-items-center px-6 py-14">
      <div className="w-full max-w-3xl">
        <div className="flex items-center gap-3 mb-8">
          <div className="w-10 h-10 rounded-xl bg-navy-700 grid place-items-center shrink-0">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white"
                 strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 17l6-6 4 4 8-8" /><path d="M15 6h6v6" />
            </svg>
          </div>
          <div>
            <h1 className="text-[19px] font-semibold text-ink tracking-tight">Cash Runway</h1>
            <p className="text-[13px] text-ink-muted">
              Nothing is set up yet. Which of these are you doing?
            </p>
          </div>
        </div>

        {error && (
          <div className="mb-5 rounded-xl border border-status-red/30 bg-status-red/5 px-4 py-3
                          text-[13px] text-ink">{error}</div>
        )}

        <div className="grid md:grid-cols-2 gap-4">
          <Door
            icon="eye"
            title="Look around first"
            lead="Load the demonstration company"
            busy={busy === 'demo'}
            disabled={!mayDecide || !!busy}
            cta="Load Northwind Robotics"
            onClick={loadDemo}
            points={[
              'Eighteen months of ledger for a real-shaped startup, as at 31-Aug-2026.',
              'Every screen populated, so you can see what the tool does before typing anything.',
              'Nothing is asserted — the balances are derived from the entries, so the numbers reconcile.',
            ]}
            foot="You can clear it and start again at any time."
          />
          <Door
            icon="building"
            title="Set up my company"
            lead="Start from an empty book"
            disabled={!mayDecide || !!busy}
            cta="Set up my company"
            onClick={() => nav('/set-up')}
            points={[
              'Ten minutes gets you a runway number you can defend: bank balances and three months of movement.',
              'Bring figures in from Tally, from a workbook your team fills in, or by typing them.',
              'The rest is staged — each screen tells you what it still needs.',
            ]}
            foot="Nothing is written until you have seen what will be written."
            primary
          />
        </div>

        {!mayDecide && (
          <p className="mt-5 text-[12.5px] text-ink-muted">
            You are signed in as {user?.role}. Setting up an entity is an Admin or CFO
            decision — ask one of them to make this choice.
          </p>
        )}

        <p className="mt-8 text-[12.5px] text-ink-muted leading-relaxed">
          Either way the sign-in accounts stay as they are. Choosing the demonstration
          company replaces any data in the application; setting up your own does not
          touch it.
        </p>
      </div>
    </div>
  )
}

function Door({ icon, title, lead, points, cta, onClick, busy, disabled, foot, primary }) {
  return (
    <div className={`rounded-2xl border bg-white p-5 flex flex-col
                     ${primary ? 'border-navy-700/30 shadow-sm' : 'border-line'}`}>
      <div className="flex items-center gap-2.5 mb-1">
        <Icon name={icon} size={17} className="text-navy-700" />
        <h2 className="text-[15px] font-semibold text-ink">{title}</h2>
      </div>
      <p className="text-[12.5px] text-ink-muted mb-4">{lead}</p>

      <ul className="space-y-2.5 mb-5 flex-1">
        {points.map((p) => (
          <li key={p} className="flex gap-2.5 text-[13px] text-ink leading-relaxed">
            <span className="mt-[7px] w-1 h-1 rounded-full bg-navy-700/50 shrink-0" />
            <span>{p}</span>
          </li>
        ))}
      </ul>

      <button
        onClick={onClick}
        disabled={disabled}
        className={`w-full rounded-lg px-4 py-2.5 text-[13px] font-medium transition
                    disabled:opacity-40 disabled:cursor-not-allowed
                    ${primary ? 'bg-navy-700 text-white hover:bg-navy-800'
                              : 'border border-line text-ink hover:bg-paper'}`}>
        {busy ? 'Loading…' : cta}
      </button>
      <p className="mt-2.5 text-[11.5px] text-ink-muted">{foot}</p>
    </div>
  )
}
