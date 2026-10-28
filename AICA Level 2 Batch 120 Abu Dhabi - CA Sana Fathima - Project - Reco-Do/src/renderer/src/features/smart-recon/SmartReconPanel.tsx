import { useCallback, useEffect, useId, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { AlertTriangle, Eye, KeyRound, Sparkles, X } from 'lucide-react'
import type { AiErrorCode, AiKeyStatus, ReconSession, Suggestion } from '@shared/contracts'
import { AI_PROVIDER_INFO } from '@shared/aiProviders'
import { formatAmount } from '@shared/format'
import { findGroupMatches, findPartialReferenceMatches } from '@engine/index'
import { eligiblePools } from '@engine/smart/common'
import { buildAiPayload, canMaskParties, describePricing, mergeSuggestions, suggestionKey, type AiPayload } from '@engine/smart/ai'
import {
  Button,
  Checkbox,
  DataTable,
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Input,
  KeyValue,
  Progress,
  type DataColumn
} from '@/components/ui'
import { getSettings } from '@/lib/db'
import { cn } from '@/lib/cn'
import { activeAi, type ActiveAi } from './aiSettings'
import { describeDiscarded, runSmartReconBatches, type RunStopCode } from './runSmartRecon'
import { shortSide } from './sides'

export interface SmartReconPanelProps {
  session: ReconSession
  /** Receives new suggestions (code and/or AI) to add to the session's AI Suggested tab. */
  onSuggestions: (s: Suggestion[]) => void
  disabled?: boolean
}

interface Options {
  includeDoubtful: boolean
  partialRef: boolean
  oneToMany: boolean
  manyToOne: boolean
  maskParties: boolean
  useAi: boolean
}

interface Notice {
  tone: 'info' | 'warning' | 'error'
  title?: string
  text: string
  /** Show a link to Settings & API Key. */
  settingsLink?: boolean
}

interface Prepared {
  signature: string
  code: Suggestion[]
  capped: boolean
  payload: AiPayload
}

type KeyStatus = AiKeyStatus

function errorTitle(code: RunStopCode, name: string): string {
  const titles: Record<RunStopCode, string> = {
    'no-key': 'No API key saved',
    'bad-key': 'API key not accepted',
    'rate-limit': 'Rate limit reached',
    overloaded: `${name} is busy`,
    network: `Could not reach ${name}`,
    api: `${name} error`,
    cancelled: 'Smart Recon cancelled'
  }
  return titles[code]
}

/** A local server or another service that needs no key counts as ready. */
function keyReady(ai: ActiveAi, status: KeyStatus | null): boolean {
  return !!status?.hasKey || !AI_PROVIDER_INFO[ai.provider].keyRequired
}

const SETTINGS_CODES: ReadonlySet<AiErrorCode | 'cancelled'> = new Set(['no-key', 'bad-key'])

function plural(n: number, one: string, many = `${one}s`): string {
  return `${n.toLocaleString('en-US')} ${n === 1 ? one : many}`
}

function errorText(e: unknown, fallback: string): string {
  if (e instanceof Error && e.message) return e.message.replace(/^Error invoking remote method '[^']+': (Error: )?/, '')
  return fallback
}

function formatUsd(usd: number): string {
  if (usd > 0 && usd < 0.01) return 'less than US$0.01'
  return `about US$${formatAmount(usd)}`
}

/** Purple Smart Reconciliation panel (master prompt §4 Step 4). Code matching runs locally; the AI step is optional. */
export function SmartReconPanel({ session, onSuggestions, disabled }: SmartReconPanelProps): React.JSX.Element {
  const result = session.result
  const cfg = result.config
  const hasAmount = cfg.keys.some((k) => k.use && k.type === 'amount')
  const maskable = useMemo(() => canMaskParties(cfg), [cfg])
  const locked = !!disabled || session.finalised !== null
  const sideA = shortSide(cfg, 'A')
  const sideB = shortSide(cfg, 'B')

  const [opts, setOpts] = useState<Options>({ includeDoubtful: false, partialRef: true, oneToMany: hasAmount, manyToOne: hasAmount, maskParties: false, useAi: true })
  const [ai, setAi] = useState<ActiveAi>(() => activeAi({}))
  const [keyStatus, setKeyStatus] = useState<KeyStatus | null>(null)
  const [keyDraft, setKeyDraft] = useState('')
  const [keySaving, setKeySaving] = useState(false)
  const [keyError, setKeyError] = useState<string | null>(null)
  const [notices, setNotices] = useState<Notice[]>([])
  const [prepared, setPrepared] = useState<Prepared | null>(null)
  const [previewOpen, setPreviewOpen] = useState(false)
  const [seenSignature, setSeenSignature] = useState<string | null>(null)
  const [progress, setProgress] = useState<{ done: number; total: number } | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const mounted = useRef(true)

  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
      abortRef.current?.abort()
    }
  }, [])

  const refreshKey = useCallback(async (): Promise<void> => {
    try {
      const s = await window.recoDo.secrets.status()
      if (mounted.current) setKeyStatus(s.providers?.[ai.provider] ?? (ai.provider === 'anthropic' ? s : { hasKey: false, masked: null }))
    } catch {
      if (mounted.current) setKeyStatus({ hasKey: false, masked: null })
    }
  }, [ai.provider])

  useEffect(() => {
    void refreshKey()
    getSettings()
      .then((s) => {
        if (!mounted.current) return
        setAi(activeAi(s))
        setOpts((o) => ({ ...o, maskParties: s.maskPartiesDefault }))
      })
      .catch(() => undefined) // Defaults stay in place when settings cannot be read.
  }, [refreshKey])

  const unresolved = useMemo(() => {
    const p = eligiblePools(result, opts.includeDoubtful)
    return p.a.length + p.b.length
  }, [result, opts.includeDoubtful])

  const signature = useMemo(
    () => JSON.stringify([session.id, session.updatedAt, session.suggestions.length, opts, ai.provider, ai.model, ai.baseUrl]),
    [session.id, session.updatedAt, session.suggestions.length, opts, ai.provider, ai.model, ai.baseUrl]
  )
  const running = progress !== null
  const set = (patch: Partial<Options>): void => setOpts((o) => ({ ...o, ...patch }))

  /** Code-side matches for the ticked options (no network). */
  const codeMatches = useCallback((): { code: Suggestion[]; capped: boolean } => {
    const code: Suggestion[] = []
    let capped = false
    if (hasAmount && (opts.oneToMany || opts.manyToOne)) {
      const g = findGroupMatches(result, { includeDoubtful: opts.includeDoubtful })
      capped = g.capped
      for (const s of g.suggestions) {
        const oneA = s.aIds.length === 1 && s.bIds.length > 1
        if (oneA ? opts.oneToMany : opts.manyToOne) code.push(s)
      }
    }
    if (opts.partialRef) code.push(...findPartialReferenceMatches(result, { includeDoubtful: opts.includeDoubtful }))
    return { code, capped }
  }, [result, hasAmount, opts])

  const prepare = useCallback((): Prepared => {
    if (prepared && prepared.signature === signature) return prepared
    const { code, capped } = codeMatches()
    const fresh = mergeSuggestions(session.suggestions, code, [])
    const openCode = session.suggestions.filter((s) => s.status === 'open' && s.source !== 'ai')
    const payload = buildAiPayload(result, {
      includeDoubtful: opts.includeDoubtful,
      maskParties: opts.maskParties && maskable,
      codeCandidates: [...openCode, ...fresh],
      model: ai.model,
      provider: ai.provider,
      baseUrl: ai.baseUrl || undefined
    })
    const next = { signature, code: fresh, capped, payload }
    setPrepared(next)
    return next
  }, [prepared, signature, codeMatches, session.suggestions, result, opts.includeDoubtful, opts.maskParties, maskable, ai])

  const cappedNotice: Notice = {
    tone: 'warning',
    text: 'The sum-match search was capped to keep it fast, so some combinations were not checked. Results shown are still exact.'
  }

  const runCode = (): void => {
    if (locked) return
    const { code, capped } = codeMatches()
    const fresh = mergeSuggestions(session.suggestions, code, [])
    const next: Notice[] = []
    const groups = fresh.filter((s) => s.source === 'code-group').length
    const refs = fresh.filter((s) => s.source === 'code-partial-ref').length
    next.push(
      fresh.length > 0
        ? { tone: 'info', title: 'Code matching finished', text: `Found ${plural(groups, 'sum match', 'sum matches')} and ${plural(refs, 'partial-reference match', 'partial-reference matches')}. They are in the AI Suggested tab for your approval.` }
        : { tone: 'info', title: 'Code matching finished', text: 'No new matches were found by code.' }
    )
    if (capped) next.push(cappedNotice)
    setNotices(next)
    if (fresh.length > 0) onSuggestions(fresh)
  }

  const saveKey = async (): Promise<void> => {
    const key = keyDraft.trim()
    if (!key) {
      setKeyError(`Paste your ${ai.provider === 'custom' ? '' : `${ai.shortName} `}API key first.`)
      return
    }
    setKeySaving(true)
    setKeyError(null)
    try {
      const { warning } = await window.recoDo.secrets.setApiKey(ai.provider, key)
      setKeyDraft('')
      await refreshKey()
      if (warning && mounted.current) setNotices([{ tone: 'warning', title: 'Key saved', text: warning }])
    } catch (e) {
      setKeyError(errorText(e, 'The key could not be saved. Please try again.'))
    } finally {
      if (mounted.current) setKeySaving(false)
    }
  }

  const openPreview = (): void => {
    prepare()
    setSeenSignature(signature)
    setPreviewOpen(true)
  }

  const sendToAi = async (): Promise<void> => {
    if (locked || running) return
    const p = prepare()
    if (seenSignature !== p.signature) {
      setSeenSignature(p.signature)
      setPreviewOpen(true)
      return
    }
    setPreviewOpen(false)
    if (ai.provider === 'custom' && (!ai.baseUrl || !ai.model)) {
      setNotices([{ tone: 'error', title: 'AI service not set up', text: 'Enter and save the base URL and model of your AI service in Settings & API Key, then run Smart Recon again.', settingsLink: true }])
      return
    }
    if (!keyReady(ai, keyStatus)) {
      setNotices([{ tone: 'error', title: errorTitle('no-key', ai.shortName), text: `Save your ${ai.shortName} API key below or in Settings & API Key, then run Smart Recon again.`, settingsLink: true }])
      return
    }
    if (p.payload.batches.length === 0) {
      const next: Notice[] = [{ tone: 'info', text: 'There is nothing to send: Smart Recon needs unresolved lines on both sides.' }]
      if (p.code.length > 0) {
        next.unshift({ tone: 'info', title: 'Code matching finished', text: `${plural(p.code.length, 'match', 'matches')} found by code were added for your approval.` })
        onSuggestions(p.code)
      }
      setNotices(next)
      return
    }
    const controller = new AbortController()
    abortRef.current = controller
    setNotices([])
    setProgress({ done: 0, total: p.payload.batches.length })
    const outcome = await runSmartReconBatches({
      batches: p.payload.batches,
      model: ai.model,
      provider: ai.provider,
      baseUrl: ai.baseUrl || undefined,
      result,
      maskMap: p.payload.maskMap,
      includeDoubtful: opts.includeDoubtful,
      complete: (req) => window.recoDo.ai.complete(req),
      cancel: (requestId) => window.recoDo.ai.cancel(requestId),
      onProgress: (x) => {
        if (mounted.current) setProgress(x)
      },
      signal: controller.signal
    })
    abortRef.current = null
    if (!mounted.current) return
    setProgress(null)
    const merged = mergeSuggestions(session.suggestions, p.code, outcome.suggestions)
    const listed = new Set(session.suggestions.filter((s) => s.status === 'open').map(suggestionKey))
    const confirmed = outcome.suggestions.filter((s) => listed.has(suggestionKey(s))).length
    if (merged.length > 0) onSuggestions(merged)
    const aiCount = merged.filter((s) => s.source === 'ai').length
    const codeCount = merged.length - aiCount
    const next: Notice[] = []
    if (outcome.completed > 0) {
      next.push({
        tone: 'info',
        title: 'Smart Recon finished',
        text: `${ai.shortName} suggested ${plural(aiCount, 'new match', 'new matches')}${codeCount > 0 ? ` and code found ${plural(codeCount, 'match', 'matches')}` : ''}.${confirmed > 0 ? ` ${ai.shortName} also agreed with ${plural(confirmed, 'match', 'matches')} already in your list.` : ''} Nothing is matched until you approve it in the AI Suggested tab.`
      })
    } else if (codeCount > 0) {
      next.push({ tone: 'info', title: 'Code matching finished', text: `Code found ${plural(codeCount, 'match', 'matches')}. They are in the AI Suggested tab for your approval.` })
    }
    const discarded = describeDiscarded(outcome.discarded)
    if (discarded) next.push({ tone: 'info', text: discarded })
    if (outcome.unreadable > 0) {
      next.push({ tone: 'warning', text: `${plural(outcome.unreadable, 'batch', 'batches')} came back in a format the app could not read and ${outcome.unreadable === 1 ? 'was' : 'were'} skipped. You can run Smart Recon again.` })
    }
    if (outcome.stop) {
      const left = outcome.total - outcome.completed
      const kept = outcome.completed > 0 ? ` ${plural(outcome.completed, 'batch', 'batches')} finished and ${outcome.completed === 1 ? 'its' : 'their'} suggestions were kept; ${plural(left, 'batch', 'batches')} ${left === 1 ? 'was' : 'were'} not sent.` : ''
      next.push({ tone: outcome.stop.code === 'cancelled' ? 'warning' : 'error', title: errorTitle(outcome.stop.code, ai.shortName), text: `${outcome.stop.message}${kept}`, settingsLink: SETTINGS_CODES.has(outcome.stop.code) })
      if (outcome.stop.code === 'bad-key' || outcome.stop.code === 'no-key') void refreshKey()
    }
    if (p.capped) next.push(cappedNotice)
    setNotices(next)
  }

  const runSmart = (): void => {
    if (!opts.useAi) runCode()
    else void sendToAi()
  }

  const cancel = (): void => abortRef.current?.abort()

  const checkboxes: Array<{ key: keyof Options; label: string; hint?: string; disabled?: boolean }> = [
    { key: 'includeDoubtful', label: 'Include Doubtful lines' },
    { key: 'partialRef', label: 'Reference found inside remarks' },
    { key: 'oneToMany', label: `1 ${sideA} : many ${sideB} (sum match)`, disabled: !hasAmount, hint: hasAmount ? undefined : 'Needs an Amount key' },
    { key: 'manyToOne', label: `Many ${sideA} : 1 ${sideB} (sum match)`, disabled: !hasAmount, hint: hasAmount ? undefined : 'Needs an Amount key' },
    {
      key: 'maskParties',
      label: 'Mask party names before sending',
      disabled: !opts.useAi || !maskable,
      hint: maskable ? undefined : 'No party or name column is mapped, so there is nothing to mask'
    },
    { key: 'useAi', label: `Use AI (${ai.shortName}) for fuzzy text` }
  ]

  return (
    <section aria-label="Smart Reconciliation" className="rounded-2xl bg-gradient-to-br from-[#2A2160] via-[#33287A] to-[#45369C] p-5 text-white shadow-lg">
      <h2 className="flex items-center gap-2 text-[17px] font-bold">
        <Sparkles size={17} aria-hidden />
        Smart Reconciliation
      </h2>
      <p className="mt-1 text-[13px] leading-snug text-white/75">
        Runs only on the {plural(unresolved, 'unresolved line')}. Exact matches are never sent.
      </p>

      <p className="mt-2 flex flex-wrap items-center gap-x-1.5 text-[12.5px] text-white/80" aria-label="AI destination">
        <span>Sends to:</span>
        <span className="font-semibold text-white">{ai.provider === 'custom' ? (ai.host ?? 'not set up yet') : ai.shortName}</span>
        {ai.model && (
          <>
            <span aria-hidden>·</span>
            <span className="font-mono text-[12px] text-white/90">{ai.model}</span>
          </>
        )}
        <Link to="/workspace/settings" className="ml-1 text-[12px] font-semibold text-white/80 underline-offset-2 hover:text-white hover:underline">
          Change
        </Link>
      </p>

      <KeyBox
        ai={ai}
        status={keyStatus}
        draft={keyDraft}
        onDraft={setKeyDraft}
        onSave={() => void saveKey()}
        saving={keySaving}
        error={keyError}
        disabled={locked}
        needed={opts.useAi}
      />

      <div className="mt-4 space-y-2">
        {checkboxes.map((c) => (
          <PanelCheckbox
            key={c.key}
            label={c.label}
            hint={c.hint}
            checked={c.key === 'maskParties' ? opts.maskParties && maskable : opts[c.key]}
            disabled={locked || running || c.disabled}
            onChange={(v) => set({ [c.key]: v } as Partial<Options>)}
          />
        ))}
      </div>

      {running && progress && (
        <div className="mt-4 rounded-lg bg-white/10 p-3">
          <Progress
            tone="teal"
            value={progress.total > 0 ? (progress.done / progress.total) * 100 : null}
            label={<span className="text-white">{`Sending to ${ai.shortName}…`}</span>}
            detail={<span className="text-white/75">{`Batch ${Math.min(progress.done + 1, progress.total)} of ${progress.total}`}</span>}
          />
          <Button size="sm" variant="secondary" className="mt-3" onClick={cancel}>
            <X size={14} />
            Cancel
          </Button>
        </div>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-2.5">
        <Button variant="teal" size="lg" onClick={runSmart} disabled={locked || running || unresolved === 0}>
          Run Smart Recon
        </Button>
        <Button variant="secondary" onClick={runCode} disabled={locked || running || unresolved === 0} title="Sum and partial-reference matching on this computer. Nothing is sent.">
          Run code matching
        </Button>
      </div>
      {opts.useAi && (
        <button
          type="button"
          onClick={openPreview}
          disabled={locked || running || unresolved === 0}
          className="mt-3 inline-flex items-center gap-1.5 text-[13px] font-semibold text-white/90 underline-offset-2 outline-none hover:underline focus-visible:ring-2 focus-visible:ring-white/50 disabled:opacity-50"
        >
          <Eye size={14} aria-hidden />
          Preview data to be sent
        </button>
      )}

      {notices.length > 0 && (
        <div className="mt-4 space-y-2" aria-live="polite">
          {notices.map((n, i) => (
            <NoticeBox key={i} notice={n} />
          ))}
        </div>
      )}

      <PreviewDialog
        open={previewOpen}
        onOpenChange={setPreviewOpen}
        prepared={prepared}
        ai={ai}
        masked={opts.maskParties && maskable}
        hasKey={keyReady(ai, keyStatus)}
        sideA={sideA}
        sideB={sideB}
        onSend={() => void sendToAi()}
        canSend={!locked && !running}
      />
    </section>
  )
}

// ───────────────────────── Pieces ─────────────────────────

function PanelCheckbox({ label, hint, checked, disabled, onChange }: { label: string; hint?: string; checked: boolean; disabled?: boolean; onChange: (v: boolean) => void }): React.JSX.Element {
  const id = useId()
  return (
    <div className={cn('flex items-start gap-2.5', disabled && 'opacity-60')}>
      <Checkbox
        id={id}
        checked={checked}
        disabled={disabled}
        onCheckedChange={(v) => onChange(v === true)}
        className="mt-[1px] border-white/60 bg-transparent data-[state=checked]:border-teal data-[state=checked]:bg-teal"
      />
      <label htmlFor={id} className={cn('text-[13.5px] leading-snug text-white select-none', disabled ? 'cursor-not-allowed' : 'cursor-pointer')}>
        {label}
        {hint && <span className="ml-1.5 text-[12px] text-white/60">({hint})</span>}
      </label>
    </div>
  )
}

function KeyBox(props: {
  ai: ActiveAi
  status: KeyStatus | null
  draft: string
  onDraft: (v: string) => void
  onSave: () => void
  saving: boolean
  error: string | null
  disabled: boolean
  needed: boolean
}): React.JSX.Element {
  const { status, ai } = props
  const info = AI_PROVIDER_INFO[ai.provider]
  const inputId = useId()
  if (status === null) {
    return <div className="mt-4 h-10 animate-pulse rounded-lg bg-white/10" aria-label="Checking API key" />
  }
  if (status.hasKey) {
    return (
      <div className="mt-4 flex items-center justify-between gap-3 rounded-lg bg-white/12 px-3.5 py-2.5">
        <span className="flex min-w-0 items-center gap-2 font-mono text-[13px] text-white/90">
          <KeyRound size={14} className="shrink-0 text-white/70" aria-hidden />
          <span className="truncate">{status.masked ?? 'API key saved'}</span>
        </span>
        <Link to="/workspace/settings" className="shrink-0 text-[12px] font-semibold text-white/80 hover:text-white hover:underline">
          Change
        </Link>
      </div>
    )
  }
  return (
    <div className="mt-4 rounded-lg bg-white/10 p-3">
      <label htmlFor={inputId} className="text-[12.5px] font-semibold text-white">
        {ai.provider === 'custom' ? 'API key for this service (optional for local servers)' : `${info.name} API key ${props.needed ? '(needed for the AI step)' : '(optional)'}`}
      </label>
      <div className="mt-1.5 flex gap-2">
        <Input
          id={inputId}
          type="password"
          autoComplete="off"
          spellCheck={false}
          placeholder={info.keyPlaceholder}
          value={props.draft}
          disabled={props.disabled || props.saving}
          aria-invalid={props.error ? true : undefined}
          onChange={(e) => props.onDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') props.onSave()
          }}
          className="font-mono"
        />
        <Button variant="teal" onClick={props.onSave} loading={props.saving} disabled={props.disabled}>
          Save
        </Button>
      </div>
      {props.error && (
        <p role="alert" className="mt-1.5 text-[12px] text-[#FFC9C9]">
          {props.error}
        </p>
      )}
      <p className="mt-1.5 text-[12px] leading-snug text-white/65">
        Stored encrypted on this computer only. You can also manage it in{' '}
        <Link to="/workspace/settings" className="font-semibold text-white underline-offset-2 hover:underline">
          Settings &amp; API Key
        </Link>
        .
      </p>
    </div>
  )
}

function NoticeBox({ notice }: { notice: Notice }): React.JSX.Element {
  return (
    <div
      role={notice.tone === 'error' ? 'alert' : undefined}
      className={cn(
        'rounded-lg px-3 py-2.5 text-[12.5px] leading-relaxed',
        notice.tone === 'error' ? 'bg-[#C0292B]/25 text-white ring-1 ring-[#FF9C9C]/40' : notice.tone === 'warning' ? 'bg-[#A86B00]/25 text-white ring-1 ring-[#FFD27A]/30' : 'bg-white/10 text-white/90'
      )}
    >
      {notice.title && (
        <div className="mb-0.5 flex items-center gap-1.5 font-semibold text-white">
          {notice.tone !== 'info' && <AlertTriangle size={13} aria-hidden />}
          {notice.title}
        </div>
      )}
      {notice.text}
      {notice.settingsLink && (
        <>
          {' '}
          <Link to="/workspace/settings" className="font-semibold text-white underline underline-offset-2">
            Open Settings &amp; API Key
          </Link>
        </>
      )}
    </div>
  )
}

type PreviewRow = Record<string, string | number>

function PreviewDialog(props: {
  open: boolean
  onOpenChange: (open: boolean) => void
  prepared: Prepared | null
  ai: ActiveAi
  masked: boolean
  hasKey: boolean
  sideA: string
  sideB: string
  onSend: () => void
  canSend: boolean
}): React.JSX.Element {
  const p = props.prepared?.payload
  const rows = p?.previewRows ?? []
  const columns = useMemo<DataColumn<PreviewRow>[]>(() => {
    const keys = rows.length > 0 ? Object.keys(rows[0]) : []
    const label: Record<string, string> = { batch: 'Batch', side: 'Side', id: 'Row id', date: 'Date (ISO)', amount: 'Amount', text: 'Reference / remarks', party: props.masked ? 'Party (masked)' : 'Party' }
    const width: Record<string, number> = { batch: 64, side: 90, id: 88, date: 104, amount: 120, party: 170 }
    return keys.map((k) => ({
      id: k,
      header: label[k] ?? k,
      width: width[k],
      minWidth: k === 'text' ? 220 : undefined,
      numeric: k === 'amount',
      value: (r: PreviewRow) => r[k],
      className: k === 'id' || k === 'date' ? 'font-mono text-[12px]' : undefined
    }))
  }, [rows, props.masked])
  const pricing = describePricing(props.ai.provider, props.ai.model, props.ai.baseUrl)
  const destination = props.ai.host ?? 'the AI service (not set up yet)'
  const costText =
    pricing.kind === 'local'
      ? 'Runs on your own server, no API cost'
      : pricing.kind === 'unknown' || p?.estimate.usd === null || p?.estimate.usd === undefined
        ? 'Cost estimate not available for this model'
        : `${formatUsd(p.estimate.usd)} (${pricing.family} at US$${pricing.input} / US$${pricing.output} per million tokens; an approximation)`
  const system = p?.batches[0]?.system ?? ''

  return (
    <Dialog open={props.open} onOpenChange={props.onOpenChange}>
      <DialogContent width={1040}>
        <DialogHeader>
          <DialogTitle>{`Data to be sent to ${props.ai.shortName}`}</DialogTitle>
          <DialogDescription>
            These are exactly the values that leave this computer if you continue, and they go only to <span className="font-mono font-semibold text-ink">{destination}</span>. Nothing else is sent: no file names, no other columns, no matched lines and no balances.
          </DialogDescription>
        </DialogHeader>
        <DialogBody className="space-y-4">
          {p && p.batches.length > 0 ? (
            <>
              <KeyValue
                dense
                items={[
                  { label: 'Lines', value: `${props.sideA} ${p.rowCount.a.toLocaleString('en-US')} · ${props.sideB} ${p.rowCount.b.toLocaleString('en-US')}`, numeric: true },
                  { label: 'Batches (at most 200 lines each)', value: p.batches.length.toLocaleString('en-US'), numeric: true },
                  { label: 'Code candidates sent for ranking', value: p.candidateCount.toLocaleString('en-US'), numeric: true },
                  { label: 'Sent to', value: `${props.ai.label} (${destination})` },
                  { label: 'Model (from Settings)', value: <span className="font-mono text-[12.5px]">{props.ai.model || 'not set'}</span> },
                  { label: 'Estimated tokens (input / output)', value: `${p.estimate.inputTokens.toLocaleString('en-US')} / ${p.estimate.outputTokens.toLocaleString('en-US')}`, numeric: true },
                  { label: 'Estimated cost', value: costText },
                  { label: 'Party names', value: props.masked ? 'Masked as PARTY_01, PARTY_02 … (the party column and name columns such as Name or Employee are masked, and those names are also masked wherever they appear in other text)' : 'Sent as they appear in the files' }
                ]}
              />
              <DataTable<PreviewRow> rows={rows} columns={columns} rowKey={(r) => String(r.id)} height={360} aria-label="Rows to be sent" />
              <details className="rounded-lg border border-line bg-[#F7F9FB] px-3 py-2 text-[12.5px]">
                <summary className="cursor-pointer font-semibold text-ink">Instructions sent with every batch</summary>
                <pre className="mt-2 max-h-56 overflow-auto font-mono text-[11.5px] leading-relaxed whitespace-pre-wrap text-muted">{system}</pre>
              </details>
            </>
          ) : (
            <p className="py-6 text-center text-[13.5px] text-muted">There is nothing to send: Smart Recon needs unresolved lines on both sides.</p>
          )}
        </DialogBody>
        <DialogFooter>
          <Button variant="secondary" onClick={() => props.onOpenChange(false)}>
            Close
          </Button>
          {p && p.batches.length > 0 && (
            <Button
              variant="primary"
              className="bg-ai hover:bg-[#4b36bd]"
              onClick={props.onSend}
              disabled={!props.canSend || !props.hasKey}
              title={props.hasKey ? undefined : `Save your ${props.ai.shortName} API key first`}
            >
              <Sparkles size={15} />
              Send {plural(p.batches.length, 'batch', 'batches')} to {props.ai.shortName}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
