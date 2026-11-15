import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode, type RefObject } from 'react';
import { Link, useLocation, useSearchParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../api';
import { Modal } from './ui';
import { Assistant } from './Assistant';
import { THEMES, applyTheme, storedTheme, type ThemeId } from '../themes';
import { useApp } from '../state';
import { addMonths, fyOf, monthEnd, monthLabel, monthsIn } from '@shared/periods';
import { fmtDate } from '@shared/format';
import { AppIcon, ChevronDownIcon, GridIcon, SignOutIcon, ThemeIcon } from './icons';
import { filterQuery, locate, visibleGroups } from './nav';


const initials = (name: string) => name.split(/\s+/).filter(Boolean).map((w) => w[0]).slice(0, 2).join('').toUpperCase() || '?';

/** Close a <details> menu on moving to another page, on a click outside and on Esc. */
function useDismiss(ref: RefObject<HTMLDetailsElement>) {
  const { pathname } = useLocation();
  useEffect(() => {
    if (ref.current) ref.current.open = false;
  }, [ref, pathname]);
  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      const el = ref.current;
      if (el?.open && !el.contains(e.target as Node)) el.open = false;
    };
    const onKey = (e: KeyboardEvent) => {
      const el = ref.current;
      if (e.key === 'Escape' && el?.open) {
        el.open = false;
        el.querySelector('summary')?.focus();
      }
    };
    document.addEventListener('click', onClick);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('click', onClick);
      document.removeEventListener('keydown', onKey);
    };
  }, [ref]);
}

/** The frame around every signed-in page, in the NOVEX App launcher style: the white module bar, the current
 *  group's pages as tabs (not on the home, where the tiles do the same job), then the page on the grey ground. */
export function Layout({ children }: { children: ReactNode }) {
  const { company, demoMode } = useApp();
  const home = useLocation().pathname === '/';
  const qs = filterQuery(useSearchParams()[0]);
  const qc = useQueryClient();
  const [closed, setClosed] = useState(false);
  const showClosed = useCallback(() => { setClosed(true); qc.clear(); }, [qc]);
  if (closed) {
    return (
      <main className="closed">
        <div className="signin-card">
          <h1>Tally MIS is closed</h1>
          <p className="sub">Company data has been removed. To use it again, open Tally MIS and sync your company.</p>
        </div>
      </main>
    );
  }
  return (
    <div className="shell">
      <a href="#main" className="skip">Skip to content</a>
      <header className="modbar no-print">
        <div className="bar-in">
          <div className="who">
            
            {demoMode
              ? <Link className="appic" to={`/${qs}`} aria-label="Tally MIS home" title="Tally MIS home"><AppIcon name="tally" /></Link>
              : <>
                  <Link className="square" to={`/${qs}`} aria-label="Tally MIS home" title="Tally MIS home"><GridIcon /></Link>
                  <span className="appic"><AppIcon name="tally" /></span>
                </>}
            <div className="title">
              <b>Tally MIS</b>
              <small>{company ? company.name : 'No company yet'}</small>
            </div>
          </div>
          <CompanyPicker />
          <UserMenu onClosed={showClosed} />
        </div>
      </header>
      {!home && <ModuleNav />}
      {!home && <div className="filters no-print"><div className="bar-in"><FilterBar /></div></div>}
      <main id="main" className={home ? 'content home' : 'content'}>
        <LicenceBanner />
        {company?.is_demo && <div className="banner demo" role="note">DEMO DATA — a fictional sample company generated for exploring the dashboard. Not real financial information.</div>}
        {company && !home && <PeriodNotice />}
        {children}
      </main>
      <Assistant />
    </div>
  );
}

/** Shown while there is no valid licence key: evaluation mode limits real data (the demo company is never limited). */
function LicenceBanner() {
  const q = useQuery<any>({ queryKey: ['licence'], queryFn: () => api('/api/licence') });
  const l = q.data;
  if (!l || l.status === 'licensed') return null;
  const lim = l.evaluationLimits;
  return (
    <div className="banner warn no-print" role="note">
      {l.status === 'evaluation'
        ? <>EVALUATION MODE — the demo company is unlimited; real data is limited to {lim.companies} company, {lim.monthsPerSync} months per sync and {lim.importMB} MB per file. </>
        : <>{l.message} </>}
      <Link to="/settings">Enter a licence key</Link>
    </div>
  );
}

/** Only shown when there is more than one company to choose from. */
function CompanyPicker() {
  const { companies, companyId, setCompanyId } = useApp();
  const setSp = useSearchParams()[1];
  if (companies.length < 2) return null;
  return (
    <label className="picker">
      <span className="sr-only">Company</span>
      <select value={companyId ?? ''} onChange={(e) => { setCompanyId(Number(e.target.value)); setSp(new URLSearchParams()); }}>
        {companies.map((c) => <option key={c.id} value={c.id}>{c.name}{c.is_demo ? ' [DEMO]' : ''}</option>)}
      </select>
    </label>
  );
}

/** A group switcher with tiles, then the current group's pages as tabs. */
function ModuleNav() {
  const { user, demoMode } = useApp();
  const { pathname } = useLocation();
  const qs = filterQuery(useSearchParams()[0]);
  const menu = useRef<HTMLDetailsElement>(null);
  const tabs = useRef<HTMLUListElement>(null);
  useDismiss(menu);
  // On a narrow screen the tabs scroll sideways: keep the current page's tab in view.
  useEffect(() => {
    tabs.current?.querySelector('[aria-current]')?.scrollIntoView({ block: 'nearest', inline: 'nearest' });
  }, [pathname]);
  const groups = visibleGroups(user, demoMode);
  const { group, current } = locate(groups, pathname);
  return (
    <nav className="modnav no-print" aria-label="Main">
      <div className="bar-in">
        <details ref={menu} className="groups">
          <summary>
            <span className="gi"><AppIcon name={group.icon} /></span>
            {group.label}
            <span className="sr-only">: switch to another part of Tally MIS</span>
            <ChevronDownIcon />
          </summary>
          <div className="pop">
            <p className="pop-h">Go to</p>
            <ul>
              {groups.map((g) => (
                <li key={g.key}>
                  <Link to={`${g.items[0].to}${qs}`} aria-current={g.key === group.key ? 'true' : undefined}>
                    <span className="pi"><AppIcon name={g.icon} /></span>
                    {g.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </details>
        <span className="vline" aria-hidden="true" />
        <ul ref={tabs} className="pages">
          {group.items.map((n) => (
            <li key={n.to}><Link to={`${n.to}${qs}`} aria-current={n === current ? 'page' : undefined}>{n.label}</Link></li>
          ))}
        </ul>
      </div>
    </nav>
  );
}

/** The menu top-right: pick one of the five themes, or close the app (which removes all company data). */
function UserMenu({ onClosed }: { onClosed: () => void }) {
  const [theme, setTheme] = useState<ThemeId>(storedTheme());
  const menu = useRef<HTMLDetailsElement>(null);
  useDismiss(menu);
  const pick = (id: ThemeId) => { setTheme(id); applyTheme(id); };
  const closeApp = async () => {
    if (!confirm('Close Tally MIS? All company data will be removed from memory, and any sync in progress will stop.')) return;
    try { await api('/api/close', { method: 'POST' }); } catch { /* the app may already be gone */ }
    onClosed();
  };
  return (
    <details ref={menu} className="me">
      <summary aria-label="Menu: theme and close">
        <span className="me-t"><b>Theme</b><small>{THEMES.find((t) => t.id === theme)?.label}</small></span>
        <span className="av" aria-hidden="true"><ThemeIcon /></span>
        <ChevronDownIcon />
      </summary>
      <div className="me-pop">
        <div className="me-h"><b>Colour theme</b><small>Saved on this PC</small></div>
        {THEMES.map((t) => (
          <button key={t.id} type="button" className={t.id === theme ? 'theme-on' : undefined} aria-pressed={t.id === theme} onClick={() => pick(t.id)}>
            <span className="swatch" aria-hidden="true">{t.swatch.map((c) => <i key={c} style={{ background: c }} />)}</span>
            {t.label}
          </button>
        ))}
        <button type="button" onClick={closeApp}><SignOutIcon />Close &amp; remove data</button>
      </div>
    </details>
  );
}

/** Company meta (data range, financial years, last sync). Polls while a sync is running. */
function useCompanyMeta() {
  const { companyId } = useApp();
  return useQuery<any>({
    queryKey: ['meta', companyId], queryFn: () => api(`/api/companies/${companyId}/meta`), enabled: !!companyId,
    refetchInterval: (q) => (q.state.data?.lastRun?.status === 'running' ? 3000 : false),
  });
}

function defaultRange(fyFrom: string, dataTo: string, startMonth: number) {
  const f = fyOf(fyFrom, startMonth);
  return { from: f.from, to: monthEnd(dataTo) < f.to ? monthEnd(dataTo) : f.to };
}

/** Explains empty figures: the selected period has no transactions, or a sync is still loading data. */
function PeriodNotice() {
  const { company } = useApp();
  const meta = useCompanyMeta();
  const [sp, setSp] = useSearchParams();
  const from = sp.get('from');
  const to = sp.get('to');
  const m = meta.data;
  if (!m) return null;
  if (m.lastRun?.status === 'running') {
    return <div className="banner info" role="status">◌ A sync is running for this company. Figures will refresh automatically when it finishes.</div>;
  }
  if (!m.dataFrom || !m.dataTo) {
    const r = m.lastRun;
    return (
      <div className="banner warn" role="note">
        {r?.status === 'succeeded' && r.from_date && r.to_date
          ? <>The last sync covered {fmtDate(r.from_date)} – {fmtDate(r.to_date)} and found no vouchers in that period, so period figures are zero. Sync again with dates that include this company's entries under <Link to="/sources">Data sources</Link>.</>
          : <>No vouchers have been imported for this company yet, so period figures are zero. Run a sync or import a Day Book under <Link to="/sources">Data sources</Link>.</>}
      </div>
    );
  }
  if (from && to && (to < m.dataFrom || from > m.dataTo)) {
    return (
      <div className="banner warn" role="note">
        ⚠ No transactions in the selected period. This company's data covers {fmtDate(m.dataFrom)} – {fmtDate(m.dataTo)}; balances shown are opening balances.
        <button className="btn sm" onClick={() => {
          const d = defaultRange(m.financialYears[0].from, m.dataTo, company?.fy_start_month ?? 4);
          const n = new URLSearchParams(sp);
          n.set('from', d.from);
          n.set('to', d.to);
          n.delete('custom');
          setSp(n);
        }}>Show latest year</button>
      </div>
    );
  }
  return null;
}

export function FilterBar() {
  const { companies, company } = useApp();
  const [sp, setSp] = useSearchParams();
  const qc = useQueryClient();
  const meta = useCompanyMeta();
  const fys: { label: string; from: string; to: string }[] = meta.data?.financialYears ?? [];
  const startMonth = company?.fy_start_month ?? 4;
  const from = sp.get('from');
  const to = sp.get('to');
  // When a sync that was running finishes, every cached figure for the company is stale: reload them all.
  const runStatus: string | undefined = meta.data?.lastRun?.status;
  const prevStatus = useRef(runStatus);
  useEffect(() => {
    if (prevStatus.current === 'running' && runStatus && runStatus !== 'running') qc.invalidateQueries();
    prevStatus.current = runStatus;
  }, [runStatus, qc]);
  const fy = from ? fyOf(from, startMonth) : fys[0] ? fyOf(fys[0].from, startMonth) : null;
  const set = (patch: Record<string, string | null>) => {
    const n = new URLSearchParams(sp);
    for (const [k, v] of Object.entries(patch)) if (v === null) n.delete(k); else n.set(k, v);
    setSp(n);
  };
  const periods = useMemo(() => {
    if (!fy) return [];
    const out = [{ key: `${fy.from}|${fy.to}`, label: 'Full year' }];
    const dataTo = meta.data?.dataTo as string | undefined;
    if (dataTo && dataTo >= fy.from && dataTo < fy.to) out.push({ key: `${fy.from}|${monthEnd(dataTo)}`, label: `Year to date (${monthLabel(dataTo)})` });
    for (let q = 0; q < 4; q++) {
      const qf = addMonths(fy.from, q * 3);
      out.push({ key: `${qf}|${monthEnd(addMonths(qf, 2))}`, label: `Q${q + 1} (${monthLabel(qf)}–${monthLabel(addMonths(qf, 2))})` });
    }
    for (const m of monthsIn(fy)) out.push({ key: `${m}|${monthEnd(m)}`, label: monthLabel(m) });
    return out;
  }, [fy?.from, fy?.to, meta.data?.dataTo]); // eslint-disable-line react-hooks/exhaustive-deps
  // With no explicit period, or a period in a financial year this company has no data for (e.g. carried over in the
  // address bar from another company), use the server default: latest financial year to date.
  const fyKnown = !from || fys.some((f) => f.from === fyOf(from, startMonth).from);
  useEffect(() => {
    if ((!from || !fyKnown) && fys[0] && meta.data?.dataTo) {
      const n = new URLSearchParams(sp);
      const d = defaultRange(fys[0].from, meta.data.dataTo, startMonth);
      n.set('from', d.from);
      n.set('to', d.to);
      n.delete('custom');
      setSp(n, { replace: true });
    }
  }, [from, fyKnown, fys[0]?.from, meta.data?.dataTo]); // eslint-disable-line react-hooks/exhaustive-deps
  const curKey = from && to ? `${from}|${to}` : fy ? `${fy.from}|${fy.to}` : '';
  const isCustom = !!(from && to && !periods.some((p) => p.key === curKey));

  if (!companies.length) return <span className="muted">No companies yet — sync from Tally or load the demo from Data sources.</span>;
  return (
    <div className="row" style={{ flex: 1 }}>
      <select aria-label="Financial year" value={fy ? `${fy.from}` : ''} onChange={(e) => { const f = fyOf(e.target.value, startMonth); set({ from: f.from, to: f.to }); }}>
        {(fys.length ? fys : fy ? [fy] : []).map((f) => <option key={f.from} value={f.from}>{f.label}</option>)}
      </select>
      <select aria-label="Period" value={isCustom ? 'custom' : curKey} onChange={(e) => { if (e.target.value === 'custom') set({ from: from ?? fy?.from ?? null, to: to ?? fy?.to ?? null, custom: '1' }); else { const [a, b] = e.target.value.split('|'); set({ from: a, to: b, custom: null }); } }}>
        {periods.map((p) => <option key={p.key} value={p.key}>{p.label}</option>)}
        <option value="custom">Custom range…</option>
      </select>
      {(isCustom || sp.get('custom')) && <>
        <input type="date" aria-label="From date" value={from ?? ''} onChange={(e) => e.target.value && set({ from: e.target.value })} />
        <input type="date" aria-label="To date" value={to ?? ''} onChange={(e) => e.target.value && set({ to: e.target.value })} />
      </>}
      <select aria-label="Comparison" value={sp.get('compare') ?? 'previous_year'} onChange={(e) => set({ compare: e.target.value })}>
        <option value="previous_year">vs same period last year</option>
        <option value="previous_period">vs previous period</option>
        <option value="none">No comparison</option>
      </select>
      {!!meta.data?.costCentres?.length && (
        <select aria-label="Cost centre" value={sp.get('costCentre') ?? ''} onChange={(e) => set({ costCentre: e.target.value || null })}>
          <option value="">All cost centres</option>
          {meta.data.costCentres.map((c: string) => <option key={c} value={c}>{c}</option>)}
        </select>
      )}
      <span className="spacer" />
      <span className="small muted" title="Last successful synchronisation">
        {company?.base_currency ?? 'INR'} · Synced {meta.data?.lastSuccessfulSync ? fmtDate(meta.data.lastSuccessfulSync) : 'never'}
        {meta.data?.lastRun && meta.data.lastRun.status !== 'succeeded' ? <span style={{ color: 'var(--critical)' }}> · last run {meta.data.lastRun.status}</span> : null}
      </span>
    </div>
  );
}
