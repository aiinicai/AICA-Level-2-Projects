import { ArrowLeft, ArrowRight } from 'lucide-react'
import type { Suggestion } from '@shared/contracts'
import { Button, Card, SectionTitle, useToast } from '@/components/ui'
import { SmartReconPanel } from '@/features/smart-recon'
import { errorMessage } from '@/lib/useAsync'
import { useWizard } from '../WizardContext'
import { WizardHeader, WizardStepper } from '../WizardPage'
import { SuggestionList } from './SuggestionList'
import { applySuggestions } from './applySuggestions'

/** Hands Smart Recon results to the session and saves it. Shared by the step and the results side panel. */
export function useSuggestionsHandler(): (list: Suggestion[]) => Promise<void> {
  const { latestSession, commit } = useWizard()
  const toast = useToast()
  return async (list) => {
    // Smart Recon may run for minutes while the user keeps reviewing: add to the newest session, never to the
    // one captured when the run started.
    const s = latestSession()
    if (!s) return
    try {
      const { next, added } = applySuggestions(s, list)
      if (added === 0) {
        toast.info('No new suggestions', 'Everything Smart Recon found is already in the AI Suggested list.')
        return
      }
      if (!(await commit(next))) return
      toast({ tone: 'ai', title: `${added} new suggestion${added === 1 ? '' : 's'}`, description: 'They are in the AI Suggested tab, waiting for your approval. Nothing is matched until you approve it.' })
    } catch (err) {
      toast.error('The suggestions could not be added', errorMessage(err))
    }
  }
}

export function SmartReconStep(): React.JSX.Element {
  const { state, dispatch } = useWizard()
  const onSuggestions = useSuggestionsHandler()
  const session = state.session
  return (
    <>
      <WizardHeader
        right={
          <>
            <Button variant="secondary" onClick={() => dispatch({ type: 'go', step: 2 })}>
              <ArrowLeft size={15} /> Back
            </Button>
            <Button onClick={() => dispatch({ type: 'go', step: 4 })} data-testid="to-review">
              Review &amp; export <ArrowRight size={15} />
            </Button>
          </>
        }
      />
      <WizardStepper />
      {!session ? (
        <Card className="p-6 text-[14px] text-muted">Run the reconciliation first.</Card>
      ) : (
        <div className="grid items-start gap-5 xl:grid-cols-[400px_minmax(0,1fr)]">
          <SmartReconPanel session={session} onSuggestions={(list) => void onSuggestions(list)} disabled={!!session.finalised} />
          <Card className="min-w-0 p-5">
            <SectionTitle className="mb-3">AI suggested — approve or reject</SectionTitle>
            <SuggestionList />
          </Card>
        </div>
      )}
    </>
  )
}
