import { useEffect } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { fmtDate, fmtDateTime, inr, monthLabel } from "@/lib/gst/format";
import { R_DEFS, comparisons, gstr9, summarise, supplierSummary, totalTax } from "@/lib/gst/recon";
import { noticeStatus } from "@/lib/gst/notices";
import { getState, latestRun, log, overridesFor, useApp, useClient } from "@/lib/store";

/** Printable one-page summary — the browser's “Save as PDF” produces the PDF report. */
export const Route = createFileRoute("/print/$clientId")({
  head: () => ({ meta: [{ title: "GST summary report · Complete GST Suite" }] }),
  component: PrintPage,
});

function PrintPage() {
  const { clientId } = Route.useParams();
  const client = useClient(clientId);
  const firm = useApp((s) => s.firm);
  const tol = useApp((s) => s.prefs.tolerance);
  const soon = useApp((s) => s.prefs.reminderDays);
  const run = useApp((s) => latestRun(s.runs, clientId));
  const notices = useApp((s) => s.notices).filter((n) => n.clientId === clientId);
  useEffect(() => {
    if (!client) return;
    log("Exported PDF summary report", clientId);
    const t = setTimeout(() => window.print(), 600);
    return () => clearTimeout(t);
  }, [client, clientId]);
  if (!client) return <p className="p-8 text-sm">Client not found — open this page from the app after loading your clients.</p>;
  const sum = summarise(clientId, tol);
  const comps = comparisons(clientId, tol);
  const g9 = gstr9(clientId, overridesFor(getState().draftOverrides, clientId, "GSTR-9")).filter((l) => ["4N", "5N", "6A", "6J", "7J", "8A", "8D", "10/14", "10/14-INT"].includes(l.id));
  const sup = supplierSummary(clientId, tol).slice(0, 10);
  const th = "border border-slate-300 bg-[#1F3864] px-2 py-1 text-left text-white";
  const td = "border border-slate-300 px-2 py-1";
  return (
    <div className="mx-auto max-w-[1100px] bg-white p-8 text-[12px] text-slate-900 print:p-0">
      <div className="mb-4 flex justify-end gap-2 print:hidden"><Button onClick={() => window.print()}>Save as PDF / Print</Button></div>
      <div className="flex items-start justify-between bg-[#1F3864] p-4 text-white">
        <div><div className="text-xl font-bold">GST Summary Report</div><div>{client.name} · GSTIN {client.gstin} · FY 2025-26</div></div>
        <div className="text-right">{firm?.name}<div>{fmtDateTime(new Date().toISOString())}</div></div>
      </div>
      <p className="my-3">{run ? <>Last run {fmtDateTime(run.at)} via {run.route ?? "—"} by {run.by}: <b>{run.status}</b> — {run.error ?? run.message}</> : "Not run yet — figures below are calculated from the current data."}</p>
      <div className="grid grid-cols-4 gap-2">
        {[["Tax difference 3B vs books", sum.netTaxDiff], ["ITC at risk", sum.itcAtRisk], ["DRC-03 payable", sum.drc03], ["Interest u/s 50 (est.)", sum.interest]].map(([k, v]) => (
          <div key={k as string} className="border border-slate-300 p-2"><div className="text-[11px] text-slate-500">{k}</div><div className="text-base font-semibold">{inr(v as number)}</div></div>
        ))}
      </div>
      {sum.partialMonths.length > 0 && <p className="mt-2 text-amber-700">Partial data: {Object.entries(sum.missing).filter(([, m]) => m.length).map(([k, m]) => `${k.toUpperCase()} ${m.map(monthLabel).join(", ")}`).join("; ")}</p>}
      <h2 className="mb-1 mt-4 font-semibold text-[#1F3864]">Reconciliations (tax, Difference = A − B)</h2>
      <table className="w-full border-collapse">
        <thead><tr>{["#", "Reconciliation", "Side A", "Side B", "Difference", "Months", "Meaning"].map((h) => <th key={h} className={th}>{h}</th>)}</tr></thead>
        <tbody>{comps.map((c) => { const dm = c.rows.filter((r) => r.status === "Difference"); return (
          <tr key={c.id}><td className={td}>{c.id}</td><td className={td}>{c.title}</td><td className={`${td} text-right`}>{inr(totalTax(c.total.a))}</td><td className={`${td} text-right`}>{inr(totalTax(c.total.b))}</td>
            <td className={`${td} text-right ${dm.length ? "font-semibold text-red-700" : "text-green-700"}`}>{inr(totalTax(c.total.diff))}</td><td className={td}>{dm.map((r) => monthLabel(r.month)).join(", ") || "—"}</td>
            <td className={td}>{dm.length ? (totalTax(c.total.diff) > 0 ? R_DEFS[c.id].pos : R_DEFS[c.id].neg) : "Matched"}</td></tr>); })}</tbody>
      </table>
      <h2 className="mb-1 mt-4 font-semibold text-[#1F3864]">GSTR-9 key tables</h2>
      <table className="w-full border-collapse">
        <thead><tr>{["Table", "Particulars", "Taxable", "IGST", "CGST", "SGST", "Cess"].map((h) => <th key={h} className={th}>{h}</th>)}</tr></thead>
        <tbody>{g9.map((l) => <tr key={l.id}><td className={td}>{l.id}</td><td className={td}>{l.label}</td>{(["taxable", "igst", "cgst", "sgst", "cess"] as const).map((h) => <td key={h} className={`${td} text-right`}>{l.heads.includes(h) ? inr(l.v[h]) : "—"}</td>)}</tr>)}</tbody>
      </table>
      <h2 className="mb-1 mt-4 font-semibold text-[#1F3864]">Top suppliers — ITC at risk</h2>
      <table className="w-full border-collapse">
        <thead><tr>{["Supplier", "GSTIN", "Invoices", "ITC at risk"].map((h) => <th key={h} className={th}>{h}</th>)}</tr></thead>
        <tbody>{sup.length ? sup.map((s) => <tr key={s.gstin}><td className={td}>{s.party}</td><td className={td}>{s.gstin}</td><td className={`${td} text-right`}>{s.rows.length}</td><td className={`${td} text-right`}>{inr(s.atRisk)}</td></tr>) : <tr><td className={td} colSpan={4}>None</td></tr>}</tbody>
      </table>
      <h2 className="mb-1 mt-4 font-semibold text-[#1F3864]">Notices</h2>
      <table className="w-full border-collapse">
        <thead><tr>{["Status", "Form", "Nature", "Reference", "Reply due", "Internal status"].map((h) => <th key={h} className={th}>{h}</th>)}</tr></thead>
        <tbody>{notices.length ? notices.map((n) => <tr key={n.id}><td className={td}>{noticeStatus(n, new Date(), soon)}</td><td className={td}>{n.form}</td><td className={td}>{n.subject}</td><td className={td}>{n.ref}</td><td className={td}>{fmtDate(n.due)}</td><td className={td}>{n.status}</td></tr>) : <tr><td className={td} colSpan={6}>None</td></tr>}</tbody>
      </table>
      <p className="mt-4 text-[11px] text-slate-500">Generated by Complete GST Suite. Draft for review — verify tax paid against the electronic ledgers before filing.</p>
    </div>
  );
}
