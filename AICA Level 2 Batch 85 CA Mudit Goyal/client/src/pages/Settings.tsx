import React, { useEffect, useState } from 'react';
import { TaxType, changePassword, updateSettings } from '../api';
import { useAuth } from '../contexts/AuthContext';
import { useSettings } from '../contexts/SettingsContext';
import { errorMessage } from '../utils/errorMessage';
import { formatDateDdMmmYy } from '../utils/format';

const GST_RATES = [5, 12, 18, 28];

/** A saved / failed banner that clears itself, so the page never nags. */
const Flash: React.FC<{ tone: 'ok' | 'error'; children: React.ReactNode }> = ({ tone, children }) => (
  <div
    role={tone === 'error' ? 'alert' : 'status'}
    className={`text-sm rounded-lg px-3 py-2 border ${
      tone === 'ok'
        ? 'text-green-800 bg-green-50 border-green-200'
        : 'text-red-700 bg-red-50 border-red-200'
    }`}
  >
    {children}
  </div>
);

const Settings: React.FC = () => {
  const { isAdmin } = useAuth();

  return (
    <div className="space-y-6 max-w-3xl">
      <h1 className="text-xl font-semibold text-gray-900">Settings</h1>

      {isAdmin ? (
        <>
          <FirmProfile />
          <InvoicingDefaults />
        </>
      ) : (
        <p className="text-sm text-gray-500">
          Firm and invoicing settings are managed by an administrator.
        </p>
      )}

      <MyAccount />
    </div>
  );
};

// ── Firm profile ─────────────────────────────────────────────────────────────

const FirmProfile: React.FC = () => {
  const { settings, refresh } = useSettings();
  const [form, setForm] = useState({
    firmName: '', firmAddress: '', firmGstin: '', firmEmail: '', firmPhone: '',
  });
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  // Seeded from the loaded settings rather than held as initial state — the
  // fetch finishes after the first render, so initial state would be blank.
  useEffect(() => {
    if (!settings) return;
    setForm({
      firmName: settings.firmName,
      firmAddress: settings.firmAddress,
      firmGstin: settings.firmGstin,
      firmEmail: settings.firmEmail,
      firmPhone: settings.firmPhone,
    });
  }, [settings]);

  const set = (patch: Partial<typeof form>) => {
    setForm((prev) => ({ ...prev, ...patch }));
    setSaved(false);
  };

  const save = async () => {
    if (!settings) return;
    setError('');
    setBusy(true);
    try {
      // The whole settings row is sent: the endpoint validates and replaces it
      // as one object, so posting only the changed half would blank the rest.
      await updateSettings({
        ...settings,
        ...form,
        defaultGstRate: Number(settings.defaultGstRate),
      });
      await refresh();
      setSaved(true);
    } catch (err) {
      setError(errorMessage(err, 'Could not save the firm profile'));
    } finally {
      setBusy(false);
    }
  };

  if (!settings) return <div className="card text-sm text-gray-500">Loading settings…</div>;

  return (
    <section className="card space-y-4">
      <div>
        <h2 className="font-semibold text-gray-900">Firm profile</h2>
        <p className="text-sm text-gray-500 mt-0.5">Printed as the letterhead on every invoice PDF.</p>
      </div>

      <div className="grid sm:grid-cols-2 gap-3">
        <div className="sm:col-span-2">
          <label className="label" htmlFor="firmName">Firm name *</label>
          <input id="firmName" className="input-field" value={form.firmName} onChange={(e) => set({ firmName: e.target.value })} />
        </div>
        <div className="sm:col-span-2">
          <label className="label" htmlFor="firmAddress">Address</label>
          <textarea id="firmAddress" className="input-field" rows={2} value={form.firmAddress} onChange={(e) => set({ firmAddress: e.target.value })} />
        </div>
        <div>
          <label className="label" htmlFor="firmGstin">GSTIN</label>
          <input
            id="firmGstin"
            className="input-field uppercase"
            value={form.firmGstin}
            onChange={(e) => set({ firmGstin: e.target.value.toUpperCase() })}
          />
        </div>
        <div>
          <label className="label" htmlFor="firmPhone">Phone</label>
          <input id="firmPhone" className="input-field" value={form.firmPhone} onChange={(e) => set({ firmPhone: e.target.value })} />
        </div>
        <div className="sm:col-span-2">
          <label className="label" htmlFor="firmEmail">Billing email</label>
          <input id="firmEmail" type="email" className="input-field" value={form.firmEmail} onChange={(e) => set({ firmEmail: e.target.value })} />
        </div>
      </div>

      {error && <Flash tone="error">{error}</Flash>}
      {saved && <Flash tone="ok">Firm profile saved.</Flash>}

      <div className="flex justify-end">
        <button className="btn-primary" onClick={save} disabled={busy}>
          {busy ? 'Saving…' : 'Save firm profile'}
        </button>
      </div>
    </section>
  );
};

// ── Invoicing defaults ───────────────────────────────────────────────────────

const InvoicingDefaults: React.FC = () => {
  const { settings, refresh } = useSettings();
  const [prefix, setPrefix] = useState('');
  const [taxType, setTaxType] = useState<TaxType>('CGST_SGST');
  const [gstRate, setGstRate] = useState(18);
  const [termDays, setTermDays] = useState(30);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!settings) return;
    setPrefix(settings.invoicePrefix);
    setTaxType(settings.defaultTaxType);
    setGstRate(Number(settings.defaultGstRate));
    setTermDays(settings.defaultPaymentTermDays);
  }, [settings]);

  const save = async () => {
    if (!settings) return;
    setError('');
    setBusy(true);
    try {
      await updateSettings({
        ...settings,
        invoicePrefix: prefix.trim(),
        defaultTaxType: taxType,
        defaultGstRate: gstRate,
        defaultPaymentTermDays: termDays,
      });
      await refresh();
      setSaved(true);
    } catch (err) {
      setError(errorMessage(err, 'Could not save the invoicing defaults'));
    } finally {
      setBusy(false);
    }
  };

  if (!settings) return null;

  return (
    <section className="card space-y-4">
      <div>
        <h2 className="font-semibold text-gray-900">Invoicing defaults</h2>
        <p className="text-sm text-gray-500 mt-0.5">
          Where a new invoice starts. Changing these never alters an invoice that already exists.
        </p>
      </div>

      <div className="grid sm:grid-cols-2 gap-3">
        <div>
          <label className="label" htmlFor="prefix">Invoice number prefix</label>
          <input
            id="prefix"
            className="input-field"
            value={prefix}
            maxLength={12}
            onChange={(e) => {
              setPrefix(e.target.value);
              setSaved(false);
            }}
          />
          <p className="text-xs text-gray-500 mt-1">
            Next number will look like{' '}
            <span className="font-medium text-gray-700">{(prefix.trim() || 'MGSG')}/26-27/0007</span>
          </p>
        </div>
        <div>
          <label className="label" htmlFor="termDays">Payment terms</label>
          <div className="flex items-center gap-2">
            <input
              id="termDays"
              type="number"
              min={0}
              max={365}
              className="input-field"
              value={termDays}
              onChange={(e) => {
                setTermDays(Number(e.target.value));
                setSaved(false);
              }}
            />
            <span className="text-sm text-gray-500 whitespace-nowrap">days</span>
          </div>
          <p className="text-xs text-gray-500 mt-1">Sets the due date on a new invoice.</p>
        </div>
        <div>
          <label className="label" htmlFor="defaultTax">Default tax</label>
          <select
            id="defaultTax"
            className="input-field"
            value={taxType}
            onChange={(e) => {
              setTaxType(e.target.value as TaxType);
              setSaved(false);
            }}
          >
            <option value="CGST_SGST">CGST + SGST (within the state)</option>
            <option value="IGST">IGST (inter-state)</option>
            <option value="NONE">No GST</option>
          </select>
        </div>
        <div>
          <label className="label" htmlFor="defaultRate">Default GST rate</label>
          <select
            id="defaultRate"
            className="input-field"
            value={gstRate}
            disabled={taxType === 'NONE'}
            onChange={(e) => {
              setGstRate(Number(e.target.value));
              setSaved(false);
            }}
          >
            {GST_RATES.map((r) => (
              <option key={r} value={r}>{r}%</option>
            ))}
          </select>
        </div>
      </div>

      {error && <Flash tone="error">{error}</Flash>}
      {saved && <Flash tone="ok">Invoicing defaults saved.</Flash>}

      <div className="flex items-center justify-between gap-3">
        <span className="text-xs text-gray-400">Last changed {formatDateDdMmmYy(settings.updatedAt)}</span>
        <button className="btn-primary" onClick={save} disabled={busy}>
          {busy ? 'Saving…' : 'Save defaults'}
        </button>
      </div>
    </section>
  );
};

// ── My account ───────────────────────────────────────────────────────────────

const MyAccount: React.FC = () => {
  const { user } = useAuth();
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const save = async () => {
    setError('');
    setSaved(false);
    if (next.length < 8) return setError('The new password must be at least 8 characters');
    // Checked here rather than server-side: the confirmation box exists to
    // catch a typo before it becomes a password nobody knows.
    if (next !== confirm) return setError('The two new passwords do not match');
    if (next === current) return setError('The new password must be different from the current one');

    setBusy(true);
    try {
      await changePassword(current, next);
      setCurrent('');
      setNext('');
      setConfirm('');
      setSaved(true);
    } catch (err) {
      setError(errorMessage(err, 'Could not change the password'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="card space-y-4">
      <div>
        <h2 className="font-semibold text-gray-900">My account</h2>
        <p className="text-sm text-gray-500 mt-0.5">
          Signed in as {user?.staffName ?? user?.email} · {user?.role}
        </p>
      </div>

      <div className="grid sm:grid-cols-2 gap-3">
        <div className="sm:col-span-2">
          <label className="label" htmlFor="currentPassword">Current password</label>
          <input
            id="currentPassword"
            type="password"
            className="input-field"
            autoComplete="current-password"
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
          />
        </div>
        <div>
          <label className="label" htmlFor="newPassword">New password</label>
          <input
            id="newPassword"
            type="password"
            className="input-field"
            autoComplete="new-password"
            value={next}
            onChange={(e) => setNext(e.target.value)}
          />
        </div>
        <div>
          <label className="label" htmlFor="confirmPassword">Confirm new password</label>
          <input
            id="confirmPassword"
            type="password"
            className="input-field"
            autoComplete="new-password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
          />
        </div>
      </div>

      <p className="text-xs text-gray-500">At least 8 characters.</p>

      {error && <Flash tone="error">{error}</Flash>}
      {saved && <Flash tone="ok">Password changed. It applies the next time you sign in.</Flash>}

      <div className="flex justify-end">
        <button className="btn-primary" onClick={save} disabled={busy || !current || !next}>
          {busy ? 'Saving…' : 'Change password'}
        </button>
      </div>
    </section>
  );
};

export default Settings;
