import { useMemo, useState } from 'react'
import { FileDown, FileSpreadsheet, Link2, Lock, PanelRightClose, PanelRightOpen, ScrollText, Search, X } from 'lucide-react'
import type { EngineLine, MatchPair, ReconSession, Side } from '@shared/contracts'
import { formatAmount, formatDate } from '@shared/format'
import { acceptPair, addNote, buildStatement, canFinalise, finalise, manualMatch, rejectPair, unmatchPair } from '@engine/index'
import { autoComment, buildReconWorkbook, buildSummaryHtml, exportFileName } from '@export/index'
import { Button, Card, DataTable, Input, Tabs, TabsContent, TabsList, TabsTrigger, Tooltip, useToast, type DataColumn } from '@/components/ui'
import { SmartReconPanel, SuggestionCard } from '@/features/smart-recon'
import { errorMessage } from '@/lib/useAsync'
import { cn } from '@/lib/cn'
import { useWizard } from '../WizardContext'
import { WizardHeader, WizardStepper } from '../WizardPage'
import { clip, shortSideNames } from '../helpers'
import { useSuggestionsHandler } from '../smart/SmartReconStep'
import { SuggestionList } from '../smart/SuggestionList'
import { approveSuggestion, rejectSuggestion } from '@engine/index'
import { AuditDrawer } from './AuditDrawer'
import { FinaliseDialog, ManualMatchDialog, NoteDialog } from './dialogs'
import { KpiCards } from './KpiCards'
import {
  applyMany,
  cellText,
  comparableTotal,
  configHasAmount,
  displayColumns,
  lineIndex,
  lineSearchText,
  matchesQuery,
  pairSearchText,
  pairsForTier,
  reviewKpis,
  rowLabel,
  unmatchedLines,
  type ReviewTab
} from './model'
import { PairTable, type PairActions } from './PairTable'
import { StatementCard } from './StatementCard'
import { Money } from './Money'

const TABLE_HEIGHT = 540

type PairTab = 'matched' | 'doubtful' | 'likely'

function SearchBox({ value, onChange, label }: { value: string; onChange: (v: string) => void; label: string }): React.JSX.Element {
  return (
    <div className="relative w-[280px] max-w-full">
      <Search size={15} className="pointer-events-none absolute top-1/2 left-2.5 -translate-y-1/2 text-muted" />
      <Input value={value} onChange={(e) => onChange(e.target.value)} placeholder="Search reference, name, amount…" aria-label={label} className="h-8 pr-8 pl-8 text-[12.5px]" />
      {value && (
        <button type="button" aria-label="Clear search" onClick={() => onChange('')} className="absolute top-1/2 right-2 -translate-y-1/2 rounded p-0.5 text-muted hover:text-ink">
          <X size={14} />
        </button>
      )}
    </div>
  )
}

function withPreparer(s: ReconSession, name: string): ReconSession {
  return s.meta.preparer || !name ? s : { ...s, meta: { ...s.meta, preparer: name } }
}

export function ReviewStep(): React.JSX.Element {
  const { state, module, settings, act, commit, latestSession, ensureUser } = useWizard()
  const toast = useToast()
  const session = state.session
  const [tab, setTab] = useState<ReviewTab>('doubtful')
  const [queries, setQueries] = useState<Record<ReviewTab, string>>({ matched: '', doubtful: '', likely: '', unmatchedA: '', unmatchedB: '', ai: '' })
  const [selPairs, setSelPairs] = useState<Set<string>>(new Set())
  const [selA, setSelA] = useState<Set<string>>(new Set())
  const [selB, setSelB] = useState<Set<string>>(new Set())
  const [noteFor, setNoteFor] = useState<MatchPair | null>(null)
  const [matchOpen, setMatchOpen] = useState(false)
  const [finaliseOpen, setFinaliseOpen] = useState(false)
  const [finaliseUser, setFinaliseUser] = useState('')
  const [auditOpen, setAuditOpen] = useState(false)
  // The side panel (Smart Recon + statement) starts open on wide screens; on narrower ones the table gets the room.
  const [panelOpen, setPanelOpen] = useState(() => window.innerWidth >= 1680)
  const [exporting, setExporting] = useState<'xlsx' | 'pdf' | null>(null)
  const onSuggestions = useSuggestionsHandler()

  const result = session?.result
  const idx = useMemo(() => (result ? lineIndex(result) : new Map<string, EngineLine>()), [result])
  const kpis = useMemo(() => (session ? reviewKpis(session, idx) : null), [session, idx])
  const statement = useMemo(() => {
    if (!session) return null
    try {
      return buildStatement(session.result, session.meta)
    } catch {
      return null
    }
  }, [session])
  const cfg = result?.config
  const colsA = useMemo(() => (cfg ? displayColumns(cfg, 'A', Object.keys(result?.linesA[0]?.values ?? {})) : []), [cfg, result])
  const colsB = useMemo(() => (cfg ? displayColumns(cfg, 'B', Object.keys(result?.linesB[0]?.values ?? {})) : []), [cfg, result])
  const pairLists = useMemo(
    () => (result ? { matched: pairsForTier(result, 'matched'), doubtful: pairsForTier(result, 'doubtful'), likely: pairsForTier(result, 'likely') } : { matched: [], doubtful: [], likely: [] }),
    [result]
  )
  const q = queries[tab]
  const shownPairs = useMemo(() => {
    if (tab !== 'matched' && tab !== 'doubtful' && tab !== 'likely') return []
    const list = pairLists[tab]
    if (!q.trim()) return list
    return list.filter((p) => matchesQuery(pairSearchText(p, idx), q))
  }, [tab, pairLists, q, idx])
  const shownLines = useMemo(() => {
    if (!result || (tab !== 'unmatchedA' && tab !== 'unmatchedB')) return []
    const lines = unmatchedLines(result, tab === 'unmatchedA' ? 'A' : 'B', idx)
    if (!q.trim()) return lines
    return lines.filter((l) => matchesQuery(lineSearchText([l]), q))
  }, [result, tab, q, idx])

  if (!session || !result || !cfg || !kpis) {
    return (
      <>
        <WizardHeader />
        <WizardStepper />
        <Card className="p-6 text-[14px] text-muted">Run the reconciliation first.</Card>
      </>
    )
  }

  const locked = !!session.finalised
  const hasAmount = configHasAmount(cfg)
  const nameA = cfg.sideAName
  const nameB = cfg.sideBName
  const [shortA, shortB] = shortSideNames(module.id, nameA, nameB)
  const currency = session.meta.currency || cfg.currency
  const pending = session.suggestions.filter((s) => s.status === 'open')
  const finaliseCheck = canFinalise(session)

  const changeTab = (t: string): void => {
    setTab(t as ReviewTab)
    setSelPairs(new Set())
  }

  const bulk = async (ids: string[], fn: (s: ReconSession, id: string, user: string) => ReconSession, verb: string): Promise<void> => {
    const user = await ensureUser()
    // Read the newest session after the await: a decision may have been made while the name dialog was open.
    const current = latestSession()
    if (!user || !current) return
    const r = applyMany(current, ids, (cur, id) => fn(cur, id, user))
    if (r.done > 0 && !(await commit(r.state, { revertOnFail: true }))) return
    if (r.done > 0) toast.success(`${r.done} pair${r.done === 1 ? '' : 's'} ${verb}`)
    if (r.errors.length > 0) toast.error(`${r.errors.length} pair${r.errors.length === 1 ? '' : 's'} could not be ${verb}`, r.errors[0])
    setSelPairs(new Set())
  }

  const actions: PairActions = {
    onAccept: (p) => void act((s, u) => acceptPair(s, p.id, u), 'Accepted and moved to Matched'),
    onReject: (p) => void act((s, u) => rejectPair(s, p.id, u), 'Rejected; both sides are back in Unmatched'),
    onUnmatch: (p) => void act((s, u) => unmatchPair(s, p.id, u), 'Unmatched; both sides are back in Unmatched'),
    onNote: (p) => setNoteFor(p)
  }

  const exportExcel = async (): Promise<void> => {
    if (!statement) return
    setExporting('xlsx')
    try {
      const s = withPreparer(session, settings.preparerName)
      const bytes = await buildReconWorkbook(s, statement)
      const r = await window.recoDo.files.save({ defaultName: exportFileName(s, 'xlsx'), filters: [{ name: 'Excel workbook', extensions: ['xlsx'] }], data: bytes })
      if (r.saved) toast.success('Excel workbook saved', r.path)
    } catch (err) {
      toast.error('The Excel export failed', errorMessage(err))
    } finally {
      setExporting(null)
    }
  }

  const exportPdf = async (): Promise<void> => {
    if (!statement) return
    setExporting('pdf')
    try {
      const s = withPreparer(session, settings.preparerName)
      const r = await window.recoDo.pdf.fromHtml({ html: buildSummaryHtml(s, statement), defaultName: exportFileName(s, 'pdf') })
      if (r.saved) toast.success('PDF summary saved', r.path)
    } catch (err) {
      toast.error('The PDF export failed', errorMessage(err))
    } finally {
      setExporting(null)
    }
  }

  const startFinalise = async (): Promise<void> => {
    const user = finaliseCheck.ok ? await ensureUser() : settings.preparerName
    if (finaliseCheck.ok && !user) return
    setFinaliseUser(user ?? '')
    setFinaliseOpen(true)
  }

  const lineColumns = (side: Side): DataColumn<EngineLine>[] => {
    const cols = side === 'A' ? colsA : colsB
    const out: DataColumn<EngineLine>[] = [
      { id: 'row', header: 'Row', width: 64, value: (l) => rowLabel(l.id).replace('row ', ''), className: 'text-muted' },
      ...cols.map<DataColumn<EngineLine>>((c) => ({
        id: c.column,
        header: c.label,
        minWidth: c.kind === 'date' ? 104 : 130,
        width: c.kind === 'date' ? 108 : undefined,
        value: (l) => (l.values[c.column] instanceof Date ? (l.values[c.column] as Date) : cellText(l.values[c.column]))
      }))
    ]
    if (hasAmount) out.push({ id: 'amount', header: `Amount (${currency})`, width: 140, numeric: true, cell: (l) => <Money n={l.amount} /> })
    out.push({ id: 'comment', header: 'Comment', minWidth: 150, cell: (l) => <span className="truncate text-[12px] text-likely">{autoComment(cfg.moduleId, side, l)}</span> })
    return out
  }

  // Only lines that are still unmatched count (Smart Recon approvals may have matched some meanwhile).
  const openA = new Set(result.unmatchedA)
  const openB = new Set(result.unmatchedB)
  const pickA = [...selA].filter((id) => openA.has(id))
  const pickB = [...selB].filter((id) => openB.has(id))
  const selLinesA = pickA.map((id) => idx.get(id)).filter((l): l is EngineLine => !!l)
  const selLinesB = pickB.map((id) => idx.get(id)).filter((l): l is EngineLine => !!l)
  const totalA = comparableTotal(pickA, idx)
  const totalB = comparableTotal(pickB, idx)

  const pairEmpty = (t: PairTab): string =>
    q ? 'No pairs match the search.' : t === 'doubtful' ? 'No Doubtful pairs. Nothing needs review here.' : t === 'likely' ? 'No Likely pairs.' : 'No matched pairs yet.'

  const pairTab = (t: PairTab): React.JSX.Element => {
    const selectedHere = [...selPairs].filter((id) => shownPairs.some((p) => p.id === id))
    return (
      <>
        <div className="mb-3 flex flex-wrap items-center gap-2.5">
          <SearchBox value={queries[t]} onChange={(v) => setQueries((x) => ({ ...x, [t]: v }))} label={`Search ${t} pairs`} />
          <span className="text-[12.5px] text-muted">
            {shownPairs.length.toLocaleString('en-US')} pair{shownPairs.length === 1 ? '' : 's'}
          </span>
          {!locked && selectedHere.length > 0 && (
            <div className="ml-auto flex items-center gap-2">
              <span className="text-[12.5px] font-semibold">{selectedHere.length} selected</span>
              {t !== 'matched' ? (
                <>
                  <Button size="sm" variant="secondary" className="text-matched" onClick={() => void bulk(selectedHere, (s, id, u) => acceptPair(s, id, u), 'accepted')}>
                    Accept selected
                  </Button>
                  <Button size="sm" variant="secondary" className="text-unmatched" onClick={() => void bulk(selectedHere, (s, id, u) => rejectPair(s, id, u), 'rejected')}>
                    Reject selected
                  </Button>
                </>
              ) : (
                <Button size="sm" variant="secondary" onClick={() => void bulk(selectedHere, (s, id, u) => unmatchPair(s, id, u), 'unmatched')}>
                  Unmatch selected
                </Button>
              )}
            </div>
          )}
        </div>
        <PairTable
          pairs={shownPairs}
          config={cfg}
          idx={idx}
          colsA={colsA}
          colsB={colsB}
          nameA={nameA}
          nameB={nameB}
          shortA={shortA}
          shortB={shortB}
          hasAmount={hasAmount}
          selected={selPairs}
          onSelectedChange={setSelPairs}
          actions={actions}
          locked={locked}
          height={shownPairs.length === 0 ? 200 : TABLE_HEIGHT}
          empty={pairEmpty(t)}
        />
        <p className="mt-2 text-[12px] text-muted">Reason shown on hover and in the expanded row · Bulk accept / reject with the checkboxes · Every decision is logged with user and time</p>
      </>
    )
  }

  const lineTab = (side: Side): React.JSX.Element => {
    const sel = side === 'A' ? selA : selB
    const setSel = side === 'A' ? setSelA : setSelB
    const t: ReviewTab = side === 'A' ? 'unmatchedA' : 'unmatchedB'
    return (
      <>
        <div className="mb-3 flex flex-wrap items-center gap-2.5">
          <SearchBox value={queries[t]} onChange={(v) => setQueries((x) => ({ ...x, [t]: v }))} label={`Search unmatched lines in ${side === 'A' ? nameA : nameB}`} />
          <span className="text-[12.5px] text-muted">
            {shownLines.length.toLocaleString('en-US')} line{shownLines.length === 1 ? '' : 's'}
          </span>
          {!locked && <span className="text-[12px] text-muted">Tick lines here and on the other Unmatched tab, then “Match selected”.</span>}
        </div>
        <DataTable
          aria-label={`Unmatched lines in ${side === 'A' ? nameA : nameB}`}
          rows={shownLines}
          columns={lineColumns(side)}
          rowKey={(l) => l.id}
          rowHeight={36}
          height={shownLines.length === 0 ? 200 : Math.min(TABLE_HEIGHT, 46 + shownLines.length * 36)}
          selectable={!locked}
          selected={sel}
          onSelectedChange={setSel}
          empty={q ? 'No lines match the search.' : `Every ${side === 'A' ? nameA : nameB} line is matched or in review.`}
        />
      </>
    )
  }

  const showMatchBar = !locked && (tab === 'unmatchedA' || tab === 'unmatchedB') && pickA.length + pickB.length > 0
  const first = pending[0]

  return (
    <>
      <WizardHeader
        right={
          <>
            <Tooltip content="Audit trail">
              <Button variant="secondary" size="icon" aria-label="Open audit trail" onClick={() => setAuditOpen(true)}>
                <ScrollText size={16} />
              </Button>
            </Tooltip>
            <Button variant="outline" loading={exporting === 'xlsx'} disabled={!statement || exporting !== null} onClick={() => void exportExcel()} data-testid="export-xlsx">
              {exporting !== 'xlsx' && <FileSpreadsheet size={15} />} Export Excel
            </Button>
            <Button variant="outline" loading={exporting === 'pdf'} disabled={!statement || exporting !== null} onClick={() => void exportPdf()} data-testid="export-pdf">
              {exporting !== 'pdf' && <FileDown size={15} />} Export PDF
            </Button>
            {!locked && (
              <Button variant="teal" onClick={() => void startFinalise()} data-testid="finalise">
                Finalise &amp; sign off
              </Button>
            )}
          </>
        }
      />
      <WizardStepper />
      {locked && session.finalised && (
        <div role="status" className="mb-4 flex items-center gap-2.5 rounded-xl border border-[#A9DCCB] bg-[#E9F7F1] px-4 py-3 text-[13.5px] text-ink">
          <Lock size={16} className="text-matched" />
          Finalised and signed off by <strong>{session.finalised.by}</strong> on {formatDate(new Date(session.finalised.at))}. This reconciliation is read-only; exports stay available.
        </div>
      )}
      <KpiCards session={session} kpis={kpis} shortA={shortA} shortB={shortB} active={tab} onPick={changeTab} />

      <div className={cn('grid items-start gap-5', panelOpen && 'xl:grid-cols-[minmax(0,1fr)_340px]')}>
        <Card className="@container/tabs min-w-0 p-5">
          <Tabs value={tab} onValueChange={changeTab}>
            <div className="mb-4 flex items-end gap-2">
              <TabsList className="min-w-0 flex-1 gap-0 [&>button]:px-1.5 [&>button]:text-[13px] @3xl/tabs:gap-1 @3xl/tabs:[&>button]:px-3 @3xl/tabs:[&>button]:text-[13.5px]">
                <TabsTrigger value="matched" tone="matched" count={result.stats.matched}>
                  Matched
                </TabsTrigger>
                <TabsTrigger value="doubtful" tone="doubtful" count={result.stats.doubtful}>
                  Doubtful
                </TabsTrigger>
                <TabsTrigger value="likely" tone="likely" count={result.stats.likely}>
                  Likely
                </TabsTrigger>
                <TabsTrigger value="unmatchedA" tone="unmatched" count={result.stats.unmatchedA} title={`Unmatched – ${nameA}`}>
                  Unmatched – {clip(shortA)}
                </TabsTrigger>
                <TabsTrigger value="unmatchedB" tone="unmatched" count={result.stats.unmatchedB} title={`Unmatched – ${nameB}`}>
                  Unmatched – {clip(shortB)}
                </TabsTrigger>
                <TabsTrigger value="ai" tone="ai" count={pending.length}>
                  AI Suggested
                </TabsTrigger>
              </TabsList>
              <Button
                variant={panelOpen ? 'ghost' : 'secondary'}
                size="sm"
                aria-expanded={panelOpen}
                onClick={() => setPanelOpen((o) => !o)}
                className="mb-1.5 shrink-0"
                data-testid="toggle-panel"
                aria-label={panelOpen ? 'Hide panel' : 'Smart Recon & statement'}
                title={panelOpen ? 'Hide panel' : 'Smart Recon & statement'}
              >
                {panelOpen ? <PanelRightClose size={15} /> : <PanelRightOpen size={15} />}
                {/* Icon only when the card is narrow, so the six tabs keep their room. */}
                <span className="hidden @4xl/tabs:inline">{panelOpen ? 'Hide panel' : 'Smart Recon & statement'}</span>
              </Button>
            </div>
            <TabsContent value="matched">{pairTab('matched')}</TabsContent>
            <TabsContent value="doubtful">{pairTab('doubtful')}</TabsContent>
            <TabsContent value="likely">{pairTab('likely')}</TabsContent>
            <TabsContent value="unmatchedA">{lineTab('A')}</TabsContent>
            <TabsContent value="unmatchedB">{lineTab('B')}</TabsContent>
            <TabsContent value="ai">
              <div className="mb-3">
                <SearchBox value={queries.ai} onChange={(v) => setQueries((x) => ({ ...x, ai: v }))} label="Search suggestions" />
              </div>
              <SuggestionList query={queries.ai} />
            </TabsContent>
          </Tabs>

          {showMatchBar && (
            <div className="sticky bottom-0 mt-3 flex flex-wrap items-center gap-3 rounded-xl border border-primary/40 bg-[#EEF4FD] px-4 py-2.5 text-[13px]" role="region" aria-label="Manual match">
              <span>
                <strong>{pickA.length}</strong> {shortA} line{pickA.length === 1 ? '' : 's'}
                {hasAmount && <span className="num text-muted"> ({formatAmount(totalA)})</span>}
              </span>
              <span className="text-muted">↔</span>
              <span>
                <strong>{pickB.length}</strong> {shortB} line{pickB.length === 1 ? '' : 's'}
                {hasAmount && <span className="num text-muted"> ({formatAmount(totalB)})</span>}
              </span>
              {hasAmount && (
                <span className={cn('num font-semibold', Math.abs(totalA - totalB) < 0.005 ? 'text-matched' : 'text-unmatched')}>Difference {formatAmount(Math.round((totalA - totalB) * 100) / 100)}</span>
              )}
              <div className="ml-auto flex gap-2">
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => {
                    setSelA(new Set())
                    setSelB(new Set())
                  }}
                >
                  Clear
                </Button>
                <Tooltip content="Tick at least one line on each Unmatched tab." disabled={pickA.length > 0 && pickB.length > 0}>
                  <span>
                    <Button size="sm" disabled={pickA.length === 0 || pickB.length === 0} onClick={() => setMatchOpen(true)}>
                      <Link2 size={14} /> Match selected
                    </Button>
                  </span>
                </Tooltip>
              </div>
            </div>
          )}
        </Card>

        {panelOpen && (
          <div className="flex min-w-0 flex-col gap-4">
            {!locked && <SmartReconPanel session={session} onSuggestions={(list) => void onSuggestions(list)} disabled={locked} />}
            {first && (
              <SuggestionCard
                suggestion={first}
                result={result}
                disabled={locked}
                onApprove={(x) => void act((s, u) => approveSuggestion(s, x.id, u), 'Suggestion approved and moved to Matched')}
                onReject={(x) => void act((s, u) => rejectSuggestion(s, x.id, u), 'Suggestion rejected')}
              />
            )}
            {statement && <StatementCard statement={statement} currency={currency} />}
          </div>
        )}
      </div>

      <NoteDialog
        open={!!noteFor}
        initial={noteFor?.note ?? ''}
        onOpenChange={(o) => !o && setNoteFor(null)}
        onSave={async (note) => {
          if (!noteFor) return
          const ok = await act((s, u) => addNote(s, noteFor.id, u, note), 'Note saved')
          if (ok) setNoteFor(null)
        }}
      />
      <ManualMatchDialog
        open={matchOpen}
        onOpenChange={setMatchOpen}
        linesA={selLinesA}
        linesB={selLinesB}
        nameA={nameA}
        nameB={nameB}
        hasAmount={hasAmount}
        totalA={totalA}
        totalB={totalB}
        currency={currency}
        onConfirm={async (reason) => {
          const ok = await act((s, u) => manualMatch(s, pickA, pickB, u, reason || undefined), 'Lines matched manually')
          if (ok) {
            setMatchOpen(false)
            setSelA(new Set())
            setSelB(new Set())
          }
        }}
      />
      <FinaliseDialog
        open={finaliseOpen}
        onOpenChange={setFinaliseOpen}
        reasons={finaliseCheck.reasons}
        preparer={finaliseUser}
        onConfirm={async () => {
          const ok = await act((s, u) => finalise(s, u), 'Reconciliation finalised and signed off')
          if (ok) setFinaliseOpen(false)
        }}
      />
      <AuditDrawer open={auditOpen} onOpenChange={setAuditOpen} entries={session.audit} />
    </>
  )
}
