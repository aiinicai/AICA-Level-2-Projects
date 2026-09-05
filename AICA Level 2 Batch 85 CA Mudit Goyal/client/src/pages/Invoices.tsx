import React, { useCallback, useEffect, useState } from 'react';
import {
  Invoice, InvoiceStatus, PaymentMode,
  getInvoices, issueInvoice, cancelInvoice, deleteInvoice, addPayment, deletePayment,
} from '../api';
import { formatRupeesUI, formatDateDdMmmYy, todayInputValue } from '../utils/format';
import { errorMessage } from '../utils/errorMessage';
import { downloadInvoicePdf, letterheadFrom } from '../utils/invoicePdf';
import { useSettings } from '../contexts/SettingsContext';
import Modal from '../components/Modal';
import InvoiceForm from '../components/InvoiceForm';
import StatusBadge from '../components/StatusBadge';

const STATUS_FILTERS: Array<{ value: string; label: string }> = [
  { value: '', label: 'All' },
  { value: 'DRAFT', label: 'Draft' },
  { value: 'SENT', label: 'Issued' },
  { value: 'PARTIALLY_PAID', label: 'Part paid' },
  { value: 'PAID', label: 'Paid' },
  { value: 'CANCELLED', label: 'Cancelled' },
];

const PAYMENT_MODES: PaymentMode[] = ['BANK', 'UPI', 'CHEQUE', 'CASH', 'OTHER'];

const num = (v: string | number | null | undefined): number => Number(v ?? 0) || 0;

const Invoices: React.FC = () => {
  const { settings } = useSettings();
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [summary, setSummary] = useState({ count: 0, billed: 0, collected: 0, outstanding: 0 });
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Invoice | null>(null);
  const [detail, setDetail] = useState<Invoice | null>(null);
  const [payFor, setPayFor] = useState<Invoice | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getInvoices({ search: search || undefined, status: status || undefined });
      setInvoices(res.data.invoices);
      setSummary(res.data.summary);
      setError('');
    } catch (err) {
      setError(errorMessage(err, 'Could not load invoices'));
    } finally {
      setLoading(false);
    }
  }, [search, status]);

  // Debounced so typing in the search box does not fire a request per keystroke.
  useEffect(() => {
    const t = setTimeout(load, 250);
    return () => clearTimeout(t);
  }, [load]);

  const act = async (fn: () => Promise<unknown>, confirmText?: string) => {
    if (confirmText && !window.confirm(confirmText)) return;
    try {
      await fn();
      setDetail(null);
      await load();
    } catch (err) {
      window.alert(errorMessage(err, 'That did not work'));
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-semibold text-gray-900">Invoices</h1>
        <button
          className="btn-primary"
          onClick={() => {
            setEditing(null);
            setFormOpen(true);
          }}
        >
          + New invoice
        </button>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {[
          { label: 'Invoices', value: String(summary.count) },
          { label: 'Billed', value: `₹${formatRupeesUI(summary.billed)}` },
          { label: 'Collected', value: `₹${formatRupeesUI(summary.collected)}` },
          { label: 'Outstanding', value: `₹${formatRupeesUI(summary.outstanding)}` },
        ].map((tile) => (
          <div key={tile.label} className="card">
            <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">{tile.label}</div>
            <div className="mt-1 text-xl font-semibold">{tile.value}</div>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap gap-2">
        <input
          className="input-field flex-1 min-w-[12rem]"
          placeholder="Search number, client or GSTIN…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select className="input-field w-auto" value={status} onChange={(e) => setStatus(e.target.value)}>
          {STATUS_FILTERS.map((f) => (
            <option key={f.value} value={f.value}>{f.label}</option>
          ))}
        </select>
      </div>

      {error && <div className="card text-sm text-red-700">{error}</div>}

      {loading ? (
        <div className="text-sm text-gray-500">Loading…</div>
      ) : invoices.length === 0 ? (
        <div className="card text-sm text-gray-500">No invoices match this filter.</div>
      ) : (
        <>
          {/* Desktop table */}
          <div className="hidden md:block bg-white rounded-xl border border-gray-200 overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr>
                  <th className="table-header">Invoice</th>
                  <th className="table-header">Client</th>
                  <th className="table-header">Date</th>
                  <th className="table-header text-right">Total</th>
                  <th className="table-header text-right">Balance</th>
                  <th className="table-header">Status</th>
                  <th className="table-header" />
                </tr>
              </thead>
              <tbody>
                {invoices.map((inv) => (
                  <tr key={inv.id} className="hover:bg-gray-50">
                    <td className="table-cell font-medium whitespace-nowrap">{inv.invoiceNumber}</td>
                    <td className="table-cell">
                      {inv.clientName}
                      {inv.clientGstin && <div className="text-xs text-gray-400">{inv.clientGstin}</div>}
                    </td>
                    <td className="table-cell whitespace-nowrap">{formatDateDdMmmYy(inv.invoiceDate)}</td>
                    <td className="table-cell text-right tabular-nums whitespace-nowrap">₹{formatRupeesUI(inv.totalAmount)}</td>
                    <td className="table-cell text-right tabular-nums whitespace-nowrap">
                      ₹{formatRupeesUI(num(inv.totalAmount) - num(inv.paidAmount))}
                    </td>
                    <td className="table-cell"><StatusBadge status={inv.status} /></td>
                    <td className="table-cell text-right whitespace-nowrap">
                      <button className="text-brand-600 hover:underline text-sm" onClick={() => setDetail(inv)}>
                        Open
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Phone list */}
          <div className="md:hidden space-y-2">
            {invoices.map((inv) => (
              <button key={inv.id} onClick={() => setDetail(inv)} className="card w-full text-left block">
                <div className="flex justify-between items-start gap-3">
                  <div className="min-w-0">
                    <div className="font-medium truncate">{inv.clientName}</div>
                    <div className="text-xs text-gray-500 mt-0.5">
                      {inv.invoiceNumber} · {formatDateDdMmmYy(inv.invoiceDate)}
                    </div>
                  </div>
                  <div className="text-right shrink-0">
                    <div className="font-semibold tabular-nums">₹{formatRupeesUI(inv.totalAmount)}</div>
                    <div className="mt-1"><StatusBadge status={inv.status} /></div>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </>
      )}

      {/* ── New / edit ──────────────────────────────────────────────────── */}
      <Modal
        open={formOpen}
        wide
        title={editing ? `Edit ${editing.invoiceNumber}` : 'New invoice'}
        onClose={() => setFormOpen(false)}
      >
        <InvoiceForm
          invoice={editing}
          onCancel={() => setFormOpen(false)}
          onSaved={() => {
            setFormOpen(false);
            setDetail(null);
            load();
          }}
        />
      </Modal>

      {/* ── Detail ─────────────────────────────────────────────────────── */}
      <Modal open={!!detail} wide title={detail?.invoiceNumber ?? ''} onClose={() => setDetail(null)}>
        {detail && (
          <div className="space-y-5">
            <div className="flex flex-wrap justify-between gap-4">
              <div className="text-sm">
                <div className="font-medium text-gray-900">{detail.clientName}</div>
                {detail.clientAddress && <div className="text-gray-500 mt-0.5 whitespace-pre-line">{detail.clientAddress}</div>}
                {detail.clientGstin && <div className="text-gray-500 mt-0.5">GSTIN: {detail.clientGstin}</div>}
              </div>
              <div className="text-sm text-right">
                <StatusBadge status={detail.status} />
                <div className="text-gray-500 mt-2">Dated {formatDateDdMmmYy(detail.invoiceDate)}</div>
                {detail.dueDate && <div className="text-gray-500">Due {formatDateDdMmmYy(detail.dueDate)}</div>}
              </div>
            </div>

            <div className="border border-gray-200 rounded-lg overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr>
                    <th className="table-header">Description</th>
                    <th className="table-header text-right">Qty</th>
                    <th className="table-header text-right">Rate</th>
                    <th className="table-header text-right">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {detail.lineItems.map((line, i) => (
                    <tr key={line.id ?? i}>
                      <td className="table-cell">
                        {line.description}
                        {line.hsnSac && <span className="text-xs text-gray-400 ml-2">{line.hsnSac}</span>}
                      </td>
                      <td className="table-cell text-right tabular-nums">{Number(line.quantity)}</td>
                      <td className="table-cell text-right tabular-nums">₹{formatRupeesUI(line.rate)}</td>
                      <td className="table-cell text-right tabular-nums">₹{formatRupeesUI(line.amount)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="flex justify-end">
              <div className="w-64 text-sm space-y-1">
                <div className="flex justify-between"><span className="text-gray-600">Taxable value</span><span className="tabular-nums">₹{formatRupeesUI(detail.amount)}</span></div>
                {detail.cgstAmount && <div className="flex justify-between"><span className="text-gray-600">CGST @ {Number(detail.cgstRate)}%</span><span className="tabular-nums">₹{formatRupeesUI(detail.cgstAmount)}</span></div>}
                {detail.sgstAmount && <div className="flex justify-between"><span className="text-gray-600">SGST @ {Number(detail.sgstRate)}%</span><span className="tabular-nums">₹{formatRupeesUI(detail.sgstAmount)}</span></div>}
                {detail.igstAmount && <div className="flex justify-between"><span className="text-gray-600">IGST @ {Number(detail.igstRate)}%</span><span className="tabular-nums">₹{formatRupeesUI(detail.igstAmount)}</span></div>}
                <div className="flex justify-between font-semibold border-t border-gray-200 pt-1.5 mt-1.5"><span>Total</span><span className="tabular-nums">₹{formatRupeesUI(detail.totalAmount)}</span></div>
                <div className="flex justify-between"><span className="text-gray-600">Received</span><span className="tabular-nums">₹{formatRupeesUI(detail.paidAmount)}</span></div>
                <div className="flex justify-between font-medium"><span>Balance due</span><span className="tabular-nums">₹{formatRupeesUI(num(detail.totalAmount) - num(detail.paidAmount))}</span></div>
              </div>
            </div>

            {detail.payments.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-2">Payments</h3>
                <div className="space-y-1.5">
                  {detail.payments.map((p) => (
                    <div key={p.id} className="flex items-center justify-between text-sm bg-gray-50 rounded-lg px-3 py-2">
                      <div>
                        <span className="tabular-nums font-medium">₹{formatRupeesUI(p.amount)}</span>
                        <span className="text-gray-500"> · {p.mode} · {formatDateDdMmmYy(p.paymentDate)}</span>
                        {p.reference && <span className="text-gray-400"> · {p.reference}</span>}
                      </div>
                      <button
                        className="text-xs text-red-600 hover:underline"
                        onClick={() => act(() => deletePayment(p.id), 'Remove this payment?')}
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {detail.notes && <p className="text-sm text-gray-600 whitespace-pre-line">{detail.notes}</p>}

            <div className="flex flex-wrap gap-2 justify-end border-t border-gray-200 pt-4">
              <button className="btn-secondary" onClick={() => downloadInvoicePdf(detail, letterheadFrom(settings))}>
                Download PDF
              </button>

              {detail.status === 'DRAFT' && (
                <>
                  <button className="btn-secondary" onClick={() => { setEditing(detail); setFormOpen(true); }}>Edit</button>
                  <button className="btn-primary" onClick={() => act(() => issueInvoice(detail.id))}>Issue</button>
                  <button className="btn-danger" onClick={() => act(() => deleteInvoice(detail.id), `Delete ${detail.invoiceNumber}?`)}>Delete</button>
                </>
              )}

              {(detail.status === 'SENT' || detail.status === 'PARTIALLY_PAID') && (
                <>
                  <button className="btn-secondary" onClick={() => act(() => cancelInvoice(detail.id), `Cancel ${detail.invoiceNumber}?`)}>Cancel invoice</button>
                  <button className="btn-primary" onClick={() => setPayFor(detail)}>Record payment</button>
                </>
              )}
            </div>
          </div>
        )}
      </Modal>

      {/* ── Record payment ─────────────────────────────────────────────── */}
      <PaymentModal
        invoice={payFor}
        onClose={() => setPayFor(null)}
        onSaved={(updated) => {
          setPayFor(null);
          setDetail(updated);
          load();
        }}
      />
    </div>
  );
};

const PaymentModal: React.FC<{
  invoice: Invoice | null;
  onClose: () => void;
  onSaved: (invoice: Invoice) => void;
}> = ({ invoice, onClose, onSaved }) => {
  const [amount, setAmount] = useState('');
  const [paymentDate, setPaymentDate] = useState(todayInputValue());
  const [mode, setMode] = useState<PaymentMode>('BANK');
  const [reference, setReference] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const balance = invoice ? num(invoice.totalAmount) - num(invoice.paidAmount) : 0;

  // Reset each time a different invoice is opened, and start with the balance
  // filled in — settling in full is the usual case.
  useEffect(() => {
    if (!invoice) return;
    setAmount(String(Math.round((num(invoice.totalAmount) - num(invoice.paidAmount)) * 100) / 100));
    setPaymentDate(todayInputValue());
    setMode('BANK');
    setReference('');
    setError('');
  }, [invoice]);

  const submit = async () => {
    if (!invoice) return;
    const value = Number(amount);
    if (!isFinite(value) || value <= 0) return setError('Enter an amount greater than zero');

    setBusy(true);
    try {
      const res = await addPayment(invoice.id, { amount: value, paymentDate, mode, reference: reference.trim() });
      onSaved(res.data);
    } catch (err) {
      setError(errorMessage(err, 'Could not record the payment'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal open={!!invoice} title="Record payment" onClose={onClose}>
      {invoice && (
        <div className="space-y-4">
          <p className="text-sm text-gray-600">
            {invoice.invoiceNumber} · {invoice.clientName} · balance{' '}
            <span className="font-medium tabular-nums">₹{formatRupeesUI(balance)}</span>
          </p>

          <div>
            <label className="label">Amount</label>
            <input className="input-field" type="number" min="0" step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Date</label>
              <input className="input-field" type="date" value={paymentDate} onChange={(e) => setPaymentDate(e.target.value)} />
            </div>
            <div>
              <label className="label">Mode</label>
              <select className="input-field" value={mode} onChange={(e) => setMode(e.target.value as PaymentMode)}>
                {PAYMENT_MODES.map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </div>
          </div>
          <div>
            <label className="label">Reference</label>
            <input className="input-field" value={reference} onChange={(e) => setReference(e.target.value)} placeholder="UTR / cheque number" />
          </div>

          {error && <div role="alert" className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</div>}

          <div className="flex gap-2 justify-end">
            <button className="btn-secondary" onClick={onClose} disabled={busy}>Cancel</button>
            <button className="btn-primary" onClick={submit} disabled={busy}>{busy ? 'Saving…' : 'Record'}</button>
          </div>
        </div>
      )}
    </Modal>
  );
};

export default Invoices;
