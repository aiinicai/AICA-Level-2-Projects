import { useState } from 'react';
import { Ban, ExternalLink, Save } from 'lucide-react';
import type { MsmeStatus, Row, Supplier } from '../types';
import { BLOCK_CATEGORIES } from '../lib/rules';
import { itc } from '../lib/engine';
import { checkGstin, stateOf } from '../lib/gstin';
import { money } from '../lib/format';
import { Btn, Field, inputCls, Modal, Notice } from './ui';

export function BlockModal({ row, onCancel, onConfirm }: { row: Row; onCancel: () => void; onConfirm: (catId: string, reason: string) => void }) {
  const [cat, setCat] = useState<string>(BLOCK_CATEGORIES[0].id);
  const [reason, setReason] = useState('');
  return (
    <Modal
      title="Block credit under Section 17(5)"
      onClose={onCancel}
      footer={
        <>
          <Btn onClick={onCancel}>Cancel</Btn>
          <Btn kind="danger" icon={<Ban className="w-3.5 h-3.5" />} onClick={() => onConfirm(cat, reason)}>
            Block credit
          </Btn>
        </>
      }
    >
      <div className="flex flex-col gap-3 text-xs">
        <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 grid grid-cols-2 gap-x-3 gap-y-1">
          <span className="text-slate-500">Supplier</span>
          <span className="font-semibold truncate">{row.name || '—'}</span>
          <span className="text-slate-500">GSTIN</span>
          <span className="font-mono">{row.gstin}</span>
          <span className="text-slate-500">Invoice</span>
          <span className="font-mono">
            {row.inv} · {row.date || 'no date'}
          </span>
          <span className="text-slate-500">ITC</span>
          <span className="font-semibold">{money(itc(row))}</span>
        </div>
        <Field label="Category under Section 17(5)">
          <select className={inputCls} value={cat} onChange={(e) => setCat(e.target.value)}>
            {BLOCK_CATEGORIES.map((c) => (
              <option key={c.id} value={c.id}>
                {c.sec} — {c.lbl}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Note (optional)">
          <input className={inputCls} value={reason} onChange={(e) => setReason(e.target.value)} placeholder="e.g. Car purchased for director" />
        </Field>
        <Notice tone="warn">A blocked invoice stays in the reconciliation, but its ITC is shown as a reversal in GSTR-3B Table 4(B)(1).</Notice>
      </div>
    </Modal>
  );
}

export function RemarkModal({ label, initial, onCancel, onSave }: { label: string; initial: string; onCancel: () => void; onSave: (text: string) => void }) {
  const [text, setText] = useState(initial);
  return (
    <Modal
      title="Note for this invoice"
      onClose={onCancel}
      footer={
        <>
          {initial && (
            <Btn kind="ghost" className="mr-auto text-red-600" onClick={() => onSave('')}>
              Delete note
            </Btn>
          )}
          <Btn onClick={onCancel}>Cancel</Btn>
          <Btn kind="primary" icon={<Save className="w-3.5 h-3.5" />} onClick={() => onSave(text)}>
            Save note
          </Btn>
        </>
      }
    >
      <p className="text-xs text-slate-500 mb-2">{label}</p>
      <textarea autoFocus rows={4} className={inputCls} value={text} onChange={(e) => setText(e.target.value)} placeholder="e.g. Supplier confirmed GSTR-1 will be amended in November return" />
    </Modal>
  );
}

const MSME_OPTIONS: { id: MsmeStatus; lbl: string }[] = [
  { id: 'unverified', lbl: 'Not checked yet' },
  { id: 'unregistered', lbl: 'Not MSME / large enterprise' },
  { id: 'micro', lbl: 'Micro enterprise' },
  { id: 'small', lbl: 'Small enterprise' },
  { id: 'medium', lbl: 'Medium enterprise' },
];

/**
 * Supplier details. MSME status is recorded by the user after checking the Udyam
 * registration; the app does not look it up itself.
 */
export function SupplierModal({ gstin, name, current, onCancel, onSave }: { gstin: string; name: string; current?: Supplier; onCancel: () => void; onSave: (s: Supplier) => void }) {
  const [s, setS] = useState<Supplier>(
    current ?? { gstin, email: '', msmeStatus: 'unverified', udyamNumber: '', notes: '', verifiedAt: '' }
  );
  const chk = checkGstin(gstin);
  const mse = s.msmeStatus === 'micro' || s.msmeStatus === 'small';
  const udyamOk = !s.udyamNumber || /^UDYAM-[A-Z]{2}-\d{2}-\d{7}$/i.test(s.udyamNumber.trim());
  return (
    <Modal
      title="Supplier details"
      onClose={onCancel}
      footer={
        <>
          <Btn onClick={onCancel}>Cancel</Btn>
          <Btn kind="primary" icon={<Save className="w-3.5 h-3.5" />} onClick={() => onSave(s)}>
            Save
          </Btn>
        </>
      }
    >
      <div className="flex flex-col gap-3 text-xs">
        <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
          <p className="font-semibold text-slate-800">{name || 'Supplier'}</p>
          <p className="font-mono mt-0.5">{gstin}</p>
          <p className="text-slate-500 mt-0.5">
            {stateOf(gstin)} · {chk.valid ? 'GSTIN check digit OK' : chk.error}
          </p>
        </div>
        <Field label="Supplier e-mail (used for follow-up e-mails)">
          <input type="email" className={inputCls} value={s.email} onChange={(e) => setS({ ...s, email: e.target.value })} placeholder="accounts@supplier.com" />
        </Field>
        <Notice>
          Check the supplier's Udyam registration yourself (ask the supplier for the Udyam certificate, or search on the{' '}
          <a className="underline font-semibold" href="https://udyamregistration.gov.in/" target="_blank" rel="noreferrer">
            Udyam portal <ExternalLink className="w-3 h-3 inline" />
          </a>
          ), then record the result here.
        </Notice>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <Field label="MSME classification">
            <select className={inputCls} value={s.msmeStatus} onChange={(e) => setS({ ...s, msmeStatus: e.target.value as MsmeStatus })}>
              {MSME_OPTIONS.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.lbl}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Udyam registration no." hint={udyamOk ? 'Format: UDYAM-MH-00-0000000' : 'Should look like UDYAM-MH-00-0000000'}>
            <input
              className={inputCls}
              value={s.udyamNumber}
              disabled={s.msmeStatus === 'unverified' || s.msmeStatus === 'unregistered'}
              onChange={(e) => setS({ ...s, udyamNumber: e.target.value.toUpperCase() })}
              placeholder="UDYAM-MH-00-0000000"
            />
          </Field>
        </div>
        <Field label="Notes">
          <textarea rows={2} className={inputCls} value={s.notes} onChange={(e) => setS({ ...s, notes: e.target.value })} placeholder="e.g. Udyam certificate received on 12/10/2026" />
        </Field>
        {mse && <Notice tone="warn">Micro / small enterprise: Section 43B(h) of the Income-tax Act allows the expense only if paid within 15 days (45 days with a written agreement).</Notice>}
        {s.verifiedAt && <p className="text-[0.65rem] text-slate-400">Last recorded: {s.verifiedAt}</p>}
      </div>
    </Modal>
  );
}
