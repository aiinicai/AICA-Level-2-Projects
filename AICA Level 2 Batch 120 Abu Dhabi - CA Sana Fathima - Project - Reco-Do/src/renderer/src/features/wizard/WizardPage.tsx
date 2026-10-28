import { Link } from 'react-router-dom'
import { AlertTriangle, History } from 'lucide-react'
import { Button, Card, EmptyState, PAGE_TITLE, Spinner, Stepper } from '@/components/ui'
import { reachableSteps } from './reducer'
import { shortSideNames, stepStatusLines } from './helpers'
import { STEP_TITLES, type StepIndex } from './types'
import { useWizard, WizardHost } from './WizardContext'
import { ReconSwitcher } from './ReconSwitcher'
import type { ModuleId } from '@shared/modules'
import { UploadStep } from './upload/UploadStep'
import { MapStep } from './map/MapStep'
import { ReconcileStep } from './run/ReconcileStep'
import { SmartReconStep } from './smart/SmartReconStep'
import { ReviewStep } from './review/ReviewStep'

const HEADER_SUFFIX = ['Setup', 'Setup', 'Reconcile', 'Smart Recon', 'Results'] as const

/** Page title with the In progress menu and New reconciliation beside it, subtitle, and per-step actions on the right. */
export function WizardHeader({ right }: { right?: React.ReactNode }): React.JSX.Element {
  const { state, module } = useWizard()
  const parts: string[] = []
  if (state.accountLabel) parts.push(state.accountLabel)
  if (state.period) parts.push(state.period)
  const session = state.session
  if (state.step >= 2 && session) {
    const [a, b] = shortSideNames(state.moduleId, state.sideAName, state.sideBName)
    const st = session.result.stats
    parts.push(state.moduleId === 'general' ? `${st.linesA} vs ${st.linesB} lines` : `${st.linesA} ${shortName(a)} lines vs ${st.linesB} ${shortName(b)} lines`)
  }
  const subtitle = parts.length ? parts.join(' · ') : `${state.sideAName} vs ${state.sideBName}`
  return (
    <div className="mb-5 flex flex-wrap items-start justify-between gap-x-6 gap-y-3">
      <div className="min-w-0 flex-[1_1_24rem]">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <h1 className={PAGE_TITLE}>{`${module.name} — ${HEADER_SUFFIX[state.step]}`}</h1>
          <ReconSwitcher />
        </div>
        <p className="mt-1 text-sm text-muted">{subtitle}</p>
      </div>
      {right && <div className="ml-auto flex shrink-0 flex-wrap items-center justify-end gap-2.5">{right}</div>}
    </div>
  )
}

function shortName(name: string): string {
  return name.length > 28 ? `${name.slice(0, 26)}…` : name
}

export function WizardStepper(): React.JSX.Element {
  const { state, dispatch, configErrors } = useWizard()
  const reachable = reachableSteps(state)
  const lines = stepStatusLines(state, configErrors)
  const completed: number[] = []
  if (state.files.A && state.files.B) completed.push(0)
  if (state.config && configErrors.length === 0 && (state.session || state.step > 1)) completed.push(1)
  if (state.session) completed.push(2)
  if (state.session && state.step > 3) completed.push(3)
  if (state.session?.finalised) completed.push(4)
  return (
    <nav aria-label="Reconciliation steps">
      <Stepper
        steps={STEP_TITLES.map((title, i) => ({ title, subtitle: lines[i], disabled: !reachable.has(i as StepIndex) }))}
        current={state.step}
        completed={completed}
        onStepClick={(i) => dispatch({ type: 'go', step: i as StepIndex })}
      />
    </nav>
  )
}

function Body(): React.JSX.Element {
  const { state, resuming, resumeError, startNew } = useWizard()
  if (resuming) {
    return (
      <>
        <WizardHeader />
        <Card className="flex items-center gap-3 p-6 text-[14px] text-muted">
          <Spinner /> Opening the saved reconciliation…
        </Card>
      </>
    )
  }
  if (resumeError) {
    return (
      <>
        <WizardHeader />
        <Card>
          <EmptyState
            icon={<AlertTriangle size={22} />}
            title="The reconciliation could not be opened"
            description={resumeError}
            action={
              <div className="flex gap-2.5">
                <Button variant="secondary" asChild>
                  <Link to="/workspace/history">
                    <History size={15} /> Recon History
                  </Link>
                </Button>
                <Button onClick={startNew}>Start a new reconciliation</Button>
              </div>
            }
          />
        </Card>
      </>
    )
  }
  switch (state.step) {
    case 0:
      return <UploadStep />
    case 1:
      return <MapStep />
    case 2:
      return <ReconcileStep />
    case 3:
      return <SmartReconStep />
    case 4:
      return <ReviewStep />
  }
}

export function WizardPage({ moduleId }: { moduleId: ModuleId }): React.JSX.Element {
  return (
    <WizardHost moduleId={moduleId}>
      <Body />
    </WizardHost>
  )
}
