import { useEffect, useMemo, useState } from 'react'
import { AlertTriangle, ArrowLeft, ArrowRight, Sparkles } from 'lucide-react'
import { Button, Card, EmptyState, Progress } from '@/components/ui'
import { useWizard } from '../WizardContext'
import { WizardHeader, WizardStepper } from '../WizardPage'
import { shortSideNames } from '../helpers'
import { KpiCards } from '../review/KpiCards'
import { lineIndex, reviewKpis } from '../review/model'

function Elapsed(): React.JSX.Element {
  const [start] = useState(() => performance.now())
  const [now, setNow] = useState(start)
  useEffect(() => {
    const t = window.setInterval(() => setNow(performance.now()), 200)
    return () => window.clearInterval(t)
  }, [])
  return <span className="num">{((now - start) / 1000).toFixed(1)} s</span>
}

export function ReconcileStep(): React.JSX.Element {
  const { state, module, dispatch, running, runError, run } = useWizard()
  const session = state.session
  const [shortA, shortB] = shortSideNames(module.id, state.sideAName, state.sideBName)
  const kpis = useMemo(() => (session ? reviewKpis(session, lineIndex(session.result)) : null), [session])
  const rowsA = state.files.A?.table.rows.length ?? 0
  const rowsB = state.files.B?.table.rows.length ?? 0

  let body: React.ReactNode
  if (running) {
    body = (
      <Card className="p-8" aria-live="polite">
        <div className="mx-auto max-w-xl">
          <div className="mb-1 text-[16px] font-bold">Reconciling…</div>
          <p className="mb-4 text-[13.5px] text-muted">
            Matching {rowsA.toLocaleString('en-US')} {shortA} lines against {rowsB.toLocaleString('en-US')} {shortB} lines on every selected key. Exact matches
            first, then Doubtful, then Likely. No data leaves this computer.
          </p>
          <Progress label="Matching lines" detail={<Elapsed />} />
        </div>
      </Card>
    )
  } else if (runError) {
    body = (
      <Card>
        <EmptyState
          icon={<AlertTriangle size={22} />}
          title="The reconciliation could not be completed"
          description={runError}
          action={
            <div className="flex gap-2.5">
              <Button variant="secondary" onClick={() => dispatch({ type: 'go', step: 1 })}>
                <ArrowLeft size={15} /> Back to Map &amp; rules
              </Button>
              <Button onClick={() => void run()}>Try again</Button>
            </div>
          }
        />
      </Card>
    )
  } else if (session && kpis) {
    const st = session.result.stats
    const rate = st.linesA > 0 ? Math.round((st.matched / st.linesA) * 100) : 0
    body = (
      <>
        <KpiCards session={session} kpis={kpis} shortA={shortA} shortB={shortB} />
        <Card className="flex flex-wrap items-center gap-5 p-5">
          <div className="min-w-0 flex-1">
            <div className="text-[15px] font-bold">
              {rate}% of {shortA} lines matched automatically
            </div>
            <p className="mt-0.5 text-[13px] text-muted">
              Finished in {(session.result.durationMs / 1000).toFixed(2)} s. {st.doubtful + st.likely} lines need a look and {st.unmatchedA + st.unmatchedB} lines are unmatched.
              Smart Recon can look for sum matches and references written differently among the leftovers.
            </p>
          </div>
          <div className="flex gap-2.5">
            {state.origin === 'new' && (
              <Button variant="secondary" onClick={() => dispatch({ type: 'go', step: 1 })}>
                <ArrowLeft size={15} /> Map &amp; rules
              </Button>
            )}
            <Button variant="outline" onClick={() => dispatch({ type: 'go', step: 4 })} data-testid="to-review">
              Skip to review <ArrowRight size={15} />
            </Button>
            <Button onClick={() => dispatch({ type: 'go', step: 3 })} data-testid="to-smart">
              <Sparkles size={15} /> Smart Recon
            </Button>
          </div>
        </Card>
      </>
    )
  } else {
    body = (
      <Card>
        <EmptyState
          title="Ready to reconcile"
          description="Run the reconciliation from the Map & rules step."
          action={<Button onClick={() => dispatch({ type: 'go', step: 1 })}>Go to Map &amp; rules</Button>}
        />
      </Card>
    )
  }

  return (
    <>
      <WizardHeader />
      <WizardStepper />
      {body}
    </>
  )
}
