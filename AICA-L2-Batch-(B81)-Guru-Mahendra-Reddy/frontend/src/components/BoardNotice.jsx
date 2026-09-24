// Shown to a board member when something on the screen they are looking at has
// been withheld.
//
// This is not decoration. A board member who can see that a thing was withheld
// is being governed; one who cannot is being misled — and the difference is the
// whole reason the visibility policy is allowed to exist at all. So the notice
// is deliberately plain, names what is hidden, and says who decided.
import React from 'react'
import { useApp } from '../lib/store'
import { Icon } from './ui'

export default function BoardNotice() {
  const { user, restricted } = useApp()
  if (!user || user.role !== 'Board Read-Only') return null
  if (!restricted?.length) return null

  return (
    <div className="rounded-xl border border-line bg-paper px-4 py-2.5 mb-4
                    flex items-start gap-3">
      <Icon name="eyeoff" size={15} className="text-ink-muted mt-0.5" />
      <p className="text-[12.5px] text-ink-muted leading-relaxed">
        <span className="text-ink font-medium">Some detail on this screen is restricted: </span>
        {restricted.join(', ')}.
        {' '}Every figure you can see is the same figure the CFO sees — what is withheld
        is the detail behind it, by the CFO's decision in Setup.
      </p>
    </div>
  )
}
