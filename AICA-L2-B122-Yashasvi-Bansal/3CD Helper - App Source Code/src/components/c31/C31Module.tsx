import { useMemo, useRef, useState } from "react";
import { FileSpreadsheet, Flag, Trash2 } from "lucide-react";
import { supabase } from "@/integrations/supabase/client";
import { useFirm } from "@/contexts/FirmContext";
import { useToast } from "@/components/Toast";
import { Alert, Badge, Button, Card, Modal, Select, Spinner, Toggle, cn } from "@/components/ui";
import { useRows, useParties } from "@/hooks/useModuleData";
import { RowsGrid, type GridColumn } from "@/components/modules/RowsGrid";
import { Kpi, ReportTable, SubTabs, exportClauseWorkbook, type Col, type ExportSection } from "@/components/modules/common";
import { UploadsList } from "@/components/UploadsList";
import { C31Upload } from "./C31Upload";
import { WhatsAppShare } from "@/components/WhatsAppShare";
import { ClientLinkPanel } from "@/components/ClientLinkPanel";
import { computeClause31, combineRows, isCredit, txnKey, CHEQUE_ANSWER_LABEL, ENTRY_TYPE_LABEL, MODE_LABEL, NOTE1_CODES, type ChequeAnswer, type LoanTxn, type SameDayOrder, type C31Row } from "@/lib/c31/engine";
import { formatDate, formatINR } from "@/lib/format";
import { errMsg, logActivity } from "@/lib/db";
import { normalizeParty } from "@/lib/party";

type Row = LoanTxn & { row_no: number | null };
interface Bal { id: string; normalized_name: string; party_name: string; opening_balance: number }
type Tab = "upload" | "entries" | "parties" | "report";

const TYPE_OPTIONS = (["taken", "repaid", "specified_taken", "specified_repaid", "interest", "tds"] as const).map((v) => ({ value: v, label: ENTRY_TYPE_LABEL[v] }));
const ReviewMark = () => <span title="Review" className="inline-flex items-center gap-0.5 rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-amber-800"><Flag className="h-3 w-3" />Review</span>;

export function C31Module({ eng, client, editable, onEngChanged }: { eng: any; client: any; editable: boolean; onEngChanged: () => void }) {
  const { firm } = useFirm();
  const toast = useToast();
  const txns = useRows<Row>("loan_txns", eng.id, "txn_date");
  const bals = useRows<Bal>("loan_balances", eng.id, "party_name");
  const { parties, ensure, update } = useParties(eng.client_id);
  const [tab, setTab] = useState<Tab | null>(null);
  const [show, setShow] = useState<string | null>(null);
  const [incoming, setIncoming] = useState<File | null>(null);
  const [bulkMode, setBulkMode] = useState("");
  const [delRow, setDelRow] = useState<C31Row | null>(null);
  const queue = useRef<Promise<unknown>>(Promise.resolve());
  const order: SameDayOrder = eng.clause_answers?.c31_order ?? "credit_first";
  const cheque = useMemo<Record<string, ChequeAnswer>>(() => eng.clause_answers?.c31_cheque ?? {}, [eng.clause_answers]);
  const combine: boolean = !!eng.clause_answers?.c31_combine;

  const openings = useMemo(() => Object.fromEntries(bals.rows.map((b) => [b.normalized_name, Number(b.opening_balance)])), [bals.rows]);
  const result = useMemo(() => computeClause31(txns.rows.map((t) => ({ ...t, amount: Number(t.amount) })), openings, parties, { order, cheque }), [txns.rows, openings, parties, order, cheque]);
  const byKey = useMemo(() => { const m = new Map<string, Row>(); txns.rows.forEach((t) => m.set(txnKey(t), t)); return m; }, [txns.rows]);
  const lists = useMemo(() => [result.a, result.b, result.c, result.d, result.e].map((l) => (combine ? combineRows(l) : l)), [result, combine]);

  if (txns.loading || bals.loading) return <div className="flex justify-center py-12"><Spinner /></div>;
  const current: Tab = tab ?? (txns.rows.length ? "report" : "upload");

  // answers are merged into what is saved now, one save after another, so quick changes never undo each other
  const saveAnswers = (patch: (cur: Record<string, any>) => Record<string, unknown>) => {
    const run = queue.current.then(async () => {
      const { data, error: rErr } = await supabase.from("engagements").select("clause_answers").eq("id", eng.id).single();
      if (rErr) throw rErr;
      const cur = ((data?.clause_answers ?? {}) as Record<string, any>);
      const { error } = await supabase.from("engagements").update({ clause_answers: { ...cur, ...patch(cur) } as any }).eq("id", eng.id);
      if (error) throw error;
    }).then(() => onEngChanged(), (e) => toast(errMsg(e), "error"));
    queue.current = run;
    return run;
  };
  const setOrder = (o: SameDayOrder) => saveAnswers(() => ({ c31_order: o }));
  const setCheque = (keys: string[], a: ChequeAnswer) => saveAnswers((cur) => {
    const next = { ...(cur.c31_cheque ?? {}) };
    keys.forEach((k) => { next[k] = a; });
    return { c31_cheque: next };
  });

  const bulk = (ids: string[], clear: () => void) => (
    <span className="flex items-center gap-1.5">
      <Select aria-label="Set mode" className="h-8 w-56 text-xs" value={bulkMode} onChange={(e) => setBulkMode(e.target.value)}>
        <option value="">Set mode of {ids.length} ticked…</option>
        {Object.entries(MODE_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
      </Select>
      <Button size="sm" disabled={!bulkMode} onClick={async () => {
        try { await txns.patchMany(ids, { mode: bulkMode } as Partial<Row>); toast(`Mode set on ${ids.length} entries`); setBulkMode(""); clear(); }
        catch (e) { toast(errMsg(e), "error"); }
      }}>Apply</Button>
    </span>
  );

  // "How paid / received" on each report line: changes the mode of that line's entries
  const HOW: [string, string][] = [["electronic", "Bank – NEFT / RTGS / UPI / ECS"], ["cheque", "A/c payee cheque"], ["draft", "A/c payee draft"], ["no", "Cheque / draft – not a/c payee"],
    ["cash", "Cash"], ["journal", "Journal entry"], ["transfer", "Transfer / adjustment"], ["other", "Other"]];
  const howOf = (row: C31Row) => row.cheque ? (row.chequeAnswer ?? "cheque") : (byKey.get(row.keys[0])?.mode ?? "other");
  const setHow = async (row: C31Row, v: string) => {
    const ids = row.keys.map((k) => byKey.get(k)?.id).filter(Boolean) as string[];
    if (!ids.length) return;
    try {
      const mode = v === "cheque" || v === "draft" ? "ac_payee_cheque" : v === "no" ? "non_ac_payee_cheque" : v;
      await txns.patchMany(ids, { mode } as Partial<Row>);
      if (v === "cheque" || v === "draft" || v === "no") await setCheque(row.keys, v as ChequeAnswer);
    } catch (e) { toast(errMsg(e), "error"); }
  };

  const columns: GridColumn<Row>[] = [
    { key: "txn_date", label: "Date", type: "date" },
    { key: "party_name", label: "Party (ledger)", type: "readonly", width: "200px" },
    { key: "kind", label: "Debit / credit", type: "select", required: true, options: [...TYPE_OPTIONS, ...(["given", "repayment_received"] as const).map((v) => ({ value: v, label: ENTRY_TYPE_LABEL[v] }))], width: "230px" },
    { key: "amount", label: "Amount", type: "number", width: "130px", min0: true },
    { key: "mode", label: "Mode", type: "select", required: true, options: Object.entries(MODE_LABEL).map(([value, label]) => ({ value, label })), width: "210px" },
    { key: "nature_code", label: "Code (Note 1)", type: "select", options: [{ value: "", label: "Auto" }, ...Object.entries(NOTE1_CODES).map(([value, label]) => ({ value, label: `${value} – ${label}` }))], width: "130px" },
    { key: "voucher_no", label: "Voucher", width: "110px" },
    { key: "include", label: "Include", type: "bool" },
    { key: "remark", label: "Narration / remark", width: "220px" },
  ];
  const addRow = async () => {
    const name = prompt("Party name (lender / borrower ledger)");
    if (!name?.trim()) return;
    try {
      await txns.add({ engagement_id: eng.id, firm_id: firm!.id, party_name: name.trim(), normalized_name: normalizeParty(name) || name.trim().toLowerCase(), kind: "taken", amount: 0, mode: "electronic" });
      await ensure([{ party_name: name.trim() }]);
    } catch (e) { toast(errMsg(e), "error"); }
  };

  const meta = { client: client.name, pan: client.pan, ay: eng.assessment_year, firm: firm?.name };
  const C_A: Col[] = [{ label: "Name of lender / depositor" }, { label: "Address" }, { label: "PAN" }, { label: "Amount", num: true }, { label: "Code" }, { label: "Squared up during the PY?" }, { label: "Maximum amount outstanding", num: true }, { label: "Otherwise than by a/c payee cheque / draft / ECS?" }, { label: "If by cheque / draft, a/c payee?" }];
  const C_C: Col[] = [{ label: "Name of payee" }, { label: "Address" }, { label: "PAN" }, { label: "Amount of repayment", num: true }, { label: "Code" }, { label: "Maximum amount outstanding", num: true }, { label: "Otherwise than by a/c payee cheque / draft / ECS?" }, { label: "If by cheque / draft, a/c payee?" }];
  const C_D: Col[] = [{ label: "Name of payer" }, { label: "Address" }, { label: "PAN" }, { label: "Amount of repayment received", num: true }];
  const mark = (r: C31Row) => (r.review ? "Review" : "");
  const RV: Col = { label: "Review" };
  const sec: ExportSection[] = [
    { sheet: "31(a)", title: "31(a) Particulars of each loan or deposit in an amount exceeding the limit specified in section 269SS taken or accepted during the previous year", cols: [...C_A, RV], rows: lists[0].map((r) => [r.party_name, r.address, r.pan, r.amount, r.code, r.squaredUp, r.maxOutstanding, r.otherwise, r.acPayee, mark(r)]) },
    { sheet: "31(b)", title: "31(b) Particulars of each specified sum in an amount exceeding the limit specified in section 269SS taken or accepted during the previous year", cols: [...C_A, RV], rows: lists[1].map((r) => [r.party_name, r.address, r.pan, r.amount, r.code, r.squaredUp, r.maxOutstanding, r.otherwise, r.acPayee, mark(r)]) },
    { sheet: "31(c)", title: "31(c) Particulars of each repayment of loan or deposit or any specified advance in an amount exceeding the limit specified in section 269T made during the previous year", cols: [...C_C, RV], rows: lists[2].map((r) => [r.party_name, r.address, r.pan, r.amount, r.code, r.maxOutstanding, r.otherwise, r.acPayee, mark(r)]) },
    { sheet: "31(d)", title: "31(d) Particulars of repayment of loan or deposit or any specified advance in an amount exceeding the limit specified in section 269T received otherwise than by a cheque or bank draft or use of electronic clearing system through a bank account", cols: [...C_D, RV], rows: lists[3].map((r) => [r.party_name, r.address, r.pan, r.amount, mark(r)]) },
    { sheet: "31(e)", title: "31(e) Particulars of repayment of loan or deposit or any specified advance in an amount exceeding the limit specified in section 269T received by a cheque or bank draft which is not an account payee cheque or account payee bank draft", cols: [...C_D, RV], rows: lists[4].map((r) => [r.party_name, r.address, r.pan, r.amount, mark(r)]) },
  ];
  const showParty = show ? result.parties.find((p) => p.normalized_name === show) : null;

  return (
    <div>
      <SubTabs<Tab> value={current} onChange={setTab} tabs={[["upload", "Upload"], ["entries", "Entries", <Badge key="e" className="ml-1.5 bg-navy-50 text-navy-800">{txns.rows.length}</Badge>],
        ["parties", "Parties & opening balances"], ["report", "Clause 31 report", result.reviewParties ? <Badge key="r" className="ml-1.5 bg-amber-100 text-amber-800">{result.reviewParties}</Badge> : undefined]]} />

      {current === "upload" && (
        <div className="space-y-4">
          {editable ? <C31Upload eng={eng} clientId={eng.client_id} clientName={client.name} incoming={incoming} ensureParties={ensure} existingOpenings={Object.fromEntries(bals.rows.map((b) => [b.normalized_name, b.id]))}
            onDone={() => { setIncoming(null); txns.reload(); bals.reload(); setTab("report"); }} /> : <Alert tone="info">This year is locked or read-only.</Alert>}
          <ClientLinkPanel engagement={eng} client={client} module="clause31" editable={editable} onUse={(f) => { setIncoming(f); window.scrollTo({ top: 0, behavior: "smooth" }); }} />
          <UploadsList engagementId={eng.id} module="clause31" editable={editable} onChanged={() => { txns.reload(); }} />
        </div>
      )}

      {current === "entries" && (
        <RowsGrid<Row> rows={txns.rows} columns={columns} editable={editable} onPatch={txns.patch} onDelete={txns.remove} onAdd={addRow} addLabel="Add entry"
          searchKeys={["party_name", "remark", "voucher_no"]} bulkActions={bulk} rowClass={(r) => (!r.include ? "text-slate-400" : "")}
          toolbar={<span className="text-xs text-slate-500">Tick rows (or search, then "Select all") to set the mode together – NEFT, RTGS, UPI and ECS are all "Bank". Debit / credit is of the party's account; loan taken, repayment, loan given or received back is worked out from the running balance.</span>} />
      )}

      {current === "parties" && (
        <Card>
          <div className="overflow-x-auto">
            <table className="table-pro">
              <thead><tr><th>Name in report</th><th>PAN</th><th>Address</th><th className="text-right">Opening (Cr + / Dr −)</th><th className="text-right">Credits</th><th className="text-right">Debits</th><th className="text-right">Closing</th><th>Bank / Govt lender</th></tr></thead>
              <tbody>
                {result.parties.map((p) => {
                  const pm = parties[p.normalized_name];
                  const bal = bals.rows.find((b) => b.normalized_name === p.normalized_name);
                  return (
                    <tr key={p.normalized_name}>
                      <td>
                        <input key={p.party_name} disabled={!editable || !pm} defaultValue={p.party_name} className="h-8 w-48 rounded border border-slate-200 px-1.5 text-sm font-medium"
                          onBlur={(e) => { const v = e.target.value.trim(); if (pm && v && v !== p.party_name) update(p.normalized_name, { party_name: v }).catch((x) => toast(errMsg(x), "error")); }} />
                        {pm && txns.rows.find((t) => t.normalized_name === p.normalized_name)?.party_name !== p.party_name && <div className="mt-0.5 text-[10px] text-slate-400">Ledger: {txns.rows.find((t) => t.normalized_name === p.normalized_name)?.party_name}</div>}
                      </td>
                      <td><input disabled={!editable || !pm} defaultValue={pm?.pan ?? p.pan} className="h-8 w-28 rounded border border-slate-200 px-1.5 font-mono text-xs uppercase" onBlur={(e) => pm && e.target.value.toUpperCase() !== (pm.pan ?? "") && update(p.normalized_name, { pan: e.target.value.toUpperCase() || null }).catch((x) => toast(errMsg(x), "error"))} /></td>
                      <td><input disabled={!editable || !pm} defaultValue={pm?.address ?? ""} className="h-8 w-52 rounded border border-slate-200 px-1.5 text-xs" onBlur={(e) => pm && e.target.value !== (pm.address ?? "") && update(p.normalized_name, { address: e.target.value || null }).catch((x) => toast(errMsg(x), "error"))} /></td>
                      <td className="text-right"><input disabled={!editable} defaultValue={bal ? Number(bal.opening_balance) : ""} inputMode="decimal" placeholder="0" className="h-8 w-32 rounded border border-slate-200 px-1.5 text-right text-xs"
                        onBlur={async (e) => {
                          const v = Number(e.target.value.replace(/,/g, "") || 0);
                          if (!isFinite(v)) return toast("Enter a number", "error");
                          try {
                            if (bal) { if (v !== Number(bal.opening_balance)) await bals.patch(bal.id, { opening_balance: v }); }
                            else if (v) await bals.add({ engagement_id: eng.id, firm_id: firm!.id, party_name: p.party_name, normalized_name: p.normalized_name, opening_balance: v });
                          } catch (x) { toast(errMsg(x), "error"); }
                        }} /></td>
                      <td className="num">{formatINR(p.credits, { symbol: false })}</td>
                      <td className="num">{formatINR(p.debits, { symbol: false })}</td>
                      <td className="num">{formatINR(Math.abs(p.closing), { symbol: false })} {p.closing > 0.5 ? "Cr" : p.closing < -0.5 ? "Dr" : ""}</td>
                      <td><Toggle checked={!!pm?.is_exempt_lender} disabled={!editable || !pm} onChange={(v) => update(p.normalized_name, { is_exempt_lender: v }).catch((x) => toast(errMsg(x), "error"))} /></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="border-t border-slate-100 px-4 py-2 text-xs text-slate-500">Opening balance on 1 April: credit balance (amount owed by the assessee) as plus, debit balance (amount owed to the assessee) as minus. Turn on "Bank / Govt lender" for lenders covered by the provisos to s.269SS / 269T – they are left out of the report.</p>
        </Card>
      )}

      {current === "report" && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Kpi label="Parties" value={result.parties.length} tone="navy" />
            <Kpi label="31(a) + (b) entries" value={lists[0].length + lists[1].length} />
            <Kpi label="31(c) entries" value={lists[2].length} />
            <Kpi label="Accounts to review" value={result.reviewParties} />
          </div>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <label className="flex items-center gap-2 text-sm text-slate-600">Entries on the same day:
              <Select className="h-9 w-56 text-sm" value={order} disabled={!editable} onChange={(e) => setOrder(e.target.value as SameDayOrder)}>
                <option value="credit_first">Credits first</option><option value="debit_first">Debits first</option><option value="as_entered">In voucher order</option>
              </Select></label>
            <label className="flex items-center gap-2 text-sm text-slate-600" title="Entries of a party with the same code and the same answers in every column are shown as one line">
              <Toggle checked={combine} disabled={!editable} onChange={(v) => saveAnswers(() => ({ c31_combine: v }))} />Combine similar entries</label>
            <div className="flex flex-wrap gap-2">
              <Button icon={<FileSpreadsheet className="h-4 w-4" />} onClick={async () => { exportClauseWorkbook("Clause31", meta, sec); await logActivity(firm!.id, "report.exported", "engagement", eng.id, { format: "xlsx", clause: "31" }); }}>Export Clause 31 (Excel)</Button>
              <WhatsAppShare client={client} engagement={eng} label="Clause 31 report" build={() => exportClauseWorkbook("Clause31", meta, sec, true)} />
            </div>
          </div>
          {result.reviewParties > 0 && (
            <Card className="px-5 py-3">
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <ReviewMark />
                {result.parties.filter((p) => p.review).map((p) => <button key={p.normalized_name} onClick={() => setShow(p.normalized_name)} className="rounded-full border border-slate-200 px-2.5 py-0.5 text-xs font-medium hover:border-navy-400">{p.party_name}</button>)}
              </div>
            </Card>
          )}
          {sec.map((s, si) => {
            const list = lists[si];
            const payeeCol = s.cols.findIndex((c) => c.label.startsWith("If by cheque"));
            return <ReportTable key={s.sheet} title={s.title} cols={s.cols.slice(0, -1)}
              rows={s.rows.map((r, ri) => r.slice(0, -1).map((v, j) => {
                const row = list[ri];
                if (j === 0) return (
                  <span key="n" className="inline-flex items-center gap-1.5">{v}
                    {row.review && <button onClick={() => setShow(row.party)}><ReviewMark /></button>}
                    {editable && row.keys?.length > 0 && <button title="Delete the entries of this line" aria-label="Delete this line" className="text-slate-300 hover:text-red-600" onClick={() => setDelRow(row)}><Trash2 className="h-3.5 w-3.5" /></button>}
                  </span>);
                if (j === payeeCol && editable && row.keys?.length) return (
                  <span key="p" className="inline-flex flex-col gap-0.5">
                    <Select aria-label="How paid / received" className="h-8 w-52 text-xs" value={howOf(row)} onChange={(e) => setHow(row, e.target.value)}>
                      {HOW.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
                    </Select>
                    <span className="text-[10px] text-slate-400">In the report: {v as string}</span>
                  </span>);
                return v;
              }) as any)} />;
          })}
        </div>
      )}

      {delRow && (() => {
        const ents = delRow.keys.map((k) => byKey.get(k)).filter(Boolean) as Row[];
        return (
          <Modal open onClose={() => setDelRow(null)} title="Delete this line's entries?"
            footer={<><Button variant="ghost" onClick={() => setDelRow(null)}>Cancel</Button>
              <Button variant="danger" disabled={!ents.length} onClick={async () => {
                try { await txns.remove(ents.map((t) => t.id)); toast(`${ents.length} ${ents.length === 1 ? "entry" : "entries"} deleted`); } catch (e) { toast(errMsg(e), "error"); }
                setDelRow(null);
              }}>Delete {ents.length} {ents.length === 1 ? "entry" : "entries"}</Button></>}>
            <p className="mb-2 text-sm text-slate-600">{delRow.party_name}: these entries are removed from this year. The balance and the report are worked out again.</p>
            <ul className="space-y-1 text-sm">{ents.map((t) => <li key={t.id} className="flex justify-between gap-3"><span>{formatDate(t.txn_date)} · {ENTRY_TYPE_LABEL[t.kind]}{t.voucher_no ? ` · Vch ${t.voucher_no}` : ""}</span><span className="tabular-nums">{formatINR(Number(t.amount))}</span></li>)}</ul>
          </Modal>);
      })()}

      {showParty && (
        <Modal open onClose={() => setShow(null)} title={showParty.party_name} wide>
          <div className="mb-3 text-sm text-slate-600">Opening {formatINR(Math.abs(showParty.opening))} {showParty.opening > 0 ? "Cr" : showParty.opening < 0 ? "Dr" : ""} · Closing {formatINR(Math.abs(showParty.closing))} {showParty.closing > 0.5 ? "Cr" : showParty.closing < -0.5 ? "Dr" : ""}</div>
          <div className="max-h-[60vh] overflow-auto">
            <table className="table-pro">
              <thead><tr><th>Date</th><th>Voucher</th><th>Mode</th><th className="text-right">Debit</th><th className="text-right">Credit</th><th>Narration</th></tr></thead>
              <tbody>{txns.rows.filter((t) => t.include && t.normalized_name === showParty.normalized_name).sort((a, b) => (a.txn_date ?? "").localeCompare(b.txn_date ?? "")).map((t) => (
                <tr key={t.id} className={cn((t.mode === "cash" || t.mode === "non_ac_payee_cheque" || t.mode === "journal" || t.mode === "transfer" || t.mode === "other") && Number(t.amount) >= 20000 && "bg-amber-50/60")}>
                  <td>{formatDate(t.txn_date)}</td><td>{t.voucher_no ?? ""}</td><td className="text-xs">{MODE_LABEL[t.mode]}</td>
                  <td className="num">{!isCredit(t.kind) ? formatINR(Number(t.amount), { symbol: false }) : ""}</td>
                  <td className="num">{isCredit(t.kind) ? formatINR(Number(t.amount), { symbol: false }) : ""}</td>
                  <td className="text-xs text-slate-500">{t.remark ?? ""}</td>
                </tr>))}</tbody>
            </table>
          </div>
        </Modal>
      )}
    </div>
  );
}
