import { useMemo, useState } from 'react';
import type * as XLSX from 'xlsx';
import { RefreshCw, Upload } from 'lucide-react';
import type { Kind } from '../types';
import { autoMap, detectHeaderRow, FIELDS, sheetRows, toTable, type FieldKey, type Mapping } from '../lib/importer';
import { toIndianDate } from '../lib/dates';
import { Badge, Btn, cx, inputCls, Modal, Notice } from './ui';

export const KIND_LABEL: Record<Kind, string> = {
  g2b: 'GSTR-2B',
  bks: 'Purchase register (books)',
  cdn_g2b: 'GSTR-2B credit / debit notes',
  cdn_bks: 'Books credit / debit notes',
  rcm: 'Reverse-charge (RCM) bills',
};

export interface PendingImport {
  kind: Kind;
  file: File;
  wb: XLSX.WorkBook;
  sheet: string;
}

/** Column-mapping popup: shows what was detected, lets the user change any column, previews rows. */
export function MappingModal({ p, onCancel, onConfirm }: { p: PendingImport; onCancel: () => void; onConfirm: (mapping: Mapping, allSheets: boolean, sheet: string) => void }) {
  const [sheet, setSheet] = useState(p.sheet);
  // GSTR-2B Excel files hold B2B, B2BA and CDNR on separate sheets, so read them all by default.
  const [allSheets, setAllSheets] = useState(p.kind === 'g2b' && p.wb.SheetNames.length > 1);
  const table = useMemo(() => {
    const raw = sheetRows(p.wb, sheet);
    return toTable(raw, detectHeaderRow(raw));
  }, [p.wb, sheet]);
  const detected = useMemo(() => autoMap(table), [table]);
  const [mapping, setMapping] = useState<Mapping>(detected.map);
  const [conf, setConf] = useState(detected.conf);
  const [lastTable, setLastTable] = useState(table);
  if (lastTable !== table) {
    setLastTable(table);
    setMapping(detected.map);
    setConf(detected.conf);
  }

  const missing = FIELDS.filter((f) => f.req && !mapping[f.k]);
  const mapped = FIELDS.filter((f) => mapping[f.k]);
  const confBadge = (k: FieldKey) => {
    const c = conf[k] ?? 0;
    if (!mapping[k]) return <Badge tone="slate">Not mapped</Badge>;
    if (c >= 90) return <Badge tone="green">Sure</Badge>;
    if (c >= 60) return <Badge tone="amber">Likely</Badge>;
    return <Badge tone="orange">Check</Badge>;
  };

  return (
    <Modal
      wide
      title={`Match columns: ${KIND_LABEL[p.kind]}`}
      onClose={onCancel}
      footer={
        <>
          <Btn
            icon={<RefreshCw className="w-3.5 h-3.5" />}
            onClick={() => {
              setMapping(detected.map);
              setConf(detected.conf);
            }}
            className="mr-auto"
          >
            Detect again
          </Btn>
          <Btn onClick={onCancel}>Cancel</Btn>
          <Btn kind="primary" icon={<Upload className="w-3.5 h-3.5" />} disabled={missing.length > 0} onClick={() => onConfirm(mapping, allSheets, sheet)}>
            Import
          </Btn>
        </>
      }
    >
      <div className="flex flex-col gap-3">
        <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4 text-xs">
          <span className="text-slate-500 truncate">
            File: <b className="text-slate-700">{p.file.name}</b> · {table.rows.length.toLocaleString('en-IN')} data rows · headings on row {table.headerIdx + 1}
          </span>
          <label className="flex items-center gap-2 sm:ml-auto">
            <span className="text-slate-500">Sheet</span>
            <select className={cx(inputCls, 'w-auto')} value={sheet} onChange={(e) => setSheet(e.target.value)}>
              {p.wb.SheetNames.map((s) => (
                <option key={s}>{s}</option>
              ))}
            </select>
          </label>
          {p.wb.SheetNames.length > 1 && (
            <label className="flex items-center gap-2 text-slate-600">
              <input type="checkbox" checked={allSheets} onChange={(e) => setAllSheets(e.target.checked)} className="accent-teal-600" />
              Import all sheets (B2B, B2BA, CDNR)
            </label>
          )}
        </div>

        {missing.length > 0 && <Notice tone="warn">Choose a column for: {missing.map((f) => f.lbl).join(', ')}.</Notice>}

        <div className="border border-slate-200 rounded-lg overflow-hidden">
          <div className="tbl-wrap max-h-[45vh]">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Field</th>
                  <th>Column in your file</th>
                  <th>Detection</th>
                  <th>First values</th>
                </tr>
              </thead>
              <tbody>
                {FIELDS.map((f) => (
                  <tr key={f.k}>
                    <td>
                      <span className="font-semibold text-slate-700">
                        {f.lbl}
                        {f.req && <span className="text-red-500"> *</span>}
                      </span>
                      <span className="block text-[0.65rem] text-slate-400">{f.hint}</span>
                    </td>
                    <td>
                      <select
                        className={cx(inputCls, 'min-w-[11rem]')}
                        value={mapping[f.k] ?? ''}
                        onChange={(e) => {
                          const v = e.target.value;
                          setMapping((m) => {
                            const n = { ...m };
                            if (v) n[f.k] = v;
                            else delete n[f.k];
                            return n;
                          });
                          setConf((c) => ({ ...c, [f.k]: v ? 100 : 0 }));
                        }}
                      >
                        <option value="">— not in this file —</option>
                        {table.headers.map((h) => (
                          <option key={h} value={h}>
                            {h}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>{confBadge(f.k)}</td>
                    <td className="text-slate-500 font-mono text-[0.68rem]">
                      {mapping[f.k]
                        ? table.rows
                            .slice(0, 3)
                            .map((r) => String(r[mapping[f.k]!] ?? ''))
                            .join(' · ')
                        : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {mapped.length > 0 && (
          <div>
            <p className="text-[0.7rem] font-semibold text-slate-600 mb-1">Preview (first 5 rows, as they will be read)</p>
            <div className="border border-slate-200 rounded-lg tbl-wrap max-h-48">
              <table className="tbl">
                <thead>
                  <tr>
                    {mapped.map((f) => (
                      <th key={f.k}>{f.lbl}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {table.rows.slice(0, 5).map((r, i) => (
                    <tr key={i}>
                      {mapped.map((f) => {
                        const v = r[mapping[f.k]!];
                        return <td key={f.k}>{f.k === 'date' ? toIndianDate(v) || String(v ?? '') : String(v ?? '')}</td>;
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-[0.65rem] text-slate-400 mt-1">Dates are read day-first (dd/mm/yyyy). Excel date cells are converted exactly.</p>
          </div>
        )}
      </div>
    </Modal>
  );
}
