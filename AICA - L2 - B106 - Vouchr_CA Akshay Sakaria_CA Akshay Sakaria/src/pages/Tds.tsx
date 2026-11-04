import { useRef, useState } from 'react';
import { DpdpNote } from '../ui/DpdpNote';
import { useStore } from '../data/store';
import { useTr } from '../i18n';
import { fyLabel, monthName, toIso, todayIso } from '../lib/dates';
import { docName, saveDocument } from '../lib/storage';
import { fmtInr, round2 } from '../lib/money';
import { downloadCsv } from '../lib/csv';
import { tdsDueDate } from '../lib/alerts';
import { tdsEntries } from '../lib/tdsAdvance';
import { parseChallanText } from '../lib/extract';
import { pdfText, photoText } from '../lib/docread';
import { Empty, PageHead, useAttempt, useToast } from '../ui/common';
import { Icon } from '../ui/Icon';

interface ChallanForm { month: string; amount: string; bsrCode: string; challanNo: string; paidOn: string; cin?: string; fileName?: string; itns?: string; file?: File }

export function Tds() {
  const { scoped, s, addChallan, client } = useStore();
  const tr = useTr();
  const toast = useToast();
  const attempt = useAttempt();
  const fileRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState<string>();
  // bills (TDS still due on them) + advances (TDS deducted when paid) — the same list the challan alerts use
  const rows = tdsEntries(scoped.expenses, scoped.payments);
  const byMonth = new Map<string, number>();
  for (const r of rows) byMonth.set(r.month, round2((byMonth.get(r.month) ?? 0) + r.tds));
  const months = [...byMonth.keys()].sort();
  const vendor = (id?: string) => s.vendors.find((v) => v.id === id);
  const paidFor = (m: string) => round2(scoped.challans.filter((c) => c.month === m).reduce((a, c) => a + c.amount, 0));
  const [form, setForm] = useState<ChallanForm>();

  /** Deposit on/before the 7th usually pays the previous month's TDS; otherwise the oldest unpaid month. */
  function guessMonth(deposit?: string): string {
    const unpaid = months.filter((m) => paidFor(m) < (byMonth.get(m) ?? 0));
    if (deposit) {
      const d = new Date(deposit + 'T00:00:00'); d.setDate(1); d.setMonth(d.getMonth() - 1);
      const prev = toIso(d).slice(0, 7);
      if (unpaid.includes(prev)) return prev;
    }
    return unpaid[0] ?? months[months.length - 1] ?? todayIso().slice(0, 7);
  }

  async function onReceipt(f?: File) {
    if (!f) return;
    setBusy(tr('Reading challan receipt…'));
    try {
      const text = f.type === 'application/pdf' ? await pdfText(f) : await photoText(f, (p) => setBusy(tr('Reading challan receipt…') + ` ${p}%`));
      const c = parseChallanText(text);
      if (c.found < 2) { toast(tr('Could not read the challan — please type the details.'), true); }
      setForm({
        month: guessMonth(c.depositDate), amount: c.amount ? String(c.amount) : '', bsrCode: c.bsrCode ?? '', challanNo: c.challanNo ?? '',
        paidOn: c.depositDate ?? todayIso(), cin: c.cin, fileName: f.name, itns: c.itns, file: f
      });
      if (c.found >= 2) toast(tr('Read {n} of 4 challan details — please check.', { n: c.found }));
    } catch {
      toast(tr('Could not read the challan — please type the details.'), true);
      setForm({ month: guessMonth(), amount: '', bsrCode: '', challanNo: '', paidOn: todayIso(), fileName: f.name });
    } finally {
      setBusy(undefined);
    }
  }

  function exportCsv() {
    downloadCsv('form140_working.csv', ['Deductee name', 'PAN', 'PAN status', 'TDS code', 'Date of credit', 'Amount paid/credited', 'Rate %', 'TDS', 'Challan BSR', 'Challan no', 'Challan date'],
      rows.map((r) => {
        const v = vendor(r.vendorId);
        const ch = scoped.challans.find((c) => c.month === r.month);
        return [r.vendorName, v?.pan ?? 'PANNOTAVBL', v?.panStatus ?? '', r.code ?? '', r.date, r.base, r.ratePct ?? '', r.tds, ch?.bsrCode, ch?.challanNo, ch?.paidOn];
      }));
  }

  async function save() {
    if (!form || !client) return;
    let doc: { fileId?: string; filePath?: string } = {};
    if (form.file) {
      try {
        const d = await saveDocument({ clientId: client.id, clientName: client.name, fy: fyLabel(form.paidOn), kind: 'TDS Challans', file: form.file,
          name: docName(form.paidOn, `TDS-${form.month}`, form.challanNo, form.file.name) });
        doc = { fileId: d.fileId, filePath: d.path };
      } catch { toast(tr('Could not save the receipt file — the challan is saved without it.'), true); }
    }
    const ok = attempt(() => addChallan({ month: form.month, amount: Number(form.amount), bsrCode: form.bsrCode.trim(), challanNo: form.challanNo.trim(), paidOn: form.paidOn, cin: form.cin, fileName: form.fileName, ...doc }), 'Challan recorded');
    if (ok) setForm(undefined);
  }

  return (
    <div className="content stack">
      <PageHead title={tr('TDS & Form 140')}>
        <button className="btn primary" onClick={() => fileRef.current?.click()} disabled={!!busy}><Icon name="camera" size={16} /> {tr('Snap / upload challan')}</button>
        <button className="btn" onClick={exportCsv} disabled={!rows.length}><Icon name="download" size={16} /> {tr('Form 140 working (CSV)')}</button>
      </PageHead>
      <DpdpNote kind="export" />
      <input ref={fileRef} type="file" accept="image/*,application/pdf" hidden data-testid="challan-file" onChange={(e) => { onReceipt(e.target.files?.[0]); e.target.value = ''; }} />
      {busy && <div className="banner info busy"><Icon name="refresh" size={18} /> {busy}</div>}
      <div className="banner warn small"><Icon name="alert" size={16} /><span>{tr('The CSV is a working sheet for the quarterly statement. The final Form 140 upload file must follow the official RPU/FVU specification — pending.')}</span></div>

      {form && (
        <div className="card pad stack" style={{ borderColor: 'var(--brand)' }}>
          <h3>{tr('Record challan')}{form.fileName ? ` — ${form.fileName}` : ''}</h3>
          <p className="tiny muted req-legend"><b>*</b> {tr('Required')}</p>
          <div className="row wrap" style={{ alignItems: 'flex-start' }}>
            <div className="field"><label htmlFor="ch-month" className="req">{tr('TDS month')}</label>
              <select id="ch-month" className="input sm" value={form.month} onChange={(e) => setForm({ ...form, month: e.target.value })}>
                {(months.length ? months : [form.month]).map((m) => <option key={m} value={m}>{monthName(m)}</option>)}
              </select>
            </div>
            <div className="field"><label htmlFor="ch-amt" className="req">{tr('Amount')}</label><input id="ch-amt" className="input sm num" inputMode="decimal" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value.replace(/[^0-9.]/g, '') })} /></div>
            <div className="field"><label htmlFor="ch-bsr" className="req">{tr('BSR code (7 digits)')}</label><input id="ch-bsr" className="input sm mono" maxLength={7} inputMode="numeric" value={form.bsrCode} onChange={(e) => setForm({ ...form, bsrCode: e.target.value.replace(/\D/g, '') })} /></div>
            <div className="field"><label htmlFor="ch-no" className="req">{tr('Challan serial no. (5 digits)')}</label><input id="ch-no" className="input sm mono" maxLength={5} inputMode="numeric" value={form.challanNo} onChange={(e) => setForm({ ...form, challanNo: e.target.value.replace(/\D/g, '') })} /></div>
            <div className="field"><label htmlFor="ch-date" className="req">{tr('Date of deposit')}</label><input id="ch-date" type="date" className="input sm" max={todayIso()} value={form.paidOn} onChange={(e) => setForm({ ...form, paidOn: e.target.value })} /></div>
          </div>
          {form.cin && <div className="small">CIN: <span className="mono">{form.cin}</span></div>}
          {form.itns && form.itns !== '281' && <div className="banner danger small"><Icon name="alert" size={16} />{tr('This receipt is ITNS {n}, not a TDS challan (ITNS 281). Check you uploaded the right receipt.', { n: form.itns })}</div>}
          {form.paidOn < form.month + '-01' && <div className="banner danger small"><Icon name="alert" size={16} />{tr('Challan date is before the TDS month — check the month or the receipt')}</div>}
          {form.paidOn > tdsDueDate(form.month) && <div className="banner danger small">{tr('Paid after the due date ({date}) — interest applies.', { date: tdsDueDate(form.month) })}</div>}
          <div className="row"><button className="btn primary" onClick={save}>{tr('Save challan')}</button><button className="btn" onClick={() => setForm(undefined)}>{tr('Cancel')}</button></div>
        </div>
      )}

      <div className="card">
        <div className="card-head"><h2>{tr('Challan tracker')}</h2></div>
        {byMonth.size === 0 ? <Empty>{tr('No TDS deducted')}</Empty> : (
          <div className="table-wrap">
            <table className="t num cards-sm">
              <thead><tr><th>{tr('Month')}</th><th className="right">{tr('TDS deducted')}</th><th className="right">{tr('Challans paid')}</th><th>{tr('Status')}</th><th /></tr></thead>
              <tbody>{months.map((m) => {
                const amt = byMonth.get(m)!;
                const paid = paidFor(m);
                const ch = scoped.challans.filter((c) => c.month === m);
                return (
                  <tr key={m}>
                    <td>{monthName(m)}<div className="tiny muted">{tr('Due')} {tdsDueDate(m)}</div></td>
                    <td className="right">{fmtInr(amt)}</td><td className="right">{fmtInr(paid)}</td>
                    <td>{paid >= amt ? <span className="badge ok">{tr('Paid')}</span> : paid > 0 ? <span className="badge warn">{tr('Short')} {fmtInr(round2(amt - paid))}</span> : <span className="badge danger">{tr('Not paid')}</span>}
                      {ch.map((c) => <div key={c.id} className="tiny muted">BSR {c.bsrCode} · #{c.challanNo} · {c.paidOn}{c.paidOn > tdsDueDate(m) && <span className="badge danger" style={{ marginLeft: 6 }}>{tr('Late — interest applies')}</span>}</div>)}</td>
                    <td>{paid < amt && <button className="btn sm" onClick={() => setForm({ month: m, amount: String(round2(amt - paid)), bsrCode: '', challanNo: '', paidOn: todayIso() })}>{tr('Type it in')}</button>}</td>
                  </tr>
                );
              })}</tbody>
            </table>
          </div>
        )}
      </div>

      <div className="card">
        <div className="card-head"><h2>{tr('Deductee register')}</h2></div>
        <div className="table-wrap">
          <table className="t num cards-sm">
            <thead><tr><th>{tr('Date')}</th><th>{tr('Deductee')}</th><th>PAN</th><th>{tr('Code')}</th><th className="right">{tr('Amount')}</th><th className="right">{tr('Rate')}</th><th className="right">TDS</th></tr></thead>
            <tbody>{rows.map((r) => {
              const v = vendor(r.vendorId);
              return (
                <tr key={r.kind + r.ref + r.date}><td>{r.date}</td><td>{r.vendorName}{r.kind === 'advance' && <span className="badge info" style={{ marginLeft: 6 }}>{tr('Advance')}</span>}{r.check && <span className="badge warn" style={{ marginLeft: 6 }}>{tr('Advance TDS section differs from the bill — CA to check')}</span>}</td>
                  <td className="mono">{v?.pan ?? <span className="badge danger">{tr('Missing')}</span>} {v?.panStatus && v.panStatus !== 'Operative' && <span className="badge warn">{tr(v.panStatus)}</span>}</td>
                  <td className="mono">{r.code}</td><td className="right">{fmtInr(r.base)}</td><td className="right">{r.ratePct}%</td><td className="right">{fmtInr(r.tds)}</td></tr>
              );
            })}</tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
