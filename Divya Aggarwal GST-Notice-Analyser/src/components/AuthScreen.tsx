import React, { useState } from 'react';
import { Building2, LogIn, UserPlus, ArrowRight, KeyRound } from 'lucide-react';
import {
  signIn, signUp, createFirm, joinFirm, getMyMemberships, setActiveFirm,
  FirmMembership,
} from '../services/db';

// ── Shell ────────────────────────────────────────────────────────────────────
const Shell: React.FC<{ title: string; subtitle: string; children: React.ReactNode }> = ({
  title, subtitle, children,
}) => (
  <div className="flex min-h-full items-center justify-center bg-[#F8FAFC] p-6">
    <div className="w-full max-w-sm">
      <div className="mb-6 flex items-center gap-2.5">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#4338CA] text-sm font-bold text-white">CA</div>
        <div>
          <div className="text-[10px] font-bold uppercase tracking-wider text-[#4338CA]">GST Notice Analyser</div>
          <div className="text-xs font-semibold text-slate-700">CA Workstation</div>
        </div>
      </div>
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="text-base font-bold text-slate-900">{title}</h1>
        <p className="mt-1 text-xs text-slate-500">{subtitle}</p>
        <div className="mt-5">{children}</div>
      </div>
    </div>
  </div>
);

const field =
  'w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-[#4338CA] focus:outline-none';
const primaryBtn =
  'flex w-full items-center justify-center gap-2 rounded-lg bg-[#4338CA] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#3730A3] disabled:opacity-50';
const errBox = 'rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-800';
const okBox = 'rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-800';

// ── Sign in / sign up ────────────────────────────────────────────────────────
export const AuthScreen: React.FC<{ onSignedIn: () => void }> = ({ onSignedIn }) => {
  const [mode, setMode] = useState<'in' | 'up'>('in');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true); setErr(null); setMsg(null);
    try {
      if (mode === 'in') {
        await signIn(email, password);
        onSignedIn();
      } else {
        const { needsConfirmation } = await signUp(email, password);
        if (needsConfirmation) {
          setMsg('Account created. Check your email to confirm, then sign in.');
          setMode('in');
        } else {
          onSignedIn();
        }
      }
    } catch (e2: any) {
      setErr(e2.message || 'Something went wrong.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <Shell
      title={mode === 'in' ? 'Sign in' : 'Create an account'}
      subtitle={mode === 'in' ? 'Access your firm’s workspace.' : 'One account per person; you’ll join or create a firm next.'}
    >
      <form onSubmit={submit} className="space-y-3">
        <div className="space-y-1">
          <label className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Email</label>
          <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
            autoComplete="email" className={field} />
        </div>
        <div className="space-y-1">
          <label className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Password</label>
          <input type="password" required minLength={6} value={password} onChange={(e) => setPassword(e.target.value)}
            autoComplete={mode === 'in' ? 'current-password' : 'new-password'} className={field} />
        </div>
        {err && <div className={errBox}>{err}</div>}
        {msg && <div className={okBox}>{msg}</div>}
        <button type="submit" disabled={busy} className={primaryBtn}>
          {busy ? 'Please wait…' : mode === 'in'
            ? <><LogIn className="h-4 w-4" /> Sign in</>
            : <><UserPlus className="h-4 w-4" /> Create account</>}
        </button>
      </form>
      <button
        onClick={() => { setMode(mode === 'in' ? 'up' : 'in'); setErr(null); setMsg(null); }}
        className="mt-3 w-full text-center text-xs font-medium text-[#4338CA] hover:underline"
      >
        {mode === 'in' ? 'New here? Create an account' : 'Already have an account? Sign in'}
      </button>
    </Shell>
  );
};

// ── Choose / create / join a firm ────────────────────────────────────────────
export const FirmPicker: React.FC<{ onReady: () => void }> = ({ onReady }) => {
  const [memberships, setMemberships] = useState<FirmMembership[] | null>(null);
  const [tab, setTab] = useState<'pick' | 'create' | 'join'>('pick');
  const [name, setName] = useState('');
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  React.useEffect(() => {
    getMyMemberships()
      .then((m) => { setMemberships(m); setTab(m.length ? 'pick' : 'create'); })
      .catch((e) => { setErr(e.message); setMemberships([]); setTab('create'); });
  }, []);

  const choose = (firmId: string) => { setActiveFirm(firmId); onReady(); };

  const doCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true); setErr(null);
    try { await createFirm(name); onReady(); }
    catch (e2: any) { setErr(e2.message); setBusy(false); }
  };

  const doJoin = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true); setErr(null);
    try { await joinFirm(code); onReady(); }
    catch (e2: any) { setErr(e2.message); setBusy(false); }
  };

  if (memberships === null) {
    return <Shell title="Loading…" subtitle="Fetching your firms."><div /></Shell>;
  }

  return (
    <Shell title="Your firm" subtitle="Work is shared with everyone in the same firm.">
      <div className="mb-4 flex gap-1 rounded-lg bg-slate-100 p-1 text-xs font-semibold">
        {memberships.length > 0 && (
          <button onClick={() => setTab('pick')}
            className={`flex-1 rounded-md px-2 py-1.5 ${tab === 'pick' ? 'bg-white text-[#3730A3] shadow-sm' : 'text-slate-500'}`}>
            Choose
          </button>
        )}
        <button onClick={() => setTab('create')}
          className={`flex-1 rounded-md px-2 py-1.5 ${tab === 'create' ? 'bg-white text-[#3730A3] shadow-sm' : 'text-slate-500'}`}>
          Create
        </button>
        <button onClick={() => setTab('join')}
          className={`flex-1 rounded-md px-2 py-1.5 ${tab === 'join' ? 'bg-white text-[#3730A3] shadow-sm' : 'text-slate-500'}`}>
          Join
        </button>
      </div>

      {err && <div className={`${errBox} mb-3`}>{err}</div>}

      {tab === 'pick' && (
        <div className="space-y-2">
          {memberships.map((m) => (
            <button key={m.firmId} onClick={() => choose(m.firmId)}
              className="flex w-full items-center justify-between rounded-lg border border-slate-200 px-3 py-2.5 text-left hover:border-[#4338CA] hover:bg-indigo-50/40">
              <span className="flex items-center gap-2 text-sm font-semibold text-slate-800">
                <Building2 className="h-4 w-4 text-[#4338CA]" /> {m.firmName}
              </span>
              <span className="flex items-center gap-1 text-[11px] text-slate-400">
                {m.role} <ArrowRight className="h-3.5 w-3.5" />
              </span>
            </button>
          ))}
        </div>
      )}

      {tab === 'create' && (
        <form onSubmit={doCreate} className="space-y-3">
          <div className="space-y-1">
            <label className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Firm name</label>
            <input required value={name} onChange={(e) => setName(e.target.value)}
              placeholder="e.g. V. K. Sharma & Associates" className={field} />
          </div>
          <button type="submit" disabled={busy || !name.trim()} className={primaryBtn}>
            <Building2 className="h-4 w-4" /> {busy ? 'Creating…' : 'Create firm'}
          </button>
          <p className="text-[11px] text-slate-500">You become the owner and get a join code to invite your team.</p>
        </form>
      )}

      {tab === 'join' && (
        <form onSubmit={doJoin} className="space-y-3">
          <div className="space-y-1">
            <label className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Join code</label>
            <input required value={code} onChange={(e) => setCode(e.target.value.toUpperCase())}
              placeholder="8-character code from your firm" className={`${field} font-mono tracking-widest`} />
          </div>
          <button type="submit" disabled={busy || !code.trim()} className={primaryBtn}>
            <KeyRound className="h-4 w-4" /> {busy ? 'Joining…' : 'Join firm'}
          </button>
          <p className="text-[11px] text-slate-500">Ask the firm owner for the code (Settings &rarr; Team).</p>
        </form>
      )}
    </Shell>
  );
};
