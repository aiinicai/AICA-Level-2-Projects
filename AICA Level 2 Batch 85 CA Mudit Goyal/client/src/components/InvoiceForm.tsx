import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Invoice, LineItem, TaxType, createInvoice, updateInvoice } from '../api';
import { formatRupeesUI, todayInputValue } from '../utils/format';
import { errorMessage } from '../utils/errorMessage';
import { useSettings } from '../contexts/SettingsContext';

interface DraftLine {
  description: string;
  hsnSac: string;
  quantity: string;
  rate: string;
}

const BLANK_LINE: DraftLine = { description: '', hsnSac: '', quantity: '1', rate: '' };

const GST_RATES = [5, 12, 18, 28];

const toDraftLine = (line: LineItem): DraftLine => ({
  description: line.description,
  hsnSac: line.hsnSac ?? '',
  quantity: String(Number(line.quantity)),
  rate: String(Number(line.rate)),
});

const num = (v: string): number => {
  const n = Number(v);
  return isFinite(n) ? n : 0;
};

const r2 = (n: number) => Math.round((n + Number.EPSILON) * 100) / 100;

/**
 * Raise or correct an invoice.
 *
 * Client details are typed here rather than picked from a list — this subset
 * has no clients module, so the invoice carries them itself.
 *
 * The totals shown while typing mirror the server's arithmetic exactly (see
 * server/src/lib/money.ts). They are a preview, not the source of truth: the
 * server recomputes everything from the line items it is sent.
 */
const InvoiceForm: React.FC<{
  invoice?: Invoice | null;
  onSaved: (invoice: Invoice) => void;
  onCancel: () => void;
}> = ({ invoice, onSaved, onCancel }) => {
  const { settings } = useSettings();

  const [clientName, setClientName] = useState(invoice?.clientName ?? '');
  const [clientGstin, setClientGstin] = useState(invoice?.clientGstin ?? '');
  const [clientState, setClientState] = useState(invoice?.clientState ?? '');
  const [clientAddress, setClientAddress] = useState(invoice?.clientAddress ?? '');
  const [clientEmail, setClientEmail] = useState(invoice?.clientEmail ?? '');
  const [invoiceDate, setInvoiceDate] = useState(invoice?.invoiceDate?.slice(0, 10) ?? todayInputValue());
  const [dueDate, setDueDate] = useState(invoice?.dueDate?.slice(0, 10) ?? '');
  const [taxType, setTaxType] = useState<TaxType>(invoice?.taxType ?? settings?.defaultTaxType ?? 'CGST_SGST');
  const [gstRate, setGstRate] = useState(() => {
    const fallback = Number(settings?.defaultGstRate ?? 18);
    if (!invoice) return fallback;
    // CGST and SGST are each half the rate the user picked, so the combined
    // rate is what has to be put back in the box.
    if (invoice.taxType === 'IGST') return Number(invoice.igstRate ?? fallback);
    if (invoice.taxType === 'CGST_SGST') return Number(invoice.cgstRate ?? fallback / 2) * 2;
    return fallback;
  });

  const [notes, setNotes] = useState(invoice?.notes ?? '');
  const [lines, setLines] = useState<DraftLine[]>(
    invoice?.lineItems.length ? invoice.lineItems.map(toDraftLine) : [{ ...BLANK_LINE }],
  );
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  // The settings arrive after the first render, so the due date is filled in
  // once they land. A due date the user has already typed must survive that —
  // hence the ref, rather than an effect keyed on `dueDate` itself.
  const dueDateTouched = useRef(Boolean(invoice?.dueDate));

  useEffect(() => {
    if (invoice || !settings || dueDateTouched.current) return;
    const base = new Date(`${invoiceDate}T00:00:00.000Z`);
    if (Number.isNaN(base.getTime())) return;
    base.setUTCDate(base.getUTCDate() + settings.defaultPaymentTermDays);
    setDueDate(base.toISOString().slice(0, 10));
  }, [settings, invoiceDate, invoice]);

  const totals = useMemo(() => {
    const taxable = r2(lines.reduce((sum, l) => sum + num(l.quantity) * num(l.rate), 0));
    if (taxType === 'CGST_SGST') {
      const half = r2(gstRate / 2);
      const cgst = r2(taxable * (half / 100));
      return { taxable, cgst, sgst: cgst, igst: 0, total: r2(taxable + cgst * 2), half };
    }
    if (taxType === 'IGST') {
      const igst = r2(taxable * (gstRate / 100));
      return { taxable, cgst: 0, sgst: 0, igst, total: r2(taxable + igst), half: gstRate };
    }
    return { taxable, cgst: 0, sgst: 0, igst: 0, total: taxable, half: 0 };
  }, [lines, taxType, gstRate]);

  const setLine = (index: number, patch: Partial<DraftLine>) =>
    setLines((prev) => prev.map((l, i) => (i === index ? { ...l, ...patch } : l)));

  const removeLine = (index: number) =>
    setLines((prev) => (prev.length === 1 ? prev : prev.filter((_, i) => i !== index)));

  const submit = async (issue: boolean) => {
    setError('');
    if (!clientName.trim()) return setError('Client name is required');
    if (!lines.some((l) => l.description.trim() && num(l.rate) > 0)) {
      return setError('Add at least one line with a description and a rate');
    }

    setBusy(true);
    try {
      const payload = {
        clientName: clientName.trim(),
        clientGstin: clientGstin.trim(),
        clientState: clientState.trim(),
        clientAddress: clientAddress.trim(),
        clientEmail: clientEmail.trim(),
        invoiceDate,
        dueDate: dueDate || null,
        taxType,
        gstRate: taxType === 'NONE' ? 0 : gstRate,
        notes: notes.trim(),
        // Blank rows are a natural by-product of typing; they are dropped here
        // rather than rejected.
        lineItems: lines
          .filter((l) => l.description.trim())
          .map((l) => ({
            description: l.description.trim(),
            hsnSac: l.hsnSac.trim(),
            quantity: num(l.quantity),
            rate: num(l.rate),
          })),
        ...(invoice ? {} : { status: issue ? 'SENT' : 'DRAFT' }),
      };

      const res = invoice ? await updateInvoice(invoice.id, payload) : await createInvoice(payload);
      onSaved(res.data);
    } catch (err) {
      setError(errorMessage(err, 'Could not save the invoice'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-5">
      <section className="grid sm:grid-cols-2 gap-3">
        <div className="sm:col-span-2">
          <label className="label">Client name *</label>
          <input className="input-field" value={clientName} onChange={(e) => setClientName(e.target.value)} />
        </div>
        <div>
          <label className="label">GSTIN</label>
          <input
            className="input-field uppercase"
            value={clientGstin}
            onChange={(e) => setClientGstin(e.target.value.toUpperCase())}
            placeholder="27AABCS1429B1ZQ"
          />
        </div>
        <div>
          <label className="label">Place of supply</label>
          <input className="input-field" value={clientState} onChange={(e) => setClientState(e.target.value)} placeholder="Maharashtra" />
        </div>
        <div className="sm:col-span-2">
          <label className="label">Address</label>
          <textarea className="input-field" rows={2} value={clientAddress} onChange={(e) => setClientAddress(e.target.value)} />
        </div>
        <div>
          <label className="label">Client email</label>
          <input className="input-field" type="email" value={clientEmail} onChange={(e) => setClientEmail(e.target.value)} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">Invoice date</label>
            <input className="input-field" type="date" value={invoiceDate} onChange={(e) => setInvoiceDate(e.target.value)} />
          </div>
          <div>
            <label className="label">Due date</label>
            <input
              className="input-field"
              type="date"
              value={dueDate}
              min={invoiceDate}
              onChange={(e) => {
                dueDateTouched.current = true;
                setDueDate(e.target.value);
              }}
            />
          </div>
        </div>
      </section>

      <section>
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold text-gray-700">Line items</h3>
          <button type="button" className="text-sm text-brand-600 hover:underline" onClick={() => setLines((p) => [...p, { ...BLANK_LINE }])}>
            + Add line
          </button>
        </div>

        <div className="space-y-2">
          {lines.map((line, i) => (
            <div key={i} className="grid grid-cols-12 gap-2 items-start">
              <input
                className="input-field col-span-12 sm:col-span-5"
                placeholder="Description"
                value={line.description}
                onChange={(e) => setLine(i, { description: e.target.value })}
              />
              <input
                className="input-field col-span-4 sm:col-span-2"
                placeholder="HSN/SAC"
                value={line.hsnSac}
                onChange={(e) => setLine(i, { hsnSac: e.target.value })}
              />
              <input
                className="input-field col-span-3 sm:col-span-1 text-right"
                type="number"
                min="0"
                step="0.01"
                placeholder="Qty"
                value={line.quantity}
                onChange={(e) => setLine(i, { quantity: e.target.value })}
              />
              <input
                className="input-field col-span-4 sm:col-span-2 text-right"
                type="number"
                min="0"
                step="0.01"
                placeholder="Rate"
                value={line.rate}
                onChange={(e) => setLine(i, { rate: e.target.value })}
              />
              <div className="col-span-1 sm:col-span-2 flex items-center justify-end gap-2 pt-2">
                <span className="hidden sm:inline text-sm text-gray-600 tabular-nums">
                  ₹{formatRupeesUI(num(line.quantity) * num(line.rate))}
                </span>
                <button
                  type="button"
                  onClick={() => removeLine(i)}
                  disabled={lines.length === 1}
                  aria-label={`Remove line ${i + 1}`}
                  className="text-gray-400 hover:text-red-600 disabled:opacity-30"
                >
                  ×
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="grid sm:grid-cols-2 gap-4">
        <div className="space-y-3">
          <div>
            <label className="label">Tax</label>
            <select className="input-field" value={taxType} onChange={(e) => setTaxType(e.target.value as TaxType)}>
              <option value="CGST_SGST">CGST + SGST (within the state)</option>
              <option value="IGST">IGST (inter-state)</option>
              <option value="NONE">No GST</option>
            </select>
          </div>
          {taxType !== 'NONE' && (
            <div>
              <label className="label">GST rate</label>
              <select className="input-field" value={gstRate} onChange={(e) => setGstRate(Number(e.target.value))}>
                {GST_RATES.map((r) => (
                  <option key={r} value={r}>{r}%</option>
                ))}
              </select>
            </div>
          )}
          <div>
            <label className="label">Notes</label>
            <textarea className="input-field" rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
          </div>
        </div>

        <div className="bg-gray-50 rounded-lg p-4 text-sm space-y-1.5 self-start">
          <div className="flex justify-between"><span className="text-gray-600">Taxable value</span><span className="tabular-nums">₹{formatRupeesUI(totals.taxable)}</span></div>
          {taxType === 'CGST_SGST' && (
            <>
              <div className="flex justify-between"><span className="text-gray-600">CGST @ {totals.half}%</span><span className="tabular-nums">₹{formatRupeesUI(totals.cgst)}</span></div>
              <div className="flex justify-between"><span className="text-gray-600">SGST @ {totals.half}%</span><span className="tabular-nums">₹{formatRupeesUI(totals.sgst)}</span></div>
            </>
          )}
          {taxType === 'IGST' && (
            <div className="flex justify-between"><span className="text-gray-600">IGST @ {gstRate}%</span><span className="tabular-nums">₹{formatRupeesUI(totals.igst)}</span></div>
          )}
          <div className="flex justify-between pt-2 mt-1 border-t border-gray-200 font-semibold text-base">
            <span>Total</span><span className="tabular-nums">₹{formatRupeesUI(totals.total)}</span>
          </div>
        </div>
      </section>

      {error && (
        <div role="alert" className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</div>
      )}

      <div className="flex flex-wrap gap-2 justify-end pt-1">
        <button type="button" className="btn-secondary" onClick={onCancel} disabled={busy}>Cancel</button>
        <button type="button" className="btn-secondary" onClick={() => submit(false)} disabled={busy}>
          {invoice ? 'Save changes' : 'Save as draft'}
        </button>
        {!invoice && (
          <button type="button" className="btn-primary" onClick={() => submit(true)} disabled={busy}>
            {busy ? 'Saving…' : 'Save & issue'}
          </button>
        )}
      </div>
    </div>
  );
};

export default InvoiceForm;
