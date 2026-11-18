import { useRef, useState } from "react";
import { Check, Copy, FileUp, Minus, PlugZap, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Money, Panel, StatusBadge, Term } from "./common";
import { DataTable } from "./DataTable";
import { DATA_SOURCES, getClientData, type Client, type DataSource, type Invoice, type ItcType } from "@/lib/gst/demo";
import { MONTHS, fmtDate, fmtDateTime, inr, monthLabel } from "@/lib/gst/format";
import { supplierSummary, totalTax } from "@/lib/gst/recon";
import { requestOtp, sessionStatus, GspError } from "@/lib/gst/gsp";
import { noticeFromLibrary } from "@/lib/gst/notices";
import {
  ParseError, REGISTER_FIELDS, REGISTER_FIELD_LABELS, REQUIRED_FIELDS, detectPortalFile, guessMapping, parseDaybookXml, registerToInvoices, rowsToRecords, vouchersToInvoices,
  type DetectedFile, type RegisterField, type Voucher,
} from "@/lib/gst/parsers";
import {
  addNotices, addUploadedFile, markFollowUp, refreshClientSession, saveClient, saveMapping, setPurchaseCategory, store3b, storeBooks, storeReturnRows, uploadsOf, useApp, verifyClientOtp,
} from "@/lib/store";
import { cn } from "@/lib/utils";

const DS_HELP: Record<DataSource, string> = {
  Auto: "Uses the GSP API when this GSTIN is connected; otherwise uses the files you uploaded.",
  "GSP API": "Always uses the API. If the session has expired, this client stops with “Request OTP”.",
  "Downloaded files": "Never calls the API. Only the files you uploaded are used.",
};

export function ConnectData({ client }: { client: Client }) {
  useApp((s) => s.clients);
  return (
    <div className="space-y-6">
      <div className="grid gap-6 xl:grid-cols-2">
        <DataSourceCard client={client} />
        <GspCard client={client} />
      </div>
      <FilesCard client={client} />
      <BooksCard client={client} />
    </div>
  );
}

function DataSourceCard({ client }: { client: Client }) {
  return (
    <Panel title={<Term k="Data source">Where portal data comes from</Term>}>
      <div className="grid gap-4 md:grid-cols-2">
        <RadioGroup value={client.dataSource} onValueChange={(v) => { saveClient({ ...client, dataSource: v as DataSource }, false); toast.success(`Data source set to ${v}`); }} aria-label="Data source">
          {DATA_SOURCES.map((d) => (
            <label key={d} className={cn("flex cursor-pointer items-start gap-3 rounded-md border p-3", client.dataSource === d && "border-primary bg-accent/40")}>
              <RadioGroupItem value={d} className="mt-0.5" />
              <span><span className="text-sm font-medium">{d}{d === "Auto" && <span className="ml-1 text-xs text-muted-foreground">(default)</span>}</span></span>
            </label>
          ))}
        </RadioGroup>
        <aside className="rounded-md bg-muted p-3 text-xs leading-relaxed text-muted-foreground">
          {DATA_SOURCES.map((d) => <p key={d} className="mb-2 last:mb-0"><span className="font-semibold text-foreground">{d}:</span> {DS_HELP[d]}</p>)}
        </aside>
      </div>
    </Panel>
  );
}

function GspCard({ client }: { client: Client }) {
  const session = useApp((s) => s.sessions[client.id]);
  const [otp, setOtp] = useState("");
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const st = sessionStatus(session);
  const guard = (fn: () => void) => { try { fn(); } catch (e) { setMsg({ ok: false, text: e instanceof GspError || e instanceof Error ? e.message : String(e) }); } };
  return (
    <Panel title={<Term k="GSP">GSP connection (OTP based)</Term>} actions={<StatusBadge status={st === "Connected" ? "Matched" : st === "Expired" ? "Overdue" : "neutral"} label={st} />}>
      <div className="space-y-3 text-sm">
        <p className="text-muted-foreground">{session ? <>Session {st === "Connected" ? "valid till" : "expired on"} <span className="font-medium text-foreground">{fmtDateTime(session.expiry)}</span>{st === "Connected" && " — it refreshes automatically before expiry."}</> : "Not connected yet."}</p>
        {!client.apiEnabled && <p className="rounded-md bg-warning/15 p-2 text-xs text-warning-foreground">API access is not enabled for this client. Ask the client to follow the steps below, then switch on “API access enabled” in Edit client.</p>}
        <div className="flex flex-wrap items-end gap-2">
          <Button onClick={() => guard(() => { setMsg({ ok: true, text: requestOtp(client) }); })}>Request OTP</Button>
          <div className="space-y-1">
            <Label htmlFor="otp" className="text-xs">OTP received by the client</Label>
            <Input id="otp" inputMode="numeric" maxLength={6} className="w-36 font-mono tracking-widest" placeholder="6 digits" value={otp} onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))} onKeyDown={(e) => e.key === "Enter" && guard(() => { verifyClientOtp(client.id, otp); setOtp(""); setMsg({ ok: true, text: "Connected to the GSP." }); })} />
          </div>
          <Button variant="outline" disabled={otp.length !== 6} onClick={() => guard(() => { verifyClientOtp(client.id, otp); setOtp(""); setMsg({ ok: true, text: "Connected to the GSP." }); })}>Verify</Button>
          {st === "Connected" && <Button variant="ghost" onClick={() => guard(() => { refreshClientSession(client.id); setMsg({ ok: true, text: "Token refreshed." }); })}>Refresh token</Button>}
        </div>
        {msg && <p className={cn("text-xs", msg.ok ? "text-info" : "text-destructive")}>{msg.text}</p>}
        <div className="rounded-md border p-3 text-xs leading-relaxed text-muted-foreground">
          <div className="mb-1 font-medium text-foreground">How the client enables API access</div>
          <ol className="list-decimal space-y-0.5 pl-4">
            <li>Log in to gst.gov.in.</li>
            <li>Go to My Profile › Manage API Access.</li>
            <li>Select <b>Yes</b>, choose the GSP and the duration, then Confirm.</li>
            <li>Click “Request OTP” here and enter the OTP the client receives.</li>
          </ol>
          <p className="mt-2 flex gap-1.5"><ShieldCheck className="h-3.5 w-3.5 shrink-0 text-success" /> We never ask for or store the GST portal password. Only the GSP session reference and its expiry are kept.</p>
        </div>
      </div>
    </Panel>
  );
}

function FilesCard({ client }: { client: Client }) {
  useApp((s) => s.notices);
  const [results, setResults] = useState<{ name: string; ok: boolean; text: string }[]>([]);
  const [drag, setDrag] = useState(false);
  const [busy, setBusy] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const cd = getClientData(client.id);

  async function handle(files: FileList | File[]) {
    setBusy(true);
    const out: { name: string; ok: boolean; text: string }[] = [];
    for (const f of Array.from(files)) {
      try {
        const lower = f.name.toLowerCase();
        let det: DetectedFile;
        if (lower.endsWith(".json")) det = detectPortalFile({ json: await f.text() }, client.gstin);
        else if (/\.(xlsx|xlsm|csv)$/.test(lower)) {
          const { readSheetRows } = await import("@/lib/gst/excel");
          det = detectPortalFile({ rows: await readSheetRows(f) }, client.gstin);
        } else throw new ParseError(`Unsupported file type. Use GSTR-1 / 2B / 3B JSON or the Excel templates.`);
        let text: string;
        let period = "";
        let rows = 0;
        if ("rows" in det) {
          storeReturnRows(client.id, det.type === "GSTR-1" ? "gstr1" : "gstr2b", det.month, det.rows);
          period = monthLabel(det.month);
          rows = det.rows.length;
          text = `${det.type} for ${period}: ${rows} row(s)`;
        } else if ("notices" in det) {
          const added = addNotices(det.notices.map((n) => noticeFromLibrary({ ...n, clientId: client.id, gstin: n.gstin || client.gstin, assignedTo: n.assignedTo || client.staff })));
          rows = det.notices.length;
          text = `Notices template: ${added} new, ${rows - added} duplicate(s) skipped`;
        } else {
          store3b(client.id, det.byMonth);
          const ms = Object.keys(det.byMonth).sort();
          period = ms.length > 1 ? `${monthLabel(ms[0]!)} to ${monthLabel(ms.at(-1)!)}` : monthLabel(ms[0]!);
          rows = ms.length;
          text = `${det.type}: ${rows} month(s) (${period})`;
        }
        addUploadedFile(client.id, { name: f.name, kind: det.type, period, rows, gstin: det.gstin, status: "Imported", message: text });
        out.push({ name: f.name, ok: true, text });
      } catch (e) {
        const text = e instanceof Error ? e.message : String(e);
        addUploadedFile(client.id, { name: f.name, kind: "Unknown", period: "", rows: 0, gstin: "", status: "Rejected", message: text });
        out.push({ name: f.name, ok: false, text });
      }
    }
    setResults(out);
    setBusy(false);
    toast.success(`${out.filter((r) => r.ok).length} file(s) imported, ${out.filter((r) => !r.ok).length} rejected`);
  }

  const kinds = [["gstr1", "GSTR-1"], ["gstr2b", "GSTR-2B"], ["gstr3b", "GSTR-3B"]] as const;
  const gaps = kinds.flatMap(([k, label]) => (cd.missing[k].length ? [`${label}: ${cd.missing[k].map(monthLabel).join(", ")}`] : []));
  return (
    <Panel title="Portal files (downloaded from gst.gov.in)" actions={gaps.length ? <StatusBadge status="Partial data" /> : <StatusBadge status="Matched" label="All 36 return-months available" />}>
      <p className="mb-3 text-xs text-muted-foreground">Drop GSTR-1 / GSTR-2B / GSTR-3B JSON files, the GSTR-3B 12-month summary Excel or the manual notices template. Any file name works — the type and period are read from the content. A file of another GSTIN is rejected.</p>
      <div
        role="button"
        tabIndex={0}
        aria-label="Upload portal files"
        onClick={() => input.current?.click()}
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && input.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); void handle(e.dataTransfer.files); }}
        className={cn("flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-8 text-center transition-colors", drag ? "border-primary bg-accent/50" : "hover:bg-accent/30")}
      >
        <FileUp className="h-6 w-6 text-muted-foreground" />
        <div className="text-sm font-medium">{busy ? "Reading files…" : "Drag & drop files here, or click to browse"}</div>
        <div className="text-xs text-muted-foreground">JSON, XLSX or CSV · several files at once</div>
      </div>
      <input ref={input} type="file" multiple accept=".json,.xlsx,.xlsm,.csv" className="hidden" onChange={(e) => { if (e.target.files?.length) void handle(e.target.files); e.target.value = ""; }} />
      {results.length > 0 && (
        <ul className="mt-3 space-y-1 text-sm">
          {results.map((r, i) => <li key={i} className={r.ok ? "text-success" : "text-destructive"}>{r.ok ? "✔" : "✖"} <span className="font-mono text-xs">{r.name}</span> — {r.text}</li>)}
        </ul>
      )}
      <div className="mt-5">
        <div className="mb-2 text-sm font-medium"><Term k="Partial data">Coverage — 12 months × returns</Term></div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-sm">
            <thead className="text-xs text-muted-foreground"><tr className="border-b"><th className="py-2 pr-2 text-left font-medium">Return</th>{MONTHS.map((m) => <th key={m} className="py-2 text-center font-medium">{monthLabel(m)}</th>)}</tr></thead>
            <tbody>
              {kinds.map(([k, label]) => (
                <tr key={k} className="border-b last:border-0">
                  <td className="py-2 pr-2"><Term k={label} /></td>
                  {MONTHS.map((m) => {
                    const has = !cd.missing[k].includes(m);
                    return <td key={m} className="py-2 text-center">{has ? <Check className="mx-auto h-4 w-4 text-success" aria-label={`${label} ${monthLabel(m)} available`} /> : <Minus className="mx-auto h-4 w-4 text-warning-foreground" aria-label={`${label} ${monthLabel(m)} missing`} />}</td>;
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {gaps.length > 0 && <p className="mt-2 text-xs text-warning-foreground">Partial data — missing {gaps.join("; ")}. The client still runs; these months are flagged amber.</p>}
      </div>
    </Panel>
  );
}

const BRIDGE_DEFAULT = "http://127.0.0.1:8765";

function BooksCard({ client }: { client: Client }) {
  useApp((s) => s.clients);
  const [map, setMap] = useState<{ kind: "sales" | "purchase"; name: string; headers: string[]; records: Record<string, unknown>[] } | null>(null);
  const [bridge, setBridge] = useState(BRIDGE_DEFAULT);
  const [bridgeState, setBridgeState] = useState<"Not checked" | "Connected" | "Not reachable">("Not checked");
  const [sel, setSel] = useState<Set<string>>(new Set());
  const reg = useRef<HTMLInputElement>(null);
  const xml = useRef<HTMLInputElement>(null);
  const [regKind, setRegKind] = useState<"sales" | "purchase">("sales");
  const cd = getClientData(client.id);
  const up = uploadsOf(client.id);

  async function openRegister(f: File) {
    try {
      const { readSheetRows } = await import("@/lib/gst/excel");
      const { headers, records } = rowsToRecords(await readSheetRows(f));
      if (!records.length) throw new Error("No rows found in this file.");
      setMap({ kind: regKind, name: f.name, headers, records });
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not read the register");
    }
  }
  function loadVouchers(vs: Voucher[], label: string) {
    const { sales, purchases } = vouchersToInvoices(vs);
    if (sales.length) storeBooks(client.id, "sales", sales, label);
    if (purchases.length) storeBooks(client.id, "purchases", purchases, label);
    toast.success(`${label}: ${sales.length} sales and ${purchases.length} purchase vouchers loaded`);
  }
  async function bridgeCall(fetchAll: boolean) {
    const url = `${bridge.replace(/\/$/, "")}/tally/vouchers?${new URLSearchParams({ company: client.tallyCompany, from: fetchAll ? "20250401" : "20250401", to: fetchAll ? "20260331" : "20250401" })}`;
    try {
      const ctl = new AbortController();
      const t = setTimeout(() => ctl.abort(), fetchAll ? 20000 : 3000);
      const res = await fetch(url, { signal: ctl.signal });
      clearTimeout(t);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setBridgeState("Connected");
      if (fetchAll) {
        const body = (await res.json()) as Voucher[] | { vouchers: Voucher[] };
        loadVouchers(Array.isArray(body) ? body : body.vouchers, "Local Tally Bridge");
      } else toast.success("Local Tally Bridge is reachable");
    } catch (e) {
      setBridgeState("Not reachable");
      toast.error(`Local Tally Bridge not reachable at ${bridge}`, { description: e instanceof Error ? e.message : undefined });
    }
  }

  return (
    <Panel title={<Term k="Books">Books (Tally)</Term>}>
      <p className="mb-4 text-xs text-muted-foreground">A browser cannot read Tally directly, so there are two ways in: upload Tally exports, or run the optional Local Tally Bridge on this computer.</p>
      <div className="mb-4 grid gap-3 md:grid-cols-2">
        <div className="rounded-md border p-3 text-sm"><div className="text-xs text-muted-foreground">Sales register in use</div><div className="font-medium">{cd.sales.length} vouchers</div><div className="text-xs text-muted-foreground">{up.booksLabel?.sales ?? (client.demo ? "Demo books (seeded)" : "Not uploaded yet")}</div></div>
        <div className="rounded-md border p-3 text-sm"><div className="text-xs text-muted-foreground">Purchase register in use</div><div className="font-medium">{cd.purchases.length} vouchers</div><div className="text-xs text-muted-foreground">{up.booksLabel?.purchases ?? (client.demo ? "Demo books (seeded)" : "Not uploaded yet")}</div></div>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="space-y-2 rounded-md border p-3">
          <div className="text-sm font-medium">(a) Upload Tally exports</div>
          <p className="text-xs text-muted-foreground">Sales Register and Purchase Register as Excel/CSV (you map the columns once — we remember it for this client), or the Day Book as XML.</p>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="outline" onClick={() => { setRegKind("sales"); reg.current?.click(); }}>Sales Register</Button>
            <Button size="sm" variant="outline" onClick={() => { setRegKind("purchase"); reg.current?.click(); }}>Purchase Register</Button>
            <Button size="sm" variant="outline" onClick={() => xml.current?.click()}>Day Book (XML)</Button>
          </div>
          <input ref={reg} type="file" accept=".xlsx,.xlsm,.csv" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) void openRegister(f); e.target.value = ""; }} />
          <input ref={xml} type="file" accept=".xml" className="hidden" onChange={async (e) => {
            const f = e.target.files?.[0];
            e.target.value = "";
            if (!f) return;
            try {
              const buf = new Uint8Array(await f.arrayBuffer());
              const text = buf[0] === 0xff && buf[1] === 0xfe ? new TextDecoder("utf-16le").decode(buf) : new TextDecoder().decode(buf);
              loadVouchers(parseDaybookXml(text), `Tally Day Book: ${f.name}`);
              addUploadedFile(client.id, { name: f.name, kind: "Tally Day Book", period: "FY 2025-26", rows: 0, gstin: "", status: "Imported" });
            } catch (err) { toast.error(err instanceof Error ? err.message : "Could not read the XML"); }
          }} />
        </div>
        <div className="space-y-2 rounded-md border p-3">
          <div className="flex items-center justify-between text-sm font-medium">(b) Local Tally Bridge <StatusBadge status={bridgeState === "Connected" ? "Matched" : bridgeState === "Not reachable" ? "Failed" : "neutral"} label={bridgeState} /></div>
          <div className="flex flex-wrap gap-2">
            <Input className="h-8 w-56 font-mono text-xs" value={bridge} onChange={(e) => setBridge(e.target.value)} aria-label="Bridge address" />
            <Button size="sm" variant="outline" onClick={() => void bridgeCall(false)}><PlugZap className="mr-1.5 h-3.5 w-3.5" /> Test</Button>
            <Button size="sm" onClick={() => void bridgeCall(true)}>Fetch FY vouchers</Button>
          </div>
          <p className="text-xs leading-relaxed text-muted-foreground">Setup: run a small service on this computer that reads Tally (XML port 9000) and answers <code className="rounded bg-muted px-1">GET /tally/vouchers?company=&amp;from=YYYYMMDD&amp;to=YYYYMMDD</code> with JSON vouchers <code className="rounded bg-muted px-1">[{"{"}date, voucher_type, voucher_no, party, gstin, reference, ledgers:[{"{"}name, amount{"}"}]{"}"}]</code>. Tax ledgers are classified by name (IGST / CGST / SGST / UTGST / Cess); purchases are tagged Inputs / Capital goods / Input services from ledger names.</p>
        </div>
      </div>
      <div className="mt-5">
        <div className="mb-2 text-sm font-medium"><Term k="Table 6">Purchase categories</Term> <span className="text-xs font-normal text-muted-foreground">— used for the GSTR-9 Table 6B split; select rows to override</span></div>
        <DataTable
          rows={cd.purchases}
          rowKey={(p) => p.id}
          exportName={`${client.id}_purchase_categories`}
          selection={{ selected: sel, onChange: setSel }}
          maxHeight="40vh"
          empty={{ message: "Upload the purchase register to see purchases here." }}
          toolbar={
            <select aria-label="Set category for selected rows" disabled={!sel.size} className="h-8 rounded-md border bg-background px-2 text-sm disabled:opacity-50" value="" onChange={(e) => { if (!e.target.value) return; setPurchaseCategory(client.id, cd.purchases, [...sel], e.target.value as ItcType); toast.success(`${sel.size} invoice(s) set to ${e.target.value}`); setSel(new Set()); }}>
              <option value="">Set category for {sel.size} selected…</option>
              <option>Inputs</option><option>Capital goods</option><option>Input services</option>
            </select>
          }
          columns={[
            { key: "party", title: "Supplier", header: "Supplier", value: (p) => p.party, filter: true },
            { key: "no", title: "Invoice no", header: "Invoice no", value: (p) => p.no, cell: (p) => <span className="font-mono text-xs">{p.no}</span> },
            { key: "date", title: "Date", header: "Date", value: (p) => p.date, cell: (p) => fmtDate(p.date) },
            { key: "cat", title: "Category", header: "Category", value: (p) => p.itcType ?? "Inputs", filter: true },
            { key: "taxable", title: "Taxable", header: "Taxable", value: (p) => p.taxable, money: true, align: "right" },
            { key: "tax", title: "GST", header: "GST", value: (p) => totalTax(p), money: true, align: "right" },
          ]}
        />
      </div>
      {map && <MappingDialog state={map} clientId={client.id} remembered={up.mapping?.[map.kind]} onClose={() => setMap(null)} />}
    </Panel>
  );
}

function MappingDialog({ state, clientId, remembered, onClose }: { state: { kind: "sales" | "purchase"; name: string; headers: string[]; records: Record<string, unknown>[] }; clientId: string; remembered?: Record<string, string> | undefined; onClose: () => void }) {
  const initial = remembered && Object.values(remembered).every((h) => state.headers.includes(h)) ? remembered : guessMapping(state.headers);
  const [m, setM] = useState<Partial<Record<RegisterField, string>>>(initial);
  const fields = REGISTER_FIELDS.filter((f) => !(state.kind === "sales" && (f === "sup_inv_no" || f === "category")));
  const missing = REQUIRED_FIELDS.filter((f) => !m[f]);
  const save = () => {
    const rows = registerToInvoices(state.records, m, state.kind);
    if (!rows.length) return void toast.error("No rows with a valid date and amount — please check the Date and Taxable value columns.");
    saveMapping(clientId, state.kind, m as Record<string, string>);
    storeBooks(clientId, state.kind === "sales" ? "sales" : "purchases", rows, `Tally export: ${state.name}`);
    addUploadedFile(clientId, { name: state.name, kind: `Tally ${state.kind === "sales" ? "Sales" : "Purchase"} Register`, period: "FY 2025-26", rows: rows.length, gstin: "", status: "Imported" });
    toast.success(`${rows.length} ${state.kind} vouchers loaded`);
    onClose();
  };
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>Match your {state.kind === "sales" ? "Sales" : "Purchase"} Register columns</DialogTitle>
          <DialogDescription>Tell us which column holds each value. We remember this for the client, so next time it is automatic. Fields marked * are required.</DialogDescription>
        </DialogHeader>
        <div className="grid gap-3 sm:grid-cols-2">
          {fields.map((f) => (
            <label key={f} className="flex items-center justify-between gap-2 text-sm">
              <span>{REGISTER_FIELD_LABELS[f]}{REQUIRED_FIELDS.includes(f) && " *"}</span>
              <select className="h-8 w-52 rounded-md border bg-background px-2 text-sm" value={m[f] ?? ""} onChange={(e) => setM({ ...m, [f]: e.target.value || undefined })}>
                <option value="">— not mapped —</option>
                {state.headers.map((h) => <option key={h}>{h}</option>)}
              </select>
            </label>
          ))}
        </div>
        <div className="overflow-x-auto rounded-md border">
          <table className="w-full text-xs">
            <thead className="bg-muted"><tr>{state.headers.map((h) => <th key={h} className="whitespace-nowrap px-2 py-1 text-left font-medium">{h}</th>)}</tr></thead>
            <tbody>{state.records.slice(0, 5).map((r, i) => <tr key={i} className="border-t">{state.headers.map((h) => <td key={h} className="whitespace-nowrap px-2 py-1">{String(r[h] ?? "")}</td>)}</tr>)}</tbody>
          </table>
        </div>
        {missing.length > 0 && <p className="text-sm text-destructive">Please map: {missing.map((f) => REGISTER_FIELD_LABELS[f]).join(", ")}</p>}
        <DialogFooter>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button disabled={missing.length > 0} onClick={save}>Use this mapping</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function SupplierFollowUp({ client }: { client: Client }) {
  const followUps = useApp((s) => s.followUps);
  const firm = useApp((s) => s.firm);
  const tol = useApp((s) => s.prefs.tolerance);
  const groups = supplierSummary(client.id, tol);
  if (groups.length === 0)
    return <Panel title="Supplier follow-up"><p className="text-sm text-muted-foreground">Nothing to follow up — every supplier has reported your purchase invoices correctly.</p></Panel>;
  const total = groups.reduce((s, g) => s + g.atRisk, 0);
  return (
    <Panel title={<Term k="ITC at risk">Suppliers to follow up — largest ITC at risk first</Term>} actions={<span className="text-sm font-semibold">{inr(total)} at risk</span>}>
      <div className="space-y-4">
        {groups.map(({ gstin, party: name, rows, atRisk }) => {
          const key = `${client.id}|${gstin}`;
          const msg = `Subject: GST invoices missing / mismatched in GSTR-2B — ${client.name}\n\nDear ${name},\n\nWe act for ${client.name} (GSTIN ${client.gstin}). While reconciling our purchase records with GSTR-2B, the following invoices issued by you (GSTIN ${gstin}) are not correctly reflected:\n\n${rows.map((r) => `- ${r.books!.no} dated ${fmtDate(r.books!.date)}: taxable ${inr(r.books!.taxable)}, GST ${inr(totalTax(r.books!))} — ${r.kind === "Only in Books" ? "not reported in your GSTR-1" : `reported with GST ${inr(totalTax(r.ret!))} (value mismatch)`}`).join("\n")}\n\nTotal GST at risk: ${inr(atRisk)}\n\nKindly report or amend these invoices in your next GSTR-1 / IFF so that the credit reflects in our GSTR-2B, and confirm once done.\n\nRegards,\n${firm?.partner ?? ""}\n${firm?.name ?? ""}`;
          return (
            <div key={gstin} className="rounded-md border p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div><div className="font-medium">{name}</div><div className="font-mono text-[11px] text-muted-foreground">{gstin}</div></div>
                <div className="text-right">
                  <Money value={atRisk} rows={rows.map((r) => ({ ...r.books!, note: r.kind }))} title={`${name} — invoices to follow up`} className="font-semibold" />
                  <div className="text-xs text-muted-foreground">{rows.length} invoice(s) · ITC at risk</div>
                </div>
              </div>
              <ul className="mt-3 space-y-1 text-sm">
                {rows.map((r) => (
                  <li key={r.books!.id} className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs">{r.books!.no}</span>
                    <span className="text-xs text-muted-foreground">{fmtDate(r.books!.date)}</span>
                    <StatusBadge status={r.kind} />
                    <span className="text-xs text-muted-foreground">books {inr(totalTax(r.books!))}{r.ret ? ` vs 2B ${inr(totalTax(r.ret))}` : ""}</span>
                  </li>
                ))}
              </ul>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <Button size="sm" variant="outline" onClick={() => { void navigator.clipboard?.writeText(msg); toast.success("Follow-up email copied — paste it into your mail app"); }}><Copy className="mr-1.5 h-3.5 w-3.5" /> Copy follow-up email</Button>
                <Button size="sm" onClick={() => markFollowUp(key, client.id, name)}>Mark reminder sent</Button>
                {followUps[key] && <span className="text-xs text-muted-foreground">Last reminder: {fmtDateTime(followUps[key]!)}</span>}
              </div>
            </div>
          );
        })}
      </div>
    </Panel>
  );
}

export type { Invoice };
