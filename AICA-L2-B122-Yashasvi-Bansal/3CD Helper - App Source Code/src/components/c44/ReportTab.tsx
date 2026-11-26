import { useEffect, useState } from "react";
import { FileSpreadsheet, FileJson, FileText, Printer, CheckCircle2, AlertTriangle, Pencil } from "lucide-react";
import { supabase } from "@/integrations/supabase/client";
import { useFirm } from "@/contexts/FirmContext";
import { useTeam } from "@/hooks/useTeam";
import { useToast } from "@/components/Toast";
import { Alert, Button, Card, CardHeader, Field, Input, Modal, cn } from "@/components/ui";
import { CLAUSE44, CATEGORY_LABEL, Category, Clause44Summary, EXCEPTION_LABEL } from "@/lib/clause44";
import { formatDate, formatINR, previousYearOf } from "@/lib/format";
import { errMsg, fetchAll, logActivity } from "@/lib/db";
import { downloadCsv, downloadJson, safeFileName, sheetFromAoa, workbookBlob, writeWorkbook, type WorkbookSheets } from "@/lib/export";
import { WhatsAppShare } from "@/components/WhatsAppShare";
import { LedgerReport, ledgerSheets, loadLedgerData } from "./LedgerReport";

interface Props {
  engagement: any;
  client: any;
  summary: Clause44Summary;
  editable: boolean;
  onChanged: () => void;
}

export function ReportTab({ engagement, client, summary, editable, onChanged }: Props) {
  const { firm } = useFirm();
  const { nameOf } = useTeam();
  const toast = useToast();
  const [prev, setPrev] = useState<Clause44Summary | null>(null);
  const [busy, setBusy] = useState("");
  const [plOpen, setPlOpen] = useState(false);

  const pl = engagement.pl_total_expenditure === null ? null : Number(engagement.pl_total_expenditure);
  const s = summary;
  const totalsTie = Math.abs(s.reported_total - (s.registered_total + s.unregistered)) < 0.005;
  const diff = pl === null ? null : Math.round((pl - s.reported_total) * 100) / 100;

  // Year-on-year comparison
  useEffect(() => {
    const prevAy = previousYearOf(engagement.assessment_year); // previous AY string equals this year's FY
    supabase.from("engagements").select("id").eq("client_id", engagement.client_id).eq("assessment_year", prevAy).maybeSingle().then(async ({ data }) => {
      if (!data) return;
      const r = await supabase.rpc("clause44_summary", { p_eng: data.id });
      const row = Array.isArray(r.data) ? r.data[0] : r.data;
      if (row && Number(row.row_count) > 0) setPrev({ ...row, reported_total: Number(row.reported_total), registered_total: Number(row.registered_total), unregistered: Number(row.unregistered), exempt: Number(row.exempt), composition: Number(row.composition), other_registered: Number(row.other_registered) } as Clause44Summary);
    });
  }, [engagement.id]);

  const meta: (string | number | null)[][] = [
    ["Name of assessee", client.name],
    ["PAN", client.pan ?? ""],
    ["Assessment year", engagement.assessment_year],
    ["Previous year", previousYearOf(engagement.assessment_year)],
  ];

  const clauseAoa = (): (string | number | null)[][] => [
    [`Clause ${CLAUSE44.clause}: ${CLAUSE44.title}`],
    [],
    [CLAUSE44.columns.sr, CLAUSE44.columns.total, CLAUSE44.columns.registeredGroup, null, null, null, CLAUSE44.columns.unregistered],
    [null, null, CLAUSE44.columns.exempt, CLAUSE44.columns.composition, CLAUSE44.columns.other_registered, CLAUSE44.columns.registered_total, null],
    [1, s.reported_total, s.exempt, s.composition, s.other_registered, s.registered_total, s.unregistered],
  ];

  /** The full Clause 44 workbook – downloaded, or shared on WhatsApp. */
  const buildWorkbook = async (): Promise<{ sheets: WorkbookSheets; fileName: string }> => {
      const [parties, exceptions, excluded] = await Promise.all([
        supabase.rpc("clause44_party_summary", { p_eng: engagement.id }).then((r) => r.data ?? []),
        supabase.rpc("clause44_exceptions", { p_eng: engagement.id }).then((r) => r.data ?? []),
        fetchAll<any>((from, to) => supabase.from("expense_rows").select("row_no, txn_date, party_name, effective_gstin, expense_head, amount, remark, updated_by").eq("engagement_id", engagement.id).eq("include", false).order("row_no").range(from, to)),
      ]);
      const header: (string | number | null)[][] = [
        [firm?.name ?? ""], ...meta, ["Prepared by", nameOf(engagement.created_by)], ["Reviewed by", engagement.reviewed_by ? `${nameOf(engagement.reviewed_by)} on ${formatDate(engagement.reviewed_at)}` : ""],
        ["UDIN", engagement.udin ?? ""], [],
      ];
      const c44 = [...header, ...clauseAoa(), [], [CLAUSE44.note]];
      const hOff = header.length + 2; // row index of the column heading block
      const merges = [
        { s: { r: header.length, c: 0 }, e: { r: header.length, c: 6 } },
        { s: { r: hOff, c: 2 }, e: { r: hOff, c: 5 } },
        { s: { r: hOff, c: 0 }, e: { r: hOff + 1, c: 0 } },
        { s: { r: hOff, c: 1 }, e: { r: hOff + 1, c: 1 } },
        { s: { r: hOff, c: 6 }, e: { r: hOff + 1, c: 6 } },
      ];
      const partyAoa = [["Party", "GSTIN", "Category", "Included amount", "Excluded amount", "Entries"],
        ...parties.map((p: any) => [p.party_name, p.gstin ?? "", p.category === "mixed" ? "Mixed" : p.category ? CATEGORY_LABEL[p.category as Category] : "Excluded", Number(p.included_amount), Number(p.excluded_amount), Number(p.row_count)])];
      const excAoa = [["Exception", "Party", "Detail", "Amount", "Entries"], ...exceptions.map((e: any) => [EXCEPTION_LABEL[e.kind] ?? e.kind, e.party_name, e.detail, Number(e.amount), Number(e.row_count)])];
      const exclAoa = [["Row", "Date", "Party", "GSTIN", "Expense head", "Amount", "Reason", "Excluded by"],
        ...excluded.map((r) => [r.row_no, formatDate(r.txn_date), r.party_name, r.effective_gstin ?? "", r.expense_head ?? "", Number(r.amount), r.remark ?? "", nameOf(r.updated_by)])];
      const recon = [
        ["Reconciliation with Profit & Loss account"], [],
        ["Total expenditure as per P&L", pl ?? "Not entered"],
        ["Less: entries excluded from Clause 44", s.excluded],
        ["Total of entries uploaded", s.total_uploaded],
        ["Expenditure reported in Clause 44", s.reported_total],
        ["Difference (P&L – reported)", diff ?? ""],
      ];
      const ledger = await loadLedgerData(engagement, engagement.client_id, false);
      return { fileName: `Clause44_${safeFileName(client.name)}_AY${engagement.assessment_year}.xlsx`, sheets: [
        { name: "Clause 44", ws: sheetFromAoa(c44, [8, 22, 22, 22, 22, 22, 24], merges) },
        { name: "Party-wise", ws: sheetFromAoa(partyAoa, [40, 18, 18, 18, 18, 10]) },
        { name: "Exceptions", ws: sheetFromAoa(excAoa, [28, 36, 30, 16, 10]) },
        { name: "Excluded items", ws: sheetFromAoa(exclAoa, [8, 12, 36, 18, 28, 16, 40, 20]) },
        { name: "Reconciliation", ws: sheetFromAoa(recon, [45, 22]) },
        ...(ledger ? ledgerSheets(ledger.report) : []),
      ] };
  };

  const exportExcel = async () => {
    setBusy("xlsx");
    try {
      const { sheets, fileName } = await buildWorkbook();
      writeWorkbook(sheets, fileName);
      await logActivity(firm!.id, "report.exported", "engagement", engagement.id, { format: "xlsx" });
    } catch (e) { toast(errMsg(e), "error"); }
    setBusy("");
  };

  const exportCsv = async () => {
    downloadCsv([...meta, [], ...clauseAoa()], `Clause44_${safeFileName(client.name)}_AY${engagement.assessment_year}.csv`);
    await logActivity(firm!.id, "report.exported", "engagement", engagement.id, { format: "csv" });
  };
  const exportJson = async () => {
    downloadJson({
      clause: "44", assessee: client.name, pan: client.pan, assessment_year: engagement.assessment_year,
      total_expenditure: s.reported_total,
      registered: { exempt: s.exempt, composition: s.composition, other_registered: s.other_registered, total: s.registered_total },
      unregistered: s.unregistered, generated_at: new Date().toISOString(), firm: firm?.name, udin: engagement.udin ?? null,
    }, `Clause44_${safeFileName(client.name)}_AY${engagement.assessment_year}.json`);
    await logActivity(firm!.id, "report.exported", "engagement", engagement.id, { format: "json" });
  };

  if (s.row_count === 0) return <Card><div className="p-8 text-center text-sm text-slate-500">Upload data to generate the Clause 44 report.</div></Card>;

  return (
    <div className="space-y-4">
      <div className="no-print flex flex-wrap gap-2">
        <Button icon={<FileSpreadsheet className="h-4 w-4" />} onClick={exportExcel} loading={busy === "xlsx"}>Excel (full workbook)</Button>
        <Button variant="outline" icon={<FileText className="h-4 w-4" />} onClick={exportCsv}>CSV</Button>
        <Button variant="outline" icon={<FileJson className="h-4 w-4" />} onClick={exportJson}>JSON</Button>
        <Button variant="outline" icon={<Printer className="h-4 w-4" />} onClick={() => window.print()}>Print / Save PDF</Button>
        <WhatsAppShare client={client} engagement={engagement} label="Clause 44 report" build={async () => { const w = await buildWorkbook(); return { blob: workbookBlob(w.sheets), fileName: w.fileName }; }} />
      </div>

      <LedgerReport engagement={engagement} client={client} editable={editable && !engagement.locked} onChanged={onChanged}>
      <Card className="print-area overflow-hidden">
        <div className="border-b border-slate-200 bg-navy-950 px-6 py-5 text-white print:bg-white print:text-black">
          <div className="text-xs uppercase tracking-widest text-navy-300 print:text-slate-500">{firm?.name}{firm?.frn ? ` · FRN ${firm.frn}` : ""}</div>
          <div className="mt-1 text-lg font-bold">Form 3CD – Clause {CLAUSE44.clause}</div>
          <div className="text-sm text-navy-200 print:text-slate-600">{CLAUSE44.title}</div>
        </div>
        <div className="grid gap-x-8 gap-y-2 px-6 py-4 text-sm sm:grid-cols-2">
          {meta.map(([k, v]) => <div key={String(k)} className="flex justify-between gap-4 border-b border-dashed border-slate-100 py-1"><span className="text-slate-500">{k}</span><span className="font-medium">{v}</span></div>)}
        </div>
        <div className="overflow-x-auto px-6 pb-6">
          <table className="w-full min-w-[760px] border-collapse text-sm">
            <thead>
              <tr className="bg-slate-50">
                <th rowSpan={2} className="border border-slate-300 p-2 text-left align-bottom">{CLAUSE44.columns.sr}</th>
                <th rowSpan={2} className="border border-slate-300 p-2 text-left align-bottom">{CLAUSE44.columns.total}</th>
                <th colSpan={4} className="border border-slate-300 p-2 text-center">{CLAUSE44.columns.registeredGroup}</th>
                <th rowSpan={2} className="border border-slate-300 p-2 text-left align-bottom">{CLAUSE44.columns.unregistered}</th>
              </tr>
              <tr className="bg-slate-50 text-xs">
                <th className="border border-slate-300 p-2 text-left font-medium">{CLAUSE44.columns.exempt}</th>
                <th className="border border-slate-300 p-2 text-left font-medium">{CLAUSE44.columns.composition}</th>
                <th className="border border-slate-300 p-2 text-left font-medium">{CLAUSE44.columns.other_registered}</th>
                <th className="border border-slate-300 p-2 text-left font-medium">{CLAUSE44.columns.registered_total}</th>
              </tr>
            </thead>
            <tbody>
              <tr className="font-semibold tabular-nums">
                <td className="border border-slate-300 p-2">1</td>
                <td className="border border-slate-300 p-2 text-right">{formatINR(s.reported_total, { symbol: false })}</td>
                <td className="border border-slate-300 p-2 text-right">{formatINR(s.exempt, { symbol: false })}</td>
                <td className="border border-slate-300 p-2 text-right">{formatINR(s.composition, { symbol: false })}</td>
                <td className="border border-slate-300 p-2 text-right">{formatINR(s.other_registered, { symbol: false })}</td>
                <td className="border border-slate-300 p-2 text-right">{formatINR(s.registered_total, { symbol: false })}</td>
                <td className="border border-slate-300 p-2 text-right">{formatINR(s.unregistered, { symbol: false })}</td>
              </tr>
            </tbody>
          </table>
          <p className="mt-2 text-xs text-slate-500">Amounts in ₹. {CLAUSE44.note}</p>
        </div>
        <div className="grid gap-4 border-t border-slate-100 px-6 py-4 text-xs text-slate-600 sm:grid-cols-3">
          <div>Prepared by: <b>{nameOf(engagement.created_by)}</b></div>
          <div>Reviewed by: <b>{engagement.reviewed_by ? `${nameOf(engagement.reviewed_by)} (${formatDate(engagement.reviewed_at)})` : "Pending"}</b></div>
          <div>UDIN: <b>{engagement.udin || "—"}</b></div>
        </div>
        <div className="border-t border-slate-100 px-6 py-3 text-[11px] text-slate-400">Prepared using 3CD Helper – subject to verification by the auditor.</div>
      </Card>
      </LedgerReport>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title="Checks" />
          <ul className="space-y-3 px-5 py-4 text-sm">
            <Check ok={totalsTie} text="Total = registered (exempt + composition + other) + unregistered" />
            <Check ok={s.invalid_gstin_count === 0} text={s.invalid_gstin_count ? `${s.invalid_gstin_count} entries have an invalid GSTIN (reported as unregistered)` : "All GSTINs are valid or blank"} />
            <Check ok={s.negative_count === 0} text={s.negative_count ? `${s.negative_count} negative entries (credits) are netted` : "No negative entries"} />
            <Check ok={diff !== null && Math.abs(diff) < 1} text={diff === null ? "Enter total expenditure as per P&L to reconcile" : Math.abs(diff) < 1 ? "Reconciled with P&L" : `Difference with P&L: ${formatINR(diff)}`} />
          </ul>
        </Card>
        <Card>
          <CardHeader title="Reconciliation with P&L" action={editable && <Button size="sm" variant="ghost" icon={<Pencil className="h-4 w-4" />} onClick={() => setPlOpen(true)}>Edit P&L total</Button>} />
          <dl className="space-y-2 px-5 py-4 text-sm">
            <Row k="Total expenditure as per P&L" v={pl === null ? "Not entered" : formatINR(pl)} />
            <Row k="Total of uploaded entries" v={formatINR(s.total_uploaded)} />
            <Row k="Less: excluded entries" v={`(${formatINR(s.excluded)})`} />
            <Row k="Reported in Clause 44" v={formatINR(s.reported_total)} bold />
            <Row k="Difference (P&L – reported)" v={diff === null ? "—" : formatINR(diff)} tone={diff !== null && Math.abs(diff) >= 1 ? "bad" : undefined} />
          </dl>
        </Card>
      </div>

      {prev && (
        <Card>
          <CardHeader title={`Year-on-year (vs AY ${previousYearOf(engagement.assessment_year)})`} />
          <div className="overflow-x-auto">
            <table className="table-pro">
              <thead><tr><th>Bucket</th><th className="num">Previous AY</th><th className="num">This AY</th><th className="num">Change</th></tr></thead>
              <tbody>
                {(["exempt", "composition", "other_registered", "unregistered"] as Category[]).map((k) => <YoY key={k} label={CATEGORY_LABEL[k]} a={prev[k]} b={s[k]} />)}
                <YoY label="Total" a={prev.reported_total} b={s.reported_total} bold />
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {plOpen && <PlModal engagement={engagement} onClose={() => setPlOpen(false)} onSaved={() => { setPlOpen(false); onChanged(); }} />}
    </div>
  );
}

function Check({ ok, text }: { ok: boolean; text: string }) {
  return <li className="flex items-start gap-2">{ok ? <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" /> : <AlertTriangle className="h-4 w-4 shrink-0 text-amber-600" />}<span>{text}</span></li>;
}
function Row({ k, v, bold, tone }: { k: string; v: string; bold?: boolean; tone?: "bad" }) {
  return <div className={cn("flex justify-between gap-4", bold && "border-t border-slate-200 pt-2 font-semibold", tone === "bad" && "text-red-600")}><dt>{k}</dt><dd className="tabular-nums">{v}</dd></div>;
}
function YoY({ label, a, b, bold }: { label: string; a: number; b: number; bold?: boolean }) {
  const pct = a ? ((b - a) / Math.abs(a)) * 100 : null;
  return (
    <tr className={cn(bold && "font-semibold")}>
      <td>{label}</td><td className="num">{formatINR(a, { symbol: false })}</td><td className="num">{formatINR(b, { symbol: false })}</td>
      <td className={cn("num", pct !== null && Math.abs(pct) > 25 && "text-amber-700")}>{pct === null ? "—" : `${pct > 0 ? "+" : ""}${pct.toFixed(1)}%`}</td>
    </tr>
  );
}

function PlModal({ engagement, onClose, onSaved }: { engagement: any; onClose: () => void; onSaved: () => void }) {
  const toast = useToast();
  const [v, setV] = useState(engagement.pl_total_expenditure ?? "");
  const [busy, setBusy] = useState(false);
  return (
    <Modal open onClose={onClose} title="Total expenditure as per P&L"
      footer={<><Button variant="ghost" onClick={onClose}>Cancel</Button><Button loading={busy} onClick={async () => {
        setBusy(true);
        const n = String(v).trim() === "" ? null : Number(String(v).replace(/,/g, ""));
        if (n !== null && !isFinite(n)) { toast("Enter a number", "error"); setBusy(false); return; }
        const { error } = await supabase.from("engagements").update({ pl_total_expenditure: n }).eq("id", engagement.id);
        setBusy(false);
        if (error) toast(errMsg(error), "error"); else onSaved();
      }}>Save</Button></>}>
      <Field label="Amount (₹)" hint="Total of expenses debited to the P&L account (as used for the Clause 44 reconciliation)">
        <Input value={v} onChange={(e) => setV(e.target.value)} inputMode="decimal" autoFocus />
      </Field>
      <Alert tone="info" className="mt-4">Tip: the difference should be explained by entries you excluded (depreciation, provisions, salary, etc.).</Alert>
    </Modal>
  );
}

