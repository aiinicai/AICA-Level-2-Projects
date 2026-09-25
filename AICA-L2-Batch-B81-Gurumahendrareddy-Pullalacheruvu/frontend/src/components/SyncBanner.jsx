// Read on every sign-in. A failed sync has to be louder than a successful one:
// the dangerous state is not "sync failed", it is "sync failed four days ago
// and the screen still shows numbers".
import React, { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useEndpoint } from '../lib/store'
import { Icon } from './ui'

const TONE = {
  red:   { bg: 'bg-status-red/[0.06]',   border: 'border-status-red/30',   dot: 'bg-status-red' },
  amber: { bg: 'bg-status-amber/[0.07]', border: 'border-status-amber/35', dot: 'bg-status-amber' },
  green: { bg: 'bg-status-green/[0.05]', border: 'border-status-green/25', dot: 'bg-status-green' },
  grey:  { bg: 'bg-grey/[0.05]',         border: 'border-line',            dot: 'bg-grey' },
}

export default function SyncBanner() {
  const { data } = useEndpoint('/api/connect/status')
  const [dismissed, setDismissed] = useState(false)
  const nav = useNavigate()
  const loc = useLocation()

  if (!data || dismissed) return null
  // On the Tally screen itself the same sentence is already on the card below,
  // and saying it twice reads as a stutter rather than as emphasis.
  if (loc.pathname === '/setup' && loc.search.includes('layer=tally')) return null
  // A healthy connection does not need a banner. Silence is the reward for
  // everything working.
  if (data.level === 'green') return null

  const t = TONE[data.level] || TONE.grey
  const actionable = data.level === 'red' || data.level === 'amber'

  return (
    <div className={`rounded-xl border ${t.border} ${t.bg} px-4 py-2.5 mb-4
                     flex items-center gap-3`}>
      <span className={`w-2 h-2 rounded-full shrink-0 ${t.dot}`} />
      <p className="text-[12.5px] text-ink flex-1 min-w-0">
        {data.headline}
        {data.last_run?.message && (
          <span className="text-ink-muted"> {data.last_run.message}</span>
        )}
      </p>
      {actionable && (
        <button onClick={() => nav('/setup?layer=tally')}
                className="text-[12.5px] font-medium text-navy-700 hover:underline
                           underline-offset-4 shrink-0 whitespace-nowrap">
          {data.unmapped_ledgers > 0 ? 'Map the ledgers' : 'Open Tally setup'}
        </button>
      )}
      <button onClick={() => setDismissed(true)}
              className="text-ink-faint hover:text-ink shrink-0" title="Dismiss until next sign-in">
        <Icon name="check" size={14} />
      </button>
    </div>
  )
}
