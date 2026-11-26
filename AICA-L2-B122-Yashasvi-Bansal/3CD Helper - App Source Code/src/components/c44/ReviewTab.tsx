import { useCallback, useEffect, useMemo, useState } from "react";
import { Search, ChevronLeft, ChevronRight, Pencil, History, AlertTriangle, CheckSquare, XSquare, Filter } from "lucide-react";
import { supabase } from "@/integrations/supabase/client";
import { useFirm } from "@/contexts/FirmContext";
import { useTeam } from "@/hooks/useTeam";
import { useToast } from "@/components/Toast";
import { Alert, Badge, Button, Card, EmptyState, Field, Input, Modal, Select, Spinner, StatCard, Textarea, cn } from "@/components/ui";
import { CATEGORY_COLOR, CATEGORY_LABEL, Category, Clause44Summary, EXCEPTION_LABEL, EXCLUSION_REASONS } from "@/lib/clause44";
import { formatDate, formatDateTime, formatINR, formatINRShort } from "@/lib/format";
import { errMsg, logActivity } from "@/lib/db";
import { cleanGstin, gstinStatus } from "@/lib/validators";
import { normalizeParty } from "@/lib/party";

type View = "entries" | "parties" | "heads" | "exceptions";
const PAGE = 50;

interface Row {
  id: string; row_no: number; party_name: string; normalized_name: string; gstin: string | null; effective_gstin: string | null;
  gstin_status: "valid" | "invalid" | "blank"; expense_head: string | null; amount: number; txn_date: string | null; nature: string | null;
  category: Category; category_override: Category | null; include: boolean; remark: string | null; updated_by: string; updated_at: string;
}

export function ReviewTab({ engagementId, editable, summary, onChanged }: { engagementId: string; editable: boolean; summary: Clause44Summary; onChanged: () => void }) {
  const [view, setView] = useState<View>("entries");
  const [partyFilter, setPartyFilter] = useState<string>("");

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-6">
        <StatCard label="Reported total" value={formatINRShort(summary.reported_total)} tone="navy" sub={`${(summary.row_count - summary.excluded_count).toLocaleString("en-IN")} entr${summary.row_count - summary.excluded_count === 1 ? "y" : "ies"}`} />
        <StatCard label="Other registered" value={formatINRShort(summary.other_registered)} />
        <StatCard label="Composition" value={formatINRShort(summary.composition)} />
        <StatCard label="Exempt" value={formatINRShort(summary.exempt)} />
        <StatCard label="Unregistered" value={formatINRShort(summary.unregistered)} />
        <StatCard label="Excluded" value={formatINRShort(summary.excluded)} sub={`${summary.excluded_count.toLocaleString("en-IN")} entr${summary.excluded_count === 1 ? "y" : "ies"}`} tone={summary.excluded_count ? "warn" : "default"} />
      </div>

      <div className="flex gap-1 overflow-x-auto rounded-xl bg-slate-100 p-1">
        {([["entries", "Entries"], ["parties", "By party"], ["heads", "By expense head"], ["exceptions", "Exceptions"]] as [View, string][]).map(([k, l]) => (
          <button key={k} onClick={() => setView(k)} className={cn("flex-1 whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium", view === k ? "bg-white text-navy-900 shadow-sm" : "text-slate-600")}>
            {l}{k === "exceptions" && summary.invalid_gstin_count > 0 && <span className="ml-1.5 rounded-full bg-red-600 px-1.5 text-xs text-white">!</span>}
          </button>
        ))}
      </div>

      {view === "entries" && <Entries engagementId={engagementId} editable={editable} onChanged={onChanged} partyFilter={partyFilter} clearParty={() => setPartyFilter("")} />}
      {view === "parties" && <ByParty engagementId={engagementId} onOpen={(n) => { setPartyFilter(n); setView("entries"); }} />}
      {view === "heads" && <ByHead engagementId={engagementId} editable={editable} onChanged={onChanged} />}
      {view === "exceptions" && <Exceptions engagementId={engagementId} onOpen={(n) => { setPartyFilter(n); setView("entries"); }} />}
    </div>
  );
}

/* ------------------------------ Entries ------------------------------ */
function Entries({ engagementId, editable, onChanged, partyFilter, clearParty }: { engagementId: string; editable: boolean; onChanged: () => void; partyFilter: string; clearParty: () => void }) {
  const { firm } = useFirm();
  const toast = useToast();
  const [rows, setRows] = useState<Row[]>([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [qDebounced, setQDebounced] = useState("");
  const [cat, setCat] = useState("");
  const [gst, setGst] = useState("");
  const [inc, setInc] = useState("yes");   // rows that count first; excluded ones are one click away
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [editRow, setEditRow] = useState<Row | null>(null);
  const [bulk, setBulk] = useState<null | "exclude" | "include">(null);

  useEffect(() => { const t = setTimeout(() => setQDebounced(q), 350); return () => clearTimeout(t); }, [q]);
  useEffect(() => { setPage(0); }, [qDebounced, cat, gst, inc, partyFilter]);

  const load = useCallback(async () => {
    setLoading(true);
    let query = supabase.from("expense_rows").select("*", { count: "exact" }).eq("engagement_id", engagementId);
    if (partyFilter) query = query.eq("normalized_name", partyFilter);
    if (cat) query = query.eq("category", cat);
    if (gst) query = query.eq("gstin_status", gst);
    if (inc) query = query.eq("include", inc === "yes");
    const s = qDebounced.replace(/[,()%*\\]/g, " ").trim();
    if (s) query = query.or(`party_name.ilike.%${s}%,expense_head.ilike.%${s}%,gstin.ilike.%${s}%,remark.ilike.%${s}%`);
    const { data, count: c, error } = await query.order("row_no", { ascending: true }).order("id").range(page * PAGE, page * PAGE + PAGE - 1);
    if (error) toast(errMsg(error), "error");
    setRows((data as Row[]) ?? []);
    setCount(c ?? 0);
    setSelected(new Set());
    setLoading(false);
  }, [engagementId, partyFilter, cat, gst, inc, qDebounced, page]);
  useEffect(() => { load(); }, [load]);

  const refreshAll = async (reclassify = false) => {
    if (reclassify) await supabase.rpc("reclassify_engagement", { p_eng: engagementId });
    await load();
    onChanged();
  };

  const toggleInclude = async (r: Row) => {
    if (r.include) { setSelected(new Set([r.id])); setBulk("exclude"); return; }
    const { error } = await supabase.from("expense_rows").update({ include: true, remark: null }).eq("id", r.id);
    if (error) return toast(errMsg(error), "error");
    refreshAll();
  };

  const pages = Math.max(1, Math.ceil(count / PAGE));
  const allOnPage = rows.length > 0 && rows.every((r) => selected.has(r.id));

  return (
    <Card>
      <div className="flex flex-col gap-2 border-b border-slate-100 p-3 lg:flex-row">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search party, head, GSTIN, remark" className="pl-9" />
        </div>
        <div className="grid grid-cols-3 gap-2 lg:flex">
          <Select value={cat} onChange={(e) => setCat(e.target.value)} className="lg:w-44"><option value="">All categories</option>{Object.entries(CATEGORY_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</Select>
          <Select value={gst} onChange={(e) => setGst(e.target.value)} className="lg:w-36"><option value="">Any GSTIN</option><option value="valid">Valid</option><option value="invalid">Invalid</option><option value="blank">Blank</option></Select>
          <Select value={inc} onChange={(e) => setInc(e.target.value)} className="lg:w-36"><option value="">All rows</option><option value="yes">Included</option><option value="no">Excluded</option></Select>
        </div>
      </div>
      {partyFilter && (
        <div className="flex items-center gap-2 border-b border-slate-100 bg-navy-50 px-4 py-2 text-sm"><Filter className="h-4 w-4" />Party: <b>{partyFilter}</b><button className="ml-auto text-navy-700 underline" onClick={clearParty}>Clear</button></div>
      )}
      {selected.size > 0 && editable && (
        <div className="flex flex-wrap items-center gap-2 border-b border-slate-100 bg-amber-50 px-4 py-2 text-sm">
          <b>{selected.size} selected</b>
          <Button size="sm" variant="outline" icon={<XSquare className="h-4 w-4" />} onClick={() => setBulk("exclude")}>Exclude</Button>
          <Button size="sm" variant="outline" icon={<CheckSquare className="h-4 w-4" />} onClick={() => setBulk("include")}>Include</Button>
          <button className="ml-auto text-slate-600 underline" onClick={() => setSelected(new Set())}>Clear</button>
        </div>
      )}

      {loading ? <div className="flex justify-center py-12"><Spinner /></div> : rows.length === 0 ? (
        <EmptyState title="No entries" text="Upload a ledger or change the filters." />
      ) : (
        <div className="overflow-x-auto">
          <table className="table-pro">
            <thead>
              <tr>
                {editable && <th className="w-8"><input type="checkbox" checked={allOnPage} onChange={() => setSelected(allOnPage ? new Set() : new Set(rows.map((r) => r.id)))} /></th>}
                <th>Row</th><th>Date</th><th>Party</th><th>GSTIN</th><th>Expense head</th><th className="num">Amount</th><th>Category</th><th>Include</th><th></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className={cn(!r.include && "bg-slate-50 text-slate-400")}>
                  {editable && <td><input type="checkbox" checked={selected.has(r.id)} onChange={() => setSelected((s) => { const n = new Set(s); n.has(r.id) ? n.delete(r.id) : n.add(r.id); return n; })} /></td>}
                  <td className="text-xs text-slate-400">{r.row_no}</td>
                  <td className="whitespace-nowrap text-xs">{formatDate(r.txn_date)}</td>
                  <td className="max-w-[240px]"><div className="truncate font-medium text-slate-800">{r.party_name}</div>{r.remark && <div className="truncate text-xs text-amber-700">{r.remark}</div>}</td>
                  <td className="whitespace-nowrap font-mono text-xs">
                    {r.effective_gstin ?? <span className="text-slate-400">—</span>}
                    {r.gstin_status === "invalid" && <AlertTriangle className="ml-1 inline h-3.5 w-3.5 text-red-600" />}
                    {!r.gstin && r.effective_gstin && <span className="ml-1 rounded bg-slate-100 px-1 text-[10px] text-slate-500">master</span>}
                  </td>
                  <td className="max-w-[180px] truncate text-xs">{r.expense_head}</td>
                  <td className={cn("num", r.amount < 0 && "text-red-600")}>{formatINR(r.amount, { symbol: false })}</td>
                  <td><Badge className={CATEGORY_COLOR[r.category]}>{CATEGORY_LABEL[r.category]}{r.category_override && " ✎"}</Badge></td>
                  <td><input type="checkbox" checked={r.include} disabled={!editable} onChange={() => toggleInclude(r)} className="h-4 w-4 accent-navy-800" /></td>
                  <td><button onClick={() => setEditRow(r)} className="rounded p-1 text-slate-500 hover:bg-slate-100" aria-label="Edit"><Pencil className="h-4 w-4" /></button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <div className="flex items-center justify-between border-t border-slate-100 px-4 py-3 text-sm">
        <span className="text-slate-500">{count.toLocaleString("en-IN")} entries</span>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="outline" disabled={page === 0} onClick={() => setPage((p) => p - 1)}><ChevronLeft className="h-4 w-4" /></Button>
          <span>Page {page + 1} / {pages}</span>
          <Button size="sm" variant="outline" disabled={page + 1 >= pages} onClick={() => setPage((p) => p + 1)}><ChevronRight className="h-4 w-4" /></Button>
        </div>
      </div>

      {bulk && (
        <BulkModal mode={bulk} count={selected.size} onClose={() => setBulk(null)} onApply={async (remark) => {
          const ids = Array.from(selected);
          const { error } = await supabase.from("expense_rows").update({ include: bulk === "include", remark: bulk === "include" ? null : remark }).in("id", ids);
          if (error) { toast(errMsg(error), "error"); return; }
          await logActivity(firm!.id, "rows.bulk_include", "engagement", engagementId, { count: ids.length, include: bulk === "include", remark });
          toast(`${ids.length} entries ${bulk === "include" ? "included" : "excluded"}`);
          setBulk(null); refreshAll();
        }} />
      )}
      {editRow && <EditRowModal row={editRow} editable={editable} engagementId={engagementId} onClose={() => setEditRow(null)} onSaved={() => { setEditRow(null); refreshAll(true); }} />}
    </Card>
  );
}

function BulkModal({ mode, count, onClose, onApply }: { mode: "include" | "exclude"; count: number; onClose: () => void; onApply: (remark: string) => Promise<void> }) {
  const [reason, setReason] = useState(EXCLUSION_REASONS[0]);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <Modal open onClose={onClose} title={mode === "exclude" ? `Exclude ${count} entr${count === 1 ? "y" : "ies"}` : `Include ${count} entr${count === 1 ? "y" : "ies"}`}
      footer={<><Button variant="ghost" onClick={onClose}>Cancel</Button><Button loading={busy} onClick={async () => { setBusy(true); await onApply(reason === "Other" ? note || "Other" : note ? `${reason} – ${note}` : reason); setBusy(false); }}>{mode === "exclude" ? "Exclude" : "Include"}</Button></>}>
      {mode === "exclude" ? (
        <div className="space-y-4">
          <p className="text-sm text-slate-600">Excluded entries are left out of Clause 44 and listed in the reconciliation with this reason.</p>
          <Field label="Reason" required><Select value={reason} onChange={(e) => setReason(e.target.value)}>{EXCLUSION_REASONS.map((r) => <option key={r}>{r}</option>)}</Select></Field>
          <Field label="Note (optional)"><Input value={note} onChange={(e) => setNote(e.target.value)} /></Field>
        </div>
      ) : <p className="text-sm text-slate-600">These entries will be counted in Clause 44 again.</p>}
    </Modal>
  );
}

function EditRowModal({ row, editable, engagementId, onClose, onSaved }: { row: Row; editable: boolean; engagementId: string; onClose: () => void; onSaved: () => void }) {
  const toast = useToast();
  const { nameOf } = useTeam();
  const [r, setR] = useState({ ...row, amount: String(row.amount), gstin: row.gstin ?? "", expense_head: row.expense_head ?? "", remark: row.remark ?? "", category_override: row.category_override ?? "" });
  const [history, setHistory] = useState<any[]>([]);
  const [comments, setComments] = useState<any[]>([]);
  const [comment, setComment] = useState("");
  const [saving, setSaving] = useState(false);
  const { firm } = useFirm();

  useEffect(() => {
    supabase.from("row_history").select("*").eq("record_id", row.id).order("changed_at", { ascending: false }).then(({ data }) => setHistory(data ?? []));
    supabase.from("comments").select("*").eq("row_id", row.id).order("created_at").then(({ data }) => setComments(data ?? []));
  }, [row.id]);

  const st = gstinStatus(r.gstin);
  const save = async () => {
    const amt = Number(String(r.amount).replace(/,/g, ""));
    if (!isFinite(amt)) return toast("Amount is not a number", "error");
    setSaving(true);
    const g = cleanGstin(r.gstin);
    const { error } = await supabase.from("expense_rows").update({
      party_name: r.party_name.trim(), normalized_name: normalizeParty(r.party_name) || r.party_name.toLowerCase(), gstin: g || null,
      expense_head: r.expense_head || null, amount: amt, include: r.include, remark: r.remark || null,
      category_override: r.category_override || null,
    }).eq("id", row.id);
    if (!error && normalizeParty(r.party_name) !== row.normalized_name) {
      const { data: en } = await supabase.from("engagements").select("client_id").eq("id", engagementId).single();
      if (en) await supabase.rpc("upsert_parties", { p_client: en.client_id, p_parties: [{ party_name: r.party_name.trim(), normalized_name: normalizeParty(r.party_name), gstin: st === "valid" ? g : null }] });
    }
    setSaving(false);
    if (error) return toast(errMsg(error), "error");
    toast("Entry updated");
    onSaved();
  };

  const addComment = async () => {
    if (!comment.trim()) return;
    const { data, error } = await supabase.from("comments").insert({ engagement_id: engagementId, firm_id: firm!.id, row_id: row.id, body: comment.trim() }).select("*").single();
    if (error) return toast(errMsg(error), "error");
    setComments((c) => [...c, data]); setComment("");
  };

  return (
    <Modal open onClose={onClose} title={`Entry – row ${row.row_no}`} wide
      footer={editable ? <><Button variant="ghost" onClick={onClose}>Cancel</Button><Button onClick={save} loading={saving}>Save</Button></> : <Button onClick={onClose}>Close</Button>}>
      <div className="grid gap-6 lg:grid-cols-5">
        <div className="grid gap-3 sm:grid-cols-2 lg:col-span-3">
          <Field label="Party name" className="sm:col-span-2"><Input value={r.party_name} disabled={!editable} onChange={(e) => setR({ ...r, party_name: e.target.value })} /></Field>
          <Field label="GSTIN (this entry)" error={st === "invalid" ? "Invalid GSTIN (checksum/format)" : undefined} hint={!r.gstin && row.effective_gstin ? `Using party master GSTIN ${row.effective_gstin}` : undefined}>
            <Input value={r.gstin} disabled={!editable} onChange={(e) => setR({ ...r, gstin: e.target.value.toUpperCase() })} className="font-mono" maxLength={15} />
          </Field>
          <Field label="Amount (₹)"><Input value={r.amount} disabled={!editable} onChange={(e) => setR({ ...r, amount: e.target.value })} inputMode="decimal" /></Field>
          <Field label="Expense head" className="sm:col-span-2"><Input value={r.expense_head} disabled={!editable} onChange={(e) => setR({ ...r, expense_head: e.target.value })} /></Field>
          <Field label="Category" hint="Automatic from GSTIN & party master. Override only when needed.">
            <Select value={r.category_override} disabled={!editable} onChange={(e) => setR({ ...r, category_override: e.target.value as Category | "" })}>
              <option value="">Automatic ({CATEGORY_LABEL[row.category]})</option>
              {Object.entries(CATEGORY_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </Select>
          </Field>
          <Field label="Include in Clause 44">
            <Select value={r.include ? "yes" : "no"} disabled={!editable} onChange={(e) => setR({ ...r, include: e.target.value === "yes" })}><option value="yes">Yes</option><option value="no">No – excluded</option></Select>
          </Field>
          <Field label="Remark / exclusion reason" className="sm:col-span-2"><Input value={r.remark} disabled={!editable} onChange={(e) => setR({ ...r, remark: e.target.value })} /></Field>
          <p className="text-xs text-slate-500 sm:col-span-2">Last edited by {nameOf(row.updated_by)} · {formatDateTime(row.updated_at)}</p>
        </div>
        <div className="space-y-5 lg:col-span-2">
          <div>
            <h4 className="mb-2 flex items-center gap-2 text-sm font-semibold"><History className="h-4 w-4" />Change history</h4>
            {history.length === 0 ? <p className="text-xs text-slate-500">No changes since import.</p> : (
              <ul className="max-h-48 space-y-2 overflow-y-auto text-xs">
                {history.map((h) => (
                  <li key={h.id} className="rounded-lg bg-slate-50 p-2">
                    <b>{h.field}</b>: <span className="text-red-600 line-through">{h.old_value || "∅"}</span> → <span className="text-emerald-700">{h.new_value || "∅"}</span>
                    <div className="text-slate-500">{nameOf(h.changed_by)} · {formatDateTime(h.changed_at)}</div>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div>
            <h4 className="mb-2 text-sm font-semibold">Comments</h4>
            <ul className="mb-2 max-h-40 space-y-2 overflow-y-auto text-sm">
              {comments.map((c) => <li key={c.id} className="rounded-lg bg-navy-50 p-2"><div>{c.body}</div><div className="text-xs text-slate-500">{nameOf(c.created_by)} · {formatDateTime(c.created_at)}</div></li>)}
            </ul>
            <Textarea value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Add a working-paper note…" rows={2} />
            <Button size="sm" variant="secondary" className="mt-2" onClick={addComment} disabled={!comment.trim()}>Add comment</Button>
          </div>
        </div>
      </div>
    </Modal>
  );
}

/* ------------------------------ By party ------------------------------ */
function ByParty({ engagementId, onOpen }: { engagementId: string; onOpen: (normalized: string) => void }) {
  const [list, setList] = useState<any[] | null>(null);
  const [q, setQ] = useState("");
  useEffect(() => { supabase.rpc("clause44_party_summary", { p_eng: engagementId }).then(({ data }) => setList(data ?? [])); }, [engagementId]);
  const shown = useMemo(() => (list ?? []).filter((p) => !q || p.party_name.toLowerCase().includes(q.toLowerCase()) || (p.gstin ?? "").includes(q.toUpperCase())), [list, q]);
  if (!list) return <div className="flex justify-center py-12"><Spinner /></div>;
  return (
    <Card>
      <div className="border-b border-slate-100 p-3"><Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search party or GSTIN" /></div>
      <div className="max-h-[600px] overflow-auto">
        <table className="table-pro">
          <thead><tr><th>Party</th><th>GSTIN</th><th>Category</th><th className="num">Included</th><th className="num">Excluded</th><th className="num">Entries</th></tr></thead>
          <tbody>
            {shown.slice(0, 1000).map((p) => (
              <tr key={p.normalized_name} className="cursor-pointer" onClick={() => onOpen(p.normalized_name)}>
                <td className="max-w-[260px] truncate font-medium">{p.party_name}{Number(p.gstin_variants) > 1 && <Badge className="ml-2 bg-red-100 text-red-700">{p.gstin_variants} GSTINs</Badge>}</td>
                <td className={cn("font-mono text-xs", p.gstin_status === "invalid" && "text-red-600")}>{p.gstin ?? "—"}</td>
                <td>{p.category === "mixed" ? <Badge className="bg-purple-100 text-purple-800">Mixed</Badge> : p.category ? <Badge className={CATEGORY_COLOR[p.category as Category]}>{CATEGORY_LABEL[p.category as Category]}</Badge> : <Badge>Excluded</Badge>}</td>
                <td className="num">{formatINR(p.included_amount, { symbol: false })}</td>
                <td className="num text-slate-400">{Number(p.excluded_amount) ? formatINR(p.excluded_amount, { symbol: false }) : ""}</td>
                <td className="num">{p.row_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

/* ------------------------------ By head ------------------------------ */
function ByHead({ engagementId, editable, onChanged }: { engagementId: string; editable: boolean; onChanged: () => void }) {
  const { firm } = useFirm();
  const toast = useToast();
  const [list, setList] = useState<any[] | null>(null);
  const [target, setTarget] = useState<{ head: string; mode: "include" | "exclude" } | null>(null);
  const load = () => supabase.rpc("clause44_head_summary", { p_eng: engagementId }).then(({ data }) => setList(data ?? []));
  useEffect(() => { load(); }, [engagementId]);
  if (!list) return <div className="flex justify-center py-12"><Spinner /></div>;
  return (
    <Card>
      <Alert tone="info" className="m-3">Exclude whole expense heads that are not "expenditure" for Clause 44 (e.g. depreciation, provisions, salary). Every exclusion needs a reason and appears in the reconciliation.</Alert>
      <div className="overflow-x-auto">
        <table className="table-pro">
          <thead><tr><th>Expense head</th><th className="num">Total</th><th className="num">Included</th><th className="num">Excluded</th><th className="num">Entries</th>{editable && <th></th>}</tr></thead>
          <tbody>
            {list.map((h) => {
              const allExcluded = Number(h.excluded_count) === Number(h.row_count);
              return (
                <tr key={h.expense_head} className={cn(allExcluded && "text-slate-400")}>
                  <td className="font-medium">{h.expense_head}</td>
                  <td className="num">{formatINR(h.total, { symbol: false })}</td>
                  <td className="num">{formatINR(h.included_amount, { symbol: false })}</td>
                  <td className="num">{Number(h.excluded_amount) ? formatINR(h.excluded_amount, { symbol: false }) : ""}</td>
                  <td className="num">{h.row_count}</td>
                  {editable && (
                    <td className="whitespace-nowrap text-right">
                      {!allExcluded && <Button size="sm" variant="outline" onClick={() => setTarget({ head: h.expense_head, mode: "exclude" })}>Exclude</Button>}
                      {Number(h.excluded_count) > 0 && <Button size="sm" variant="ghost" onClick={() => setTarget({ head: h.expense_head, mode: "include" })}>Include</Button>}
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {target && (
        <BulkModal mode={target.mode} count={Number(list.find((h) => h.expense_head === target.head)?.row_count ?? 0)} onClose={() => setTarget(null)}
          onApply={async (remark) => {
            let qb = supabase.from("expense_rows").update({ include: target.mode === "include", remark: target.mode === "include" ? null : remark }).eq("engagement_id", engagementId);
            qb = target.head === "(blank)" ? qb.is("expense_head", null) : qb.eq("expense_head", target.head);
            const { error } = await qb;
            if (error) { toast(errMsg(error), "error"); return; }
            await logActivity(firm!.id, "rows.bulk_include", "engagement", engagementId, { head: target.head, include: target.mode === "include", remark });
            toast(`"${target.head}" ${target.mode === "include" ? "included" : "excluded"}`);
            setTarget(null); load(); onChanged();
          }} />
      )}
    </Card>
  );
}

/* ------------------------------ Exceptions ------------------------------ */
function Exceptions({ engagementId, onOpen }: { engagementId: string; onOpen: (normalized: string) => void }) {
  const [list, setList] = useState<any[] | null>(null);
  useEffect(() => { supabase.rpc("clause44_exceptions", { p_eng: engagementId }).then(({ data }) => setList(data ?? [])); }, [engagementId]);
  if (!list) return <div className="flex justify-center py-12"><Spinner /></div>;
  if (!list.length) return <Card><EmptyState title="No exceptions found" text="GSTINs are valid and no duplicates or negative amounts were detected." /></Card>;
  const groups = list.reduce<Record<string, any[]>>((acc, e) => { (acc[e.kind] ??= []).push(e); return acc; }, {});
  return (
    <div className="space-y-4">
      {Object.entries(groups).map(([kind, items]) => (
        <Card key={kind}>
          <div className="flex items-center gap-2 border-b border-slate-100 px-5 py-3"><AlertTriangle className="h-4 w-4 text-amber-600" /><b>{EXCEPTION_LABEL[kind] ?? kind}</b><Badge>{items.length}</Badge></div>
          <div className="overflow-x-auto">
            <table className="table-pro">
              <thead><tr><th>Party</th><th>Detail</th><th className="num">Amount</th><th className="num">Entries</th></tr></thead>
              <tbody>{items.slice(0, 300).map((e, i) => (
                <tr key={i} className="cursor-pointer" onClick={() => onOpen(e.normalized_name)}>
                  <td className="font-medium">{e.party_name}</td><td className="font-mono text-xs">{e.detail}</td>
                  <td className="num">{formatINR(e.amount, { symbol: false })}</td><td className="num">{e.row_count}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        </Card>
      ))}
    </div>
  );
}
