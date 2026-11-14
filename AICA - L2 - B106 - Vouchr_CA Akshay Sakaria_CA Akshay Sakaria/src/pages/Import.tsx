// Bulk import from Excel (admins): pick what to import → download the sample format → upload the filled file →
// every row is checked exactly like a manual entry (dry run) → import only the rows that passed.
import { DpdpNote } from '../ui/DpdpNote';
import { useRef, useState } from 'react';
import { useStore, type ImportKind, type ImportRow, type ImportRowResult } from '../data/store';
import { useTr } from '../i18n';
import { datasetOf, downloadTemplate, mapGrid, readGrid } from '../lib/importer';
import { downloadCsv } from '../lib/csv';
import { PageHead, useToast } from '../ui/common';
import { Icon } from '../ui/Icon';

const ORDER: ImportKind[] = ['sources', 'centres', 'vendors', 'bills', 'payments'];

interface Preview { file: string; rows: ImportRow[]; results: ImportRowResult[]; missing: string[]; unknown: string[] }

export function Import() {
  const st = useStore();
  const { client } = st;
  const tr = useTr();
  const toast = useToast();
  const fileRef = useRef<HTMLInputElement>(null);
  const [kind, setKind] = useState<ImportKind>('vendors');
  const [busy, setBusy] = useState(false);
  const [preview, setPreview] = useState<Preview>();
  const ds = datasetOf(kind);
  if (!client) return null;

  const choose = (k: ImportKind) => { setKind(k); setPreview(undefined); };

  async function onFile(f?: File) {
    if (!f) return;
    setBusy(true);
    try {
      const parsed = mapGrid(ds, await readGrid(f));
      if (parsed.missing.length) { setPreview({ file: f.name, rows: [], results: [], missing: parsed.missing, unknown: parsed.unknown }); return; }
      const bad = new Set(parsed.cellErrors.map((c) => c.row));
      const rows = parsed.rows.filter((r) => !bad.has(r._row as number));
      const checked = st.importData(kind, rows, false);
      const results = [...checked, ...parsed.cellErrors.map((c) => ({ row: c.row, ok: false, label: `#${c.row}`, message: c.message, vars: c.vars }))].sort((a, b) => a.row - b.row);
      setPreview({ file: f.name, rows, results, missing: [], unknown: parsed.unknown });
    } catch (err) {
      toast(tr('Could not read this file. Save it as .xlsx or .csv and try again.'), true);
      st.logEvent('error', 'excel_import', 'Excel import failed: {err}', { err: (err as Error).message });
    } finally {
      setBusy(false);
    }
  }

  function commit() {
    if (!preview) return;
    const res = st.importData(kind, preview.rows, true);
    const n = res.filter((r) => r.ok).length;
    toast(tr('{n} row(s) imported', { n }) + (kind === 'bills' && n ? ' · ' + tr('They are now in the CA review queue.') : ''));
    setPreview(undefined);
  }

  const okCount = preview?.results.filter((r) => r.ok).length ?? 0;
  const failed = preview?.results.filter((r) => !r.ok) ?? [];

  return (
    <div className="content stack" style={{ maxWidth: 980 }}>
      <PageHead title={tr('Import from Excel')} sub={tr('Download the sample format, fill it, upload it. Every row is checked before anything is saved.')} />

      <div className="tabs" role="tablist" aria-label={tr('What to import')}>
        {ORDER.map((k, i) => (
          <button key={k} role="tab" aria-selected={kind === k} className={kind === k ? 'on' : undefined} onClick={() => choose(k)}
            ref={kind === k ? (el) => el?.scrollIntoView({ block: 'nearest', inline: 'center' }) : undefined}>
            <span className="tab-step">{i + 1}</span>{tr(datasetOf(k).title)}
          </button>
        ))}
      </div>
      <DpdpNote kind="import" />
      <div className="hint">{tr('Import in this order the first time: payment sources → projects & branches → vendors → old bills → payments.')}</div>

      <div className="card pad stack">
        <div className="row between wrap">
          <div>
            <h2>{tr(ds.title)}</h2>
            <p className="small muted" style={{ margin: '4px 0 0' }}>{tr(ds.blurb)}</p>
          </div>
          <div className="row wrap">
            <button className="btn" onClick={() => downloadTemplate(ds, client)}><Icon name="download" size={16} /> {tr('Download sample format')}</button>
            <button className="btn primary" disabled={busy} onClick={() => fileRef.current?.click()}><Icon name="upload" size={16} /> {busy ? tr('Checking…') : tr('Upload filled file')}</button>
          </div>
        </div>
        <input ref={fileRef} type="file" hidden data-testid="import-file" accept=".xlsx,.csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,text/csv"
          onChange={(e) => { onFile(e.target.files?.[0]); e.target.value = ''; }} />
        <div>
          <div className="tiny muted" style={{ marginBottom: 6 }}>{tr('Columns')} · <b style={{ color: 'var(--danger)' }}>*</b> {tr('Required')}</div>
          <div className="chips">
            {ds.columns.map((c) => <span key={c.key} className="chip static" title={c.en}><span className={c.required ? 'req' : undefined}>{c.header}</span></span>)}
          </div>
        </div>
      </div>

      {preview && preview.missing.length > 0 && (
        <div className="banner danger" role="alert"><Icon name="info" size={18} />
          <span>{tr('{file}: these required columns are missing — {cols}. Use the sample format.', { file: preview.file, cols: preview.missing.join(', ') })}</span>
        </div>
      )}

      {preview && !preview.missing.length && (
        <div className="card">
          <div className="card-head row between wrap">
            <div>
              <h2>{preview.file}</h2>
              <div className="small muted">{tr('{ok} ready · {bad} with problems', { ok: okCount, bad: failed.length })}{preview.unknown.length ? ` · ${tr('Ignored columns: {cols}', { cols: preview.unknown.join(', ') })}` : ''}</div>
            </div>
            <div className="row wrap">
              {failed.length > 0 && (
                <button className="btn sm" onClick={() => downloadCsv(`${ds.kind}-problems.csv`, [tr('Row'), tr('Entry'), tr('Problem')], failed.map((r) => [r.row, r.label, tr(r.message ?? '', r.vars)]))}>
                  <Icon name="download" size={14} /> {tr('Problem rows (CSV)')}
                </button>
              )}
              <button className="btn sm" onClick={() => setPreview(undefined)}>{tr('Cancel')}</button>
              <button className="btn sm primary" disabled={!okCount} onClick={commit}><Icon name="check" size={14} /> {tr('Import {n} row(s)', { n: okCount })}</button>
            </div>
          </div>
          {preview.results.length === 0 ? <div className="pad small muted">{tr('No rows found below the headings.')}</div> : (
            <div className="table-wrap">
              <table className="t">
                <thead><tr><th className="num">{tr('Row')}</th><th>{tr('Entry')}</th><th>{tr('Result')}</th></tr></thead>
                <tbody>
                  {preview.results.slice(0, 300).map((r) => (
                    <tr key={r.row}>
                      <td className="num muted">{r.row}</td>
                      <td className="ellipsis" style={{ maxWidth: 320 }}>{r.label}</td>
                      <td>{r.ok ? <span className="badge ok">✓ {tr('Ready')}</span> : <span className="small" style={{ color: 'var(--danger)' }}>{tr(r.message ?? '', r.vars)}</span>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {preview.results.length > 300 && <div className="pad tiny muted">{tr('Showing the first 300 rows.')}</div>}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

