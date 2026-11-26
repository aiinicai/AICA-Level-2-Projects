// Clause 44 report – ledger-wise working of a Tally import: settings, parties to check on the GST portal,
// every ledger with its break-up (party-wise on opening), and the reconciliation with the books.
import { ReactNode, useCallback, useEffect, useRef, useState } from "react";
import { ChevronDown, ChevronRight, ExternalLink, FileUp, Flag, ListChecks } from "lucide-react";
import { useFirm } from "@/contexts/FirmContext";
import { useToast } from "@/components/Toast";
import { Alert, Badge, Button, Card, CardHeader, Modal, Select, Spinner, Toggle, cn } from "@/components/ui";
import { supabase } from "@/integrations/supabase/client";
import { CATEGORY_COLOR, CATEGORY_LABEL, type Category } from "@/lib/clause44";
import { formatINR } from "@/lib/format";
import { errMsg } from "@/lib/db";
import { parseFile } from "@/lib/import/parseFile";
import { ACCEPTED_FILES } from "@/lib/import/parseFile";
import { GST_PORTAL_SEARCH, GST_STATUS_LABEL, KIND_LABEL, exemptTax, gstinsIn2B, type GstStatus } from "@/lib/c44/books";
import { buildLedgerReport, ledgerChosen, ledgerTax, type C44Books, type C44Settings, type Cols, type LedgerLine, type LedgerReport as Report, type PartyMasterLite, type RowLite } from "@/lib/c44/ledgerMethod";
import { currentBooks, freshAnswers, loadPartyMaster, loadRows, loadSettings, saveBooksMeta, saveSettings, syncRows } from "@/lib/c44/ledgerStore";
import type { WorkbookSheets } from "@/lib/export";
import { callConnector, connectorVersion, versionAtLeast, GST_VERSION, type PortalResult } from "@/lib/tallyConnector";
import { sheetFromAoa } from "@/lib/export";

const db = supabase as any;
const COLS: Category[] = ["exempt", "composition", "other_registered", "unregistered"];
const amt = (n: number) => formatINR(n, { symbol: false });

interface Data { books: C44Books; rows: RowLite[]; pms: Record<string, PartyMasterLite>; s: C44Settings; report: Report }

/** Loads (and keeps in step) everything the ledger-wise report needs. null = this year has no Tally ledger import. */
export async function loadLedgerData(engagement: any, clientId: string, sync: boolean): Promise<Data | null> {
  const books = await currentBooks({ ...engagement, clause_answers: await freshAnswers(engagement.id) });
  if (!books) return null;
  const [rows0, pms, st] = await Promise.all([loadRows(engagement.id), loadPartyMaster(clientId), loadSettings(clientId)]);
  let rows = rows0;
  if (sync && (await syncRows(engagement, rows, books, pms, st.settings)) > 0) rows = await loadRows(engagement.id);
  return { books, rows, pms, s: st.settings, report: buildLedgerReport(rows, books, pms, st.settings) };
}

/** Sheets of the ledger-wise working for the Excel workbook. */
export function ledgerSheets(r: Report): WorkbookSheets {
  const head = ["Ledger", "Group", "Total", "Exempt", "Composition", "Other registered", "Unregistered"];
  const line = (l: LedgerLine) => [l.name, l.group, l.cols.total, l.cols.exempt, l.cols.composition, l.cols.other_registered, l.cols.unregistered];
  const tot = (label: string, c: Cols) => [label, "", c.total, c.exempt, c.composition, c.other_registered, c.unregistered];
  const lw: (string | number | null)[][] = [["Clause 44 – ledger-wise break-up"], [], head];
  if (r.revenue.length) { lw.push([KIND_LABEL.revenue]); r.revenue.forEach((l) => lw.push(line(l))); lw.push(tot("Total revenue expenditure", r.totals.revenue)); lw.push([]); }
  if (r.capital.length) { lw.push([KIND_LABEL.capital]); r.capital.forEach((l) => lw.push(line(l))); lw.push(tot("Total capital expenditure", r.totals.capital)); lw.push([]); }
  if (r.other.length) { lw.push(["Other uploaded entries"]); r.other.forEach((l) => lw.push(line(l))); lw.push(tot("Total other entries", r.totals.other)); lw.push([]); }
  lw.push(tot("Total (Clause 44)", r.totals.all));
  const lp: (string | number | null)[][] = [["Ledger", "Party", "GSTIN", "GST status", "Column", "Amount"]];
  [...r.revenue, ...r.capital, ...r.other].forEach((l) => l.parties.forEach((p) => lp.push([l.name, p.name, p.gstin, p.status ? GST_STATUS_LABEL[p.status] : "", CATEGORY_LABEL[p.category], p.amount])));
  const rv: (string | number | null)[][] = [["Party", "GSTIN", "Amount", "Status used", "To check", "Checked by you"]];
  [...r.review, ...r.checked].forEach((p) => rv.push([p.name, p.gstin, p.amount, GST_STATUS_LABEL[p.status], p.reasons.join("; "), p.checked ? GST_STATUS_LABEL[p.checked] : ""]));
  const rc: (string | number | null)[][] = [["Reconciliation with the books"], [],
    ["Expenses in the books (Purchase, Direct and Indirect Expenses)", r.recon.booksRevenue],
    ["Less: ledgers left out of Clause 44", -r.recon.excludedRevenue],
    ...r.excluded.map((e) => [`      ${e.name} (${e.reason})`, -e.amount]),
    ["Add: capital expenditure (additions to Fixed Assets)", r.recon.capitalAdditions],
    ...(r.recon.otherRows ? [["Add: entries uploaded from other files", r.recon.otherRows]] : []),
    ["Total expenditure reported in Clause 44", r.recon.reported]];
  return [
    { name: "Ledger-wise", ws: sheetFromAoa(lw, [40, 28, 16, 16, 16, 16, 16]) },
    { name: "Ledger x party", ws: sheetFromAoa(lp, [36, 36, 18, 14, 18, 16]) },
    { name: "Parties to check", ws: sheetFromAoa(rv, [36, 18, 16, 14, 40, 14]) },
    { name: "Reconciliation (books)", ws: sheetFromAoa(rc, [60, 18]) },
  ];
}

interface Props { engagement: any; client: any; editable: boolean; onChanged: () => void; children?: ReactNode }

export function LedgerReport({ engagement, client, editable, onChanged, children }: Props) {
  const { firm } = useFirm();
  const toast = useToast();
  const [d, setD] = useState<Data | null | undefined>(undefined);
  const [open, setOpen] = useState<Record<string, boolean>>({});
  const [busy, setBusy] = useState("");
  const [ledgersOpen, setLedgersOpen] = useState(false);
  const [checkOpen, setCheckOpen] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    try { setD(await loadLedgerData(engagement, engagement.client_id, editable)); } catch (e) { toast(errMsg(e), "error"); setD(null); }
  }, [engagement.id, engagement.clause_answers, editable]);
  useEffect(() => { load(); }, [load]);

  if (d === undefined) return <Card className="flex justify-center p-8"><Spinner /></Card>;
  if (d === null) return <>{children}</>;
  const { report: r, s, books } = d;

  /** Save the client's choices, bring rows in step and refresh the summary. */
  const apply = async (next: C44Settings, label = "Saving…") => {
    if (!firm) return;
    setBusy(label);
    try {
      await saveSettings(firm.id, engagement.client_id, next);
      const n = await syncRows(engagement, d.rows, books, d.pms, next);
      await load();
      if (n) onChanged();
    } catch (e) { toast(errMsg(e), "error"); }
    setBusy("");
  };
  /** The auditor's GST status of parties (several at once); "" = back to the books. */
  const decide = async (items: [string, GstStatus | ""][]) => {
    const checked = { ...s.checked };
    for (const [key, st] of items) { if (st) checked[key] = st; else delete checked[key]; }
    await apply({ ...s, checked });
  };

  const read2B = async (files: File[]) => {
    if (!files.length) return;
    setBusy("Reading GSTR-2B…");
    try {
      const own = ((client?.gstins ?? []) as string[]).map((o) => o.toUpperCase());
      const set = new Set<string>(books.b2b?.gstins ?? []);
      const names = new Set<string>(books.b2b?.files ?? []);
      for (const f of files) {
        const pf = await parseFile(f);
        gstinsIn2B(pf.sheets.map((x) => x.rows)).forEach((g) => { if (!own.includes(g)) set.add(g); });
        names.add(f.name);
      }
      await saveBooksMeta(engagement, { ...books, b2b: { gstins: Array.from(set).sort(), files: Array.from(names) } });
      toast(`${set.size} supplier GSTINs from GSTR-2B`);
      onChanged();
    } catch (e) { toast(errMsg(e), "error"); }
    setBusy("");
  };
  const clear2B = async () => { setBusy("Saving…"); try { await saveBooksMeta(engagement, { ...books, b2b: null }); onChanged(); } catch (e) { toast(errMsg(e), "error"); } setBusy(""); };

  const ColsCells = ({ c, bold }: { c: Cols; bold?: boolean }) => (<>
    <td className={cn("num", bold && "font-semibold")}>{amt(c.total)}</td>
    {COLS.map((k) => <td key={k} className={cn("num", bold && "font-semibold", !c[k] && "text-slate-300")}>{amt(c[k])}</td>)}
  </>);
  const sumCols = (ls: LedgerLine[]) => { const c = { total: 0, exempt: 0, composition: 0, other_registered: 0, unregistered: 0 } as Cols; ls.forEach((l) => (Object.keys(c) as (keyof Cols)[]).forEach((k) => { c[k] += l.cols[k]; })); return c; };
  /** kind → Tally group (collapsed) → ledgers → parties */
  const section = (title: string, lines: LedgerLine[], tot: Cols, key: string) => {
    if (!lines.length) return null;
    const groups = new Map<string, LedgerLine[]>();
    lines.forEach((l) => { const g = l.group || title; groups.set(g, [...(groups.get(g) ?? []), l]); });
    return (
      <>
        <tr className="bg-slate-50"><td colSpan={6} className="!py-1.5 text-xs font-semibold uppercase tracking-wide text-slate-600">{title}</td></tr>
        {Array.from(groups.entries()).map(([g, ls]) => {
          const gk = `${key}|g|${g}`;
          const gOpen = !!open[gk];
          return [
            <tr key={gk} className="cursor-pointer hover:bg-slate-50" onClick={() => setOpen({ ...open, [gk]: !gOpen })}>
              <td><span className="inline-flex items-center gap-1 font-semibold">{gOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}{g}</span>
                <span className="ml-1 text-xs text-slate-400">{ls.length} {ls.length === 1 ? "ledger" : "ledgers"}</span></td>
              <ColsCells c={sumCols(ls)} />
            </tr>,
            ...(gOpen ? ls.flatMap((l) => {
              const k = `${key}|${l.name}`;
              const isOpen = !!open[k];
              return [
                <tr key={k} className="cursor-pointer text-sm hover:bg-slate-50" onClick={() => setOpen({ ...open, [k]: !isOpen })}>
                  <td className="!pl-8"><span className="inline-flex items-center gap-1">{isOpen ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}{l.name}</span>
                    {exemptTax(l.tax) && <span className="ml-1 text-[11px] text-slate-400">exempt supply</span>}</td>
                  <ColsCells c={l.cols} />
                </tr>,
                isOpen && <tr key={`${k}|p`}><td colSpan={6} className="!p-0">
                  <table className="w-full text-xs"><tbody>{l.parties.map((p) => (
                    <tr key={p.key + p.category} className="border-t border-slate-100">
                      <td className="py-1 pl-16">{p.name}{p.gstin && <span className="ml-2 font-mono text-[10px] text-slate-400">{p.gstin}</span>}</td>
                      <td className="w-40"><Badge className={CATEGORY_COLOR[p.category]}>{CATEGORY_LABEL[p.category]}</Badge></td>
                      <td className="w-36 pr-4 text-right tabular-nums">{amt(p.amount)}</td>
                    </tr>))}</tbody></table>
                </td></tr>,
              ];
            }) : []),
          ];
        })}
        <tr className="border-t-2 border-slate-200"><td className="font-semibold">{`Total – ${title}`}</td><ColsCells c={tot} bold /></tr>
      </>
    );
  };
  const toCheckAmt = r.review.reduce((t, p) => t + p.amount, 0);

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader title="Ledger-wise working (from Tally)" subtitle={<>{books.file} · prepared {new Date(books.at).toLocaleDateString("en-IN")}</>}
          action={editable && <Button size="sm" variant="outline" icon={<ListChecks className="h-4 w-4" />} onClick={() => setLedgersOpen(true)} disabled={!!busy}>Change ledgers</Button>} />
        <div className="px-5 pb-4">
          {r.review.length > 0 ? (
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
              <div className="flex items-center gap-2 text-sm"><Flag className="h-4 w-4 text-amber-600" />
                <span><b>{r.review.length} {r.review.length === 1 ? "party" : "parties"}</b> to check on the GST portal <span className="text-slate-600">({formatINR(toCheckAmt)})</span>{r.checked.length ? <span className="text-slate-500"> · {r.checked.length} checked</span> : null}</span></div>
              <Button size="sm" onClick={() => setCheckOpen(true)}>Check parties</Button>
            </div>
          ) : (
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm">
              <span className="text-emerald-800">No party needs checking.{r.checked.length ? ` ${r.checked.length} checked by you.` : ""}</span>
              {r.checked.length > 0 && <Button size="sm" variant="ghost" onClick={() => setCheckOpen(true)}>See checked</Button>}
            </div>
          )}
          <details className="mt-3 text-sm">
            <summary className="cursor-pointer text-slate-600">Settings: bank charges, GSTR-2B</summary>
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              <label className="flex items-start gap-2"><Toggle checked={s.bankRegular} disabled={!editable || !!busy} onChange={(v) => apply({ ...s, bankRegular: v })} />
                <span>Bank charges = <b>other registered</b><span className="block text-xs text-slate-500">Bank charges debited directly by the bank are shown as paid to a registered bank.</span></span></label>
              <div className="flex items-start gap-2">
                <FileUp className="mt-0.5 h-4 w-4 shrink-0 text-navy-600" />
                <div>
                  <div>GSTR-2B: {books.b2b?.gstins?.length ? <b>{books.b2b.gstins.length} supplier GSTINs from {books.b2b.files.length} {books.b2b.files.length === 1 ? "file" : "files"}</b> : <span className="text-slate-500">not given</span>}</div>
                  <div className="text-xs text-slate-500">A registered party that never appears in GSTR-2B is marked for checking (it may be a composition dealer).</div>
                  {editable && <div className="mt-1 flex gap-2">
                    <Button size="sm" variant="outline" onClick={() => fileRef.current?.click()} disabled={!!busy}>Add GSTR-2B files</Button>
                    {books.b2b?.gstins?.length ? <Button size="sm" variant="ghost" onClick={clear2B} disabled={!!busy}>Remove</Button> : null}
                  </div>}
                  <input ref={fileRef} type="file" multiple accept={ACCEPTED_FILES} className="hidden" onChange={(e) => { const l: File[] = e.target.files ? Array.from(e.target.files) : []; e.target.value = ""; read2B(l); }} />
                </div>
              </div>
            </div>
          </details>
        </div>
        {busy && <div className="flex items-center gap-2 border-t border-slate-100 px-5 py-2 text-sm text-slate-600"><Spinner className="h-4 w-4" />{busy}</div>}
      </Card>

      <Card>
        <CardHeader title="Ledger-wise break-up" subtitle="Click a group to see its ledgers, and a ledger to see its parties." />
        <div className="overflow-x-auto">
          <table className="table-pro min-w-[860px]">
            <thead><tr><th>Ledger</th><th className="text-right">Total</th>{COLS.map((k) => <th key={k} className="text-right">{CATEGORY_LABEL[k]}</th>)}</tr></thead>
            <tbody>
              {section(KIND_LABEL.revenue, r.revenue, r.totals.revenue, "r")}
              {section(KIND_LABEL.capital, r.capital, r.totals.capital, "c")}
              {section("Entries uploaded from other files", r.other, r.totals.other, "o")}
              <tr className="bg-navy-950 text-white"><td className="font-semibold">Total (Clause 44)</td><ColsCells c={r.totals.all} bold /></tr>
            </tbody>
          </table>
        </div>
      </Card>

      {children}

      <Card>
        <CardHeader title="Reconciliation with the books" subtitle="Working paper as suggested in the ICAI Guidance Note on Tax Audit – expenses in the P&L, less items not reported, plus capital expenditure." />
        <dl className="space-y-1.5 px-5 py-4 text-sm">
          <RL k="Expenses in the books (Purchase, Direct and Indirect Expenses)" v={r.recon.booksRevenue} />
          <RL k="Less: ledgers left out of Clause 44" v={-r.recon.excludedRevenue} />
          {r.excluded.map((e) => <RL key={e.name} k={<span className="pl-5 text-slate-500">{e.name} <span className="text-xs">({e.reason})</span></span>} v={-e.amount} small />)}
          <RL k="Add: capital expenditure (additions to Fixed Assets)" v={r.recon.capitalAdditions} />
          {r.recon.otherRows ? <RL k="Add: entries uploaded from other files" v={r.recon.otherRows} /> : null}
          <RL k="Total expenditure reported in Clause 44" v={r.recon.reported} bold />
        </dl>
        <p className="border-t border-slate-100 px-5 py-2 text-xs text-slate-500">The books figure is the net of the vouchers of the period (opening / closing stock are not vouchers). Compare it with the P&L of the audited accounts.</p>
      </Card>

      {ledgersOpen && <LedgersModal books={books} s={s} onClose={() => setLedgersOpen(false)} onSave={async (next) => { setLedgersOpen(false); await apply(next, "Updating ledgers…"); }} />}
      {checkOpen && <CheckPartiesModal report={r} editable={editable} busy={!!busy} onClose={() => setCheckOpen(false)} onDecide={decide} />}
    </div>
  );
}

/** Statuses from the GST portal page ("Taxpayer Type" / "GSTIN / UIN Status"). */
export function portalStatus(taxpayerType: string, status: string): GstStatus | null {
  if (status && !/^active/i.test(status.trim())) return null;   // cancelled / suspended – the auditor decides
  if (/composition/i.test(taxpayerType)) return "composition";
  return taxpayerType.trim() ? "regular" : null;
}

function CheckPartiesModal({ report, editable, busy, onClose, onDecide }: { report: Report; editable: boolean; busy: boolean; onClose: () => void; onDecide: (items: [string, GstStatus | ""][]) => Promise<void> }) {
  const toast = useToast();
  const [tab, setTab] = useState<"todo" | "done">(report.review.length ? "todo" : "done");
  const [version, setVersion] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, PortalResult>>({});
  const [watching, setWatching] = useState<string[]>([]);
  useEffect(() => { setVersion(connectorVersion()); }, []);
  const latest = useRef({ onDecide, report });
  latest.current = { onDecide, report };
  const auto = versionAtLeast(version, GST_VERSION);
  // results come back from the portal tab through the connector
  useEffect(() => {
    if (!auto || !watching.length) return;
    let live = true;
    const t = setInterval(async () => {
      try {
        const r = await callConnector<{ results: Record<string, PortalResult> }>("gstResults", { gstins: watching });
        if (!live) return;
        const got = Object.entries(r.result.results ?? {});
        if (!got.length) return;
        setResults((x) => ({ ...x, ...r.result.results }));
        setWatching((w) => w.filter((g) => !r.result.results[g]));
        const apply: [string, GstStatus | ""][] = [];
        for (const [g, res] of got) {
          const st = portalStatus(res.taxpayerType, res.status);
          const p = latest.current.report.review.find((x) => x.gstin === g);
          if (st && p) apply.push([p.key, st]);
        }
        if (apply.length) { await latest.current.onDecide(apply); toast(`Saved from the GST portal: ${apply.length}`); }
      } catch { /* connector not answering – keep waiting */ }
    }, 2500);
    const stop = setTimeout(() => setWatching([]), 15 * 60 * 1000);
    return () => { live = false; clearInterval(t); clearTimeout(stop); };
  }, [auto, watching.join()]);

  const openPortal = async (gstin: string) => {
    if (!gstin) return;
    if (auto) {
      try { await callConnector("gstOpen", { gstin }); setWatching((w) => Array.from(new Set([...w, gstin]))); return; }
      catch (e) { toast(errMsg(e), "error"); }
    }
    try { await navigator.clipboard?.writeText(gstin); } catch { /* ignore */ }
    window.open(GST_PORTAL_SEARCH, "_blank", "noopener");
  };

  const list = tab === "todo" ? report.review : report.checked;
  return (
    <Modal open onClose={onClose} title="Check parties on the GST portal" wide
      footer={<>{tab === "todo" && editable && report.review.length > 0 && <Button variant="outline" disabled={busy} onClick={() => onDecide(report.review.map((p) => [p.key, p.status]))}>Keep all as per books</Button>}<Button onClick={onClose}>Done</Button></>}>
      <div className="mb-3 flex gap-2">
        <Button size="sm" variant={tab === "todo" ? "primary" : "ghost"} onClick={() => setTab("todo")}>To check ({report.review.length})</Button>
        <Button size="sm" variant={tab === "done" ? "primary" : "ghost"} onClick={() => setTab("done")}>Checked ({report.checked.length})</Button>
      </div>
      <Alert tone="info" className="mb-3">
        {auto ? <>Click <b>Portal</b>: the GSTIN is filled in on the GST portal by itself. Type the captcha and press Search – the taxpayer type comes back here and is saved.</>
          : <>Click <b>Portal</b>: the GSTIN is copied – paste it, type the captcha, then choose the status here. With Tally Connector {GST_VERSION} or later the GSTIN fills itself and the result comes back by itself.</>}
      </Alert>
      <div className="max-h-[55vh] overflow-auto">
        <table className="table-pro">
          <thead><tr><th>Party</th><th className="text-right">Amount</th><th>GST status</th><th></th></tr></thead>
          <tbody>
            {list.map((p) => {
              const res = p.gstin ? results[p.gstin] : undefined;
              return (
                <tr key={p.key}>
                  <td><div className="font-medium">{p.name}</div>
                    <div className="font-mono text-[11px] text-slate-500">{p.gstin || "no GSTIN"}</div>
                    {tab === "todo" && <div className="text-[11px] text-amber-700">{p.reasons.join(" · ")}</div>}
                    {res && <div className="text-[11px] text-emerald-700">Portal: {res.taxpayerType}{res.status ? ` · ${res.status}` : ""}{res.legalName ? ` · ${res.legalName}` : ""}</div>}
                    {p.gstin && watching.includes(p.gstin) && <div className="text-[11px] text-slate-500">Waiting for the portal…</div>}</td>
                  <td className="num">{amt(p.amount)}</td>
                  <td><Select aria-label={`GST status of ${p.name}`} className="h-8 w-40 text-xs" value={p.checked ?? ""} disabled={!editable || busy} onChange={(e) => onDecide([[p.key, e.target.value as GstStatus | ""]])}>
                    <option value="">{p.checked ? "Back to the books" : `As per books (${GST_STATUS_LABEL[p.status]})`}</option>
                    {(Object.keys(GST_STATUS_LABEL) as GstStatus[]).map((k) => <option key={k} value={k}>{GST_STATUS_LABEL[k]}</option>)}
                  </Select></td>
                  <td>{p.gstin && <Button size="sm" variant="outline" icon={<ExternalLink className="h-3.5 w-3.5" />} onClick={() => openPortal(p.gstin)}>Portal</Button>}</td>
                </tr>);
            })}
            {!list.length && <tr><td colSpan={4} className="text-sm text-slate-500">{tab === "todo" ? "Nothing left to check." : "No party checked yet."}</td></tr>}
          </tbody>
        </table>
      </div>
    </Modal>
  );
}

function RL({ k, v, bold, small }: { k: ReactNode; v: number; bold?: boolean; small?: boolean }) {
  return <div className={cn("flex justify-between gap-4", bold && "border-t border-slate-200 pt-2 font-semibold", small && "text-xs")}><dt>{k}</dt><dd className="tabular-nums">{v < 0 ? `(${amt(-v)})` : amt(v)}</dd></div>;
}

function LedgersModal({ books, s, onClose, onSave }: { books: C44Books; s: C44Settings; onClose: () => void; onSave: (s: C44Settings) => void }) {
  const [n, setN] = useState<C44Settings>(s);
  const list = Object.entries(books.ledgers).sort((a, b) => a[1].k.localeCompare(b[1].k) * -1 || a[1].p.localeCompare(b[1].p) || Math.abs(b[1].total) - Math.abs(a[1].total));
  return (
    <Modal open onClose={onClose} title="Ledgers in Clause 44" wide
      footer={<><Button variant="ghost" onClick={onClose}>Cancel</Button><Button onClick={() => onSave(n)}>Save</Button></>}>
      <div className="max-h-[60vh] overflow-auto">
        <table className="table-pro">
          <thead><tr><th></th><th>Ledger</th><th>Group</th><th>GST</th><th className="text-right">Amount</th></tr></thead>
          <tbody>{list.map(([name, l]) => {
            const on = ledgerChosen(name, l, n);
            const t = ledgerTax(name, l, n);
            return (
              <tr key={name} className={cn(!on && "text-slate-400")}>
                <td><input type="checkbox" aria-label={name} className="h-4 w-4 accent-navy-900" checked={on} onChange={(e) => setN({ ...n, sel: { ...n.sel, [name.toLowerCase()]: e.target.checked } })} /></td>
                <td className="font-medium">{name}{l.x && <span className="ml-2 text-[11px] text-amber-700">{l.x}</span>}</td>
                <td className="text-xs">{l.k === "capital" ? "Fixed Assets" : l.p}{l.g && l.g !== l.p ? ` › ${l.g}` : ""}</td>
                <td><Select className="h-8 w-40 text-xs" value={exemptTax(t) ? "exempt" : "taxable"} onChange={(e) => setN({ ...n, tax: { ...n.tax, [name.toLowerCase()]: e.target.value as "taxable" | "exempt" } })}>
                  <option value="taxable">Taxable</option><option value="exempt">Exempt / nil / non-GST</option></Select></td>
                <td className="num">{amt(l.total)}</td>
              </tr>);
          })}</tbody>
        </table>
      </div>
      <Alert tone="info" className="mt-3">Your choice is kept for this client and used again next year.</Alert>
    </Modal>
  );
}
