import { useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  UploadCloud, FileText, CheckCircle2, Circle, Loader2, AlertTriangle,
  Lock, Unlock, ArrowRight, Trash2, FileSpreadsheet, ScanSearch, Eye,
  ShieldCheck, Download, Clock,
} from "lucide-react";
import { api, fiscalYearFromFilename, fmtCrPlain, fmtFileSize } from "../services/api";
import { useCase } from "../hooks/useCase";
import { CardTitle, EmptyState, Spinner, StatusChip } from "../components/ui";
import type { DocumentInfo, FinancialsData, LineItem } from "../types";

const STATEMENT_LABEL: Record<string, string> = {
  pnl: "Profit & Loss", balance_sheet: "Balance Sheet", cash_flow: "Cash Flow",
};

const PIPELINE_STEPS = [
  { key: "uploaded", label: "Documents Uploaded", sub: "Files uploaded successfully" },
  { key: "extracting", label: "AI Extraction", sub: "Extracting financial data and line items" },
  { key: "reconciling", label: "Data Validation", sub: "Validating extracted data and calculations" },
  { key: "awaiting_review", label: "Verification & Review", sub: "Review discrepancies and confirm data" },
];

function stepState(docs: DocumentInfo[], stepKey: string,
): "done" | "active" | "waiting" | "failed" | "pending" {
  if (!docs.length) return "pending";
  const order = ["uploaded", "reading", "extracting", "rendering", "ai_verifying",
    "reconciling", "awaiting_review", "verified", "locked"];
  // A failed document has stopped moving; it must not drag the tracker backwards.
  // Progress reflects the documents still in flight — indexOf("failed") is -1, and
  // coercing that to 0 used to pin the whole pipeline at step 1 forever.
  const live = docs.filter((d) => d.status !== "failed");
  if (!live.length) return "failed";
  const minIdx = Math.min(...live.map((d) => {
    const i = order.indexOf(d.status);
    return i < 0 ? 0 : i;
  }));
  const stepIdx = { uploaded: 0, extracting: 2, reconciling: 5, awaiting_review: 6 }[stepKey] ?? 0;
  if (minIdx > stepIdx) return "done";
  // awaiting_review is a hand-off to the user, not background work — never spin here
  if (minIdx === stepIdx) return stepKey === "awaiting_review" ? "waiting" : "active";
  if (stepKey === "extracting" && minIdx >= 1 && minIdx <= 4) return "active";
  return "pending";
}

export default function Financials() {
  const { activeCaseId, activeCase } = useCase();
  const qc = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [tab, setTab] = useState<"data" | "verification" | "review">("data");
  const [statementFilter, setStatementFilter] = useState<string>("all");
  const [processing, setProcessing] = useState(false);
  const [uploadError, setUploadError] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["financials", activeCaseId],
    queryFn: () => api.get<FinancialsData>(`/api/valuations/${activeCaseId}/financials`),
    enabled: !!activeCaseId,
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["financials", activeCaseId] });
    qc.invalidateQueries({ queryKey: ["case", activeCaseId] });
  };

  const upload = useMutation({
    mutationFn: async (files: File[]) => {
      setUploadError("");
      setProcessing(true);
      for (const file of files) {
        const fy = fiscalYearFromFilename(file.name);
        const form = new FormData();
        form.append("file", file);
        form.append("fiscal_year_label", fy);
        const doc = await api.upload<DocumentInfo>(`/api/valuations/${activeCaseId}/documents`, form);
        await api.post(`/api/documents/${doc.id}/process`);
      }
    },
    onSettled: () => { setProcessing(false); invalidate(); },
    onError: (e: Error) => setUploadError(e.message),
  });

  const approve = useMutation({
    mutationFn: (body: { item_id?: string; approved_value?: number; note?: string; approve_all?: boolean; source?: string }) =>
      api.post(`/api/valuations/${activeCaseId}/financials/approve`, body),
    onSuccess: invalidate,
  });

  const lock = useMutation({
    mutationFn: (unlock: boolean) =>
      api.post(`/api/valuations/${activeCaseId}/financials/${unlock ? "unlock" : "lock"}`),
    onSuccess: invalidate,
  });

  const allItems = useMemo(() => {
    if (!data) return [] as LineItem[];
    return Object.entries(data.items).flatMap(([stmt, items]) =>
      items.map((i) => ({ ...i, statement: stmt })));
  }, [data]);

  const byMetric = useMemo(() => {
    const map = new Map<string, { label: string; statement: string; metric: string; periods: Record<string, LineItem> }>();
    for (const [stmt, items] of Object.entries(data?.items ?? {})) {
      for (const it of items) {
        const k = it.metric;
        if (!map.has(k)) map.set(k, { label: it.label, statement: stmt, metric: k, periods: {} });
        map.get(k)!.periods[it.period_label] = it;
      }
    }
    return Array.from(map.values());
  }, [data]);

  const needsReview = allItems.filter((i) => i.verification_status === "needs_review");

  if (!activeCaseId) return <Spinner />;
  if (isLoading || !data) return <Spinner label="Loading financials…" />;

  const failedDocs = data.documents.filter((d) => d.status === "failed");
  // Items that will be auto-adopted at lock time without anyone having looked at them.
  const unapprovedCount = allItems.filter(
    (i) => i.approved_value === null && i.verification_status !== "verified").length;
  // Values are always Python-extracted; AI vision only cross-checks them, and is off
  // by default. Say which one produced these numbers instead of implying low quality.
  const aiVerificationRan = data.extraction_counts.verifications > 0;
  const stmtCounts: Record<string, number> = { pnl: 0, balance_sheet: 0, cash_flow: 0 };
  allItems.forEach((i) => { if (i.statement && stmtCounts[i.statement] !== undefined) stmtCounts[i.statement]++; });
  const avgConfidence = allItems.length
    ? allItems.reduce((s, i) => s + (i.confidence || 0), 0) / allItems.length : 0;
  const filterCounts: [string, string, number][] = [
    ["all", "All Statements", allItems.length],
    ["balance_sheet", "Balance Sheet", stmtCounts.balance_sheet],
    ["pnl", "Profit & Loss", stmtCounts.pnl],
    ["cash_flow", "Cash Flow", stmtCounts.cash_flow],
  ];
  const rows = byMetric.filter((r) => statementFilter === "all" || r.statement === statementFilter);
  const previewRows = tab === "data" ? rows : rows.filter((r) =>
    Object.values(r.periods).some((i) =>
      tab === "review" ? i.verification_status === "needs_review"
        : i.verification_status !== "unverified"));

  const c = data.counts;
  const pct = (n: number) => (c.total ? Math.round((n / c.total) * 100) : 0);

  return (
    <div className="space-y-5">
      {/* top row */}
      <div className="grid grid-cols-12 gap-4">
        {/* upload */}
        <div className="col-span-4 card-pad">
          <CardTitle>Upload Financial Statements</CardTitle>
          <p className="text-xs text-slate3 -mt-3 mb-3">Upload last 3 years of financial statements</p>
          <button
            onClick={() => fileRef.current?.click()}
            disabled={data.locked || processing}
            className="w-full rounded-xl border-2 border-dashed border-line bg-page/50 px-4 py-8 text-center hover:border-primary/60 hover:bg-primary-50/40 transition disabled:opacity-60"
          >
            {processing ? (
              <Loader2 size={30} className="mx-auto text-primary animate-spin" />
            ) : data.locked ? (
              <Lock size={30} className="mx-auto text-slate3" />
            ) : (
              <UploadCloud size={30} className="mx-auto text-primary" />
            )}
            <p className="text-sm font-semibold text-navy mt-2.5">
              {processing ? "Processing documents…"
                : data.locked ? "Financials are locked for this case"
                : <>Drag and drop files here or <span className="text-primary">click to browse</span></>}
            </p>
            <p className="text-xs text-slate3 mt-1">
              {data.locked
                ? "Unlock below to upload or replace statements."
                : "PDF, XLSX, XLS up to 25MB each"}
            </p>
          </button>
          {data.locked && (
            <button className="btn-secondary w-full mt-2 !py-1.5 text-xs" onClick={() => lock.mutate(true)}>
              <Unlock size={13} /> Unlock to upload
            </button>
          )}
          <input ref={fileRef} type="file" multiple accept=".pdf,.xlsx,.xls" className="hidden"
            onChange={(e) => {
              const picked = Array.from(e.target.files ?? []);
              // reset first (snapshot above) so re-picking the same filename still fires onChange
              e.target.value = "";
              if (picked.length) upload.mutate(picked);
            }} />
          {uploadError && <p className="mt-2 text-xs text-risk-text">{uploadError}</p>}

          <div className="grid grid-cols-3 gap-2.5 mt-4">
            {data.documents.slice(0, 6).map((d) => (
              <div key={d.id} className="rounded-lg border border-line bg-surface p-2.5">
                <div className="flex items-center justify-between">
                  <FileText size={15} className="text-risk" />
                  {d.status === "failed"
                    ? <AlertTriangle size={14} className="text-risk" />
                    : <CheckCircle2 size={14} className="text-mint" />}
                </div>
                <p className="text-[11px] font-bold text-navy mt-1.5 truncate">{d.fiscal_year_label || d.original_filename}</p>
                <p className="text-[10px] text-slate3 truncate">{d.original_filename}</p>
                <p className="text-[10px] text-slate3">{fmtFileSize(d.size_bytes)}</p>
              </div>
            ))}
          </div>
          {data.documents.length > 0 && (
            <div className="mt-3.5">
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate2 font-medium">{data.documents.length} document(s) uploaded</span>
              </div>
              <div className="mt-1.5 h-1.5 rounded-full bg-line overflow-hidden">
                <div className="h-full bg-mint rounded-full" style={{ width: "100%" }} />
              </div>
            </div>
          )}
          {data.periods.length === 0 && data.documents.length === 0 && (
            <p className="mt-3 text-xs text-slate3">Demo tip: the seeded ABC Food case already carries verified financials — switch company in the header to explore it.</p>
          )}
        </div>

        {/* extraction progress */}
        <div className="col-span-3 card-pad">
          <CardTitle>Extraction Progress</CardTitle>
          <p className="text-xs text-slate3 -mt-3 mb-4">
            {data.locked ? "Financials are verified and locked"
              : processing ? "Extracting financial data from your documents"
              : failedDocs.length && failedDocs.length === data.documents.length
                ? "No document could be processed"
              : data.documents.length ? "Extraction finished — see the status of each step below"
              : "Upload statements to start extraction"}
          </p>
          <ol className="space-y-4">
            {PIPELINE_STEPS.map((s) => {
              const st = data.locked ? "done" : stepState(data.documents, s.key);
              return (
                <li key={s.key} className="flex gap-3">
                  <span className="mt-0.5">
                    {st === "done" ? <CheckCircle2 size={18} className="text-mint" />
                      : st === "active" ? <Loader2 size={18} className="text-primary animate-spin" />
                      : st === "waiting" ? <AlertTriangle size={18} className="text-warn" />
                      : st === "failed" ? <AlertTriangle size={18} className="text-risk" />
                      : <Circle size={18} className="text-line" />}
                  </span>
                  <div>
                    <p className={`text-[13px] font-semibold ${st === "pending" ? "text-slate3" : "text-navy"}`}>{s.label}</p>
                    <p className="text-[11px] text-slate3">
                      {st === "waiting" ? "Ready for you — review below, then lock"
                        : st === "failed" ? "Could not be completed"
                        : s.sub}
                    </p>
                  </div>
                </li>
              );
            })}
          </ol>
          {failedDocs.length > 0 && (
            <div className="mt-3 rounded-lg border border-risk/40 bg-risk-bg/40 px-3 py-2">
              <p className="text-[11.5px] font-bold text-risk-text flex items-center gap-1.5">
                <AlertTriangle size={12} /> {failedDocs.length} document(s) failed
              </p>
              {failedDocs.map((d) => (
                <p key={d.id} className="text-[11px] text-slate2 mt-1">
                  <span className="font-semibold">{d.original_filename}</span>
                  {d.error ? ` — ${d.error}` : ""}
                </p>
              ))}
              <p className="text-[11px] text-slate3 mt-1.5">
                Re-upload the file to try again. Other documents were unaffected.
              </p>
            </div>
          )}
          <div className="mt-4 rounded-lg bg-primary-50/60 border border-primary-100/50 px-3 py-2 text-[11.5px] text-primary-700 flex items-center gap-2">
            <Clock size={13} />
            {data.locked ? "Financials verified and locked"
              : processing ? "Estimated time remaining: 1 – 2 minutes"
              : !data.documents.length ? "Upload documents to begin extraction"
              : c.needs_review ? `${c.needs_review} item(s) need your review below`
              : "Extraction complete — review and lock the financials"}
          </div>
        </div>

        {/* detected + metrics */}
        <div className="col-span-5 space-y-4">
          <div className="card-pad">
            <CardTitle right={<span className="text-xs font-semibold text-primary flex items-center gap-1">View Details <ArrowRight size={12} /></span>}>
              Detected Statements
            </CardTitle>
            <div className="grid grid-cols-4 gap-3">
              {[
                ["Balance Sheets", data.periods.length ? data.periods.length : 0, "text-primary bg-primary-50"],
                ["P&L Statements", data.periods.length, "text-mint-text bg-mint-bg"],
                ["Cash Flow Statements", data.periods.length, "text-warn-text bg-warn-bg"],
                ["Notes & Others", 0, "text-risk-text bg-risk-bg"],
              ].map(([label, n, cls]) => (
                <div key={label as string} className="flex items-center gap-2.5">
                  <span className={`h-9 w-9 rounded-lg flex items-center justify-center ${cls}`}>
                    <FileSpreadsheet size={16} />
                  </span>
                  <div>
                    <p className="text-lg font-extrabold text-navy leading-5">{n}</p>
                    <p className="text-[10.5px] text-slate3 leading-tight">{label}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div className="card-pad">
              <p className="text-xs font-semibold text-slate2">Line Items Extracted</p>
              <p className="text-[26px] font-extrabold text-navy mt-1">{c.total}</p>
              <p className="text-[11px] font-semibold text-mint-text mt-0.5">▲ across {data.periods.length} financial years</p>
            </div>
            <div className="card-pad">
              <p className="text-xs font-semibold text-slate2">Extraction Confidence</p>
              <p className="text-[26px] font-extrabold text-navy mt-1">{Math.round(avgConfidence * 100)}%</p>
              <p className="text-[11px] font-semibold text-mint-text mt-0.5">
                {aiVerificationRan
                  ? (avgConfidence >= 0.85 ? "High Confidence" : "Moderate Confidence")
                  : "Python extraction"}
              </p>
            </div>
            <div className="card-pad">
              <p className="text-xs font-semibold text-slate2">Discrepancies Found</p>
              <p className="text-[26px] font-extrabold text-navy mt-1">{c.needs_review}</p>
              <button className="text-[11px] font-semibold text-primary flex items-center gap-1" onClick={() => setTab("review")}>
                View discrepancies <ArrowRight size={11} />
              </button>
            </div>
          </div>
          <div className="card-pad">
            <CardTitle tip="Share of line items by verification status.">Verification Status</CardTitle>
            <div className="h-2.5 rounded-full overflow-hidden flex bg-line">
              <div className="bg-mint h-full" style={{ width: `${pct(c.verified)}%` }} />
              <div className="bg-warn h-full" style={{ width: `${pct(c.needs_review)}%` }} />
              <div className="bg-violet2 h-full" style={{ width: `${pct(c.low_confidence + c.unverified)}%` }} />
            </div>
            <div className="flex gap-6 mt-3 text-[12px]">
              <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-mint" /> <b>{c.verified}</b> Verified <span className="text-slate3">{pct(c.verified)}%</span></span>
              <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-warn" /> <b>{c.needs_review}</b> Needs Review <span className="text-slate3">{pct(c.needs_review)}%</span></span>
              <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-violet2" /> <b>{c.low_confidence + c.unverified}</b> {aiVerificationRan ? "Other" : "Python-extracted"} <span className="text-slate3">{pct(c.low_confidence + c.unverified)}%</span></span>
              <span className="ml-auto">
                {data.locked ? (
                  <button className="btn-secondary !py-1.5 !px-3 text-xs" onClick={() => lock.mutate(true)}>
                    <Unlock size={13} /> Unlock
                  </button>
                ) : (
                  <button className="btn-primary !py-1.5 !px-3 text-xs"
                    onClick={() => {
                      // Locking adopts every un-approved python_value as approved. Say so
                      // when nothing was actually verified, rather than implying otherwise.
                      if (unapprovedCount > 0 && !window.confirm(
                        `${unapprovedCount} value(s) have not been individually reviewed.\n\n` +
                        "Locking adopts the Python-extracted number for each of them as the " +
                        "approved value. Continue?")) return;
                      lock.mutate(false);
                    }}
                    disabled={!allItems.length || needsReview.some((i) => i.approved_value === null)}>
                    <Lock size={13} /> {unapprovedCount > 0
                      ? `Lock Financials (${unapprovedCount} unreviewed)`
                      : "Lock Verified Financials"}
                  </button>
                )}
              </span>
            </div>
            {lock.isError && <p className="text-xs text-risk-text mt-2">{(lock.error as Error).message}</p>}
          </div>
        </div>
      </div>

      {/* tabs + data table */}
      <div className="card">
        <div className="flex items-center gap-6 px-6 pt-4 border-b border-line">
          {[
            ["data", "Extracted Data", null],
            ["verification", "Verification", c.verified],
            ["review", "Review & Approve", c.needs_review],
          ].map(([key, label, badge]) => (
            <button key={key as string} onClick={() => setTab(key as any)}
              className={`pb-3 text-sm font-semibold border-b-2 -mb-px flex items-center gap-2 ${
                tab === key ? "text-primary border-primary" : "text-slate2 border-transparent hover:text-navy"}`}>
              {label}
              {badge !== null && badge !== undefined && (badge as number) > 0 && (
                <span className="chip-blue">{badge}</span>
              )}
            </button>
          ))}
        </div>

        <div className="grid grid-cols-12 gap-0">
          <div className="col-span-3 border-r border-line p-5">
            <p className="text-[13px] font-bold text-navy mb-3">Statement Type</p>
            <ul className="space-y-1">
              {filterCounts.map(([key, label, n]) => (
                <li key={key}>
                  <button onClick={() => setStatementFilter(key)}
                    className={`w-full flex items-center justify-between rounded-lg px-3 py-2.5 text-sm ${
                      statementFilter === key ? "bg-primary-50 text-primary font-bold border-l-2 border-primary" : "text-slate2 hover:bg-page"}`}>
                    {label} <span className="text-xs">{n}</span>
                  </button>
                </li>
              ))}
            </ul>
            <div className="mt-6 card p-4 text-center">
              <p className="text-xs font-semibold text-slate2 mb-2">Extraction Overview</p>
              <p className="text-2xl font-extrabold text-navy">{data.documents.length || data.periods.length}</p>
              <p className="text-[11px] text-slate3">{data.documents.length ? "Documents" : "Seeded periods"}</p>
              <p className="mt-2 text-[11px] text-slate3">{data.extraction_counts.raw_items} raw extractions · {data.extraction_counts.verifications} AI verifications</p>
            </div>
          </div>

          <div className="col-span-9 p-5">
            <div className="flex items-center justify-between mb-3">
              <div>
                <p className="text-[15px] font-bold text-navy">
                  {tab === "review" ? "Discrepancies — choose the authoritative number" : "Extracted Data Preview"}
                </p>
                <p className="text-xs text-slate3">
                  {tab === "review"
                    ? "Python-extracted vs AI-verified values that disagree. Your decision is stored in the audit trail."
                    : "Preview of key financial data extracted from your documents"}
                </p>
              </div>
              <button className="btn-secondary !py-1.5 !px-3 text-xs"><Download size={13} /> Export</button>
            </div>

            {tab !== "review" ? (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr>
                      <th className="table-th">Line Item</th>
                      {data.periods.map((p) => (
                        <th key={p} className="table-th text-right">{p}<br /><span className="font-normal">(₹ Cr)</span></th>
                      ))}
                      <th className="table-th">Confidence</th>
                      <th className="table-th">Status</th>
                      <th className="table-th">Source</th>
                    </tr>
                  </thead>
                  <tbody>
                    {previewRows.map((r) => {
                      const latest = r.periods[data.periods[data.periods.length - 1]] ?? Object.values(r.periods)[0];
                      return (
                        <tr key={r.metric} className="hover:bg-page/50">
                          <td className="table-td font-semibold">{r.label}</td>
                          {data.periods.map((p) => {
                            const it = r.periods[p];
                            const v = it ? (it.approved_value ?? it.python_value) : null;
                            return <td key={p} className="table-td text-right">{v === null ? "—" : fmtCrPlain(v)}</td>;
                          })}
                          <td className="table-td">
                            <span className="flex items-center gap-2">
                              <span className="text-xs font-bold">{Math.round((latest?.confidence ?? 0) * 100)}%</span>
                              <span className="h-1.5 w-16 rounded-full bg-line overflow-hidden">
                                <span className="block h-full bg-mint rounded-full" style={{ width: `${(latest?.confidence ?? 0) * 100}%` }} />
                              </span>
                            </span>
                          </td>
                          <td className="table-td"><StatusChip status={latest?.verification_status ?? "unverified"} /></td>
                          <td className="table-td text-xs text-slate2">
                            {latest?.source_page ? `Page ${latest.source_page}` : "Seed"}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
                <p className="text-xs text-primary font-semibold mt-3 flex items-center gap-1">
                  View all {c.total} line items <ArrowRight size={12} />
                </p>
              </div>
            ) : needsReview.length === 0 ? (
              <EmptyState title="No discrepancies to review"
                body="Python extraction and AI visual verification agree on all line items." />
            ) : (
              <div className="space-y-3">
                {needsReview.map((it) => (
                  <div key={it.id} className="rounded-xl border border-warn/40 bg-warn-bg/40 p-4">
                    <div className="flex items-center justify-between">
                      <p className="font-bold text-navy text-sm">{it.label} <span className="text-slate3 font-medium">· {it.period_label}</span></p>
                      <StatusChip status={it.approved_value !== null ? "verified" : "needs_review"} />
                    </div>
                    <div className="grid grid-cols-3 gap-4 mt-3">
                      <div className="rounded-lg bg-surface border border-line p-3">
                        <p className="text-[11px] text-slate3 flex items-center gap-1"><ScanSearch size={12} /> Python Extracted</p>
                        <p className="text-base font-extrabold text-navy mt-1">₹{fmtCrPlain(it.python_value)} Cr</p>
                        <button className="btn-secondary w-full mt-2 !py-1.5 text-xs"
                          disabled={it.python_value === null}
                          onClick={() => it.python_value !== null && approve.mutate({ item_id: it.id, approved_value: it.python_value, note: "Adopted Python-extracted value" })}>
                          {it.python_value === null ? "No value" : "Use this value"}
                        </button>
                      </div>
                      <div className="rounded-lg bg-surface border border-line p-3">
                        <p className="text-[11px] text-slate3 flex items-center gap-1"><Eye size={12} /> AI Verified (p.{it.source_page})</p>
                        <p className="text-base font-extrabold text-navy mt-1">₹{fmtCrPlain(it.ai_visual_value)} Cr</p>
                        <button className="btn-secondary w-full mt-2 !py-1.5 text-xs"
                          disabled={it.ai_visual_value === null}
                          onClick={() => it.ai_visual_value !== null && approve.mutate({ item_id: it.id, approved_value: it.ai_visual_value, note: "Adopted AI-verified value" })}>
                          {it.ai_visual_value === null ? "Not readable" : "Use this value"}
                        </button>
                      </div>
                      <div className="rounded-lg bg-surface border border-line p-3">
                        <p className="text-[11px] text-slate3">Enter another value (₹ Cr)</p>
                        <ManualValue onSave={(v) => approve.mutate({ item_id: it.id, approved_value: v * 1e7, note: "Manual correction" })} />
                      </div>
                    </div>
                    {it.review_note && (
                      <p className="text-[11px] text-slate2 mt-2 flex items-center gap-1"><ShieldCheck size={12} className="text-mint-text" /> {it.review_note}</p>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* validation checks */}
            {tab === "verification" && (
              <div className="mt-5">
                <p className="text-[13px] font-bold text-navy mb-2">Accounting Validation Checks</p>
                <div className="grid grid-cols-2 gap-2">
                  {data.validation.checks.map((chk, i) => (
                    <div key={i} className={`flex items-center gap-2.5 rounded-lg border px-3 py-2 text-xs ${
                      chk.status === "pass" ? "border-mint/30 bg-mint-bg/40"
                        : chk.status === "fail" ? "border-risk/40 bg-risk-bg/40" : "border-line bg-page/50"}`}>
                      {chk.status === "pass" ? <CheckCircle2 size={14} className="text-mint-text shrink-0" />
                        : chk.status === "fail" ? <AlertTriangle size={14} className="text-risk shrink-0" />
                        : <Circle size={14} className="text-slate3 shrink-0" />}
                      <span>
                        <b className="text-navy">{chk.name}</b>
                        <span className="text-slate3"> · {chk.period} · {chk.detail}</span>
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function ManualValue({ onSave }: { onSave: (v: number) => void }) {
  const [v, setV] = useState("");
  return (
    <div className="flex gap-2 mt-1">
      <input className="input !py-1.5 text-sm" placeholder="0.00" value={v}
        onChange={(e) => setV(e.target.value)} />
      <button className="btn-primary !py-1.5 !px-3 text-xs" disabled={!v || isNaN(Number(v))}
        onClick={() => onSave(Number(v))}>Save</button>
    </div>
  );
}
