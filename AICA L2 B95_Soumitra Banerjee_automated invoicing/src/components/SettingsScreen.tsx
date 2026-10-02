import React, { useState, useEffect } from 'react';
import {
  Building2,
  Receipt,
  FileText,
  Mail,
  Save,
  CheckCircle2,
  AlertCircle,
  ToggleLeft,
  ToggleRight,
  KeyRound,
  ShieldCheck
} from 'lucide-react';
import { SystemSettings, User } from '../types';
import { systemService } from '../lib/services/systemService';

interface SettingsScreenProps {
  onRefresh: () => void;
  currentUser: User;
}

// Self-service password change: the account holder confirms their CURRENT
// password before setting a new one. Used both by an Admin changing their
// own password and by the demo/User account changing theirs.
const ChangeOwnPasswordCard: React.FC<{
  target: 'admin' | 'demo';
  accountLabel: string;
}> = ({ target, accountLabel }) => {
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (newPassword !== confirmPassword) {
      setError('New password and confirmation do not match.');
      return;
    }

    setSaving(true);
    try {
      systemService.changeLoginPassword(target, currentPassword, newPassword);
      setSuccess(`Password updated for the ${accountLabel} account.`);
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err: any) {
      setError(err.message || 'Failed to change password.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="p-4 bg-slate-50 border border-slate-200 rounded-lg space-y-3">
      <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
        Change {accountLabel} Password
      </h3>

      {error && (
        <div className="p-2.5 bg-rose-50 border border-rose-200 text-rose-700 rounded-lg text-xs flex items-center gap-2">
          <AlertCircle className="w-3.5 h-3.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}
      {success && (
        <div className="p-2.5 bg-emerald-50 border border-emerald-200 text-emerald-700 rounded-lg text-xs flex items-center gap-2">
          <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
          <span>{success}</span>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div>
          <label className="block text-[11px] font-semibold text-slate-600 mb-1">Current Password</label>
          <input
            type="password"
            required
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-[11px] font-semibold text-slate-600 mb-1">New Password</label>
          <input
            type="password"
            required
            minLength={4}
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-[11px] font-semibold text-slate-600 mb-1">Confirm New Password</label>
          <input
            type="password"
            required
            minLength={4}
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      <div className="flex justify-end">
        <button
          type="submit"
          disabled={saving}
          className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-slate-800 hover:bg-slate-900 text-white rounded-lg text-xs font-semibold shadow-xs transition disabled:opacity-50"
        >
          <KeyRound className="w-3.5 h-3.5" />
          <span>{saving ? 'Updating...' : 'Update Password'}</span>
        </button>
      </div>
    </form>
  );
};

// Admin-only reset for the OTHER account's password (no need to know its
// current value) - e.g. the Admin resetting the demo/User operator's
// password because they forgot it. Never shown to a non-Admin.
const AdminResetPasswordCard: React.FC<{
  target: 'admin' | 'demo';
  accountLabel: string;
}> = ({ target, accountLabel }) => {
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (newPassword !== confirmPassword) {
      setError('New password and confirmation do not match.');
      return;
    }

    setSaving(true);
    try {
      systemService.adminResetPassword(target, newPassword);
      setSuccess(`Password reset for the ${accountLabel} account.`);
      setNewPassword('');
      setConfirmPassword('');
    } catch (err: any) {
      setError(err.message || 'Failed to reset password.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="p-4 bg-amber-50/60 border border-amber-200 rounded-lg space-y-3">
      <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
        <ShieldCheck className="w-3.5 h-3.5 text-amber-600" />
        <span>Reset {accountLabel} Password (Admin Override)</span>
      </h3>
      <p className="text-[11px] text-slate-500 -mt-2">
        No need to know the current password - use this if the {accountLabel.toLowerCase()} account is locked out.
      </p>

      {error && (
        <div className="p-2.5 bg-rose-50 border border-rose-200 text-rose-700 rounded-lg text-xs flex items-center gap-2">
          <AlertCircle className="w-3.5 h-3.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}
      {success && (
        <div className="p-2.5 bg-emerald-50 border border-emerald-200 text-emerald-700 rounded-lg text-xs flex items-center gap-2">
          <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
          <span>{success}</span>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label className="block text-[11px] font-semibold text-slate-600 mb-1">New Password</label>
          <input
            type="password"
            required
            minLength={4}
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-[11px] font-semibold text-slate-600 mb-1">Confirm New Password</label>
          <input
            type="password"
            required
            minLength={4}
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      <div className="flex justify-end">
        <button
          type="submit"
          disabled={saving}
          className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-xs font-semibold shadow-xs transition disabled:opacity-50"
        >
          <ShieldCheck className="w-3.5 h-3.5" />
          <span>{saving ? 'Resetting...' : 'Reset Password'}</span>
        </button>
      </div>
    </form>
  );
};

export const SettingsScreen: React.FC<SettingsScreenProps> = ({ onRefresh, currentUser }) => {
  const [settings, setSettings] = useState<SystemSettings>(() => systemService.getSettings());
  const [saving, setSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    setSettings(systemService.getSettings());
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSavedSuccess(false);
    setErrorMsg('');

    try {
      systemService.updateSettings(settings);
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 4000);
      onRefresh();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">System Settings</h1>
        <p className="text-sm text-slate-500">
          Configure company profile, invoice numbering sequence, tax percentages, and email dispatch modes.
        </p>
      </div>

      {savedSuccess && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl flex items-center gap-2 text-sm font-semibold">
          <CheckCircle2 className="w-5 h-5 text-emerald-600" />
          <span>System configuration successfully updated and saved!</span>
        </div>
      )}

      {errorMsg && (
        <div className="p-4 bg-rose-50 border border-rose-200 text-rose-700 rounded-xl flex items-center gap-2 text-sm">
          <AlertCircle className="w-5 h-5" />
          <span>{errorMsg}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Company Settings */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs space-y-4">
          <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
            <Building2 className="w-5 h-5 text-blue-600" />
            <h2 className="text-base font-bold text-slate-900">Company Information (Tax Invoice Header)</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Company Legal Name</label>
              <input
                type="text"
                value={settings.companyName}
                onChange={(e) => setSettings({ ...settings, companyName: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Company Email</label>
              <input
                type="email"
                value={settings.companyEmail}
                onChange={(e) => setSettings({ ...settings, companyEmail: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">GSTIN</label>
              <input
                type="text"
                value={settings.companyGstin}
                onChange={(e) => setSettings({ ...settings, companyGstin: e.target.value.toUpperCase() })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono uppercase focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">PAN</label>
              <input
                type="text"
                value={settings.companyPan}
                onChange={(e) => setSettings({ ...settings, companyPan: e.target.value.toUpperCase() })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono uppercase focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Phone Number</label>
              <input
                type="text"
                value={settings.companyPhone}
                onChange={(e) => setSettings({ ...settings, companyPhone: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Registered Address</label>
              <input
                type="text"
                value={settings.companyAddress}
                onChange={(e) => setSettings({ ...settings, companyAddress: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>

        {/* Billing & Tax Settings */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs space-y-4">
          <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
            <Receipt className="w-5 h-5 text-blue-600" />
            <h2 className="text-base font-bold text-slate-900">Billing &amp; Tax Defaults</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Default GST / Tax Rate (%)</label>
              <input
                type="number"
                step="0.1"
                value={settings.defaultTaxRate}
                onChange={(e) => setSettings({ ...settings, defaultTaxRate: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Currency Symbol</label>
              <input
                type="text"
                value={settings.currency}
                onChange={(e) => setSettings({ ...settings, currency: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 font-bold"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Default Payment Terms</label>
              <input
                type="text"
                value={settings.paymentTerms}
                onChange={(e) => setSettings({ ...settings, paymentTerms: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Confirmation Reminder Interval (days)</label>
              <input
                type="number"
                min="1"
                step="1"
                value={settings.reminderIntervalDays}
                onChange={(e) => setSettings({ ...settings, reminderIntervalDays: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
              />
              <span className="text-[11px] text-slate-400 mt-1 block">
                Clients still awaiting confirmation get an automatic follow-up email every {settings.reminderIntervalDays || '5'} day(s) until they confirm or reject.
              </span>
            </div>
          </div>
        </div>

        {/* Invoice Numbering */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs space-y-4">
          <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
            <FileText className="w-5 h-5 text-blue-600" />
            <h2 className="text-base font-bold text-slate-900">Invoice Numbering Configuration</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Invoice Prefix</label>
              <input
                type="text"
                value={settings.invoicePrefix}
                onChange={(e) => setSettings({ ...settings, invoicePrefix: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono focus:ring-2 focus:ring-blue-500"
              />
              <span className="text-[11px] text-slate-400 mt-1 block">
                Generates numbers like <span className="font-mono text-slate-700 font-bold">{settings.invoicePrefix}2026-0001</span>
              </span>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Starting Sequence Number</label>
              <input
                type="number"
                value={settings.invoiceStartingNumber}
                onChange={(e) => setSettings({ ...settings, invoiceStartingNumber: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>

        {/* Email & SMTP Settings */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <Mail className="w-5 h-5 text-blue-600" />
              <h2 className="text-base font-bold text-slate-900">Email &amp; SMTP Configuration</h2>
            </div>

            {/* Demo Mode Toggle */}
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-slate-600">Simulated / Demo Mode:</span>
              <button
                type="button"
                onClick={() =>
                  setSettings({
                    ...settings,
                    demoMode: settings.demoMode === 'true' ? 'false' : 'true',
                  })
                }
                className="text-blue-600 focus:outline-none"
              >
                {settings.demoMode === 'true' ? (
                  <ToggleRight className="w-7 h-7 text-blue-600" />
                ) : (
                  <ToggleLeft className="w-7 h-7 text-slate-400" />
                )}
              </button>
            </div>
          </div>

          <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-900 leading-relaxed">
            <strong>Demo Mode Status: {settings.demoMode === 'true' ? 'ENABLED' : 'DISABLED'}</strong>
            <p className="mt-0.5">
              {settings.demoMode === 'true'
                ? 'Emails are captured instantly in the Email Preview / Outbox screen without needing active SMTP credentials.'
                : 'Emails will be transmitted through the configured SMTP server below.'}
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Sender Email</label>
              <input
                type="email"
                value={settings.senderEmail}
                onChange={(e) => setSettings({ ...settings, senderEmail: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">SMTP Host</label>
              <input
                type="text"
                value={settings.smtpHost}
                onChange={(e) => setSettings({ ...settings, smtpHost: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">SMTP Port</label>
              <input
                type="text"
                value={settings.smtpPort}
                onChange={(e) => setSettings({ ...settings, smtpPort: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">SMTP Username</label>
              <input
                type="text"
                value={settings.smtpUser}
                onChange={(e) => setSettings({ ...settings, smtpUser: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">SMTP Password</label>
              <input
                type="password"
                value={settings.smtpPass}
                onChange={(e) => setSettings({ ...settings, smtpPass: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>

        {/* Submit */}
        <div className="flex justify-end pt-2">
          <button
            type="submit"
            disabled={saving}
            className="inline-flex items-center gap-2 px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-semibold shadow-xs transition disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            <span>{saving ? 'Saving...' : 'Save System Settings'}</span>
          </button>
        </div>
      </form>

      {/* Login & Security - kept as its own separate forms (not nested
          inside the main settings <form> above) since each password change
          verifies and saves independently, with its own success/error
          state, rather than going through the single "Save System
          Settings" submit. */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs space-y-4">
        <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
          <KeyRound className="w-5 h-5 text-blue-600" />
          <h2 className="text-base font-bold text-slate-900">Login &amp; Security</h2>
        </div>

        <p className="text-xs text-slate-500 -mt-2">
          The admin / demo login IDs themselves stay fixed - only the password can be changed here.
        </p>

        {/* Everyone can change their own password, using their current one */}
        <ChangeOwnPasswordCard
          target={currentUser.username === 'admin' ? 'admin' : 'demo'}
          accountLabel={currentUser.username === 'admin' ? 'Admin' : 'User (demo)'}
        />

        {/* Only an Admin can reset the OTHER account's password without
            knowing it - e.g. resetting the operator's password if they're
            locked out. */}
        {currentUser.role === 'Admin' && (
          <AdminResetPasswordCard target="demo" accountLabel="User (demo)" />
        )}
      </div>
    </div>
  );
};
