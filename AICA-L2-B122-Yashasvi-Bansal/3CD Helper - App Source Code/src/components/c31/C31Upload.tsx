import { useEffect, useMemo, useRef, useState } from "react";
import { UploadCloud, FileSpreadsheet, CheckCircle2, ArrowLeft } from "lucide-react";
import { supabase } from "@/integrations/supabase/client";
import { useFirm } from "@/contexts/FirmContext";
import { useToast } from "@/components/Toast";
import { Alert, Badge, Button, Card, Select, Spinner, cn } from "@/components/ui";
import { parseFile, ACCEPTED_FILES, MAX_FILE_MB } from "@/lib/import/parseFile";
import { MAX_ZIP_MB } from "@/lib/import/zip";
import { bundleFiles } from "@/lib/import/bundle";
import type { ParsedFile } from "@/lib/import/sources";
import { presetSelection, type LedgerPreset, type LoanExtract } from "@/lib/c31/tally";
import { autoMap, c31FromTable, C31_FIELDS, type C31Draft, type C31Map, type C31Field } from "@/lib/c31/excel";
import { MODE_LABEL, lenderName, txnKey } from "@/lib/c31/engine";
import { TallyFetch } from "./TallyFetch";
import { normalizeParty } from "@/lib/party";
import { safeFileName } from "@/lib/export";
import { errMsg, logActivity } from "@/lib/db";
import { formatINR } from "@/lib/format";

const db = supabase as any;
const SAVED = "c31_ledgers";
const KIND_BADGE = { loan: ["Loan group", "bg-emerald-50 text-emerald-700"], maybe: ["Name looks like a loan", "bg-amber-50 text-amber-700"], no: ["Other", "bg-slate-100 text-slate-500"] } as const;

interface Props { eng: any; clientId: string; clientName?: string; incoming?: File | null; ensureParties: (l: { party_name: string; normalized_name?: string; pan?: string | null; address?: string | null }[]) => Promise<void>; existingOpenings: Record<string, string>; onDone: () => void }

export function C31Upload({ eng, clientId, clientName = "", incoming, ensureParties, existingOpenings, onDone }: Props) {
  const { firm } = useFirm();
  const toast = useToast();
  const fileRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [parsed, setParsed] = useState<ParsedFile | null>(null);
  const [reading, setReading] = useState(false);
  const [saving, setSaving] = useState("");
  const [err, setErr] = useState("");
  const [drag, setDrag] = useState(false);
  // Tally
  const [preset, setPreset] = useState<LedgerPreset>("daybook");
  const [saved, setSaved] = useState<{ id: string; preset: LedgerPreset; ledgers: string[] } | null>(null);
  const [sel, setSel] = useState<Set<string>>(new Set());
  // Excel
  const [sheetIdx, setSheetIdx] = useState(0);
  const [map, setMap] = useState<{ headerRow: number; map: C31Map } | null>(null);

  const reset = () => { setFile(null); setParsed(null); setErr(""); setSel(new Set()); setMap(null); setSheetIdx(0); };

  const read = async (f: File, force?: LedgerPreset) => {
    reset(); setFile(f); setReading(true);
    try {
      const pf = await parseFile(f, "c31");
      setParsed(pf);
      if (pf.loans) {
        const { data } = await db.from("column_mappings").select("id, mapping").eq("client_id", clientId).eq("name", SAVED).maybeSingle();
        const s = data ? { id: data.id, preset: (data.mapping?.preset ?? "custom") as LedgerPreset, ledgers: (data.mapping?.ledgers ?? []) as string[] } : null;
        setSaved(s);
        const p: LedgerPreset = force ?? (s ? (s.preset === "unsecured" ? "unsecured" : s.preset === "daybook" ? "daybook" : "custom") : "daybook");
        setPreset(p); setSel(presetSelection(pf.loans.ledgers, p, s?.ledgers));
      } else {
        const idx = Math.max(0, pf.sheets.findIndex((s) => s.rows.length > 1));
        setSheetIdx(idx);
        const r = c31FromTable(pf.sheets[idx].rows);
        setMap({ headerRow: r.headerRow, map: r.map });
      }
    } catch (e) { setErr(errMsg(e)); setFile(null); }
    setReading(false);
  };

  // a file the client sent through the upload link
  useEffect(() => { if (incoming) read(incoming); }, [incoming]);

  const loans: LoanExtract | undefined = parsed?.loans;
  const choose = (p: LedgerPreset) => { if (!loans) return; setPreset(p); setSel(presetSelection(loans.ledgers, p, saved?.ledgers)); };
  const toggle = (name: string) => { const k = name.toLowerCase(); const n = new Set(sel); if (n.has(k)) n.delete(k); else n.add(k); setSel(n); setPreset("custom"); };

  const sheet = parsed && !loans ? parsed.sheets[sheetIdx] : null;
  const excel = useMemo(() => (sheet && map ? c31FromTable(sheet.rows, map) : null), [sheet, map]);

  /** Drafts to save, from either source. */
  const drafts: C31Draft[] = useMemo(() => {
    if (loans) {
      return loans.postings.filter((p) => sel.has(p.ledger.toLowerCase())).map((p, i) => ({
        row_no: i + 1, txn_date: p.date || null, party_name: p.ledger, normalized_name: normalizeParty(p.ledger) || p.ledger.toLowerCase(),
        pan: loans.ledgers.find((l) => l.name === p.ledger)?.pan || null, kind: p.interest ? "interest" : p.tds ? "tds" : p.credit ? "taken" : "repaid", amount: p.amount,
        mode: p.mode, voucher_no: p.voucherNo || null, remark: [p.voucherType, p.narration].filter(Boolean).join(" – ").slice(0, 500) || null, problems: [],
      }));
    }
    return excel?.rows ?? [];
  }, [loans, sel, excel]);

  const save = async () => {
    if (!firm || !file || !drafts.length) return;
    setErr("");
    try {
      // entries already in this year (same party, date, amount and voucher no.) are not added again
      setSaving("Checking entries already imported…");
      const have = new Set<string>();
      const toTds: string[] = [];   // entries saved earlier as a repayment that Tally shows as TDS on interest
      const tdsKeys = new Set(drafts.filter((d) => d.kind === "tds").map((d) => txnKey(d as any)));
      for (let from = 0; ; from += 1000) {
        const { data, error } = await db.from("loan_txns").select("id, kind, normalized_name, txn_date, amount, voucher_no").eq("engagement_id", eng.id).range(from, from + 999);
        if (error) throw error;
        (data ?? []).forEach((t: any) => { const k = txnKey(t); have.add(k); if (t.kind === "repaid" && tdsKeys.has(k)) toTds.push(t.id); });
        if (!data || data.length < 1000) break;
      }
      const fresh = drafts.filter((d) => !have.has(txnKey(d as any)));
      for (let i = 0; i < toTds.length; i += 200) {
        const { error } = await db.from("loan_txns").update({ kind: "tds" }).in("id", toTds.slice(i, i + 200));
        if (error) throw error;
      }
      const skipped = drafts.length - fresh.length;
      // parties and opening balances first, so a later failure (or a file already imported) never leaves them out
      setSaving("Updating parties…");
      const chosen = loans ? loans.ledgers.filter((l) => sel.has(l.name.toLowerCase())) : [];
      const keyOf = (n: string) => normalizeParty(n) || n.toLowerCase();
      const partyList = loans
        ? Array.from(new Map(chosen.map((l) => [keyOf(l.name), { party_name: lenderName(l.name), normalized_name: keyOf(l.name), pan: l.pan || null, address: l.address || null }])).values())
        : Array.from(new Map(drafts.map((d) => [d.normalized_name, { party_name: lenderName(d.party_name), normalized_name: d.normalized_name, pan: d.pan }])).values());
      if (partyList.length) await ensureParties(partyList);
      // opening balances from Tally (only where none is entered yet); two ledgers of the same lender are added together
      const opSum = new Map<string, { name: string; amt: number }>();
      chosen.forEach((l) => { if (!l.opening) return; const k = keyOf(l.name); const e = opSum.get(k) ?? { name: l.name, amt: 0 }; e.amt += l.opening; opSum.set(k, e); });
      const openings = Array.from(opSum.entries()).filter(([k, e]) => e.amt && !existingOpenings[k])
        .map(([k, e]) => ({ engagement_id: eng.id, firm_id: firm.id, party_name: e.name, normalized_name: k, opening_balance: Math.round(e.amt * 100) / 100 }));
      if (openings.length) { const { error } = await db.from("loan_balances").upsert(openings, { onConflict: "engagement_id,normalized_name", ignoreDuplicates: true }); if (error) throw error; }
      if (!fresh.length) {
        if (toTds.length) { onDone(); return; }
        setErr(`All ${drafts.length.toLocaleString("en-IN")} entries of this file are already imported for this year – nothing new to add.${openings.length ? ` ${openings.length} opening balance(s) were added.` : ""}`); setSaving(""); return;
      }
      setSaving("Saving the original file…");
      const ext = (file.name.match(/\.[^.]+$/) ?? [""])[0];
      const path = `${firm.id}/${eng.id}/c31_${Date.now()}_${safeFileName(file.name.replace(/\.[^.]+$/, ""))}${ext}`;
      const st = await supabase.storage.from("uploads").upload(path, file, { upsert: false });
      const { data: up, error: upErr } = await db.from("uploads").insert({ engagement_id: eng.id, firm_id: firm.id, module: "clause31", file_name: file.name,
        storage_path: st.error ? null : path, file_size: file.size, software_detected: parsed?.software ?? null, row_count: fresh.length }).select("id").single();
      if (upErr) throw upErr;
      try {
        for (let i = 0; i < fresh.length; i += 500) {
          setSaving(`Saving entries… ${Math.min(i + 500, fresh.length)} / ${fresh.length}`);
          const chunk = fresh.slice(i, i + 500).map(({ problems, ...d }) => ({ ...d, engagement_id: eng.id, firm_id: firm.id, upload_id: up.id }));
          const { error } = await db.from("loan_txns").insert(chunk);
          if (error) throw error;
        }
      } catch (e) {
        // remove the half-saved file and its entries, so trying again imports everything
        await db.from("uploads").delete().eq("id", up.id);
        if (!st.error) await supabase.storage.from("uploads").remove([path]);
        throw e;
      }
      if (loans) {
        const mapping = { preset, ledgers: chosen.map((l) => l.name) };
        if (saved) await db.from("column_mappings").update({ mapping }).eq("id", saved.id);
        else await db.from("column_mappings").insert({ firm_id: firm.id, client_id: clientId, name: SAVED, mapping });
      }
      await logActivity(firm.id, "upload.created", "engagement", eng.id, { module: "clause31", file: file.name, rows: fresh.length, skipped });
      toast(`${fresh.length.toLocaleString("en-IN")} entries imported${skipped ? ` (${skipped.toLocaleString("en-IN")} already there, skipped)` : ""}${openings.length ? `, ${openings.length} opening balance${openings.length > 1 ? "s" : ""}` : ""}`);
      reset(); onDone();
    } catch (e) { setErr(errMsg(e)); }
    setSaving("");
  };

  const upload = (
    <Card className="p-5">
      <div onClick={() => !reading && fileRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)}
        onDrop={async (e) => { e.preventDefault(); setDrag(false); const f = await bundleFiles(e.dataTransfer.files); if (f) read(f); }}
        className={cn("flex cursor-pointer flex-col items-center rounded-2xl border-2 border-dashed px-6 py-10 text-center transition", drag ? "border-navy-500 bg-navy-50" : "border-slate-300 hover:border-navy-400 hover:bg-slate-50")}>
        {reading ? <Spinner className="h-10 w-10" /> : <UploadCloud className="h-12 w-12 text-navy-600" />}
        <div className="mt-3 font-semibold">{reading ? `Reading ${file?.name}…` : "Upload loan data"}</div>
        <div className="mt-1 max-w-xl text-sm text-slate-500">
          Tally XML – the full <b>Day Book</b>, or <b>Group Vouchers</b> of only "Unsecured Loans" (Display → Account Books → Group Vouchers → Alt+E → XML, with "Include dependent masters = Yes").
          Or an Excel / CSV loan register or ledger report from Busy, Marg or any software. You can choose <b>several files together</b> (for example 12 monthly exports). Large files: put them in a <b>ZIP</b> (up to {MAX_ZIP_MB} MB; single files up to {MAX_FILE_MB} MB).
        </div>
        <input ref={fileRef} type="file" multiple accept={ACCEPTED_FILES} className="hidden" onChange={async (e) => { const list: File[] = e.target.files ? Array.from(e.target.files) : []; e.target.value = ""; const f = await bundleFiles(list); if (f) read(f); }} />
      </div>
      {err && <Alert tone="error" className="mt-4">{err}</Alert>}
    </Card>
  );
  if (!parsed) return (
    <div className="space-y-4">
      {upload}
      <div className={reading ? "hidden" : ""}><TallyFetch ay={eng.assessment_year} clientName={clientName} onFile={(f) => read(f, "daybook")} /></div>
    </div>
  );

  const head = (
    <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
      <div className="flex items-center gap-2 text-sm"><FileSpreadsheet className="h-4 w-4 text-navy-600" /><b>{file?.name}</b><Badge className="bg-navy-50 text-navy-800">{parsed.software}</Badge>
        {parsed.files && <span className="text-xs text-slate-500">({parsed.files.length} {parsed.files.length === 1 ? "file" : "files"}: {parsed.files.slice(0, 4).join(", ")}{parsed.files.length > 4 ? " …" : ""})</span>}</div>
      <Button variant="ghost" size="sm" icon={<ArrowLeft className="h-4 w-4" />} onClick={reset} disabled={!!saving}>Choose another file</Button>
    </div>
  );
  const footer = (
    <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4">
      <span className="text-sm text-slate-600"><b>{drafts.length.toLocaleString("en-IN")}</b> entries will be imported{excel && excel.skipped ? ` · ${excel.skipped} rows skipped (totals / blank amount)` : ""}</span>
      <Button icon={saving ? undefined : <CheckCircle2 className="h-4 w-4" />} loading={!!saving} disabled={!drafts.length} onClick={save}>{saving || "Import"}</Button>
    </div>
  );

  if (loans) {
    const chosenCount = loans.ledgers.filter((l) => sel.has(l.name.toLowerCase())).length;
    return (
      <Card className="p-5">
        {head}
        <div className="mb-3 text-sm font-semibold">Which ledgers are loans?</div>
        <div className="mb-4 grid gap-2 sm:grid-cols-3">
          {([["daybook", "All loan groups", "Loans (Liability) with Secured / Unsecured Loans, Loans & Advances, Deposits"], ["unsecured", "Only Unsecured Loans", "Ledgers under the Unsecured Loans group"],
            ...(saved ? [["custom", "Last time's selection", `${saved.ledgers.length} ledgers chosen for this client`]] : [])] as [LedgerPreset, string, string][]).map(([k, t, d]) => (
            <button key={k} onClick={() => choose(k)} className={cn("rounded-xl border p-3 text-left", preset === k ? "border-navy-900 bg-navy-50 ring-1 ring-navy-900" : "border-slate-200 hover:border-navy-300")}>
              <div className="text-sm font-semibold">{t}</div><div className="text-xs text-slate-500">{d}</div>
            </button>
          ))}
        </div>
        {!loans.hasMasters && <Alert tone="warn" className="mb-3">Ledger groups are not in this file, so ledgers are suggested by name only. For group-wise selection export again with "Include dependent masters = Yes", or tick the loan ledgers below.</Alert>}
        <div className="mb-2 flex flex-wrap gap-1.5 text-xs">
          {loans.groups.map((g) => <span key={g.name} className="rounded-full bg-slate-100 px-2 py-0.5 text-slate-600">{g.name}: {g.ledgers}</span>)}
        </div>
        <div className="max-h-[420px] overflow-auto rounded-xl border border-slate-200">
          <table className="table-pro">
            <thead><tr><th className="w-10"></th><th>Ledger</th><th>Group</th><th>Suggestion</th><th className="text-right">Entries</th><th className="text-right">Opening (Cr +)</th></tr></thead>
            <tbody>{loans.ledgers.map((l) => {
              const on = sel.has(l.name.toLowerCase());
              return (
                <tr key={l.name} className={cn("cursor-pointer", on && "bg-navy-50/40")} onClick={() => toggle(l.name)}>
                  <td><input type="checkbox" checked={on} readOnly className="h-4 w-4 accent-navy-900" /></td>
                  <td className="font-medium">{l.name}{l.pan && <span className="ml-2 font-mono text-[11px] text-slate-400">{l.pan}</span>}</td>
                  <td className="text-xs text-slate-500">{l.chain.length ? l.chain.join(" › ") : "—"}</td>
                  <td><Badge className={KIND_BADGE[l.kind][1]}>{KIND_BADGE[l.kind][0]}</Badge></td>
                  <td className="num">{l.postings}</td>
                  <td className="num">{l.opening ? formatINR(l.opening, { symbol: false }) : ""}</td>
                </tr>);
            })}</tbody>
          </table>
          <p className="mt-2 text-xs text-slate-500">Openings come from the Tally ledger masters, i.e. as on the date the books begin in Tally. If the books began before this year, correct them in "Parties & opening balances".</p>
        </div>
        <p className="mt-2 text-xs text-slate-500">{chosenCount} ledger(s) selected. A loan ledger kept in another group (for example a director's loan under Sundry Creditors) appears here only if its name looks like a loan – otherwise upload that ledger separately. Your choice is remembered for this client.</p>
        {err && <Alert tone="error" className="mt-3">{err}</Alert>}
        {footer}
      </Card>
    );
  }

  // Excel / CSV mapping
  const header = excel?.header ?? [];
  return (
    <Card className="p-5">
      {head}
      <div className="mb-3 grid gap-3 sm:grid-cols-3">
        {parsed.sheets.length > 1 && (
          <label className="text-sm">Sheet<Select value={sheetIdx} onChange={(e) => { const i = Number(e.target.value); setSheetIdx(i); const r = c31FromTable(parsed.sheets[i].rows); setMap({ headerRow: r.headerRow, map: r.map }); }}>
            {parsed.sheets.map((s, i) => <option key={i} value={i}>{s.name}</option>)}</Select></label>
        )}
        <label className="text-sm">Header row<Select value={map?.headerRow ?? 0} onChange={(e) => { const h = Number(e.target.value); setMap({ headerRow: h, map: autoMap(sheet!.rows[h] ?? []) }); }}>
          {sheet!.rows.slice(0, 30).map((r, i) => <option key={i} value={i}>{`Row ${i + 1}: ${r.filter((c) => c !== null && c !== "").slice(0, 4).join(" | ")}`.slice(0, 70)}</option>)}</Select></label>
      </div>
      <div className="mb-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
        {C31_FIELDS.map((f) => (
          <label key={f.key} className="text-xs font-medium text-slate-600">{f.label}
            <Select className="mt-1 h-9 text-xs" value={map?.map[f.key] ?? ""} onChange={(e) => setMap((m) => m && ({ ...m, map: { ...m.map, [f.key as C31Field]: e.target.value === "" ? undefined : Number(e.target.value) } }))}>
              <option value="">—</option>{header.map((h, i) => <option key={i} value={i}>{String(h ?? `Column ${i + 1}`)}</option>)}
            </Select></label>
        ))}
      </div>
      {map && map.map.party === undefined && <Alert tone="warn" className="mb-3">Choose the column with the lender / borrower name.</Alert>}
      {map && map.map.amount === undefined && map.map.debit === undefined && map.map.credit === undefined && <Alert tone="warn" className="mb-3">Choose the Amount column, or the Debit and Credit columns.</Alert>}
      <div className="max-h-[360px] overflow-auto rounded-xl border border-slate-200">
        <table className="table-pro">
          <thead><tr><th>Row</th><th>Date</th><th>Party</th><th>Side</th><th className="text-right">Amount</th><th>Mode</th><th>Check</th></tr></thead>
          <tbody>{drafts.slice(0, 200).map((d) => (
            <tr key={d.row_no}><td className="text-xs text-slate-400">{d.row_no}</td><td>{d.txn_date ?? ""}</td><td>{d.party_name}</td>
              <td className="text-xs">{["taken", "specified_taken", "interest", "repayment_received"].includes(d.kind) ? "Credit" : "Debit"}{d.kind === "interest" ? " (interest)" : d.kind === "tds" ? " (TDS on interest)" : d.kind.startsWith("specified") ? " (specified sum)" : ""}</td>
              <td className="num">{formatINR(d.amount, { symbol: false })}</td><td className="text-xs">{MODE_LABEL[d.mode]}</td><td className="text-xs text-amber-700">{d.problems.join(", ")}</td></tr>
          ))}</tbody>
        </table>
      </div>
      {drafts.length > 200 && <p className="mt-1 text-xs text-slate-500">Showing first 200 of {drafts.length}.</p>}
      {err && <Alert tone="error" className="mt-3">{err}</Alert>}
      {footer}
    </Card>
  );
}
