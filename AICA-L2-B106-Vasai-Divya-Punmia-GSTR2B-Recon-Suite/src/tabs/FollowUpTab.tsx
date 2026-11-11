import { useMemo, useState } from 'react';
import { Check, Copy, FileDown, Mail, UserCog } from 'lucide-react';
import { useApp } from '../ctx';
import type { Row } from '../types';
import { followUps, itc, msmeLabel } from '../lib/engine';
import { amt, money } from '../lib/format';
import { supplierEmail, supplierNoticePdf } from '../lib/pdf';
import { downloadWorkbook, stamp } from '../lib/excel';
import { followUpRows } from '../lib/exports';
import { Badge, Btn, Card, cx, DataTable, Empty, ExportBtn, Notice, PageHead, Pills, type Col } from '../components/ui';

export default function FollowUpTab() {
  const { recon, firm, eng, suppliers, openSupplier, log, toast, goto } = useApp();
  const [mode, setMode] = useState<'missing' | 'all'>('missing');
  const [sel, setSel] = useState<string>('');
  const [view, setView] = useState<'table' | 'email'>('table');
  const [copied, setCopied] = useState(false);
  const list = useMemo(() => followUps(recon.lines, mode), [recon.lines, mode]);
  const cur = list.find((f) => f.gstin === sel) ?? list[0];
  const sup = cur ? suppliers[cur.gstin] : undefined;
  const mail = cur ? supplierEmail(cur, firm, eng.period) : null;
  const firmMissing = !firm.name;

  const cols: Col<Row & { issue: string }>[] = [
    { h: 'Invoice no.', cell: (r) => <span className="font-mono">{r.inv}</span>, foot: 'Total' },
    { h: 'Date', cell: (r) => r.date || '—' },
    { h: 'Taxable', cell: (r) => amt(r.taxable), num: true, foot: cur ? amt(cur.items.reduce((a, r) => a + r.taxable, 0)) : '' },
    { h: 'IGST', cell: (r) => amt(r.igst), num: true },
    { h: 'CGST', cell: (r) => amt(r.cgst), num: true },
    { h: 'SGST', cell: (r) => amt(r.sgst), num: true },
    { h: 'ITC', cell: (r) => <b>{amt(itc(r))}</b>, num: true, foot: cur ? amt(cur.items.reduce((a, r) => a + itc(r), 0)) : '' },
    { h: 'Issue', cell: (r) => <Badge tone={r.issue.startsWith('Not') ? 'red' : 'orange'}>{r.issue}</Badge> },
  ];

  const copy = async () => {
    if (!mail) return;
    try {
      await navigator.clipboard.writeText(`Subject: ${mail.subject}\n\n${mail.body}`);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast('Copy is blocked by the browser here. Select the text in the e-mail view and copy it.', 'error');
    }
  };

  const openMail = () => {
    if (!mail || !cur) return;
    const href = `mailto:${encodeURIComponent(sup?.email ?? '')}?subject=${encodeURIComponent(mail.subject)}&body=${encodeURIComponent(mail.body)}`;
    if (href.length > 1900) toast('Long invoice list: if your mail app cuts it short, use Copy and paste instead.', 'ok');
    window.location.href = href;
    log('FOLLOW-UP', `E-mail opened for ${cur.gstin} (${cur.items.length} invoices).`);
  };

  if (!recon.lines.length)
    return (
      <>
        <PageHead title="Supplier Follow-ups" />
        <Card>
          <Empty title="Load both files first">
            Follow-ups list suppliers whose invoices are in your books but not in GSTR-2B.{' '}
            <button className="underline text-teal-700" onClick={() => goto('imp')}>
              Import files
            </button>
          </Empty>
        </Card>
      </>
    );

  return (
    <div className="flex flex-col gap-3">
      <PageHead
        title="Supplier Follow-ups"
        sub="Suppliers whose invoices are in your books but still missing from GSTR-2B after all smart passes. Send a PDF notice or an e-mail asking them to report the invoices in GSTR-1."
        right={<ExportBtn onClick={() => downloadWorkbook(`Supplier_followups_${stamp()}`, [{ name: 'Follow-ups', rows: followUpRows(list, suppliers) }])} />}
      />
      <Pills
        value={mode}
        onChange={setMode}
        options={[
          { id: 'missing', label: 'Missing from 2B' },
          { id: 'all', label: 'Missing + ITC mismatch' },
        ]}
      />
      {firmMissing && (
        <Notice tone="warn">
          Add your firm name and contact details in{' '}
          <button className="underline font-semibold" onClick={() => goto('imp')}>
            Import & Settings
          </button>{' '}
          so they appear on notices and e-mails.
        </Notice>
      )}
      {list.length === 0 ? (
        <Card>
          <Empty title="Nothing to chase">Every invoice in your books is in GSTR-2B.</Empty>
        </Card>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-[18rem_1fr] gap-3 items-start">
          {/* Supplier list: dropdown on phones, list on larger screens */}
          <select className="lg:hidden w-full border border-slate-300 rounded-md px-2 py-2 text-sm bg-white" value={cur?.gstin} onChange={(e) => setSel(e.target.value)}>
            {list.map((f) => (
              <option key={f.gstin} value={f.gstin}>
                {f.name || f.gstin} — {f.items.length} inv · {money(f.itcAtRisk)}
              </option>
            ))}
          </select>
          <Card title={`Suppliers (${list.length})`} pad={false} className="hidden lg:block">
            <div className="max-h-[65vh] overflow-y-auto divide-y divide-slate-100">
              {list.map((f) => (
                <button
                  key={f.gstin}
                  type="button"
                  onClick={() => setSel(f.gstin)}
                  className={cx('w-full text-left px-3 py-2 hover:bg-slate-50 cursor-pointer', cur?.gstin === f.gstin && 'bg-teal-50 border-l-4 border-teal-600')}
                >
                  <p className="text-xs font-semibold text-slate-800 truncate">{f.name || 'Unknown supplier'}</p>
                  <p className="text-[0.65rem] font-mono text-slate-500">{f.gstin}</p>
                  <p className="text-[0.68rem] mt-0.5 flex justify-between">
                    <span className="text-slate-500">{f.items.length} invoice(s)</span>
                    <span className="text-red-600 font-semibold">{money(f.itcAtRisk)}</span>
                  </p>
                </button>
              ))}
            </div>
          </Card>

          {cur && mail && (
            <div className="flex flex-col gap-3 min-w-0">
              <Card>
                <div className="flex flex-col md:flex-row md:items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h3 className="font-bold text-slate-800">{cur.name || 'Unknown supplier'}</h3>
                    <p className="font-mono text-xs text-slate-500">{cur.gstin}</p>
                    <div className="flex flex-wrap gap-1.5 mt-1.5">
                      <Badge tone={sup?.msmeStatus === 'micro' || sup?.msmeStatus === 'small' ? 'amber' : sup && sup.msmeStatus !== 'unverified' ? 'sky' : 'slate'}>
                        MSME: {msmeLabel(sup)}
                      </Badge>
                      {(sup?.msmeStatus === 'micro' || sup?.msmeStatus === 'small') && <Badge tone="amber">Pay within 15 / 45 days (43B(h))</Badge>}
                      <Badge tone={sup?.email ? 'green' : 'slate'}>{sup?.email || 'No e-mail saved'}</Badge>
                      <Badge tone="red">ITC at risk {money(cur.itcAtRisk)}</Badge>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2 shrink-0">
                    <Btn icon={<UserCog className="w-3.5 h-3.5" />} onClick={() => openSupplier(cur.gstin, cur.name)}>
                      E-mail & MSME
                    </Btn>
                    <Btn
                      kind="dark"
                      icon={<FileDown className="w-3.5 h-3.5" />}
                      onClick={() => {
                        supplierNoticePdf(cur, firm, eng.period, sup);
                        log('FOLLOW-UP', `PDF notice downloaded for ${cur.gstin} (${cur.items.length} invoices).`);
                      }}
                    >
                      PDF notice
                    </Btn>
                    <Btn icon={copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />} onClick={copy}>
                      {copied ? 'Copied' : 'Copy e-mail'}
                    </Btn>
                    <Btn kind="primary" icon={<Mail className="w-3.5 h-3.5" />} onClick={openMail}>
                      Open in mail app
                    </Btn>
                  </div>
                </div>
              </Card>
              <Pills
                value={view}
                onChange={setView}
                options={[
                  { id: 'table', label: 'Invoices', count: cur.items.length },
                  { id: 'email', label: 'E-mail text' },
                ]}
              />
              {view === 'table' ? (
                <Card pad={false}>
                  <DataTable cols={cols} rows={cur.items} maxH="50vh" />
                </Card>
              ) : (
                <Card>
                  <p className="text-[0.7rem] font-semibold text-slate-500">Subject</p>
                  <p className="text-xs font-semibold text-slate-800 mb-3">{mail.subject}</p>
                  <p className="text-[0.7rem] font-semibold text-slate-500">Message</p>
                  <textarea readOnly value={mail.body} className="w-full h-80 font-mono text-[0.7rem] border border-slate-200 rounded-md p-2 bg-slate-50" />
                </Card>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
