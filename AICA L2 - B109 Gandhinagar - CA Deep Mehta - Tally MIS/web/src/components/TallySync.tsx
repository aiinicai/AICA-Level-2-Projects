import { useMemo, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { fmtDate } from '@shared/format';
import { addMonths, monthLabel, monthStart } from '@shared/periods';
import { api } from '../api';

interface OpenCompany { name: string; booksFrom: string | null; lastVoucherDate: string | null }
interface OpenCompanies { ok: boolean; message: string; port?: number; companies: OpenCompany[] }

/** Every month from `from` to `to`, as first-of-month dates (newest last). */
function monthsBetween(from: string, to: string): string[] {
  const out: string[] = [];
  for (let m = monthStart(from); m <= to; m = addMonths(m, 1)) out.push(m);
  return out;
}

/** The latest 12 months are pre-selected: most people want the current year and last year's comparison. */
function defaultMonths(all: string[]): string[] {
  return all.slice(-12);
}

/** Company data lasts one session, so this is the usual way in: pick a company open in Tally, pick months, sync. */
export function TallySyncCard() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const open = useQuery<OpenCompanies>({ queryKey: ['tally-open'], queryFn: () => api('/api/tally/companies'), retry: false });
  const [name, setName] = useState<string | undefined>();
  const [picked, setPicked] = useState<Set<string> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const d = open.data;
  const company = d?.companies.find((c) => c.name === name) ?? d?.companies[0];
  const today = new Date().toISOString().slice(0, 10);
  const all = useMemo(() => {
    if (!company) return [];
    const from = company.booksFrom ?? addMonths(today, -23);
    const to = company.lastVoucherDate && company.lastVoucherDate > today ? company.lastVoucherDate : today;
    return monthsBetween(from, to);
  }, [company, today]);
  const selected = picked ?? new Set(defaultMonths(all));
  const toggle = (m: string) => { const n = new Set(selected); if (n.has(m)) n.delete(m); else n.add(m); setPicked(n); };
  const byYear = useMemo(() => {
    const g = new Map<string, string[]>();
    for (const m of all) { const y = m.slice(0, 4); g.set(y, [...(g.get(y) ?? []), m]); }
    return [...g.entries()];
  }, [all]);
  const start = async () => {
    setBusy(true);
    setError(null);
    try {
      await api('/api/tally/sync', { body: { company: company!.name, port: d!.port, months: [...selected].sort() } });
      await qc.invalidateQueries();
      navigate('/sources');
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="card">
      <h2>Sync from Tally</h2>
      <p className="small muted">Company data is kept only while this app is open, so sync each session. Keep the company open in Tally. The app only reads from Tally; it never writes to it.</p>
      {open.isLoading && <p className="muted" role="status">Looking for Tally…</p>}
      {open.error && <div className="banner error" role="alert">{(open.error as Error).message}</div>}
      {d && !d.companies.length && <div className="banner warn" role="status">{d.message}</div>}
      {company && (
        <>
          <label className="field" style={{ maxWidth: 420 }}>Company
            <select value={company.name} onChange={(e) => { setName(e.target.value); setPicked(null); }}>{d!.companies.map((c) => <option key={c.name} value={c.name}>{c.name}</option>)}</select>
          </label>
          <div className="row mt">
            <b className="small">Months to sync ({selected.size} selected)</b>
            <span className="spacer" />
            <button type="button" className="btn sm" onClick={() => setPicked(new Set(all))}>All months</button>
            <button type="button" className="btn sm" onClick={() => setPicked(new Set(defaultMonths(all)))}>Last 12</button>
            <button type="button" className="btn sm" onClick={() => setPicked(new Set())}>Clear</button>
          </div>
          {byYear.map(([year, months]) => (
            <div key={year} className="months">
              <span className="yr">{year}</span>
              {months.map((m) => (
                <button key={m} type="button" className={`chip${selected.has(m) ? ' on' : ''}`} aria-pressed={selected.has(m)} onClick={() => toggle(m)}>{monthLabel(m).slice(0, 3)}</button>
              ))}
            </div>
          ))}
          {company.booksFrom && <p className="small muted mt">In Tally: books from {fmtDate(company.booksFrom)}. Each month is fetched separately; more months take longer.</p>}
        </>
      )}
      {error && <div className="banner error mt" role="alert">{error}</div>}
      <div className="row mt">
        {company
          ? <button className="btn primary" disabled={busy || selected.size === 0} onClick={start}>{busy ? 'Starting…' : `Sync ${selected.size} month${selected.size === 1 ? '' : 's'}`}</button>
          : <button className="btn" disabled={open.isFetching} onClick={() => open.refetch()}>Check again</button>}
      </div>
    </div>
  );
}
