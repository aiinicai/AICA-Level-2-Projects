import { Link } from 'react-router-dom'
import { Layers, Lock } from 'lucide-react'
import { getModule, MODULES, type ModuleConfig } from '@shared/modules'
import { TOOLS } from '@shared/tools'
import { computeKpis, type DashboardKpis, type HistoryEntry } from '@shared/kpis'
import { formatCompact } from '@shared/format'
import type { GeneralTemplate } from '@shared/contracts'
import { getSettings, listHistory, listTemplates, type Settings } from '@/lib/db'
import { Badge, Card, PageHeader, SectionTitle, TechnicalDetails } from '@/components/ui'
import { useAsync } from '@/lib/useAsync'
import { lastRunLabel } from '@/lib/lastRun'
import { ToolIcon } from '@/components/ToolIcon'
import { cn } from '@/lib/cn'
import { countByModule, formatWhen, loadReconItems, reconLink, STATUS_LABEL, unfinishedItems, type ReconListItem } from '@/features/wizard/inProgress'

/** How many unfinished reconciliations the In progress strip lists. */
const RECENT_UNFINISHED = 5

function Kpi({ label, value, note, noteClass }: { label: string; value: string; note: string; noteClass?: string }): React.JSX.Element {
  return (
    <Card className="px-[18px] py-4">
      <div className="text-[11.5px] tracking-wide text-muted uppercase">{label}</div>
      <div className="num mt-1.5 mb-0.5 text-[26px] font-extrabold">{value}</div>
      <div className={cn('text-[12.5px] text-muted', noteClass)}>{note}</div>
    </Card>
  )
}

function KpiRow({ k, currency, status }: { k: DashboardKpis; currency: string; status: 'ready' | 'loading' | 'error' }): React.JSX.Element {
  if (status !== 'ready') {
    return (
      <div className="mb-6 grid grid-cols-2 gap-3.5 @mid/main:grid-cols-4">
        {['Recons this month', 'Avg auto-match rate', 'Open items to review', 'Oldest open item'].map((label) => (
          <Kpi key={label} label={label} value="—" note={status === 'loading' ? 'Loading…' : 'Not available right now'} />
        ))}
      </div>
    )
  }
  const delta = k.reconsThisMonth - k.reconsLastMonth
  return (
    <div className="mb-6 grid grid-cols-2 gap-3.5 @mid/main:grid-cols-4">
      <Kpi
        label="Recons this month"
        value={String(k.reconsThisMonth)}
        note={k.reconsThisMonth || k.reconsLastMonth ? `${delta >= 0 ? '▲' : '▼'} ${Math.abs(delta)} vs last month` : 'No reconciliations yet'}
        noteClass={k.reconsThisMonth || k.reconsLastMonth ? (delta >= 0 ? 'text-matched' : 'text-unmatched') : undefined}
      />
      <Kpi
        label="Avg auto-match rate"
        value={k.avgAutoMatchRate === null ? '—' : `${(k.avgAutoMatchRate * 100).toFixed(1)}%`}
        note={k.avgAutoMatchRate === null ? 'Shown after your first recon' : 'Exact + AI accepted'}
      />
      <Kpi
        label="Open items to review"
        value={String(k.openItemCount)}
        note={k.openItemCount ? `${currency} ${formatCompact(k.openItemAmount)} unreconciled` : 'Nothing waiting'}
        noteClass={k.openItemCount ? 'text-doubtful' : undefined}
      />
      <Kpi
        label="Oldest open item"
        value={k.oldestOpenItem ? `${k.oldestOpenItem.days} days` : '—'}
        note={k.oldestOpenItem ? k.oldestOpenItem.account : 'No open items'}
        noteClass={k.oldestOpenItem ? 'text-unmatched' : undefined}
      />
    </div>
  )
}

function templateLabel(templates: GeneralTemplate[]): string {
  if (!templates.length) return 'No saved templates yet'
  return `${templates.length} template${templates.length === 1 ? '' : 's'} · latest: ${templates[0].name}`
}

function ModuleCard({
  m,
  history,
  templates,
  historyError,
  inProgress
}: {
  m: ModuleConfig
  history: HistoryEntry[] | null
  templates: GeneralTemplate[] | null
  historyError: boolean
  /** Unfinished reconciliations of this module (null while loading or when they could not be loaded). */
  inProgress: number | null
}): React.JSX.Element {
  const live = m.status === 'live'
  const footer = !live
    ? 'Not configured'
    : m.id === 'general'
      ? templates
        ? templateLabel(templates)
        : historyError
          ? 'Templates not available right now'
          : '…'
      : history
        ? lastRunLabel(m.id, history)
        : historyError
          ? 'Last run: not available right now'
          : 'Last run: …'
  // The whole card opens the module (a stretched link); the "N in progress" link sits above it.
  return (
    <div className="group relative rounded-xl focus-within:ring-2 focus-within:ring-primary/50">
      <Card className={cn('relative h-full px-[18px] pt-4 pb-3 transition group-hover:shadow-md', !live && 'bg-[#FAFBFC]')}>
        <div className="absolute top-3.5 right-3.5 flex items-center gap-1.5">
          {live && !!inProgress && (
            <Link
              to={`/module/${m.id}?inprogress=1`}
              className="relative z-10 inline-flex items-center gap-1 rounded-full bg-[#E6F0FC] px-2 py-0.5 text-[11.5px] font-semibold text-primary outline-none hover:underline focus-visible:ring-2 focus-visible:ring-primary/50"
              data-testid={`in-progress-${m.id}`}
            >
              <Layers size={12} /> {inProgress} in progress
            </Link>
          )}
          <Badge tone={live ? 'live' : 'phase2'}>{live ? 'Live' : 'Phase 2'}</Badge>
        </div>
        <div
          className="grid h-[38px] w-[38px] place-items-center rounded-[9px] text-[15px] font-extrabold text-white"
          style={{ background: m.color, opacity: live ? 1 : 0.55 }}
        >
          {m.code}
        </div>
        <h3 className={cn('mt-2.5 mb-1 text-[15.5px] font-bold', !live && 'text-muted')}>
          <Link to={`/module/${m.id}`} className="outline-none after:absolute after:inset-0 after:rounded-xl">
            {m.name}
          </Link>
        </h3>
        <p className="min-h-[37px] text-[12.8px] leading-snug text-muted">{m.description}</p>
        <div className="mt-2.5 flex justify-between border-t border-line pt-2 text-[12.5px] text-muted">
          <span className="min-w-0 truncate pr-3" title={footer}>
            {footer}
          </span>
          {live ? (
            <span className="shrink-0 font-semibold text-primary">Start →</span>
          ) : (
            <span className="shrink-0 font-semibold text-[#9AA4B2]">Coming soon</span>
          )}
        </div>
      </Card>
    </div>
  )
}

function InProgressStrip({ items, total }: { items: ReconListItem[]; total: number }): React.JSX.Element {
  return (
    <Card className="mb-6 px-[18px] py-3.5" data-testid="in-progress-strip">
      <div className="mb-2 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <span className="flex items-center gap-1.5 text-[11.5px] tracking-wide text-muted uppercase">
          <Layers size={13} /> In progress · {total}
        </span>
        <Link to="/workspace/history" className="text-[12.5px] font-semibold text-primary hover:underline">
          All in Recon History →
        </Link>
      </div>
      <ul className="divide-y divide-line">
        {items.map((i) => {
          const m = getModule(i.moduleId)
          return (
            <li key={i.id}>
              <Link
                to={reconLink(i)}
                className="flex items-center gap-3 rounded-md py-2 text-[13px] outline-none hover:bg-[#F7F9FB] focus-visible:ring-2 focus-visible:ring-primary/50"
                data-testid="in-progress-recent"
              >
                <span className="grid h-6 w-6 shrink-0 place-items-center rounded-md text-[10px] font-extrabold text-white" style={{ background: m?.color ?? '#5B6676' }}>
                  {m?.code ?? '?'}
                </span>
                <span className="min-w-0 flex-1 truncate">
                  <b className="font-semibold">{i.accountLabel || 'Untitled'}</b>
                  {i.period && <span className="text-muted"> · {i.period}</span>}
                </span>
                <span className="hidden min-w-0 shrink truncate text-[12.5px] text-muted @2xl/main:block">{i.stage}</span>
                <Badge tone={i.status === 'draft' ? 'neutral' : 'doubtful'} size="sm">
                  {STATUS_LABEL[i.status]}
                </Badge>
                <span className="num hidden shrink-0 text-right text-[12px] whitespace-nowrap text-muted @mid/main:block">{formatWhen(i.updatedAt)}</span>
                <span className="shrink-0 font-semibold text-primary">Open →</span>
              </Link>
            </li>
          )
        })}
      </ul>
    </Card>
  )
}

export function Dashboard(): React.JSX.Element {
  const historyState = useAsync(listHistory, [], 'Your saved reconciliations could not be loaded, so the figures below are not shown.')
  const settingsState = useAsync<Settings>(getSettings)
  const templatesState = useAsync(listTemplates)
  const reconsState = useAsync(loadReconItems)
  const unfinished = reconsState.data ? unfinishedItems(reconsState.data) : null
  const perModule = reconsState.data ? countByModule(reconsState.data) : null
  const settings = settingsState.data ?? null
  // While loading, and when loading failed, there is no history to show; never claim "No reconciliations yet" then.
  const history = historyState.error || historyState.loading ? null : (historyState.data ?? [])
  const templates = templatesState.error || templatesState.loading ? null : (templatesState.data ?? [])

  const kpis = computeKpis(history ?? [], new Date())
  const name = settings?.preparerName.trim()
  const initials = name
    ? name
        .split(/\s+/)
        .map((p) => p[0])
        .slice(0, 2)
        .join('')
        .toUpperCase()
    : ''

  return (
    <>
      <PageHeader
        title="Choose a reconciliation"
        subtitle="Pick a module to start, or use a tool below. Saved column mappings load automatically for repeat files."
        right={
          name ? (
            <div className="flex items-center gap-2.5 text-right text-[13px] text-muted">
              <div>
                <b className="block font-semibold text-ink">{name}</b>
                {settings?.department}
              </div>
              <div className="grid h-10 w-10 place-items-center rounded-full bg-teal text-sm font-bold text-white">{initials}</div>
            </div>
          ) : (
            <Link to="/workspace/settings" className="text-[13px] font-semibold text-primary">
              Add your name in Settings →
            </Link>
          )
        }
      />

      {historyState.error && (
        <div role="alert" className="mb-4 rounded-xl border border-[#F3C2C2] bg-[#FDF2F2] px-4 py-3 text-[13px] text-ink">
          <b className="font-semibold">{historyState.error}</b>{' '}
          <button type="button" className="font-semibold text-primary hover:underline" onClick={() => void historyState.reload()}>
            Try again
          </button>
          <TechnicalDetails details={historyState.details} />
        </div>
      )}
      <KpiRow k={kpis} currency={settings?.currency ?? 'AED'} status={historyState.error ? 'error' : history ? 'ready' : 'loading'} />
      {unfinished && unfinished.length > 0 && <InProgressStrip items={unfinished.slice(0, RECENT_UNFINISHED)} total={unfinished.length} />}

      <div className="mb-2.5 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <SectionTitle>Reconciliation modules</SectionTitle>
        <span className="text-[12.5px] text-muted">One engine, one wizard: modules differ only in defaults</span>
      </div>
      <div className="mb-6 grid grid-cols-2 gap-3.5 @mid/main:grid-cols-3">
        {MODULES.map((m) => (
          <ModuleCard
            key={m.id}
            m={m}
            history={history}
            templates={templates}
            historyError={!!historyState.error || !!templatesState.error}
            inProgress={perModule ? (perModule[m.id] ?? 0) : null}
          />
        ))}
      </div>

      <div className="mb-2.5 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <SectionTitle>Document &amp; data tools</SectionTitle>
        <span className="inline-flex items-center gap-1.5 text-xs text-matched">
          <Lock size={13} strokeWidth={2.4} />
          All tools run on this computer. Files are never uploaded.
        </span>
      </div>
      <div className="grid grid-cols-3 gap-3 @wide/main:grid-cols-6">
        {TOOLS.map((t) => (
          <Link key={t.id} to={`/tools/${t.id}`} className="block rounded-xl outline-none focus-visible:ring-2 focus-visible:ring-primary/50">
            <Card className="flex h-full flex-col p-3.5 transition hover:shadow-md">
              <ToolIcon tool={t} />
              <h4 className="mt-2 mb-1 text-[13.8px] font-bold">{t.name}</h4>
              <p className="flex-1 text-[11.8px] leading-snug text-muted">{t.description}</p>
              <div className="mt-2 text-[12.3px] font-semibold text-primary">Open →</div>
            </Card>
          </Link>
        ))}
      </div>
    </>
  )
}
