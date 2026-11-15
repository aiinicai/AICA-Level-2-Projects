import { useMemo, useState, type ReactNode } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import type { DataStatus } from '@shared/types';
import { fmtMoney } from '@shared/format';
import { useFilterQuery } from '../api';
import { useCompany } from '../state';

const STATUS_LABEL: Record<DataStatus, string> = { actual: 'Actual', calculated: 'Calculated', estimated: 'Estimated', unavailable: 'Unavailable' };
const STATUS_HELP: Record<DataStatus, string> = {
  actual: 'Taken directly from posted source records',
  calculated: 'Derived from source records by a documented formula',
  estimated: 'Derived using an assumption — see calculation notes',
  unavailable: 'Cannot be calculated defensibly from available data',
};
export function StatusBadge({ status }: { status: DataStatus }) {
  const icon = { actual: '●', calculated: 'ƒ', estimated: '≈', unavailable: '∅' }[status];
  return <span className={`badge ${status}`} title={STATUS_HELP[status]}>{icon} {STATUS_LABEL[status]}</span>;
}

export function SeverityBadge({ severity }: { severity: 'high' | 'medium' | 'low' | 'info' }) {
  const icon = { high: '▲', medium: '◆', low: '●', info: 'ℹ' }[severity];
  return <span className={`badge ${severity}`}>{icon} {severity[0].toUpperCase() + severity.slice(1)}</span>;
}

export const Loading = ({ label = 'Loading…' }: { label?: string }) => <div className="state" role="status">{label}</div>;
export const Empty = ({ children }: { children: ReactNode }) => <div className="state">{children}</div>;
export function ErrorState({ error }: { error: unknown }) {
  return <div className="banner error" role="alert">⚠ {(error as Error)?.message ?? 'Something went wrong'}</div>;
}

/** Renders query state uniformly: loading, error, then children. */
export function Q<T>({ q, children }: { q: { isLoading: boolean; error: unknown; data: T | undefined }; children: (d: T) => ReactNode }) {
  if (q.isLoading) return <Loading />;
  if (q.error) return <ErrorState error={q.error} />;
  if (q.data === undefined) return null;
  return <>{children(q.data)}</>;
}

export function Money({ v, exact }: { v: number | null | undefined; exact?: boolean }) {
  return <span className={`num ${v !== null && v !== undefined && v < 0 ? 'neg' : ''}`}>{fmtMoney(v, { exact })}</span>;
}

export function Pct({ v, dp = 1 }: { v: number | null | undefined; dp?: number }) {
  return <span className="num">{v === null || v === undefined ? '—' : `${v.toFixed(dp)}%`}</span>;
}

export function Change({ v, better = 'higher' }: { v: number | null | undefined; better?: 'higher' | 'lower' | 'neutral' }) {
  if (v === null || v === undefined) return <span className="muted">—</span>;
  const good = better === 'neutral' ? null : better === 'higher' ? v > 0 : v < 0;
  const color = v === 0 || good === null ? 'var(--text-secondary)' : good ? 'var(--good)' : 'var(--critical)';
  return <span className="num" style={{ color }}>{v > 0 ? '▲' : v < 0 ? '▼' : ''} {Math.abs(v).toFixed(1)}%</span>;
}

/** Tabs bound to the ?tab= query parameter so views are linkable. */
export function Tabs({ tabs, param = 'tab' }: { tabs: { key: string; label: string }[]; param?: string }) {
  const [sp, setSp] = useSearchParams();
  const cur = sp.get(param) ?? tabs[0].key;
  return (
    <div className="tabs" role="tablist">
      {tabs.map((t) => (
        <button key={t.key} role="tab" aria-selected={cur === t.key} className={cur === t.key ? 'active' : ''}
          onClick={() => { const n = new URLSearchParams(sp); n.set(param, t.key); setSp(n, { replace: true }); }}>{t.label}</button>
      ))}
    </div>
  );
}
export function useTab(def: string, param = 'tab') {
  const [sp] = useSearchParams();
  return sp.get(param) ?? def;
}

export function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  return (
    <div className="modal-backdrop" onClick={onClose} onKeyDown={(e) => e.key === 'Escape' && onClose()}>
      <div className="modal" role="dialog" aria-modal="true" aria-label={title} onClick={(e) => e.stopPropagation()}>
        <div className="row mb"><h2 style={{ margin: 0 }}>{title}</h2><span className="spacer" /><button className="btn sm" onClick={onClose} autoFocus>Close</button></div>
        {children}
      </div>
    </div>
  );
}

/** CSV / Excel export is planned for a later version; printing to PDF works today. */
export function ExportButtons(_props: { report: string }) {
  return (
    <span className="row no-print">
      <button className="btn sm" onClick={() => window.print()}>Print / PDF</button>
    </span>
  );
}

export interface Column<T> {
  key: string;
  label: string;
  render?: (row: T) => ReactNode;
  value?: (row: T) => string | number | null | undefined;
  num?: boolean;
  width?: number;
}

/** Sortable, searchable, paginated table for large datasets. */
export function DataTable<T>({ rows, columns, pageSize = 25, search = true, initialSort, empty = 'No rows', rowKey }: {
  rows: T[]; columns: Column<T>[]; pageSize?: number; search?: boolean; initialSort?: { key: string; dir: 1 | -1 }; empty?: ReactNode; rowKey?: (r: T, i: number) => string | number;
}) {
  const [q, setQ] = useState('');
  const [sort, setSort] = useState(initialSort ?? null);
  const [page, setPage] = useState(0);
  const val = (r: T, c: Column<T>) => (c.value ? c.value(r) : (r as any)[c.key]);
  const filtered = useMemo(() => {
    let out = rows;
    if (q) {
      const s = q.toLowerCase();
      out = out.filter((r) => columns.some((c) => String(val(r, c) ?? '').toLowerCase().includes(s)));
    }
    if (sort) {
      const c = columns.find((x) => x.key === sort.key);
      if (c) out = [...out].sort((a, b) => {
        const x = val(a, c);
        const y = val(b, c);
        if (x === y) return 0;
        if (x === null || x === undefined) return 1;
        if (y === null || y === undefined) return -1;
        return (x < y ? -1 : 1) * sort.dir;
      });
    }
    return out;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rows, q, sort]);
  const pages = Math.max(1, Math.ceil(filtered.length / pageSize));
  const cur = Math.min(page, pages - 1);
  const shown = filtered.slice(cur * pageSize, cur * pageSize + pageSize);
  return (
    <div>
      {(search || pages > 1) && (
        <div className="row mb small">
          {search && <input aria-label="Search table" placeholder="Search…" value={q} onChange={(e) => { setQ(e.target.value); setPage(0); }} />}
          <span className="spacer" />
          <span className="muted">{filtered.length} rows</span>
          {pages > 1 && <>
            <button className="btn sm" disabled={cur === 0} onClick={() => setPage(cur - 1)}>‹ Prev</button>
            <span>{cur + 1} / {pages}</span>
            <button className="btn sm" disabled={cur >= pages - 1} onClick={() => setPage(cur + 1)}>Next ›</button>
          </>}
        </div>
      )}
      <div className="table-wrap">
        <table className="data">
          <thead><tr>{columns.map((c) => (
            <th key={c.key} className={`sortable ${c.num ? 'num' : ''}`} style={c.width ? { width: c.width } : undefined}
              aria-sort={sort?.key === c.key ? (sort.dir === 1 ? 'ascending' : 'descending') : 'none'}
              tabIndex={0} onKeyDown={(e) => e.key === 'Enter' && setSort({ key: c.key, dir: sort?.key === c.key ? (-sort.dir as 1 | -1) : -1 })}
              onClick={() => setSort({ key: c.key, dir: sort?.key === c.key ? (-sort.dir as 1 | -1) : -1 })}>
              {c.label}{sort?.key === c.key ? (sort.dir === 1 ? ' ↑' : ' ↓') : ''}
            </th>))}</tr></thead>
          <tbody>
            {shown.length === 0 && <tr><td colSpan={columns.length} className="muted">{empty}</td></tr>}
            {shown.map((r, i) => (
              <tr key={rowKey ? rowKey(r, i) : i}>{columns.map((c) => <td key={c.key} className={c.num ? 'num' : ''}>{c.render ? c.render(r) : String(val(r, c) ?? '—')}</td>)}</tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/** Link that preserves the global filters. */
export function FLink({ to, children }: { to: string; children: ReactNode }) {
  const qs = useFilterQuery();
  const [path, query] = to.split('?');
  const merged = new URLSearchParams(qs);
  if (query) for (const [k, v] of new URLSearchParams(query)) merged.set(k, v);
  return <Link to={`${path}?${merged.toString()}`}>{children}</Link>;
}

export function Notes({ notes }: { notes?: string[] }) {
  if (!notes?.length) return null;
  return <ul className="small secondary" style={{ margin: '6px 0', paddingLeft: 18 }}>{notes.map((n, i) => <li key={i}>{n}</li>)}</ul>;
}

export function Share({ v }: { v: number | null }) {
  if (v === null) return <span className="muted">—</span>;
  return <span className="row" style={{ gap: 6, flexWrap: 'nowrap' }}><span className="bar-track" style={{ width: 60 }}><span className="bar-fill" style={{ width: `${Math.max(0, Math.min(100, v))}%`, display: 'block' }} /></span><span className="num small">{v.toFixed(1)}%</span></span>;
}
