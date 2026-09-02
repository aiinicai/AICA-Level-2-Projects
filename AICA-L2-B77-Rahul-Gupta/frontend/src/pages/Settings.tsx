import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Sparkles, FileText, User2, Bell, ShieldCheck, Settings2, Eye, EyeOff,
  ChevronRight, Loader2, CheckCircle2, KeyRound, Link as LinkIcon,
} from "lucide-react";
import { api } from "../services/api";
import { CardTitle, Spinner, Toggle } from "../components/ui";
import type { AIConfig, SettingsData } from "../types";

export default function SettingsPage() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["settings"],
    queryFn: () => api.get<SettingsData>("/api/settings"),
  });

  const [keyInput, setKeyInput] = useState("");
  const [showKeyField, setShowKeyField] = useState(false);
  const [profile, setProfile] = useState({ name: "", role: "", email: "", timezone: "" });
  const [statusMsg, setStatusMsg] = useState("");

  useEffect(() => {
    if (data) setProfile({
      name: data.profile.name, role: data.profile.role,
      email: data.profile.email, timezone: data.profile.timezone,
    });
  }, [data]);

  const invalidate = () => qc.invalidateQueries({ queryKey: ["settings"] });

  const saveAI = useMutation({
    mutationFn: (body: Partial<AIConfig> & { api_key?: string }) => api.put<AIConfig>("/api/settings/ai", body),
    onSuccess: (cfg) => {
      invalidate();
      setKeyInput("");
      setShowKeyField(false);
      setStatusMsg(cfg.connected ? "Key validated — connected to Gemini." : cfg.test_error ? `Saved, but connection test failed: ${cfg.test_error}` : "Saved.");
      setTimeout(() => setStatusMsg(""), 6000);
    },
  });
  const testAI = useMutation({
    mutationFn: () => api.post<{ connected: boolean; model: string }>("/api/settings/ai/test"),
    onSuccess: (r) => { invalidate(); setStatusMsg(r.connected ? `Connected (${r.model})` : "Test failed"); setTimeout(() => setStatusMsg(""), 5000); },
    onError: (e: Error) => { setStatusMsg(e.message); setTimeout(() => setStatusMsg(""), 6000); },
  });
  const saveProfile = useMutation({
    mutationFn: () => api.put("/api/settings/profile", profile),
    onSuccess: invalidate,
  });
  const savePrefs = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.put("/api/settings/preferences", body),
    onSuccess: invalidate,
  });

  if (isLoading || !data) return <Spinner label="Loading settings…" />;
  const ai = data.ai;
  const prefs = data.preferences;
  const setPref = (k: string, v: unknown) => savePrefs.mutate({ [k]: v });

  return (
    <div className="grid grid-cols-3 gap-4 items-start">
      {/* AI Configuration */}
      <div className="space-y-4">
        <div className="card-pad">
          <CardTitle icon={<Sparkles size={16} className="text-primary" />}>AI Configuration</CardTitle>
          <p className="text-xs text-slate3 -mt-3 mb-4">Configure how CompanyVal AI analyzes and generates insights.</p>

          <label className="label">Provider</label>
          <input className="input mb-4" readOnly value={ai.provider} />

          <label className="label flex items-center gap-1.5">API Key <KeyRound size={12} className="text-slate3" /></label>
          {ai.key_set && !showKeyField ? (
            <div>
              <div className="flex items-center gap-2">
                <input className="input font-mono tracking-wider" readOnly
                  value={`••••••••••••••••••••••••${ai.key_tail}`} />
                <button className="btn-secondary !px-3" onClick={() => setShowKeyField(true)}>Replace Key</button>
              </div>
              <div className="flex items-center gap-2 mt-2">
                {ai.connected ? (
                  <span className="chip-mint flex items-center gap-1"><CheckCircle2 size={11} /> Connected</span>
                ) : (
                  <span className="chip-warn">Saved — not verified</span>
                )}
                <button className="text-xs font-semibold text-primary flex items-center gap-1"
                  onClick={() => testAI.mutate()} disabled={testAI.isPending}>
                  {testAI.isPending ? <Loader2 size={11} className="animate-spin" /> : <LinkIcon size={11} />} Test Connection
                </button>
              </div>
              <p className="help-text">The key is encrypted server-side and is never shown or sent to the browser again.</p>
            </div>
          ) : (
            <div>
              <div className="flex items-center gap-2">
                <input className="input font-mono" type="password" placeholder="Paste your Gemini API key"
                  value={keyInput} onChange={(e) => setKeyInput(e.target.value)} />
                <button className="btn-primary !px-3" disabled={keyInput.trim().length < 20 || saveAI.isPending}
                  onClick={() => saveAI.mutate({ api_key: keyInput.trim() })}>
                  {saveAI.isPending ? <Loader2 size={14} className="animate-spin" /> : "Save"}
                </button>
              </div>
              <p className="help-text">Validated and encrypted on the server (React → FastAPI → Gemini; the browser never calls Gemini).</p>
              {ai.key_set && <button className="text-xs text-slate2 underline mt-1" onClick={() => setShowKeyField(false)}>Cancel</button>}
            </div>
          )}
          {statusMsg && <p className="mt-2 text-xs font-semibold text-primary-700">{statusMsg}</p>}

          <label className="label mt-4">Model</label>
          <div className="relative">
            <select className="input appearance-none pr-32" value={ai.model}
              onChange={(e) => saveAI.mutate({ model: e.target.value, model_display: e.target.options[e.target.selectedIndex].text })}>
              <option value="gemini-3.6-flash">Gemini 3.6 Flash</option>
              <option value="gemini-3.6-pro">Gemini 3.6 Pro</option>
            </select>
            <span className="absolute right-3 top-1/2 -translate-y-1/2 chip-mint">Recommended</span>
          </div>

          <label className="label mt-4 flex items-center justify-between">
            Temperature <span className="rounded border border-line px-2 py-0.5 text-xs">{ai.temperature.toFixed(1)}</span>
          </label>
          <input type="range" min={0} max={1} step={0.1} value={ai.temperature}
            className="cv-slider w-full" style={{ ["--fill" as any]: `${ai.temperature * 100}%` }}
            onChange={(e) => saveAI.mutate({ temperature: Number(e.target.value) })} />
          <div className="flex justify-between text-[10.5px] text-slate3 mt-1">
            <span>More focused</span><span>More creative</span>
          </div>

          {[
            ["structured_output", "Structured Output (JSON)", "Ensure consistent, machine-readable outputs."],
            ["visual_verification", "Visual Verification", "Enable AI verification of charts, tables, and key insights."],
            ["ai_final_report", "AI Final Report", "Let AI draft the narrative sections of reports."],
          ].map(([key, label, sub]) => (
            <div key={key} className="flex items-center justify-between mt-4">
              <div>
                <p className="text-[13px] font-semibold text-navy">{label}</p>
                <p className="text-[11px] text-slate3">{sub}</p>
              </div>
              <Toggle checked={Boolean(ai[key as keyof AIConfig])}
                onChange={(v) => saveAI.mutate({ [key]: v } as any)} />
            </div>
          ))}
        </div>

        <div className="card-pad">
          <CardTitle icon={<Bell size={16} className="text-primary" />}>Notifications</CardTitle>
          <p className="text-xs text-slate3 -mt-3 mb-3">Manage how and when you receive notifications.</p>
          {[
            ["notif_valuation_updates", "Valuation Updates", "Get notified when valuations are completed."],
            ["notif_system_alerts", "System Alerts", "Important system and usage alerts."],
            ["notif_weekly_insights", "Weekly AI Insights", "Receive weekly AI insights and tips."],
            ["notif_marketing", "Marketing & Product Updates", "Updates about new features and offers."],
          ].map(([key, label, sub]) => (
            <div key={key} className="flex items-center justify-between py-2.5 border-b border-line/60 last:border-0">
              <div>
                <p className="text-[13px] font-semibold text-navy">{label}</p>
                <p className="text-[11px] text-slate3">{sub}</p>
              </div>
              <Toggle checked={Boolean(prefs[key])} onChange={(v) => setPref(key, v)} />
            </div>
          ))}
        </div>
      </div>

      {/* Report generation + security */}
      <div className="space-y-4">
        <div className="card-pad">
          <CardTitle icon={<FileText size={16} className="text-primary" />}>Report Generation</CardTitle>
          <p className="text-xs text-slate3 -mt-3 mb-4">Customize how valuation reports are generated.</p>
          <label className="label">Report Language</label>
          <select className="input mb-4" value={String(prefs.report_language)}
            onChange={(e) => setPref("report_language", e.target.value)}>
            <option>English</option>
          </select>
          <label className="label">Report Format</label>
          <select className="input mb-4" value={String(prefs.report_format)}
            onChange={(e) => setPref("report_format", e.target.value)}>
            <option>Comprehensive (Default)</option><option>Executive Summary</option>
          </select>
          <label className="label">Currency Display</label>
          <select className="input mb-4" value={String(prefs.currency_display)}
            onChange={(e) => setPref("currency_display", e.target.value)}>
            <option>INR (₹)</option>
          </select>
          {[
            ["include_benchmarking", "Include Benchmarking", "Add industry and peer benchmarking."],
            ["include_charts", "Include Charts & Visuals", "Add visual charts and graphs to reports."],
            ["include_data_sources", "Include Data Sources", "Show data sources and references."],
          ].map(([key, label, sub]) => (
            <div key={key} className="flex items-center justify-between mt-3.5">
              <div>
                <p className="text-[13px] font-semibold text-navy">{label}</p>
                <p className="text-[11px] text-slate3">{sub}</p>
              </div>
              <Toggle checked={Boolean(prefs[key])} onChange={(v) => setPref(key, v)} />
            </div>
          ))}
        </div>

        <div className="card-pad">
          <CardTitle icon={<ShieldCheck size={16} className="text-primary" />}>Security & API</CardTitle>
          <p className="text-xs text-slate3 -mt-3 mb-3">Manage security and API access.</p>
          {[
            ["Change Password", "Update your account password.", null],
            ["Two-Factor Authentication", "Add an extra layer of security to your account.", <span key="c" className="chip-mint">Enabled</span>],
            ["API Access", "Manage API keys and access.", null],
            ["Active Sessions", "View and manage active sessions.", <span key="c" className="chip-blue">2 Active</span>],
          ].map(([label, sub, chip]) => (
            <button key={label as string} className="w-full flex items-center justify-between py-3 border-b border-line/60 last:border-0 text-left hover:bg-page/60 rounded-lg px-2 -mx-2">
              <div>
                <p className="text-[13px] font-semibold text-navy">{label}</p>
                <p className="text-[11px] text-slate3">{sub}</p>
              </div>
              <span className="flex items-center gap-2">{chip}<ChevronRight size={15} className="text-slate3" /></span>
            </button>
          ))}
        </div>
      </div>

      {/* Profile + preferences */}
      <div className="space-y-4">
        <div className="card-pad">
          <CardTitle icon={<User2 size={16} className="text-primary" />}>Profile Settings</CardTitle>
          <p className="text-xs text-slate3 -mt-3 mb-4">Update your profile and preferences.</p>
          <div className="flex items-center gap-4 mb-4">
            <span className="h-16 w-16 rounded-full bg-primary-50 text-primary text-xl font-extrabold flex items-center justify-center border-2 border-dashed border-primary-100">
              {profile.name.split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase() || "AD"}
            </span>
            <div className="flex-1 space-y-3">
              <div><label className="label !mb-1">Full Name</label>
                <input className="input" value={profile.name} onChange={(e) => setProfile((p) => ({ ...p, name: e.target.value }))} /></div>
              <div><label className="label !mb-1">Role</label>
                <input className="input" value={profile.role} onChange={(e) => setProfile((p) => ({ ...p, role: e.target.value }))} /></div>
            </div>
          </div>
          <label className="label">Email</label>
          <input className="input mb-4" value={profile.email} onChange={(e) => setProfile((p) => ({ ...p, email: e.target.value }))} />
          <label className="label">Timezone</label>
          <select className="input mb-4" value={profile.timezone} onChange={(e) => setProfile((p) => ({ ...p, timezone: e.target.value }))}>
            <option>(GMT+05:30) India Standard Time</option>
            <option>(GMT+00:00) UTC</option>
          </select>
          <div className="grid grid-cols-2 gap-3">
            <div><label className="label">Date Format</label>
              <select className="input"><option>May 16, 2025</option><option>16/05/2025</option></select></div>
            <div><label className="label">Number Format</label>
              <select className="input"><option>1,234.56</option><option>1.234,56</option></select></div>
          </div>
          <button className="btn-primary w-full mt-4" onClick={() => saveProfile.mutate()} disabled={saveProfile.isPending}>
            {saveProfile.isPending ? "Saving…" : "Save Profile"}
          </button>
        </div>

        <div className="card-pad">
          <CardTitle icon={<Settings2 size={16} className="text-primary" />}>Preferences</CardTitle>
          <p className="text-xs text-slate3 -mt-3 mb-4">Customize your experience.</p>
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-[13px] font-semibold text-navy">Default Valuation Method</p>
              <p className="text-[11px] text-slate3">Set your preferred default valuation method.</p>
            </div>
            <select className="input !w-36" value={String(prefs.default_method)}
              onChange={(e) => setPref("default_method", e.target.value)}>
              <option>DCF</option><option>Market Multiple</option><option>Adjusted NAV</option>
            </select>
          </div>
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-[13px] font-semibold text-navy">Default Discount Rate</p>
              <p className="text-[11px] text-slate3">Applied to new valuations.</p>
            </div>
            <div className="flex items-center gap-1.5">
              <input className="input !w-20 text-right" value={String(prefs.default_discount_rate)}
                onChange={(e) => setPref("default_discount_rate", Number(e.target.value) || 12.5)} />
              <span className="text-sm text-slate2 font-semibold">%</span>
            </div>
          </div>
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-[13px] font-semibold text-navy">Auto-save</p>
              <p className="text-[11px] text-slate3">Automatically save your work.</p>
            </div>
            <Toggle checked={Boolean(prefs.auto_save)} onChange={(v) => setPref("auto_save", v)} />
          </div>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[13px] font-semibold text-navy">Data Refresh Frequency</p>
              <p className="text-[11px] text-slate3">How often data is refreshed.</p>
            </div>
            <select className="input !w-28" value={String(prefs.data_refresh)}
              onChange={(e) => setPref("data_refresh", e.target.value)}>
              <option>Daily</option><option>Hourly</option><option>Weekly</option>
            </select>
          </div>
        </div>
      </div>
    </div>
  );
}
