import { useEffect, useMemo, useRef, useState, DragEvent, ReactNode } from "react";
import { UploadCloud, FileSpreadsheet, ArrowLeft, ArrowRight, CheckCircle2, AlertTriangle, Download, Save } from "lucide-react";
import { supabase } from "@/integrations/supabase/client";
import { TallyFetch } from "@/components/c31/TallyFetch";
import { LedgerPicker } from "./LedgerPicker";
import { useFirm } from "@/contexts/FirmContext";
import { useToast } from "@/components/Toast";
import { Alert, Badge, Button, Card, Field, Input, Select, Spinner, Toggle, cn } from "@/components/ui";
import { parseFile, ACCEPTED_FILES, MAX_FILE_MB } from "@/lib/import/parseFile";
import { bundleFiles } from "@/lib/import/bundle";
import type { ParsedFile } from "@/lib/import/sources";
import { FIELDS, FieldKey, Mapping, applyMapping, autoMap, columnLetters, detectHeaderRow, distinctParties, ExpenseDraft } from "@/lib/import/mapping";
import { formatINR } from "@/lib/format";
import { errMsg, logActivity } from "@/lib/db";
import { downloadExpenseTemplate, safeFileName } from "@/lib/export";

type Step = "pick" | "ledgers" | "map" | "preview" | "saving" | "done";

interface SavedMapping { id: string; name: string; client_id: string | null; mapping: { fields: Partial<Record<FieldKey, string>>; software?: string } }

const BATCH = 500;

export function UploadWizard({ engagement, clientId, clientName = "", onDone, incoming }: { engagement: { id: string; assessment_year: string; clause_answers?: any }; clientId: string; clientName?: string; onDone: () => void; incoming?: File | null }) {
  const { firm } = useFirm();
  const toast = useToast();
  const fileRef = useRef<HTMLInputElement>(null);
  const [step, setStep] = useState<Step>("pick");
  const [file, setFile] = useState<File | null>(null);
  const [parsed, setParsed] = useState<ParsedFile | null>(null);
  const [sheetIdx, setSheetIdx] = useState(0);
  const [map, setMap] = useState<Mapping>({ headerRow: 0 });
  const [opts, setOpts] = useState({ skipTotals: true, absolute: false, skipErrors: true });
  const [reading, setReading] = useState(false);
  const [err, setErr] = useState("");
  const [drag, setDrag] = useState(false);
  const [saved, setSaved] = useState<SavedMapping[]>([]);
  const [saveMapping, setSaveMapping] = useState(true);
  const [mappingName, setMappingName] = useState("");
  const [onlyProblems, setOnlyProblems] = useState(false);
  const [progress, setProgress] = useState({ done: 0, total: 0, label: "" });

  useEffect(() => {
    supabase.from("column_mappings").select("*").or(`client_id.eq.${clientId},client_id.is.null`).order("updated_at", { ascending: false })
      // only column mappings of expense files (Clause 31 keeps its ledger choice in the same table)
      .then(({ data }) => setSaved(((data as unknown as SavedMapping[]) ?? []).filter((m) => m?.mapping?.fields && typeof m.mapping.fields === "object")));
  }, [clientId]);

  const rows = parsed?.sheets[sheetIdx]?.rows ?? [];
  const header = rows[map.headerRow] ?? [];
  const width = Math.max(0, ...rows.slice(0, 50).map((r) => r.length));

  /** Apply a saved mapping (stored by column names) to the current sheet if its columns exist. */
  const applySaved = (sm: SavedMapping, base: Mapping): Mapping | null => {
    const hdr = (rows[base.headerRow] ?? []).map((h) => String(h ?? "").trim().toLowerCase());
    const next: Mapping = { headerRow: base.headerRow };
    let hits = 0;
    for (const [k, name] of Object.entries(sm.mapping.fields)) {
      const i = hdr.indexOf(String(name).trim().toLowerCase());
      if (i >= 0) { next[k as FieldKey] = i; hits++; }
    }
    return hits >= 2 && next.party !== undefined ? next : null;
  };

  const chooseSheet = (idx: number, pf = parsed) => {
    if (!pf) return;
    setSheetIdx(idx);
    const r = pf.sheets[idx].rows;
    const hr = pf.sheets[idx].preMapped ? 0 : detectHeaderRow(r);
    let m = autoMap(r, hr);
    // try saved mappings of this client first
    for (const sm of saved) {
      const hdr = (r[hr] ?? []).map((h) => String(h ?? "").trim().toLowerCase());
      const fields = Object.entries(sm.mapping.fields);
      if (fields.length && fields.every(([, n]) => hdr.includes(String(n).trim().toLowerCase()))) {
        const next: Mapping = { headerRow: hr };
        fields.forEach(([k, n]) => { next[k as FieldKey] = hdr.indexOf(String(n).trim().toLowerCase()); });
        m = next;
        toast(`Applied saved mapping "${sm.name}"`, "info");
        break;
      }
    }
    setMap(m);
  };

  const readFile = async (f: File) => {
    setErr(""); setReading(true); setFile(f);
    try {
      const pf = await parseFile(f);
      setParsed(pf);
      setMappingName(`${pf.software} – ${f.name.replace(/\.[^.]+$/, "")}`.slice(0, 60));
      chooseSheet(0, pf);
      // Tally books with their masters → ledger-wise method; anything else → column mapping
      setStep(pf.books?.vouchers.length ? "ledgers" : "map");
    } catch (e) { setErr(errMsg(e)); }
    setReading(false);
  };

  // a file the client sent through the upload link
  useEffect(() => { if (incoming) readFile(incoming); }, [incoming]);

  const onDrop = async (e: DragEvent) => { e.preventDefault(); setDrag(false); const f = await bundleFiles(e.dataTransfer.files); if (f) readFile(f); };

  const drafts: ExpenseDraft[] = useMemo(() => (step === "preview" || step === "saving" ? applyMapping(rows, map, { skipTotals: opts.skipTotals, absolute: opts.absolute }) : []), [step, rows, map, opts.skipTotals, opts.absolute]);
  const stats = useMemo(() => {
    const s = { rows: drafts.length, errors: 0, warnings: 0, invalid: 0, blank: 0, total: 0, parties: new Set<string>() };
    for (const d of drafts) {
      if (d.errors.length) s.errors++; else s.total += d.amount;
      if (d.warnings.length) s.warnings++;
      if (d.gstin_status === "invalid") s.invalid++;
      if (d.gstin_status === "blank") s.blank++;
      s.parties.add(d.normalized_name);
    }
    return s;
  }, [drafts]);

  const mappingOk = map.party !== undefined && (map.amount !== undefined || map.debit !== undefined || map.credit !== undefined);

  const save = async () => {
    if (!firm || !file) return;
    const toSave = drafts.filter((d) => !(opts.skipErrors && d.errors.length));
    if (!toSave.length) { setErr("Nothing to import."); return; }
    setStep("saving"); setErr("");
    try {
      // 1. remember the mapping by column names
      if (saveMapping && !parsed?.sheets[sheetIdx]?.preMapped) {
        const fields: Partial<Record<FieldKey, string>> = {};
        (Object.keys(map) as (keyof Mapping)[]).forEach((k) => { if (k !== "headerRow" && map[k] !== undefined) fields[k as FieldKey] = String(header[map[k] as number] ?? ""); });
        await supabase.from("column_mappings").insert({ firm_id: firm.id, client_id: clientId, name: mappingName || "Mapping", mapping: { fields, software: parsed?.software } });
      }
      // 2. keep the original file (private storage)
      setProgress({ done: 0, total: toSave.length, label: "Uploading original file…" });
      const path = `${firm.id}/${engagement.id}/${Date.now()}_${safeFileName(file.name.replace(/\.[^.]+$/, ""))}${(file.name.match(/\.[^.]+$/) ?? [""])[0]}`;
      const st = await supabase.storage.from("uploads").upload(path, file, { upsert: false });
      // 3. upload record
      const { data: up, error: upErr } = await supabase.from("uploads").insert({
        engagement_id: engagement.id, firm_id: firm.id, file_name: file.name, storage_path: st.error ? null : path,
        file_size: file.size, software_detected: parsed?.software ?? null, row_count: toSave.length,
      }).select("id").single();
      if (upErr) throw upErr;
      // 4. rows in batches
      for (let i = 0; i < toSave.length; i += BATCH) {
        setProgress({ done: i, total: toSave.length, label: "Saving entries…" });
        const chunk = toSave.slice(i, i + BATCH).map((d) => ({
          engagement_id: engagement.id, firm_id: firm.id, upload_id: up.id, row_no: d.row_no, party_name: d.party_name.slice(0, 300),
          normalized_name: d.normalized_name.slice(0, 300), gstin: d.gstin, gstin_status: d.gstin_status, expense_head: d.expense_head?.slice(0, 300) ?? null,
          amount: d.amount, txn_date: d.txn_date, nature: d.nature,
        }));
        const { error } = await supabase.from("expense_rows").insert(chunk);
        if (error) throw error;
      }
      // 5. party master + classification
      setProgress({ done: toSave.length, total: toSave.length, label: "Updating party master…" });
      const parties = distinctParties(toSave);
      for (let i = 0; i < parties.length; i += 1000) {
        const { error } = await supabase.rpc("upsert_parties", { p_client: clientId, p_parties: parties.slice(i, i + 1000) });
        if (error) throw error;
      }
      setProgress({ done: toSave.length, total: toSave.length, label: "Classifying…" });
      await supabase.rpc("reclassify_engagement", { p_eng: engagement.id });
      await logActivity(firm.id, "upload.created", "engagement", engagement.id, { file: file.name, rows: toSave.length, software: parsed?.software });
      setStep("done");
      toast(`${toSave.length.toLocaleString("en-IN")} entries imported`);
    } catch (e) {
      setErr(errMsg(e));
      setStep("preview");
    }
  };

  const reset = () => { setStep("pick"); setFile(null); setParsed(null); setErr(""); };

  /* ---------------- render ---------------- */
  if (step === "ledgers" && parsed?.books && file) {
    return <LedgerPicker engagement={engagement} clientId={clientId} file={file} books={parsed.books} software={parsed.software}
      onDone={() => { reset(); onDone(); }} onBack={reset} onUseColumns={() => setStep("map")} />;
  }
  if (step === "pick") {
    return (
      <Card className="p-5">
        <div
          onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)} onDrop={onDrop}
          onClick={() => !reading && fileRef.current?.click()}
          className={cn("flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 py-12 text-center transition",
            drag ? "border-navy-500 bg-navy-50" : "border-slate-300 hover:border-navy-400 hover:bg-slate-50")}
        >
          {reading ? <Spinner className="h-10 w-10" /> : <UploadCloud className="h-12 w-12 text-navy-600" />}
          <div className="mt-4 text-base font-semibold">{reading ? `Reading ${file?.name}…` : "Drop the expense ledger here or tap to choose"}</div>
          <div className="mt-1 text-sm text-slate-500">Excel (xlsx, xls), CSV, TXT, JSON, XML · Tally XML · GSTR-2B JSON · up to {MAX_FILE_MB} MB · you can choose several files together</div>
          <input ref={fileRef} type="file" multiple accept={ACCEPTED_FILES} className="hidden" onChange={async (e) => { const list: File[] = e.target.files ? Array.from(e.target.files) : []; e.target.value = ""; const f = await bundleFiles(list); if (f) readFile(f); }} />
        </div>
        {err && <Alert tone="error" className="mt-4">{err}</Alert>}
        <div className="mt-5 grid gap-3 text-sm text-slate-600 sm:grid-cols-3">
          <div className="rounded-xl bg-slate-50 p-3"><b className="text-slate-800">Tally:</b> best with the Tally Connector below. Or export the Day Book as XML with "Include dependent masters", or choose the Day Book and Masters XML together.</div>
          <div className="rounded-xl bg-slate-50 p-3"><b className="text-slate-800">Busy / Marg / Zoho:</b> export the ledger or purchase register as Excel/CSV.</div>
          <div className="rounded-xl bg-slate-50 p-3"><b className="text-slate-800">No export?</b> <button className="font-semibold text-navy-700 underline" onClick={downloadExpenseTemplate}><Download className="mr-1 inline h-3.5 w-3.5" />Use our template</button></div>
        </div>
        <div className={cn("mt-5", reading && "hidden")}><TallyFetch ay={engagement.assessment_year} clientName={clientName} modes={["daybook"]} onFile={(f) => readFile(f)} /></div>
      </Card>
    );
  }

  if (step === "map" && parsed) {
    const colOptions = Array.from({ length: width }, (_, i) => i);
    const sample = (i: number) => {
      for (let r = map.headerRow + 1; r < Math.min(rows.length, map.headerRow + 8); r++) {
        const v = rows[r]?.[i];
        if (v !== null && v !== undefined && String(v).trim() !== "") return String(v).slice(0, 28);
      }
      return "";
    };
    return (
      <Card className="p-5">
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <FileSpreadsheet className="h-5 w-5 text-navy-700" /><span className="font-semibold">{file?.name}</span>
          <Badge className="bg-navy-50 text-navy-800">Detected: {parsed.software}</Badge>
          <Badge>{rows.length.toLocaleString("en-IN")} rows</Badge>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {parsed.sheets.length > 1 && (
            <Field label="Sheet"><Select value={sheetIdx} onChange={(e) => chooseSheet(Number(e.target.value))}>{parsed.sheets.map((s, i) => <option key={i} value={i}>{s.name} ({s.rows.length} rows)</option>)}</Select></Field>
          )}
          <Field label="Header row" hint="The row that contains column names">
            <Select value={map.headerRow} onChange={(e) => { const hr = Number(e.target.value); setMap(autoMap(rows, hr)); }}>
              {rows.slice(0, 30).map((r, i) => <option key={i} value={i}>Row {i + 1}: {r.filter((c) => c !== null && String(c).trim()).slice(0, 4).join(" | ").slice(0, 60)}</option>)}
            </Select>
          </Field>
          {saved.length > 0 && (
            <Field label="Apply saved mapping">
              <Select value="" onChange={(e) => { const sm = saved.find((s) => s.id === e.target.value); if (!sm) return; const m = applySaved(sm, map); if (m) { setMap(m); toast(`Applied "${sm.name}"`); } else toast("This file's columns don't match that mapping", "error"); }}>
                <option value="">Choose…</option>
                {saved.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </Select>
            </Field>
          )}
        </div>

        <h3 className="mb-2 mt-6 text-sm font-semibold text-slate-800">Map your columns</h3>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {FIELDS.map((f) => (
            <Field key={f.key} label={f.label} required={f.required} hint={f.hint}>
              <Select value={map[f.key] ?? ""} onChange={(e) => setMap((m) => { const n = { ...m }; if (e.target.value === "") delete n[f.key]; else n[f.key] = Number(e.target.value); return n; })}
                className={map[f.key] !== undefined ? "border-emerald-400 bg-emerald-50/40" : ""}>
                <option value="">— Not in file —</option>
                {colOptions.map((i) => <option key={i} value={i}>{columnLetters(i)}: {String(header[i] ?? "").slice(0, 30) || "(no name)"}{sample(i) ? ` – e.g. ${sample(i)}` : ""}</option>)}
              </Select>
            </Field>
          ))}
        </div>
        {!mappingOk && <Alert tone="warn" className="mt-4">Map at least <b>Party name</b> and <b>Amount</b> (or Debit/Credit).</Alert>}

        <div className="mt-5 flex flex-wrap gap-x-8 gap-y-3 rounded-xl bg-slate-50 p-4 text-sm">
          <label className="flex items-center gap-3"><Toggle checked={opts.skipTotals} onChange={(v) => setOpts((o) => ({ ...o, skipTotals: v }))} />Skip total / opening / closing rows</label>
          <label className="flex items-center gap-3"><Toggle checked={opts.absolute} onChange={(v) => setOpts((o) => ({ ...o, absolute: v }))} />Treat all amounts as positive</label>
        </div>

        <div className="mt-5 flex flex-wrap justify-between gap-2">
          <Button variant="ghost" icon={<ArrowLeft className="h-4 w-4" />} onClick={reset}>Choose another file</Button>
          <Button disabled={!mappingOk} onClick={() => setStep("preview")}>Preview <ArrowRight className="h-4 w-4" /></Button>
        </div>
      </Card>
    );
  }

  if (step === "preview" || step === "saving") {
    const shown = (onlyProblems ? drafts.filter((d) => d.errors.length || d.warnings.length) : drafts).slice(0, 300);
    const importCount = drafts.filter((d) => !(opts.skipErrors && d.errors.length)).length;
    return (
      <Card className="p-5">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
          <Mini label="Entries" value={stats.rows.toLocaleString("en-IN")} />
          <Mini label="Total amount" value={formatINR(stats.total)} />
          <Mini label="Parties" value={stats.parties.size.toLocaleString("en-IN")} />
          <Mini label="No GSTIN / invalid" value={`${stats.blank} / ${stats.invalid}`} tone={stats.invalid ? "warn" : undefined} />
          <Mini label="Rows with errors" value={stats.errors} tone={stats.errors ? "bad" : "good"} />
        </div>
        {stats.errors > 0 && (
          <div className="mt-4 flex flex-wrap items-center gap-3 rounded-xl bg-red-50 p-3 text-sm text-red-900">
            <AlertTriangle className="h-4 w-4" />{stats.errors} rows have errors (e.g. missing amount).
            <label className="ml-auto flex items-center gap-2"><Toggle checked={opts.skipErrors} onChange={(v) => setOpts((o) => ({ ...o, skipErrors: v }))} />Skip them</label>
          </div>
        )}
        <div className="mt-4 flex items-center justify-between">
          <label className="flex items-center gap-2 text-sm"><Toggle checked={onlyProblems} onChange={setOnlyProblems} />Show only rows with issues</label>
          <span className="text-xs text-slate-500">Showing {shown.length} of {drafts.length}</span>
        </div>
        <div className="mt-3 max-h-[420px] overflow-auto rounded-xl border border-slate-200">
          <table className="table-pro">
            <thead><tr><th>Row</th><th>Date</th><th>Party</th><th>GSTIN</th><th>Head</th><th className="num">Amount</th><th>Issues</th></tr></thead>
            <tbody>
              {shown.map((d) => (
                <tr key={d.row_no} className={d.errors.length ? "bg-red-50" : d.warnings.length ? "bg-amber-50/60" : ""}>
                  <td className="text-xs text-slate-500">{d.row_no}</td>
                  <td className="whitespace-nowrap text-xs">{d.txn_date ?? ""}</td>
                  <td className="max-w-[220px] truncate">{d.party_name}</td>
                  <td className={cn("font-mono text-xs", d.gstin_status === "invalid" && "text-red-600")}>{d.gstin ?? ""}</td>
                  <td className="max-w-[180px] truncate text-xs">{d.expense_head}</td>
                  <td className="num">{formatINR(d.amount, { symbol: false })}</td>
                  <td className="text-xs">{[...d.errors, ...d.warnings].join("; ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!parsed?.sheets[sheetIdx]?.preMapped && (
          <div className="mt-4 flex flex-wrap items-center gap-3 rounded-xl bg-slate-50 p-3 text-sm">
            <label className="flex items-center gap-2"><Toggle checked={saveMapping} onChange={setSaveMapping} /><Save className="h-4 w-4" />Remember this column mapping as</label>
            <Input value={mappingName} onChange={(e) => setMappingName(e.target.value)} className="h-8 max-w-xs" disabled={!saveMapping} />
          </div>
        )}
        {err && <Alert tone="error" className="mt-4">{err}</Alert>}
        {step === "saving" ? (
          <div className="mt-5">
            <div className="mb-2 flex justify-between text-sm"><span>{progress.label}</span><span>{progress.total ? Math.round((progress.done / progress.total) * 100) : 0}%</span></div>
            <div className="h-2 overflow-hidden rounded-full bg-slate-200"><div className="h-full bg-navy-700 transition-all" style={{ width: `${progress.total ? (progress.done / progress.total) * 100 : 0}%` }} /></div>
          </div>
        ) : (
          <div className="mt-5 flex flex-wrap justify-between gap-2">
            <Button variant="ghost" icon={<ArrowLeft className="h-4 w-4" />} onClick={() => setStep("map")}>Back to mapping</Button>
            <Button onClick={save} disabled={!importCount}>Import {importCount.toLocaleString("en-IN")} entries</Button>
          </div>
        )}
      </Card>
    );
  }

  return (
    <Card className="p-8 text-center">
      <CheckCircle2 className="mx-auto h-12 w-12 text-emerald-600" />
      <h3 className="mt-3 text-lg font-semibold">Import complete</h3>
      <p className="mt-1 text-sm text-slate-500">Entries are classified. Review exclusions, flags and the party master next.</p>
      <div className="mt-6 flex flex-wrap justify-center gap-2">
        <Button variant="outline" onClick={reset}>Upload another file</Button>
        <Button onClick={onDone}>Go to review <ArrowRight className="h-4 w-4" /></Button>
      </div>
    </Card>
  );
}

function Mini({ label, value, tone }: { label: string; value: ReactNode; tone?: "warn" | "bad" | "good" }) {
  return (
    <div className={cn("rounded-xl border p-3", tone === "bad" ? "border-red-200 bg-red-50" : tone === "warn" ? "border-amber-200 bg-amber-50" : tone === "good" ? "border-emerald-200 bg-emerald-50" : "border-slate-200 bg-white")}>
      <div className="text-xs text-slate-500">{label}</div>
      <div className="mt-1 font-bold tabular-nums">{value}</div>
    </div>
  );
}
