import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  FileText, FileSpreadsheet, FileCode2, Landmark, Settings2, Check,
  Download, Link2, ArrowRight, Loader2,
} from "lucide-react";
import { api, downloadReport, fmtCr, fmtCrPlain, fmtDate, reportDownloadUrl } from "../services/api";
import { useCase } from "../hooks/useCase";
import { CardTitle, Spinner, Toggle } from "../components/ui";
import type { Readiness, ReportInfo, RunSummary } from "../types";

const TEMPLATES = [
  { key: "comprehensive", title: "Comprehensive Valuation Report", sub: "Detailed analysis with full insights", icon: <FileText size={20} />, color: "text-primary bg-primary-50" },
  { key: "executive", title: "Executive Summary Report", sub: "High-level summary for stakeholders", icon: <FileSpreadsheet size={20} />, color: "text-mint-text bg-mint-bg" },
  { key: "investment_committee", title: "Investment Committee Report", sub: "Decision-focused investment analysis", icon: <FileCode2 size={20} />, color: "text-violet2 bg-violet2-bg" },
  { key: "debt", title: "Debt Valuation Report", sub: "Lender-focused valuation report", icon: <Landmark size={20} />, color: "text-warn-text bg-warn-bg" },
  { key: "custom", title: "Custom Report", sub: "Build a report tailored to your needs", icon: <Settings2 size={20} />, color: "text-slate2 bg-page" },
];

const SECTIONS = ["Executive Summary", "Company Overview", "Financial Analysis",
  "Valuation Methodologies", "Valuation Summary", "Scenario Analysis",
  "Risk Assessment", "Key Insights & Assumptions", "Comparable Companies", "Appendices"];

export default function Reports() {
  const { activeCaseId, activeCase } = useCase();
  const qc = useQueryClient();
  const [template, setTemplate] = useState("comprehensive");
  const [sections, setSections] = useState<string[]>(SECTIONS.slice(0, 8));
  const [execMode, setExecMode] = useState("ai");
  const [scenarios, setScenarios] = useState<string[]>(["Base Case", "Upside Case", "Downside Case"]);
  const [methodologies, setMethodologies] = useState({ dcf: true, comparable: true, precedent: false, asset: false, sotp: false });
  const [extras, setExtras] = useState({ peer: true, sensitivity: true, risk: true, appendix: false, glossary: false });
  const [shareMsg, setShareMsg] = useState("");
  const [exportError, setExportError] = useState("");

  const { data: reports = [] } = useQuery({
    queryKey: ["reports", activeCaseId],
    queryFn: () => api.get<ReportInfo[]>(`/api/valuations/${activeCaseId}/reports`),
    enabled: !!activeCaseId,
  });
  const { data: valuation } = useQuery({
    queryKey: ["valuation", activeCaseId],
    queryFn: () => api.get<{ run: RunSummary | null; readiness: Readiness }>(`/api/valuations/${activeCaseId}/valuation`),
    enabled: !!activeCaseId,
  });

  const generate = useMutation({
    mutationFn: async (format: "pdf" | "html") => {
      const rep = await api.post<ReportInfo>(`/api/valuations/${activeCaseId}/reports`, {
        template,
        options: {
          sections, scenarios, methodologies, extras,
          ai_narrative: execMode === "ai",
        },
      });
      await downloadReport(rep.id, format === "pdf" && rep.has_pdf, rep.title);
      return rep;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["reports", activeCaseId] }),
    onError: (e: Error) => setExportError(e.message),
  });

  if (!activeCaseId) return <Spinner />;
  const run = valuation?.run;

  const toggleSection = (s: string) =>
    setSections((cur) => (cur.includes(s) ? cur.filter((x) => x !== s) : [...cur, s]));
  const toggleScenario = (s: string) =>
    setScenarios((cur) => (cur.includes(s) ? cur.filter((x) => x !== s) : [...cur, s]));

  return (
    <div className="grid grid-cols-12 gap-5 items-start">
      <div className="col-span-7 space-y-5">
        {/* 1 template */}
        <div className="card p-6">
          <p className="flex items-center gap-2.5 mb-4">
            <span className="h-6 w-6 rounded-full bg-primary text-white text-xs font-bold flex items-center justify-center">1</span>
            <span className="text-[15px] font-bold text-navy">Select Report Template</span>
          </p>
          <div className="grid grid-cols-5 gap-3">
            {TEMPLATES.map((t) => {
              const on = template === t.key;
              return (
                <button key={t.key} onClick={() => setTemplate(t.key)}
                  className={`relative rounded-xl2 border-2 p-3.5 text-center transition ${on ? "border-primary bg-primary-50/50" : "border-line hover:bg-page"}`}>
                  {on && <span className="absolute top-2 right-2 h-4.5 w-4.5 h-[18px] w-[18px] rounded-full bg-primary text-white flex items-center justify-center"><Check size={11} /></span>}
                  <span className={`mx-auto h-11 w-11 rounded-xl flex items-center justify-center ${t.color}`}>{t.icon}</span>
                  <p className="text-[12px] font-bold text-navy mt-2 leading-tight">{t.title}</p>
                  <p className="text-[10.5px] text-slate3 mt-1 leading-tight">{t.sub}</p>
                </button>
              );
            })}
          </div>
        </div>

        {/* 2 contents */}
        <div className="card p-6">
          <p className="flex items-center gap-2.5 mb-4">
            <span className="h-6 w-6 rounded-full bg-primary text-white text-xs font-bold flex items-center justify-center">2</span>
            <span className="text-[15px] font-bold text-navy">Report Contents</span>
          </p>
          <div className="grid grid-cols-3 gap-6">
            <div>
              <div className="flex items-center justify-between mb-2.5">
                <p className="text-[13px] font-bold text-navy">Included Sections</p>
                <button className="text-xs font-semibold text-primary" onClick={() => setSections(SECTIONS)}>Select all</button>
              </div>
              <ul className="space-y-2">
                {SECTIONS.map((s) => (
                  <li key={s}>
                    <label className="flex items-center gap-2.5 text-[12.5px] text-slate2 cursor-pointer">
                      <input type="checkbox" checked={sections.includes(s)} onChange={() => toggleSection(s)}
                        className="h-4 w-4 rounded border-line text-primary accent-[#2563EB]" />
                      {s}
                    </label>
                  </li>
                ))}
              </ul>
            </div>
            <div className="space-y-5">
              <div className="rounded-xl border border-line p-4">
                <p className="text-[13px] font-bold text-navy mb-2.5">Executive Summary Options</p>
                {[
                  ["ai", "AI-Generated Executive Summary", "Let AI create a tailored summary"],
                  ["insights", "Use Key Insights", "Use key insights as summary"],
                  ["custom", "Custom Summary", "Write your own executive summary"],
                ].map(([key, label, sub]) => (
                  <label key={key} className="flex items-start gap-2.5 mb-2.5 cursor-pointer">
                    <input type="radio" name="exec" checked={execMode === key} onChange={() => setExecMode(key)}
                      className="mt-0.5 accent-[#2563EB]" />
                    <span>
                      <span className="block text-[12.5px] font-semibold text-navy">{label}</span>
                      <span className="block text-[11px] text-slate3">{sub}</span>
                    </span>
                  </label>
                ))}
              </div>
              <div className="rounded-xl border border-line p-4">
                <p className="text-[13px] font-bold text-navy mb-2.5">Methodologies to Include</p>
                {[
                  ["dcf", "Discounted Cash Flow (DCF)"], ["comparable", "Comparable Companies"],
                  ["precedent", "Precedent Transactions"], ["asset", "Asset-Based Approach"],
                  ["sotp", "Sum-of-the-Parts"],
                ].map(([key, label]) => (
                  <div key={key} className="flex items-center justify-between py-1.5">
                    <span className="text-[12.5px] text-slate2">{label}</span>
                    <Toggle checked={methodologies[key as keyof typeof methodologies]}
                      onChange={(v) => setMethodologies((s) => ({ ...s, [key]: v }))} />
                  </div>
                ))}
              </div>
            </div>
            <div className="space-y-5">
              <div className="rounded-xl border border-line p-4">
                <p className="text-[13px] font-bold text-navy mb-1">Scenario Analysis</p>
                <p className="text-[11px] text-slate3 mb-2.5">Select scenarios to include</p>
                {["Base Case", "Upside Case", "Downside Case", "Stress Case", "Management Case"].map((s) => (
                  <label key={s} className="flex items-center gap-2.5 text-[12.5px] text-slate2 mb-2 cursor-pointer">
                    <input type="checkbox" checked={scenarios.includes(s)} onChange={() => toggleScenario(s)}
                      className="h-4 w-4 accent-[#2563EB]" />
                    {s}
                  </label>
                ))}
              </div>
              <div className="rounded-xl border border-line p-4">
                <p className="text-[13px] font-bold text-navy mb-2.5">Additional Options</p>
                {[
                  ["peer", "Include Peer Comparison"], ["sensitivity", "Include Sensitivity Analysis"],
                  ["risk", "Include Risk Assessment"], ["appendix", "Include Data Appendix"],
                  ["glossary", "Include Glossary"],
                ].map(([key, label]) => (
                  <div key={key} className="flex items-center justify-between py-1.5">
                    <span className="text-[12.5px] text-slate2">{label}</span>
                    <Toggle checked={extras[key as keyof typeof extras]}
                      onChange={(v) => setExtras((s) => ({ ...s, [key]: v }))} />
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* 3 settings */}
        <div className="card p-6">
          <p className="flex items-center gap-2.5 mb-4">
            <span className="h-6 w-6 rounded-full bg-primary text-white text-xs font-bold flex items-center justify-center">3</span>
            <span className="text-[15px] font-bold text-navy">Report Settings</span>
          </p>
          <div className="grid grid-cols-4 gap-4">
            <div><label className="label !text-[12px]">Report Language</label>
              <select className="input"><option>English</option></select></div>
            <div><label className="label !text-[12px]">Date Format</label>
              <select className="input"><option>{fmtDate(activeCase?.valuation_date)}</option></select></div>
            <div><label className="label !text-[12px]">Currency</label>
              <select className="input"><option>INR (₹) - Indian Rupee</option></select></div>
            <div><label className="label !text-[12px]">Valuation Date</label>
              <input className="input" readOnly value={activeCase?.valuation_date ?? ""} /></div>
          </div>
        </div>
      </div>

      {/* right: preview + export */}
      <div className="col-span-5 space-y-4">
        <div className="card p-5">
          <CardTitle right={<span className="chip-mint flex items-center gap-1.5"><span className="h-1.5 w-1.5 rounded-full bg-mint animate-pulse" /> Live Preview</span>}>
            Report Preview
          </CardTitle>
          <div className="rounded-xl border border-line bg-page/60 p-5">
            <div className="flex justify-between text-[10.5px] text-slate3">
              <span className="text-primary font-bold">CompanyVal AI<br />Valuation Report</span>
              <span>1 of 34</span>
            </div>
            <h2 className="text-xl font-extrabold text-navy mt-4">{activeCase?.company_name}</h2>
            <p className="text-sm text-slate2">Comprehensive Valuation Analysis</p>
            <p className="text-[11px] text-slate3 mt-1.5">Valuation Date: {fmtDate(activeCase?.valuation_date)}</p>
            <div className="mt-4 rounded-lg bg-primary-50/60 border border-primary-100/50 p-3.5">
              <p className="text-[12px] font-bold text-navy mb-1.5">Executive Summary</p>
              <ul className="list-disc ml-4 text-[11.5px] text-slate2 space-y-1">
                <li>Fair enterprise value estimated between {fmtCr(run?.range_low)} and {fmtCr(run?.range_high)}</li>
                <li>Weighted analysis suggests a central estimate of {fmtCr(run?.central_estimate)}</li>
                <li>{run?.confidence_label ?? "—"} with {Math.round(run?.readiness_score ?? 0)}% valuation readiness</li>
                <li>Multiple valuation methods support the valuation range</li>
              </ul>
            </div>
            <div className="grid grid-cols-2 gap-3 mt-3.5">
              <div className="rounded-lg bg-surface border border-line p-3">
                <p className="text-[10.5px] text-slate3">Enterprise Value (Base Case)</p>
                <p className="text-lg font-extrabold text-mint-text">{fmtCr(run?.central_estimate)}</p>
                <p className="text-[10px] text-slate3">Range: {fmtCr(run?.range_low)} – {fmtCr(run?.range_high)}</p>
              </div>
              <div className="rounded-lg bg-surface border border-line p-3">
                <p className="text-[10.5px] text-slate3 mb-1.5">Valuation Summary (₹ Cr)</p>
                <div className="flex items-end gap-2.5 h-12">
                  {run && Object.entries(run.detail?.result.methods ?? {}).map(([k, m]: [string, any], i) => {
                    const max = Math.max(...Object.values(run.detail!.result.methods).map((x: any) => x.enterprise_value ?? 0));
                    return (
                      <div key={k} className="flex-1 flex flex-col items-center gap-0.5">
                        <span className="text-[9px] font-bold text-navy">{fmtCrPlain(m.enterprise_value, 2)}</span>
                        <div className={`w-full rounded-t ${["bg-primary", "bg-teal2", "bg-violet2"][i]}`}
                          style={{ height: `${((m.enterprise_value ?? 0) / max) * 34}px` }} />
                        <span className="text-[8.5px] text-slate3">{{ dcf: "DCF", market_multiple: "Market", adjusted_nav: "NAV" }[k]}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
            <p className="flex justify-between text-[9.5px] text-slate3 mt-3 pt-2 border-t border-line">
              <span>Confidential &amp; Proprietary</span><span>Powered by CompanyVal AI</span>
            </p>
          </div>
        </div>

        <div className="card p-5 grid grid-cols-2 gap-5">
          <div>
            <p className="text-[13px] font-bold text-navy">Export Report</p>
            <p className="text-[11px] text-slate3 mb-3">Choose format to download</p>
            <div className="flex gap-2.5">
              <button className="btn-secondary flex-1 text-xs" onClick={() => { setExportError(""); generate.mutate("pdf"); }} disabled={generate.isPending || !run}>
                {generate.isPending ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} className="text-risk" />} Export as PDF
              </button>
              <button className="btn-secondary flex-1 text-xs" onClick={() => { setExportError(""); generate.mutate("html"); }} disabled={generate.isPending || !run}>
                {generate.isPending ? <Loader2 size={14} className="animate-spin" /> : <FileCode2 size={14} className="text-primary" />} Export as HTML
              </button>
            </div>
            {generate.isPending && (
              <p className="text-[11px] text-slate3 mt-2">Building the report — this can take up to a minute.</p>
            )}
            {exportError && <p className="text-[11px] text-risk-text mt-2">{exportError}</p>}
          </div>
          <div>
            <p className="text-[13px] font-bold text-navy">Share Report</p>
            <p className="text-[11px] text-slate3 mb-3">Generate a shareable link</p>
            <button className="btn-ghost-blue text-xs" disabled={!reports.length}
              onClick={() => {
                const latest = reports[0];
                const url = new URL(reportDownloadUrl(latest.id, latest.has_pdf), location.origin).href;
                navigator.clipboard.writeText(url);
                setShareMsg("Link copied to clipboard");
                setTimeout(() => setShareMsg(""), 2500);
              }}>
              <Link2 size={14} /> {shareMsg || "Generate Share Link"}
            </button>
          </div>
          {generate.isError && <p className="col-span-2 text-xs text-risk-text">{(generate.error as Error).message}</p>}
        </div>

        <div className="card p-5">
          <CardTitle right={<span className="text-xs font-semibold text-primary flex items-center gap-1">View all reports <ArrowRight size={11} /></span>}>
            Generated Reports <span className="chip-blue">{reports.length}</span>
          </CardTitle>
          {reports.length === 0 ? (
            <p className="text-sm text-slate2">No reports yet — export one to see it here.</p>
          ) : (
            <ul className="divide-y divide-line/70">
              {reports.slice(0, 5).map((r) => (
                <li key={r.id} className="flex items-center gap-3 py-2.5">
                  <FileText size={16} className="text-primary shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-[12.5px] font-semibold text-navy truncate">{r.title}</p>
                    <p className="text-[11px] text-slate3">{fmtDate(r.created_at, true)} · {r.template}</p>
                  </div>
                  <a className="text-xs font-semibold text-primary hover:underline"
                    href={reportDownloadUrl(r.id, r.has_pdf)} target="_blank" rel="noreferrer">
                    Download
                  </a>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
