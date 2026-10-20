import { useMemo, useState } from 'react'
import { Sparkles } from 'lucide-react'
import type { EngineLine, Suggestion } from '@shared/contracts'
import { approveSuggestion, rejectSuggestion } from '@engine/index'
import { EmptyState, SegmentedControl } from '@/components/ui'
import { SuggestionCard } from '@/features/smart-recon'
import { useWizard } from '../WizardContext'
import { lineIndex, lineSearchText, matchesQuery, sortedSuggestions } from '../review/model'

type Filter = 'open' | 'all'

/** Smart Recon suggestions with Approve / Reject (Smart Recon step and the AI Suggested tab). */
export function SuggestionList({ query = '', className }: { query?: string; className?: string }): React.JSX.Element {
  const { state, act } = useWizard()
  const session = state.session
  const [filter, setFilter] = useState<Filter>('open')
  const [busyId, setBusyId] = useState<string | null>(null)
  const idx = useMemo(() => (session ? lineIndex(session.result) : new Map<string, EngineLine>()), [session])
  const list = useMemo(() => {
    if (!session) return []
    const all = sortedSuggestions(session.suggestions).filter((s) => filter === 'all' || s.status === 'open')
    if (!query.trim()) return all
    return all.filter((s) => {
      const lines = [...s.aIds, ...s.bIds].map((id) => idx.get(id)).filter((l): l is EngineLine => !!l)
      return matchesQuery(`${lineSearchText(lines)} ${s.reason}`.toLowerCase(), query)
    })
  }, [session, filter, query, idx])
  if (!session) return <></>
  const locked = !!session.finalised
  const pending = session.suggestions.filter((s) => s.status === 'open').length

  const decide = async (s: Suggestion, approve: boolean): Promise<void> => {
    setBusyId(s.id)
    await act(
      (cur, user) => (approve ? approveSuggestion(cur, s.id, user) : rejectSuggestion(cur, s.id, user)),
      approve ? 'Suggestion approved and moved to Matched' : 'Suggestion rejected; the lines stay unmatched'
    )
    setBusyId(null)
  }

  return (
    <div className={className}>
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="text-[13px] text-muted">
          <strong className="text-ink">{pending}</strong> pending of {session.suggestions.length} suggestion{session.suggestions.length === 1 ? '' : 's'}
        </div>
        <SegmentedControl
          size="sm"
          className="w-[200px]"
          aria-label="Which suggestions to show"
          value={filter}
          onValueChange={setFilter}
          options={[
            { value: 'open', label: 'Pending' },
            { value: 'all', label: 'All' }
          ]}
        />
      </div>
      {list.length === 0 ? (
        <EmptyState
          icon={<Sparkles size={22} />}
          title={session.suggestions.length === 0 ? 'No suggestions yet' : query ? 'No suggestions match the search' : 'Nothing pending'}
          description={
            session.suggestions.length === 0
              ? 'Run Smart Recon to look for sum matches, partial references and (with an API key) AI matches among the unmatched lines. Every suggestion waits here for your approval.'
              : query
                ? 'Try a different word or amount.'
                : 'Every suggestion has been approved or rejected. Choose “All” to see them.'
          }
        />
      ) : (
        <div className="grid gap-3 2xl:grid-cols-2">
          {list.map((s) => (
            <SuggestionCard
              key={s.id}
              suggestion={s}
              result={session.result}
              disabled={locked || busyId !== null}
              onApprove={locked ? undefined : (x) => void decide(x, true)}
              onReject={locked ? undefined : (x) => void decide(x, false)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
