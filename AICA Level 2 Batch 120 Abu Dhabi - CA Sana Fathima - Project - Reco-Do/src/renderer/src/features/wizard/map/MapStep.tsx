import { useMemo, useRef, useState } from 'react'
import { AlertCircle, ArrowLeft, ArrowRight, ChevronDown, ChevronRight, Info } from 'lucide-react'
import type { ParsedTable, ReconConfig } from '@shared/contracts'
import { parseDate, valueOverlap } from '@shared/parsing'
import { Button, Card, FileTile, Input, SectionTitle, Select, Spinner, Tooltip } from '@/components/ui'
import { cn } from '@/lib/cn'
import { useWizard } from '../WizardContext'
import { WizardHeader, WizardStepper } from '../WizardPage'
import { ResumedNotice } from '../ResumedNotice'
import { finalConfig } from '../configFactory'
import { hasAmountKey, shortSideNames, tierRuleText } from '../helpers'
import { parsePrefixes } from '../keys'
import { AmountCard } from './AmountCard'
import { DateOrderCard } from './DateOrderCard'
import { KeyTable } from './KeyTable'
import { LoadSavedMenu, SaveSetupDialog, type SaveKind } from './SavedSetups'
import { SignCard } from './SignCard'

const NONE = '__none'

function FileSummary({ name, table, fileName }: { name: string; table: ParsedTable; fileName: string }): React.JSX.Element {
  return (
    <Card className="min-w-0 p-4">
      <SectionTitle className="mb-2.5">{name}</SectionTitle>
      <div className="flex items-center gap-3">
        <FileTile name={fileName} size={36} />
        <div className="min-w-0">
          <div className="truncate text-[14px] font-bold" title={fileName}>
            {fileName}
          </div>
          <div className="text-[12.5px] text-muted">
            {table.rows.length.toLocaleString('en-US')} rows · {table.headerRowIndex < 0 ? 'no header row' : `header on row ${table.headerRowIndex + 1}`} · {table.columns.length} columns
          </div>
        </div>
      </div>
      <ul className="mt-2.5 flex flex-wrap gap-1.5" aria-label={`Columns in ${name}`}>
        {table.columns.map((c) => (
          <li key={c} className="rounded-md border border-line bg-[#F4F6F9] px-2 py-0.5 text-[12px]">
            {c}
          </li>
        ))}
      </ul>
    </Card>
  )
}

function sampleValues(t: ParsedTable, col: string): (string | number | Date | null)[] {
  const out: (string | number | Date | null)[] = []
  const step = Math.max(1, Math.floor(t.rows.length / 400))
  for (let i = 0; i < t.rows.length && out.length < 400; i += step) out.push(t.rows[i].values[col] ?? null)
  return out
}

/** General: why each pair was proposed (header similarity and value overlap). */
function SuggestedPairs({ config, tableA, tableB }: { config: ReconConfig; tableA: ParsedTable; tableB: ParsedTable }): React.JSX.Element {
  const rows = useMemo(
    () =>
      config.keys
        .filter((k) => k.type !== 'amount' && k.columnA && k.columnB && tableA.columns.includes(k.columnA) && tableB.columns.includes(k.columnB))
        .map((k) => {
          const same = k.columnA.trim().toLowerCase() === k.columnB.trim().toLowerCase()
          const a = sampleValues(tableA, k.columnA)
          const b = sampleValues(tableB, k.columnB)
          // Dates are compared both ways, by rows (as the suggestion does), so a single repeated date is not "100%".
          const overlap = k.type === 'date' ? valueOverlap(a.map((v) => parseDate(v)), b.map((v) => parseDate(v)), { mutual: true }) : valueOverlap(a, b)
          return { k, same, overlap }
        }),
    [config.keys, tableA, tableB]
  )
  return (
    <div>
      <SectionTitle className="mb-2">Suggested pairs (from column names and values)</SectionTitle>
      {rows.length === 0 ? (
        <p className="text-[12.5px] text-muted">No pairs yet. Add a key and pick a column on each side.</p>
      ) : (
        <ul className="flex flex-col gap-1.5 text-[13px]">
          {rows.map(({ k, same, overlap }) => (
            <li key={k.id} className="flex items-baseline justify-between gap-3">
              <span className="min-w-0">
                <span className="font-medium">
                  {k.columnA} ↔ {k.columnB}
                </span>
                <span className="text-[12px] text-muted"> · {overlap > 0 ? `${Math.round(overlap * 100)}% values overlap` : same ? 'same header' : 'no values in common'}</span>
              </span>
              <span className={cn('shrink-0 text-[12.5px] font-semibold', k.use ? 'text-matched' : 'text-muted')}>{k.use ? '✓ Used' : 'Not used'}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function Advanced({ config, columnsA, columnsB, onChange }: { config: ReconConfig; columnsA: string[]; columnsB: string[]; onChange: (c: ReconConfig) => void }): React.JSX.Element {
  const [open, setOpen] = useState(false)
  const [prefixText, setPrefixText] = useState(config.referencePrefixes.join(', '))
  const party = (side: 'A' | 'B'): React.JSX.Element => {
    const cols = side === 'A' ? columnsA : columnsB
    const value = side === 'A' ? config.partyColumnA : config.partyColumnB
    return (
      <label className="flex min-w-0 flex-1 flex-col gap-1 text-[12.5px] font-semibold text-ink">
        <span className="truncate">Party column in {side === 'A' ? config.sideAName : config.sideBName}</span>
        <Select
          size="sm"
          value={value && cols.includes(value) ? value : NONE}
          onValueChange={(v) => onChange({ ...config, [side === 'A' ? 'partyColumnA' : 'partyColumnB']: v === NONE ? undefined : v })}
          options={[{ value: NONE, label: 'None' }, ...cols.map((c) => ({ value: c, label: c }))]}
        />
      </label>
    )
  }
  return (
    <Card className="p-5">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 text-[11.5px] font-bold tracking-[1.2px] text-muted uppercase outline-none hover:text-ink focus-visible:ring-2 focus-visible:ring-primary/40"
      >
        {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />} Advanced: reference prefixes and party columns
      </button>
      {open && (
        <div className="mt-4 flex flex-col gap-4">
          <label className="flex flex-col gap-1.5 text-[13px] font-semibold">
            Prefixes ignored by the Normalised rule
            <Input
              value={prefixText}
              onChange={(e) => setPrefixText(e.target.value)}
              onBlur={() => {
                const list = parsePrefixes(prefixText)
                setPrefixText(list.join(', '))
                onChange({ ...config, referencePrefixes: list })
              }}
            />
            <span className="text-[12px] font-normal text-muted">Comma separated, e.g. CHQ, FT, TT, INV, REF. “CHQ-004512” and “4512” then compare as equal.</span>
          </label>
          <div className="flex flex-col gap-3 md:flex-row">
            {party('A')}
            {party('B')}
          </div>
          <p className="-mt-2 text-[12px] text-muted">Smart Recon’s sum matching only groups lines of the same party when party columns are set.</p>
        </div>
      )}
    </Card>
  )
}

export function MapStep(): React.JSX.Element {
  const { state, module, dispatch, configErrors, run, running, settings } = useWizard()
  const [saveKind, setSaveKind] = useState<SaveKind | null>(null)
  const amountRef = useRef<HTMLDivElement>(null)
  const fa = state.files.A
  const fb = state.files.B
  if (state.origin === 'resumed') return <ResumedNotice />
  if (!fa || !fb) {
    return (
      <>
        <WizardHeader />
        <WizardStepper />
        <Card className="p-6 text-[14px] text-muted">Add both files on the Upload step first.</Card>
      </>
    )
  }
  const cfg = state.config ? finalConfig(state.config, state.sideAName, state.sideBName, settings.currency || 'AED') : null
  const setCfg = (c: ReconConfig): void => dispatch({ type: 'patchConfig', patch: c })
  const [shortA, shortB] = shortSideNames(module.id, state.sideAName, state.sideBName)
  const amount = hasAmountKey(cfg)
  const used = cfg?.keys.filter((k) => k.use) ?? []
  const general = module.id === 'general'

  return (
    <>
      <WizardHeader right={<LoadSavedMenu />} />
      <WizardStepper />
      <div className="mb-5 grid gap-5 lg:grid-cols-2">
        <FileSummary name={state.sideAName} table={fa.table} fileName={fa.fileName} />
        <FileSummary name={state.sideBName} table={fb.table} fileName={fb.fileName} />
      </div>

      {!cfg ? (
        <Card className="flex items-center gap-3 p-6 text-[14px] text-muted">
          <Spinner /> Suggesting match keys from the column names and values…
        </Card>
      ) : (
        <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_340px]">
          <div className="flex min-w-0 flex-col gap-5">
            <Card className="p-5">
              <SectionTitle className="mb-3" right={state.configSource && state.configSource.kind !== 'suggested' ? `${state.configSource.kind === 'template' ? 'Template' : 'Mapping'}: ${state.configSource.name}` : 'Suggested — please confirm'}>
                {general ? 'Match keys — column in File A ↔ column in File B' : 'Match keys — map each field'}
              </SectionTitle>
              <div className="overflow-x-auto">
                <div className="min-w-[640px]">
                  <KeyTable
                    config={cfg}
                    columnsA={fa.table.columns}
                    columnsB={fb.table.columns}
                    sideAName={state.sideAName}
                    sideBName={state.sideBName}
                    onChange={setCfg}
                    onEditAmount={() => amountRef.current?.focus()}
                  />
                </div>
              </div>
              {general && (
                <p className="mt-3 text-[12.5px] text-muted">
                  Amount is optional. With no amount key, results show record counts and the export shows a <strong className="text-ink">record-count statement</strong> instead of a balance statement.
                </p>
              )}
              {configErrors.length > 0 && (
                <div role="alert" className="mt-3 rounded-lg border border-[#F3C9C9] bg-[#FDF3F3] px-3.5 py-2.5 text-[13px]">
                  <div className="mb-1 flex items-center gap-1.5 font-semibold text-unmatched">
                    <AlertCircle size={15} /> Fix before running
                  </div>
                  <ul className="list-disc pl-6 text-ink">
                    {configErrors.map((e) => (
                      <li key={e}>{e}</li>
                    ))}
                  </ul>
                </div>
              )}
            </Card>
            {amount && (
              <AmountCard ref={amountRef} config={cfg} columnsA={fa.table.columns} columnsB={fb.table.columns} tableA={fa.table} tableB={fb.table} onChange={setCfg} />
            )}
            <DateOrderCard config={cfg} tableA={fa.table} tableB={fb.table} onChange={setCfg} />
            <Advanced config={cfg} columnsA={fa.table.columns} columnsB={fb.table.columns} onChange={setCfg} />
          </div>

          <Card className="flex flex-col gap-5 p-5 xl:sticky xl:top-0">
            {general && <SuggestedPairs config={cfg} tableA={fa.table} tableB={fb.table} />}
            {amount ? (
              <SignCard moduleId={module.id} config={cfg} tableA={fa.table} tableB={fb.table} shortA={shortA} shortB={shortB} onSign={(sign) => setCfg({ ...cfg, sign })} />
            ) : (
              !general && (
                <p className="flex gap-2 text-[13px] text-muted">
                  <Info size={16} className="mt-0.5 shrink-0" /> No amount key is used, so the sign convention does not apply.
                </p>
              )
            )}
            <div className="rounded-lg border border-[#DCD6F7] bg-[#F5F3FE] px-3.5 py-3 text-[13px] leading-relaxed text-[#3B2E8C]">
              {tierRuleText(used.length, used.some((k) => k.type === 'date'))}
            </div>
            <div className="flex flex-wrap gap-2.5">
              <Button variant="outline" onClick={() => setSaveKind(general ? 'template' : 'mapping')}>
                {general ? 'Save as template' : 'Save mapping'}
              </Button>
              {general && (
                <Button variant="ghost" onClick={() => setSaveKind('mapping')}>
                  Save mapping
                </Button>
              )}
            </div>
            <div className="flex gap-2.5">
              <Button variant="secondary" onClick={() => dispatch({ type: 'go', step: 0 })}>
                <ArrowLeft size={15} /> Back
              </Button>
              <Tooltip content={configErrors[0]} disabled={configErrors.length === 0}>
                <span className="flex-1">
                  <Button className="w-full" size="lg" disabled={configErrors.length > 0} loading={running} onClick={() => void run()} data-testid="run-recon">
                    Run reconciliation <ArrowRight size={16} />
                  </Button>
                </span>
              </Tooltip>
            </div>
          </Card>
        </div>
      )}
      <SaveSetupDialog kind={saveKind ?? 'mapping'} open={saveKind !== null} onOpenChange={(o) => !o && setSaveKind(null)} />
    </>
  )
}
