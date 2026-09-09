import React, { useState, useEffect } from 'react';
import { FirmSettings } from '../types';
import {
  getActiveFirmId, getMyMemberships, getFirmMembers, rotateJoinCode,
  FirmMember,
} from '../services/db';
import { X, Settings, Building2, Users, Copy, Check, RefreshCw } from 'lucide-react';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  settings: FirmSettings;
  onSave: (settings: FirmSettings) => Promise<void>;
  onResetDb: () => Promise<void>;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen, onClose, settings, onSave, onResetDb,
}) => {
  const [formData, setFormData] = useState<FirmSettings>({ ...settings });
  const [isSaving, setIsSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);

  const [firmName, setFirmName] = useState('');
  const [role, setRole] = useState<'owner' | 'member'>('member');
  const [joinCode, setJoinCode] = useState('');
  const [members, setMembers] = useState<FirmMember[]>([]);
  const [copied, setCopied] = useState(false);
  const [rotating, setRotating] = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    setFormData({ ...settings });
    const firmId = getActiveFirmId();
    if (!firmId) return;
    getMyMemberships().then((ms) => {
      const m = ms.find((x) => x.firmId === firmId);
      if (m) { setFirmName(m.firmName); setRole(m.role); setJoinCode(m.joinCode); }
    }).catch(() => {});
    getFirmMembers(firmId).then(setMembers).catch(() => {});
  }, [isOpen, settings]);

  if (!isOpen) return null;

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    try {
      await onSave(formData);
      setSavedSuccess(true);
      setTimeout(() => { setSavedSuccess(false); onClose(); }, 800);
    } finally {
      setIsSaving(false);
    }
  };

  const copyCode = async () => {
    try { await navigator.clipboard.writeText(joinCode); setCopied(true); setTimeout(() => setCopied(false), 2000); }
    catch { /* ignore */ }
  };

  const rotate = async () => {
    const firmId = getActiveFirmId();
    if (!firmId) return;
    setRotating(true);
    try { setJoinCode(await rotateJoinCode(firmId)); }
    catch (e: any) { alert(e.message); }
    finally { setRotating(false); }
  };

  const inputCls = 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-[#4338CA]';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4">
      <div className="flex max-h-[90vh] w-full max-w-xl flex-col overflow-hidden rounded-xl bg-white shadow-2xl">
        <div className="flex shrink-0 items-center justify-between border-b border-slate-200 bg-slate-50 px-6 py-4">
          <div className="flex items-center gap-2">
            <Settings className="h-5 w-5 text-[#4338CA]" />
            <h2 className="text-sm font-bold text-slate-900">Firm settings &amp; team</h2>
          </div>
          <button onClick={onClose} className="rounded-lg p-1 text-slate-400 hover:bg-slate-200">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSave} className="flex-1 space-y-5 overflow-y-auto p-6 text-xs">

          {/* ── Team ─────────────────────────────────────────── */}
          <div className="space-y-2.5 rounded-xl border border-slate-200 bg-slate-50 p-3.5">
            <div className="flex items-center gap-1.5 font-bold text-slate-900">
              <Users className="h-4 w-4 text-[#4338CA]" /> Team — {firmName || 'your firm'}
            </div>
            <p className="text-[11px] text-slate-600">
              Everyone with this join code can create an account and join the firm, and then sees the same clients and notices.
            </p>
            <div className="flex items-center gap-2">
              <code className="flex-1 rounded-lg border border-slate-300 bg-white px-3 py-2 font-mono text-sm tracking-widest text-slate-800">
                {joinCode || '········'}
              </code>
              <button type="button" onClick={copyCode}
                className="flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-2.5 py-2 font-semibold text-slate-600 hover:bg-slate-100">
                {copied ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : <Copy className="h-3.5 w-3.5" />}
              </button>
              {role === 'owner' && (
                <button type="button" onClick={rotate} disabled={rotating} title="Generate a new code"
                  className="flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-2.5 py-2 font-semibold text-slate-600 hover:bg-slate-100 disabled:opacity-50">
                  <RefreshCw className={`h-3.5 w-3.5 ${rotating ? 'animate-spin' : ''}`} />
                </button>
              )}
            </div>
            {members.length > 0 && (
              <div className="space-y-1 pt-1">
                {members.map((m) => (
                  <div key={m.userId} className="flex items-center justify-between text-[11px] text-slate-600">
                    <span>{m.email || m.userId.slice(0, 8)}</span>
                    <span className="rounded-full bg-slate-200 px-2 py-0.5 font-medium">{m.role}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* ── Extraction note ──────────────────────────────── */}
          <p className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-[11px] text-slate-600">
            Notice extraction: use <strong>Add Notice → Use Claude.ai</strong> (free with a Claude.ai subscription).
            Automatic extraction runs only if the workspace's Anthropic key is set as a server secret — see SUPABASE-SETUP.md.
          </p>

          {/* ── Firm letterhead ──────────────────────────────── */}
          <div className="space-y-3">
            <div className="flex items-center gap-1.5 font-bold text-gray-800">
              <Building2 className="h-4 w-4 text-gray-500" />
              <span>Firm details (used on the letterhead of generated replies)</span>
            </div>
            <div>
              <label className="mb-1 block font-semibold text-gray-700">Firm name</label>
              <input type="text" value={formData.caFirmName}
                onChange={(e) => setFormData({ ...formData, caFirmName: e.target.value })} className={inputCls} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1 block font-semibold text-gray-700">Practitioner name</label>
                <input type="text" value={formData.caName}
                  onChange={(e) => setFormData({ ...formData, caName: e.target.value })} className={inputCls} />
              </div>
              <div>
                <label className="mb-1 block font-semibold text-gray-700">ICAI membership no.</label>
                <input type="text" value={formData.membershipNo}
                  onChange={(e) => setFormData({ ...formData, membershipNo: e.target.value })} className={inputCls} />
              </div>
            </div>
            <div>
              <label className="mb-1 block font-semibold text-gray-700">Office address</label>
              <input type="text" value={formData.firmAddress}
                onChange={(e) => setFormData({ ...formData, firmAddress: e.target.value })} className={inputCls} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1 block font-semibold text-gray-700">Contact email</label>
                <input type="email" value={formData.contactEmail}
                  onChange={(e) => setFormData({ ...formData, contactEmail: e.target.value })} className={inputCls} />
              </div>
              <div>
                <label className="mb-1 block font-semibold text-gray-700">Contact phone</label>
                <input type="text" value={formData.contactPhone}
                  onChange={(e) => setFormData({ ...formData, contactPhone: e.target.value })} className={inputCls} />
              </div>
            </div>
          </div>

          {/* ── Danger zone ──────────────────────────────────── */}
          <div className="flex items-center justify-between gap-3 rounded-xl border border-red-200 bg-red-50 p-3.5">
            <div>
              <div className="text-xs font-bold text-red-900">Clear all firm data</div>
              <div className="mt-0.5 text-[11px] text-red-700">
                Permanently deletes every client, notice, reconciliation, document and discussion for this firm — for everyone.
              </div>
            </div>
            <button
              type="button"
              onClick={async () => {
                if (confirm('This permanently deletes ALL of this firm’s clients, notices and records, for every member. This cannot be undone. Continue?')) {
                  await onResetDb();
                  onClose();
                }
              }}
              className="shrink-0 whitespace-nowrap rounded-lg bg-red-600 px-4 py-2 text-[11px] font-bold text-white hover:bg-red-700"
            >
              Clear all data
            </button>
          </div>

          <div className="flex justify-end gap-2">
            <button type="button" onClick={onClose}
              className="rounded-lg px-4 py-2 font-bold text-gray-600 hover:bg-gray-100">Cancel</button>
            <button type="submit" disabled={isSaving}
              className="rounded-lg bg-[#4338CA] px-5 py-2 font-bold text-white shadow-xs hover:bg-[#3730A3]">
              {savedSuccess ? 'Saved' : isSaving ? 'Saving…' : 'Save settings'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
