import { useId } from 'react'
import { ArrowRight, ChevronDown, FlaskConical, ShieldCheck } from 'lucide-react'
import {
  Button,
  Card,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
  Field,
  Input,
  Tooltip
} from '@/components/ui'
import { useWizard } from '../WizardContext'
import { WizardHeader, WizardStepper } from '../WizardPage'
import { SAMPLE_SETS } from '../helpers'
import { FilePanel } from './FilePanel'
import { ResumedNotice } from '../ResumedNotice'

function SampleButton(): React.JSX.Element | null {
  const { module, loadSampleSet, busy } = useWizard()
  const sets = SAMPLE_SETS[module.id as keyof typeof SAMPLE_SETS]
  if (!sets) return null
  const loading = busy.A || busy.B
  if (sets.length === 1) {
    return (
      <Button variant="outline" loading={loading} onClick={() => void loadSampleSet(sets[0])} data-testid="try-samples">
        {!loading && <FlaskConical size={15} />} Try with sample files
      </Button>
    )
  }
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" loading={loading} data-testid="try-samples">
          {!loading && <FlaskConical size={15} />} Try with sample files <ChevronDown size={14} />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent className="w-[320px]">
        <DropdownMenuLabel>Choose a sample pair</DropdownMenuLabel>
        {sets.map((s) => (
          <DropdownMenuItem key={s.id} onSelect={() => void loadSampleSet(s)} data-testid={`sample-${s.id}`}>
            <span className="block font-semibold">{s.label}</span>
            <span className="block text-[12px] text-muted">{s.description}</span>
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

export function UploadStep(): React.JSX.Element {
  const { state, dispatch } = useWizard()
  const accountId = useId()
  const periodId = useId()
  const ready = !!state.files.A && !!state.files.B
  if (state.origin === 'resumed') return <ResumedNotice />
  return (
    <>
      <WizardHeader right={<SampleButton />} />
      <WizardStepper />
      <div className="grid gap-5 lg:grid-cols-2">
        <FilePanel side="A" />
        <FilePanel side="B" />
      </div>
      <Card className="mt-5 flex flex-wrap items-end gap-4 p-5">
        <Field label="Account" htmlFor={accountId} className="min-w-[240px] flex-1" hint="Shown on the results, the export and in Recon History.">
          <Input
            id={accountId}
            value={state.accountLabel}
            placeholder="e.g. ENBD Current A/c 1012-4587-001"
            maxLength={120}
            onChange={(e) => dispatch({ type: 'meta', accountLabel: e.target.value })}
          />
        </Field>
        <Field label="Period" htmlFor={periodId} className="w-[260px]" hint="Filled from the dates in the file. Edit if needed.">
          <Input id={periodId} value={state.period} placeholder="e.g. Sep 2026" maxLength={60} onChange={(e) => dispatch({ type: 'meta', period: e.target.value })} />
        </Field>
        <div className="mb-[22px] ml-auto flex items-center gap-4">
          <span className="hidden items-center gap-1.5 text-[12.5px] text-muted xl:inline-flex">
            <ShieldCheck size={15} className="text-matched" /> Files are read on this computer. Nothing is uploaded.
          </span>
          <Tooltip content="Add both files first." disabled={ready}>
            <span>
              <Button size="lg" disabled={!ready} onClick={() => dispatch({ type: 'go', step: 1 })} data-testid="to-map">
                Continue to Map &amp; rules <ArrowRight size={16} />
              </Button>
            </span>
          </Tooltip>
        </div>
      </Card>
    </>
  )
}
