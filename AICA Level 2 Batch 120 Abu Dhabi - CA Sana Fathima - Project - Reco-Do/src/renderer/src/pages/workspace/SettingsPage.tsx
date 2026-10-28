import { useCallback, useEffect, useState } from 'react'
import { CheckCircle2, FolderOpen, Globe, KeyRound, Lock, PlugZap, ShieldCheck, Sparkles, XCircle } from 'lucide-react'
import type { AiProvider, AiSecretsStatus } from '@shared/contracts'
import { AI_PROVIDER_INFO, AI_PROVIDERS, checkBaseUrl, isValidModelName, keyProblem, providerHost } from '@shared/aiProviders'
import { Badge, Button, Card, Field, Input, SectionTitle, Select, Spinner, Switch, useConfirm, useToast } from '@/components/ui'
import { getSettings, saveSettings, type Settings } from '@/lib/db'
import { describePricing, modelFor } from '@engine/smart/ai'
import { activeAi, storedModel } from '@/features/smart-recon/aiSettings'
import { errorMessage } from '@/lib/useAsync'
import { buildDate, useAppInfo } from '@/lib/appInfo'

const CURRENCIES = ['AED', 'SAR', 'QAR', 'OMR', 'KWD', 'BHD', 'USD', 'EUR', 'GBP', 'INR', 'PKR', 'EGP'].map((c) => ({ value: c, label: c }))
const PROVIDER_OPTIONS = AI_PROVIDERS.map((p) => ({ value: p, label: AI_PROVIDER_INFO[p].label }))

type KeyState = { state: 'loading' } | { state: 'ready'; status: AiSecretsStatus } | { state: 'unavailable'; message: string }

function DetailsCard({ settings, onSaved }: { settings: Settings; onSaved: (s: Settings) => void }): React.JSX.Element {
  const toast = useToast()
  const [form, setForm] = useState(settings)
  const [saving, setSaving] = useState(false)
  useEffect(() => setForm(settings), [settings])

  const dirty =
    form.preparerName !== settings.preparerName ||
    form.department !== settings.department ||
    form.currency !== settings.currency ||
    form.maskPartiesDefault !== settings.maskPartiesDefault

  const save = async (): Promise<void> => {
    setSaving(true)
    try {
      const next = await saveSettings({
        preparerName: form.preparerName.trim(),
        department: form.department.trim(),
        currency: form.currency,
        maskPartiesDefault: form.maskPartiesDefault
      })
      onSaved(next)
      toast.success('Settings saved')
    } catch (err) {
      toast.error('Settings were not saved', errorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card className="p-6">
      <SectionTitle className="mb-4">Your details</SectionTitle>
      <form
        className="flex flex-col gap-4"
        onSubmit={(e) => {
          e.preventDefault()
          void save()
        }}
      >
        <div className="grid grid-cols-2 gap-4">
          <Field label="Preparer name" htmlFor="preparer" hint="Recorded on sign-off and in the audit trail.">
            <Input
              id="preparer"
              value={form.preparerName}
              maxLength={80}
              placeholder="e.g. Sana Fathima"
              onChange={(e) => setForm({ ...form, preparerName: e.target.value })}
            />
          </Field>
          <Field label="Department" htmlFor="department" hint="Shown on the dashboard and reports.">
            <Input
              id="department"
              value={form.department}
              maxLength={80}
              placeholder="e.g. Finance — Treasury"
              onChange={(e) => setForm({ ...form, department: e.target.value })}
            />
          </Field>
        </div>
        <Field label="Default currency" htmlFor="currency" hint="Label shown next to amounts. You can change it per reconciliation.">
          <Select id="currency" value={form.currency} onValueChange={(v) => setForm({ ...form, currency: v })} options={CURRENCIES} className="max-w-[200px]" />
        </Field>

        <div className="mt-2 border-t border-line pt-5">
          <SectionTitle className="mb-4">Smart Recon defaults</SectionTitle>
          <Switch
            checked={form.maskPartiesDefault}
            onCheckedChange={(v) => setForm({ ...form, maskPartiesDefault: v })}
            label="Mask party names by default"
            description="Customer, supplier and employee names are replaced with stable tokens (e.g. PARTY_07) before rows are sent."
          />
        </div>

        <div className="flex items-center justify-end gap-3 pt-1">
          {dirty && <span className="text-[12.5px] text-muted">Unsaved changes</span>}
          <Button type="submit" loading={saving} disabled={!dirty}>
            Save settings
          </Button>
        </div>
      </form>
    </Card>
  )
}

type TestState = { state: 'idle' } | { state: 'running' } | { state: 'ok'; text: string } | { state: 'error'; text: string }

/** Provider picker, per-provider key, model, base URL (Other) and Test connection. */
function AiProviderCard({ settings, onSaved }: { settings: Settings; onSaved: (s: Settings) => void }): React.JSX.Element {
  const toast = useToast()
  const confirm = useConfirm()
  const [keys, setKeys] = useState<KeyState>({ state: 'loading' })
  const [provider, setProvider] = useState<AiProvider>(() => activeAi(settings).provider)
  const [models, setModels] = useState<Partial<Record<AiProvider, string>>>(() => Object.fromEntries(AI_PROVIDERS.map((p) => [p, storedModel(settings, p)])))
  const [baseUrl, setBaseUrl] = useState(settings.aiBaseUrl)
  const [draft, setDraft] = useState('')
  const [keyError, setKeyError] = useState<string | null>(null)
  const [keyWarning, setKeyWarning] = useState<string | null>(null)
  const [busy, setBusy] = useState<'key' | 'forget' | 'save' | null>(null)
  const [test, setTest] = useState<TestState>({ state: 'idle' })

  useEffect(() => {
    setProvider(activeAi(settings).provider)
    setModels(Object.fromEntries(AI_PROVIDERS.map((p) => [p, storedModel(settings, p)])))
    setBaseUrl(settings.aiBaseUrl)
  }, [settings])

  const refresh = useCallback(async (): Promise<void> => {
    try {
      setKeys({ state: 'ready', status: await window.recoDo.secrets.status() })
    } catch (err) {
      setKeys({ state: 'unavailable', message: errorMessage(err, 'Secure key storage is not available.') })
    }
  }, [])
  useEffect(() => {
    void refresh()
  }, [refresh])

  const info = AI_PROVIDER_INFO[provider]
  const model = (models[provider] ?? '').trim()
  const effectiveModel = modelFor(provider, model)
  const modelError = model && !isValidModelName(provider, model) ? 'Use only letters, numbers and . _ - : / @ + (no spaces).' : provider === 'custom' && !model ? 'Enter the model name your service uses.' : null
  const urlCheck = provider === 'custom' ? checkBaseUrl(baseUrl) : null
  const urlError = urlCheck && !urlCheck.ok && baseUrl.trim() ? urlCheck.message : null
  const pricing = describePricing(provider, effectiveModel, urlCheck?.ok ? urlCheck.url : null)
  const host = provider === 'custom' ? (urlCheck?.ok ? urlCheck.host : null) : providerHost(provider)

  const saved = activeAi(settings)
  const savedModels = AI_PROVIDERS.map((p) => storedModel(settings, p))
  const dirty =
    provider !== saved.provider ||
    AI_PROVIDERS.some((p, i) => (models[p] ?? '').trim() !== savedModels[i]) ||
    (provider === 'custom' && (urlCheck?.ok ? urlCheck.url : baseUrl.trim()) !== (checkBaseUrl(settings.aiBaseUrl).ok ? saved.baseUrl : settings.aiBaseUrl.trim()))
  const invalid = !!modelError || (provider === 'custom' && !urlCheck?.ok)

  const keyStatus = keys.state === 'ready' ? keys.status.providers[provider] : null
  const hasKey = !!keyStatus?.hasKey

  const changeProvider = (p: string): void => {
    setProvider(p as AiProvider)
    setDraft('')
    setKeyError(null)
    setKeyWarning(null)
    setTest({ state: 'idle' })
  }

  const saveKey = async (): Promise<void> => {
    const key = draft.trim()
    const problem = keyProblem(provider, key)
    if (problem) {
      setKeyError(problem)
      return
    }
    setKeyError(null)
    setKeyWarning(null)
    setBusy('key')
    try {
      const { warning } = await window.recoDo.secrets.setApiKey(provider, key)
      setDraft('')
      setKeyWarning(warning)
      await refresh()
      toast.success(`${info.label} key saved`, 'It is encrypted on this computer and never shown again.')
    } catch (err) {
      setKeyError(errorMessage(err))
    } finally {
      setBusy(null)
    }
  }

  const forget = async (): Promise<void> => {
    const ok = await confirm({
      title: `Forget the saved ${info.label} key?`,
      description: 'Smart Recon cannot use this provider until you add a key again. Your reconciliations are not affected.',
      confirmLabel: 'Forget key',
      tone: 'danger'
    })
    if (!ok) return
    setBusy('forget')
    try {
      await window.recoDo.secrets.forgetApiKey(provider)
      setKeyWarning(null)
      await refresh()
      toast.info('API key removed from this computer')
    } catch (err) {
      toast.error('The key could not be removed', errorMessage(err))
    } finally {
      setBusy(null)
    }
  }

  const save = async (): Promise<void> => {
    if (invalid) return
    setBusy('save')
    try {
      // The address goes to the main process first: only a saved address may ever be contacted.
      const cleanUrl = provider === 'custom' && urlCheck?.ok ? await window.recoDo.ai.setCustomBaseUrl(urlCheck.url) : null
      const aiModels = Object.fromEntries(AI_PROVIDERS.map((p) => [p, (models[p] ?? '').trim()]).filter(([, m]) => m !== '')) as Partial<Record<AiProvider, string>>
      const next = await saveSettings({
        aiProvider: provider,
        aiModels,
        // The older field keeps the Anthropic model, as before.
        aiModel: aiModels.anthropic ?? AI_PROVIDER_INFO.anthropic.defaultModel,
        aiBaseUrl: provider === 'custom' ? (cleanUrl ?? '') : settings.aiBaseUrl
      })
      onSaved(next)
      await refresh()
      setTest({ state: 'idle' })
      toast.success('AI settings saved', `Smart Recon will send to ${next.aiProvider === 'custom' ? (cleanUrl ?? 'your service') : AI_PROVIDER_INFO[next.aiProvider].label}.`)
    } catch (err) {
      toast.error('AI settings were not saved', errorMessage(err))
    } finally {
      setBusy(null)
    }
  }

  const testConnection = async (): Promise<void> => {
    setTest({ state: 'running' })
    const started = performance.now()
    try {
      const res = await window.recoDo.ai.complete({
        provider,
        ...(provider === 'custom' ? { baseUrl: saved.baseUrl } : {}),
        model: effectiveModel,
        system: 'You are a connection test. Reply with a JSON array only.',
        messages: [{ role: 'user', content: 'Connection test from Reco-Do. Reply with [] and nothing else.' }],
        maxTokens: 1_000
      })
      const seconds = ((performance.now() - started) / 1000).toFixed(1)
      if (res.ok) setTest({ state: 'ok', text: `Connected to ${host ?? info.label} with ${effectiveModel}. It answered in ${seconds} s.` })
      else setTest({ state: 'error', text: res.message })
    } catch (err) {
      setTest({ state: 'error', text: errorMessage(err, 'The test could not be sent. Please try again.') })
    }
  }

  const keyBadge =
    keys.state === 'loading' ? (
      <Spinner size={16} />
    ) : keys.state === 'unavailable' ? (
      <Badge tone="unmatched">Unavailable</Badge>
    ) : hasKey ? (
      <Badge tone="matched" dot>
        Key saved
      </Badge>
    ) : info.keyRequired ? (
      <Badge tone="neutral">No key</Badge>
    ) : (
      <Badge tone="neutral">No key (optional)</Badge>
    )

  const modelHint =
    provider === 'custom'
      ? 'The model name as your service lists it, e.g. llama-3.1-8b-instruct (LM Studio) or llama3.1:8b (Ollama).'
      : pricing.kind === 'unknown'
        ? `Default: ${info.defaultModel}. Cost estimate not available for this model; Smart Recon still works if ${info.name} knows the name.`
        : `Default: ${info.defaultModel}. Leave empty to use the default.`

  return (
    <Card className="p-6">
      <div className="mb-4 flex items-center justify-between">
        <SectionTitle>AI provider (Smart Recon)</SectionTitle>
        {keyBadge}
      </div>

      <div className="flex flex-col gap-4">
        <Field label="Provider" htmlFor="ai-provider" hint="Only Smart Recon's optional AI step uses it. Every other feature works offline.">
          <Select id="ai-provider" value={provider} onValueChange={changeProvider} options={PROVIDER_OPTIONS} />
        </Field>
        {provider === 'gemini' && (
          <p className="-mt-2 rounded-lg bg-[#E6F0FC] px-3 py-2 text-[12.5px] leading-relaxed text-primary">
            Google Antigravity is Google&apos;s coding tool; for Reco-Do use a Gemini API key from Google AI Studio.
          </p>
        )}
        {provider === 'custom' && (
          <p className="-mt-2 text-[12.5px] leading-relaxed text-muted">
            Any service that speaks the OpenAI Chat Completions format: OpenRouter, Groq, Mistral, Together, a company gateway, or a
            server on this computer such as LM Studio (http://localhost:1234/v1) or Ollama (http://localhost:11434/v1).
          </p>
        )}

        {keys.state === 'unavailable' && <p className="text-[13px] text-unmatched">{keys.message}</p>}

        {hasKey && keyStatus && (
          <div className="flex items-center justify-between gap-3 rounded-lg bg-gradient-to-r from-[#2A1F6B] to-[#4C3AB8] px-4 py-3 text-white">
            <div className="flex items-center gap-2.5">
              <KeyRound size={17} className="text-[#C9BEFF]" />
              <span className="font-mono text-[14px] tracking-wide">{keyStatus.masked}</span>
            </div>
            <Button variant="ghost" size="sm" className="text-white hover:bg-white/10" loading={busy === 'forget'} onClick={() => void forget()}>
              Forget key
            </Button>
          </div>
        )}

        <form
          onSubmit={(e) => {
            e.preventDefault()
            if (draft.trim()) void saveKey()
          }}
        >
          <Field
            label={hasKey ? 'Replace key' : `${info.label} API key`}
            htmlFor="api-key"
            error={keyError}
            hint={
              keyWarning ? (
                <span role="status" className="text-doubtful">
                  {keyWarning}
                </span>
              ) : provider === 'custom' ? (
                'Leave empty for a local server that needs no key.'
              ) : (
                `Create one at ${info.keyWhere}. ${info.keyShapeText}`
              )
            }
          >
            <div className="flex gap-2">
              <Input
                id="api-key"
                type="password"
                autoComplete="off"
                spellCheck={false}
                value={draft}
                aria-invalid={!!keyError}
                placeholder={info.keyPlaceholder}
                className="font-mono text-[13px]"
                disabled={keys.state !== 'ready'}
                onChange={(e) => {
                  setDraft(e.target.value)
                  setKeyError(null)
                }}
              />
              <Button type="submit" variant="primary" loading={busy === 'key'} disabled={!draft.trim() || keys.state !== 'ready'}>
                Save key
              </Button>
            </div>
          </Field>
        </form>

        {provider === 'custom' && (
          <Field
            label="Base URL"
            htmlFor="ai-base-url"
            error={urlError}
            hint={
              urlCheck?.ok ? (
                <span role="status" className="font-semibold text-ink">
                  Rows you send will go to {urlCheck.host}
                  {urlCheck.local ? ' (a server on this computer)' : ''}.
                </span>
              ) : (
                'https:// is required; http:// is allowed only for localhost or 127.0.0.1.'
              )
            }
          >
            <Input
              id="ai-base-url"
              value={baseUrl}
              maxLength={300}
              spellCheck={false}
              aria-invalid={!!urlError}
              placeholder="http://localhost:1234/v1"
              className="font-mono text-[13px]"
              onChange={(e) => setBaseUrl(e.target.value)}
            />
          </Field>
        )}

        <Field
          label="Model"
          htmlFor="ai-model"
          error={modelError}
          hint={
            pricing.kind === 'unknown' && provider !== 'custom' && !modelError ? (
              <span role="status" className="text-doubtful">
                {modelHint}
              </span>
            ) : (
              modelHint
            )
          }
        >
          <Input
            id="ai-model"
            value={models[provider] ?? ''}
            maxLength={200}
            spellCheck={false}
            aria-invalid={!!modelError}
            placeholder={info.defaultModel || 'model name'}
            className="max-w-[340px] font-mono text-[13px]"
            onChange={(e) => setModels({ ...models, [provider]: e.target.value })}
          />
        </Field>

        <div className="flex flex-wrap items-center justify-end gap-3 pt-1">
          {dirty && <span className="text-[12.5px] text-muted">Unsaved changes</span>}
          <Button
            variant="secondary"
            onClick={() => void testConnection()}
            loading={test.state === 'running'}
            disabled={dirty || invalid || keys.state !== 'ready'}
            title={dirty ? 'Save your changes first' : 'Sends a tiny test message (no rows from your files)'}
          >
            <PlugZap size={15} />
            Test connection
          </Button>
          <Button onClick={() => void save()} loading={busy === 'save'} disabled={!dirty || invalid}>
            Save AI settings
          </Button>
        </div>

        {test.state === 'ok' && (
          <p role="status" className="flex items-start gap-2 rounded-lg bg-[#E3F4EC] px-3 py-2 text-[12.8px] text-matched">
            <CheckCircle2 size={15} className="mt-0.5 shrink-0" />
            {test.text}
          </p>
        )}
        {test.state === 'error' && (
          <p role="alert" className="flex items-start gap-2 rounded-lg bg-[#FDECEC] px-3 py-2 text-[12.8px] text-unmatched">
            <XCircle size={15} className="mt-0.5 shrink-0" />
            {test.text}
          </p>
        )}
      </div>
    </Card>
  )
}

function PrivacyCard({ settings }: { settings: Settings | null }): React.JSX.Element {
  const ai = activeAi(settings ?? {})
  const where = ai.provider === 'custom' ? (ai.host ? `the service at ${ai.host}` : 'the service you set up') : `${ai.label} (${ai.host})`
  const points: Array<{ icon: React.ReactNode; title: string; text: string }> = [
    {
      icon: <Lock size={16} />,
      title: 'Your files stay on this computer',
      text: 'Reading files, matching, exports and all six tools run locally. Nothing is uploaded.'
    },
    {
      icon: <Sparkles size={16} />,
      title: 'Smart Recon sends only what you approve',
      text: `Only the still-unmatched rows, and only the mapped key columns (row id, date, amount, reference, party). You see a preview of exactly what will be sent before clicking Run. They go to ${where} and nowhere else.`
    },
    {
      icon: <Globe size={16} />,
      title: 'One destination at a time',
      text: 'The AI connection may reach only the chosen provider’s official address (or the exact base URL you saved for Other). Every other address is blocked.'
    },
    {
      icon: <ShieldCheck size={16} />,
      title: 'Keys are encrypted and never shown again',
      text: 'Each provider’s key is stored with Windows data protection in your user profile, used only by the app itself to call that provider, and never sent to the screen. Forget key deletes it.'
    }
  ]
  return (
    <Card className="p-6">
      <SectionTitle className="mb-4">Privacy</SectionTitle>
      <ul className="flex flex-col gap-4">
        {points.map((p) => (
          <li key={p.title} className="flex gap-3">
            <span className="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-full bg-[#E3F4EC] text-matched">{p.icon}</span>
            <div>
              <div className="text-[13.5px] font-semibold text-ink">{p.title}</div>
              <p className="mt-0.5 text-[12.8px] leading-relaxed text-muted">{p.text}</p>
            </div>
          </li>
        ))}
      </ul>
    </Card>
  )
}

/** Version, build date and where this user's data lives. */
function AboutCard(): React.JSX.Element {
  const toast = useToast()
  const info = useAppInfo()
  const built = buildDate()
  const [opening, setOpening] = useState(false)

  const openFolder = async (): Promise<void> => {
    setOpening(true)
    try {
      await window.recoDo.openDataFolder()
    } catch (err) {
      toast.error('The data folder could not be opened', errorMessage(err))
    } finally {
      setOpening(false)
    }
  }

  const rows: Array<{ label: string; value: React.ReactNode }> = [
    { label: 'Version', value: info ? `Reco-Do ${info.version}` : '…' },
    { label: 'Built', value: built ?? 'Not recorded' },
    { label: 'Data folder', value: info ? <span className="font-mono text-[12.5px] break-all">{info.dataPath}</span> : '…' }
  ]

  return (
    <Card className="p-6">
      <SectionTitle className="mb-4">About</SectionTitle>
      <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-5 gap-y-2.5 text-[13px]">
        {rows.map((r) => (
          <div key={r.label} className="contents">
            <dt className="text-muted">{r.label}</dt>
            <dd className="text-ink">{r.value}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-3 text-[12.5px] leading-relaxed text-muted">
        Your reconciliations, settings and saved keys are kept in the data folder. Updating or reinstalling Reco-Do keeps them.
      </p>
      <div className="mt-4 flex justify-end">
        <Button variant="secondary" onClick={() => void openFolder()} loading={opening} disabled={!info}>
          <FolderOpen size={15} />
          Open data folder
        </Button>
      </div>
    </Card>
  )
}

export function SettingsPage(): React.JSX.Element {
  const toast = useToast()
  const [settings, setSettings] = useState<Settings | null>(null)

  useEffect(() => {
    getSettings()
      .then(setSettings)
      .catch((err: unknown) => toast.error('Settings could not be loaded', errorMessage(err)))
  }, [toast])

  return (
    <div className="grid grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)] items-start gap-5">
      <div className="flex flex-col gap-5">
        {settings ? <DetailsCard settings={settings} onSaved={setSettings} /> : <Card className="grid h-64 place-items-center"><Spinner /></Card>}
        <PrivacyCard settings={settings} />
        <AboutCard />
      </div>
      {settings ? <AiProviderCard settings={settings} onSaved={setSettings} /> : <Card className="grid h-64 place-items-center"><Spinner /></Card>}
    </div>
  )
}
