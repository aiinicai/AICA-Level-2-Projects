import { History, Lock } from 'lucide-react'
import { Button, Card, EmptyState } from '@/components/ui'
import { useWizard } from './WizardContext'
import { WizardHeader, WizardStepper } from './WizardPage'

/**
 * Upload / Map steps of a reconciliation reopened read-only: it is finalised (signed off results never change),
 * or it was saved before Reco-Do kept the source files with each reconciliation.
 */
export function ResumedNotice(): React.JSX.Element {
  const { state, dispatch, startNew } = useWizard()
  const finalised = !!state.session?.finalised
  return (
    <>
      <WizardHeader />
      <WizardStepper />
      <Card>
        <EmptyState
          icon={finalised ? <Lock size={22} /> : <History size={22} />}
          title={finalised ? 'This reconciliation is finalised' : 'Reopened from Recon History'}
          description={
            finalised
              ? 'It was signed off, so its files and settings can no longer change. The results, audit trail and exports are still available. Start a new reconciliation to run it again with different settings.'
              : 'This reconciliation was saved before Reco-Do kept the source files, so the Upload and Map steps are not available for it. The results and every review decision are kept. Start a new reconciliation to run it again with different settings.'
          }
          action={
            <div className="flex gap-2.5">
              <Button variant="secondary" onClick={() => dispatch({ type: 'go', step: 4 })}>
                Back to results
              </Button>
              <Button onClick={startNew}>Start a new reconciliation</Button>
            </div>
          }
        />
      </Card>
    </>
  )
}
