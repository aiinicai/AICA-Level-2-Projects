import React from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { ShieldCheck, Copy, Check, KeyRound } from 'lucide-react';
import type { LicenseInfo } from '../lib/api';
import { apiActivate } from '../lib/api';

const REASON_TEXT: Record<string, string> = {
  'no-key': '',
  'machine-mismatch': 'This key was generated for a different computer. Please check the Hardware ID and request a new key.',
  'expired': 'This license key has expired. Please contact your software provider for a renewal key.',
  'malformed': 'Invalid key format. The key looks like: CMA-XXXX-XXXX-XXXX-XXXX',
  'bad-license-file': 'The stored license file is corrupted. Please re-activate.',
  'no-secret': 'Server is missing its license configuration — reinstall the application.',
  'offline': 'Could not reach the server.',
};

export function LicenseGate({ info, onActivated }: { info: LicenseInfo; onActivated: (li: LicenseInfo) => void }) {
  const [key, setKey] = React.useState('');
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(
    info.reason && REASON_TEXT[info.reason] ? REASON_TEXT[info.reason] : (info.reason && info.reason !== 'no-key' ? info.reason : null)
  );
  const [copied, setCopied] = React.useState(false);

  const copy = async () => {
    try { await navigator.clipboard.writeText(info.hardwareId); } catch { /* clipboard may be blocked on http LAN */ }
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  const activate = async () => {
    if (!key.trim()) return;
    setBusy(true);
    setError(null);
    const res = await apiActivate(key.trim());
    setBusy(false);
    if (res.ok) {
      const health = await fetch('/api/health').then(r => r.json()).catch(() => null);
      if (health) onActivated(health);
      else window.location.reload();
    } else {
      setError(REASON_TEXT[res.reason || ''] || res.reason || 'Activation failed.');
    }
  };

  return (
    <div className="bg-slate-950 min-h-screen text-slate-200 font-sans antialiased flex items-center justify-center px-4">
      <Card className="bg-slate-900 border-slate-800 rounded-3xl shadow-2xl max-w-xl w-full">
        <CardContent className="pt-8 pb-8 px-8 space-y-6">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-indigo-600 text-white rounded-2xl flex items-center justify-center shadow-lg shadow-indigo-500/30 shrink-0">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight font-display">Activation Required</h1>
              <p className="text-xs text-slate-400">CMA Pro Builder is licensed to one server computer.</p>
            </div>
          </div>

          <div className="bg-slate-950 border border-slate-800 rounded-2xl p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">Hardware ID</span>
              <Button variant="ghost" size="sm" className="h-7 text-xs text-indigo-300" onClick={copy}>
                {copied ? <Check className="h-3.5 w-3.5 mr-1" /> : <Copy className="h-3.5 w-3.5 mr-1" />}
                {copied ? 'Copied!' : 'Copy'}
              </Button>
            </div>
            <code className="block text-center text-2xl text-indigo-300 font-mono tracking-widest">{info.hardwareId}</code>
            <p className="text-[11px] text-slate-500 text-center">
              Send this Hardware ID to your software provider to receive a license key.
            </p>
          </div>

          <div className="space-y-2">
            <label className="text-[11px] font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
              <KeyRound className="h-3.5 w-3.5" /> License Key
            </label>
            <Input
              value={key}
              onChange={e => setKey(e.target.value.toUpperCase())}
              onKeyDown={e => { if (e.key === 'Enter') activate(); }}
              placeholder="CMA-XXXX-XXXX-XXXX-XXXX"
              className="bg-slate-950 border-slate-700 text-center font-mono tracking-widest text-lg h-12"
              maxLength={20}
            />
            {error && <p className="text-xs text-red-400 bg-red-950/40 border border-red-900/60 rounded-lg px-3 py-2">{error}</p>}
            <Button onClick={activate} disabled={busy || !key.trim()} className="w-full bg-indigo-600 hover:bg-indigo-500">
              {busy ? 'Activating…' : 'Activate License'}
            </Button>
          </div>

          <p className="text-center text-[11px] text-slate-600">Developed by Kuber R Purkar (7218973049)</p>
        </CardContent>
      </Card>
    </div>
  );
}
