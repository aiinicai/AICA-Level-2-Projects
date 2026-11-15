import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../api';
import { THEMES, applyTheme, storedTheme, type ThemeId } from '../themes';

interface AssistantSettings { allowGeneral: boolean; model: string; baseUrl: string; online: boolean; modelLoaded: boolean; message: string }

/** Themes and the assistant. Nothing here is company data. */
export function AppSettings() {
  const [theme, setTheme] = useState<ThemeId>(storedTheme());
  const qc = useQueryClient();
  const s = useQuery<AssistantSettings>({ queryKey: ['assistant-settings'], queryFn: () => api('/api/settings/assistant') });
  const [err, setErr] = useState<string | null>(null);
  const save = async (patch: Partial<AssistantSettings>) => {
    setErr(null);
    try { await api('/api/settings/assistant', { method: 'PUT', body: patch }); await qc.invalidateQueries({ queryKey: ['assistant-settings'] }); } catch (e: any) { setErr(e.message); }
  };
  return (
    <div>
      <h1>Appearance &amp; assistant</h1>
      <div className="card">
        <h2>Colour theme</h2>
        <div className="themes">
          {THEMES.map((t) => (
            <button key={t.id} type="button" className={`theme-card${t.id === theme ? ' on' : ''}`} aria-pressed={t.id === theme} onClick={() => { setTheme(t.id); applyTheme(t.id); }}>
              <span className="swatch big" aria-hidden="true">{t.swatch.map((c) => <i key={c} style={{ background: c }} />)}</span>
              <b>{t.label}</b><small>{t.note}</small>
            </button>
          ))}
        </div>
      </div>
      <LicenceCard />
      <div className="card mt">
        <h2>Assistant (LM Studio)</h2>
        <p className="small muted">The chat button uses a language model running on this PC through LM Studio. It only rewrites figures the app has already calculated; it never calculates anything. Nothing is sent outside this computer.</p>
        {s.data && (
          <>
            <div className={`banner ${s.data.online && s.data.modelLoaded ? 'info' : 'warn'}`} role="status">
              {s.data.online && s.data.modelLoaded ? `● Connected to ${s.data.baseUrl}, model ${s.data.model} is available.` : s.data.message}
              <button className="btn sm" style={{ marginLeft: 12 }} onClick={() => qc.invalidateQueries({ queryKey: ['assistant-settings'] })}>Check again</button>
            </div>
            <label className="row mt">
              <input type="checkbox" checked={s.data.allowGeneral} onChange={(e) => save({ allowGeneral: e.target.checked })} />
              <span><b>Allow general questions</b><br /><span className="small muted">Off (default): answers only about the open company's data. On: other questions are answered too, and clearly labelled “General knowledge — not from your company data”.</span></span>
            </label>
            <div className="grid g3 mt">
              <label className="field">Model name in LM Studio<input defaultValue={s.data.model} onBlur={(e) => e.target.value !== s.data!.model && save({ model: e.target.value })} /></label>
              <label className="field">LM Studio address (this PC only)<input defaultValue={s.data.baseUrl} onBlur={(e) => e.target.value !== s.data!.baseUrl && save({ baseUrl: e.target.value })} /></label>
            </div>
          </>
        )}
        {err && <div className="banner error mt" role="alert">{err}</div>}
      </div>
    </div>
  );
}

interface LicenceInfo {
  status: 'licensed' | 'evaluation' | 'expired' | 'wrong_machine' | 'invalid'; message: string; licensee: string | null; expires: string | null;
  companies: number | null; edition: string | null; machineId: string; evaluationLimits: { companies: number; monthsPerSync: number; importMB: number } | null;
}

/** Licence key entry. The key is checked on this PC; nothing is sent anywhere. */
function LicenceCard() {
  const qc = useQueryClient();
  const q = useQuery<LicenceInfo>({ queryKey: ['licence'], queryFn: () => api('/api/licence') });
  const [key, setKey] = useState('');
  const [err, setErr] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const l = q.data;
  const activate = async () => {
    setErr(null);
    try { await api('/api/licence', { method: 'POST', body: { key } }); setKey(''); await qc.invalidateQueries({ queryKey: ['licence'] }); } catch (e: any) { setErr(e.message); }
  };
  const remove = async () => {
    if (!confirm('Remove the licence key from this PC? The app goes back to evaluation mode.')) return;
    await api('/api/licence', { method: 'DELETE' });
    await qc.invalidateQueries({ queryKey: ['licence'] });
  };
  return (
    <div className="card mt">
      <h2>Licence</h2>
      {l && (
        <>
          <div className={`banner ${l.status === 'licensed' ? 'info' : 'warn'}`} role="status">
            {l.status === 'licensed'
              ? <>● Licensed to <b>{l.licensee}</b>{l.expires ? ` until ${l.expires}` : ' (no expiry)'}{l.companies ? ` · up to ${l.companies} real companies` : ' · unlimited companies'}</>
              : l.message}
          </div>
          {l.status !== 'licensed' && l.evaluationLimits && (
            <p className="small muted mt">Evaluation mode: the fictional demo company is unlimited. Real data is limited to {l.evaluationLimits.companies} company, {l.evaluationLimits.monthsPerSync} months per Tally sync and {l.evaluationLimits.importMB} MB per imported file. This project is for learning and evaluation; commercial use needs a licence from the author.</p>
          )}
          <div className="row mt">
            <span className="small muted">This computer's ID:</span>
            <code>{l.machineId}</code>
            <button className="btn sm" onClick={() => { navigator.clipboard?.writeText(l.machineId); setCopied(true); }}>{copied ? 'Copied' : 'Copy'}</button>
          </div>
          <p className="small muted">Send this ID to the author to get a key that works on this PC only. The ID is a one-way fingerprint; nothing else about your PC is read.</p>
          <label className="field mt">Licence key
            <textarea rows={3} value={key} onChange={(e) => setKey(e.target.value)} placeholder="Paste the licence key here" style={{ fontFamily: 'monospace' }} />
          </label>
          <div className="row mt">
            <button className="btn" disabled={!key.trim()} onClick={activate}>Activate</button>
            {l.status === 'licensed' && <button className="btn" onClick={remove}>Remove key</button>}
          </div>
          {err && <div className="banner error mt" role="alert">{err}</div>}
        </>
      )}
    </div>
  );
}

export function ComingSoon({ title }: { title: string }) {
  return (
    <div>
      <h1>{title}</h1>
      <div className="card"><p>This screen comes in a later version of Tally MIS. The overview, profit &amp; loss, receivables &amp; payables and the assistant are ready now.</p></div>
    </div>
  );
}
