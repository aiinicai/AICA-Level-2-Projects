import { Fragment, useState } from 'react';
import { fmtMoney } from '@shared/format';
import { FLink } from './ui';

export interface Line { key: string; label: string; amount: number; ledgerId?: number; status?: string; unverified?: boolean; children?: Line[] }
export interface Section { key: string; label: string; total: number | null; lines: Line[] }

/** A profit subtotal (gross profit, EBITDA…) rendered after the section `after`. */
export interface Subtotal { key: string; label: string; after: string; kind: 'amount' | 'percent'; value: number | null; status?: string }

export interface Column { label: string; sections: Section[]; subtotals?: Subtotal[]; budget?: Record<string, number> | null }

const flat = (lines: Line[], m = new Map<string, number>()) => {
  for (const l of lines) {
    m.set(l.key, l.amount);
    if (l.children) flat(l.children, m);
  }
  return m;
};

/**
 * Expandable statement: sections → class lines → ledgers (drill-through to ledger statement).
 * Optional comparison column with absolute and % change, vertical analysis (% of base) and budget.
 */
export function StatementTable({ columns, base, showChange = true, verticalLabel = '% of revenue', budget }: {
  columns: Column[]; base?: number | null; showChange?: boolean; verticalLabel?: string; budget?: Record<string, number> | null;
}) {
  const [open, setOpen] = useState<Record<string, boolean>>({});
  const primary = columns[0];
  const maps = columns.map((c) => {
    const m = new Map<string, number>();
    for (const s of c.sections) {
      m.set(`S:${s.key}`, s.total ?? 0);
      flat(s.lines, m);
    }
    return m;
  });
  const two = columns.length === 2 && showChange;
  const many = columns.length > 2;
  const cell = (v: number | undefined) => <td className={`num ${v !== undefined && v < 0 ? 'neg' : ''}`}>{v === undefined ? '—' : fmtMoney(v, { compact: false })}</td>;
  const changeCells = (key: string) => {
    if (!two) return null;
    const a = maps[0].get(key) ?? 0;
    const b = maps[1].get(key);
    const d = b === undefined ? null : a - b;
    const pct = b !== undefined && b > 0 ? ((a - b) / b) * 100 : null;
    return <><td className="num">{d === null ? '—' : fmtMoney(d, { compact: false })}</td><td className="num muted">{pct === null ? '—' : `${pct.toFixed(1)}%`}</td></>;
  };
  const vert = (key: string) => (base && base > 0 && !many ? <td className="num muted">{(((maps[0].get(key) ?? 0) / base) * 100).toFixed(1)}%</td> : !many ? <td className="num muted">—</td> : null);
  const bud = (key: string) => (budget ? <td className="num muted">{budget[key] !== undefined ? fmtMoney(budget[key], { compact: false }) : '—'}</td> : null);

  const span = 1 + columns.length + (two ? 2 : 0) + (many ? 0 : 1) + (budget ? 1 : 0);
  const subValue = (c: Column, key: string) => c.subtotals?.find((x) => x.key === key)?.value ?? null;
  const subtotalRows = (after: string) =>
    (primary.subtotals ?? []).filter((st) => st.after === after).map((st) => {
      const vals = columns.map((c) => subValue(c, st.key));
      const pctRow = st.kind === 'percent';
      const fmt = (v: number | null) => (v === null ? '—' : pctRow ? `${v.toFixed(1)}%` : fmtMoney(v, { compact: false }));
      const a = vals[0];
      const b = two ? vals[1] : null;
      const diff = a !== null && b !== null ? a - b : null;
      return (
        <tr key={`ST:${st.key}`} className={`subtotal${pctRow ? ' pct' : ''}`}>
          <td>{st.label}{st.status === 'estimated' && <span className="badge estimated" style={{ marginLeft: 6 }}>≈ estimated</span>}</td>
          {vals.map((v, i) => <td key={i} className={`num ${v !== null && v < 0 ? 'neg' : ''}`}>{fmt(v)}</td>)}
          {two && <>
            <td className="num">{diff === null ? '—' : pctRow ? `${diff >= 0 ? '+' : ''}${diff.toFixed(1)} pts` : fmtMoney(diff, { compact: false })}</td>
            <td className="num muted">{!pctRow && a !== null && b !== null && b > 0 ? `${(((a - b) / b) * 100).toFixed(1)}%` : '—'}</td>
          </>}
          {!many && <td className="num muted">{!pctRow && a !== null && base && base > 0 ? `${((a / base) * 100).toFixed(1)}%` : '—'}</td>}
          {budget && <td className="num muted">—</td>}
        </tr>
      );
    });

  const row = (l: Line, depth: number): JSX.Element => {
    const hasKids = !!l.children?.length;
    const isOpen = open[l.key];
    return (
      <Fragment key={l.key}>
        <tr>
          <td style={{ paddingLeft: 8 + depth * 18 }}>
            {hasKids ? <button className="tree-toggle" aria-expanded={!!isOpen} aria-label={`${isOpen ? 'Collapse' : 'Expand'} ${l.label}`} onClick={() => setOpen({ ...open, [l.key]: !isOpen })}>{isOpen ? '▾' : '▸'}</button> : <span style={{ display: 'inline-block', width: 18 }} />}
            {l.ledgerId ? <FLink to={`/ledgers/${l.ledgerId}`}>{l.label}</FLink> : l.label}
            {l.unverified && depth > 0 && <span className="muted small" title="Classification not yet verified by a user"> ·unverified</span>}
            {l.status === 'estimated' && <span className="badge estimated" style={{ marginLeft: 6 }}>≈ estimated</span>}
          </td>
          {maps.map((m, i) => <Fragment key={i}>{cell(m.get(l.key))}</Fragment>)}
          {changeCells(l.key)}
          {vert(l.key)}
          {bud(l.key)}
        </tr>
        {isOpen && l.children?.map((c) => row(c, depth + 1))}
      </Fragment>
    );
  };

  return (
    <div className="table-wrap" style={{ maxHeight: 'none' }}>
      <table className="data">
        <thead>
          <tr>
            <th style={{ minWidth: 230 }}>Line</th>
            {columns.map((c, i) => <th key={i} className="num">{c.label}</th>)}
            {two && <><th className="num">Change</th><th className="num">%</th></>}
            {!many && <th className="num">{verticalLabel}</th>}
            {budget && <th className="num">Budget</th>}
          </tr>
        </thead>
        <tbody>
          {primary.sections.map((s) => (
            <Fragment key={s.key}>
              <tr className="section"><td colSpan={span}>{s.label}</td></tr>
              {s.lines.map((l) => row(l, 0))}
              <tr className="total">
                <td>Total {s.label.toLowerCase()}</td>
                {maps.map((m, i) => <Fragment key={i}>{cell(m.get(`S:${s.key}`))}</Fragment>)}
                {changeCells(`S:${s.key}`)}
                {vert(`S:${s.key}`)}
                {bud(`S:${s.key}`)}
              </tr>
              {subtotalRows(s.key)}
            </Fragment>
          ))}
        </tbody>
      </table>
    </div>
  );
}
