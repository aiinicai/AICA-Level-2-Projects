import { useEffect, useMemo, useState } from "react";
import { GitMerge, Search, Check, X, Sparkles } from "lucide-react";
import { supabase } from "@/integrations/supabase/client";
import { useFirm } from "@/contexts/FirmContext";
import { useToast } from "@/components/Toast";
import { Alert, Badge, Button, Card, CardHeader, EmptyState, Input, Modal, Select, Spinner, Toggle, cn } from "@/components/ui";
import { fetchAll, errMsg, logActivity } from "@/lib/db";
import { cleanGstin, gstinStatus, GST_STATES } from "@/lib/validators";
import { suggestMerges, MergeSuggestion } from "@/lib/party";
import { formatINR } from "@/lib/format";

interface Party { id: string; party_name: string; normalized_name: string; gstin: string | null; pan: string | null; is_composition: boolean; is_exempt: boolean }

export function PartiesTab({ clientId, engagementId, editable, onChanged }: { clientId: string; engagementId: string; editable: boolean; onChanged: () => void }) {
  const { firm } = useFirm();
  const toast = useToast();
  const [parties, setParties] = useState<Party[] | null>(null);
  const [usage, setUsage] = useState<Record<string, { amount: number; rows: number }>>({});
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState("used");
  const [merge, setMerge] = useState<MergeSuggestion | null>(null);
  const [showSuggest, setShowSuggest] = useState(false);
  const [page, setPage] = useState(0);

  const load = async () => {
    const [p, u] = await Promise.all([
      fetchAll<Party>((from, to) => supabase.from("party_master").select("id, party_name, normalized_name, gstin, pan, is_composition, is_exempt").eq("client_id", clientId).order("party_name").range(from, to)),
      supabase.rpc("clause44_party_summary", { p_eng: engagementId }),
    ]);
    setParties(p);
    const m: Record<string, { amount: number; rows: number }> = {};
    (u.data ?? []).forEach((r: any) => { m[r.normalized_name] = { amount: Number(r.included_amount) + Number(r.excluded_amount), rows: Number(r.row_count) }; });
    setUsage(m);
  };
  useEffect(() => { load(); }, [clientId, engagementId]);

  const suggestions = useMemo(() => (parties ? suggestMerges(parties.map((p) => p.normalized_name)) : []), [parties]);

  const shown = useMemo(() => {
    if (!parties) return [];
    const s = q.trim().toLowerCase();
    return parties.filter((p) => {
      if (filter === "used" && !usage[p.normalized_name]) return false;
      if (filter === "registered" && gstinStatus(p.gstin) !== "valid") return false;
      if (filter === "unregistered" && gstinStatus(p.gstin) === "valid") return false;
      if (filter === "invalid" && gstinStatus(p.gstin) !== "invalid") return false;
      if (filter === "flagged" && !p.is_composition && !p.is_exempt) return false;
      return !s || p.party_name.toLowerCase().includes(s) || (p.gstin ?? "").toLowerCase().includes(s);
    }).sort((a, b) => (usage[b.normalized_name]?.amount ?? 0) - (usage[a.normalized_name]?.amount ?? 0));
  }, [parties, q, filter, usage]);

  useEffect(() => setPage(0), [q, filter]);

  const update = async (p: Party, patch: Partial<Party>) => {
    if (patch.gstin !== undefined) {
      const g = cleanGstin(patch.gstin);
      if (g && gstinStatus(g) !== "valid") { toast(`${g} is not a valid GSTIN`, "error"); return; }
      patch.gstin = g || null;
    }
    setParties((list) => list?.map((x) => (x.id === p.id ? { ...x, ...patch } : x)) ?? null);
    const { error } = await supabase.from("party_master").update(patch).eq("id", p.id);
    if (error) { toast(errMsg(error), "error"); load(); return; }
    await supabase.rpc("reclassify_engagement", { p_eng: engagementId });
    await logActivity(firm!.id, "party.updated", "party", p.id, { name: p.party_name, ...patch });
    onChanged();
  };

  if (!parties) return <div className="flex justify-center py-12"><Spinner /></div>;
  const PAGE = 100;
  const pageRows = shown.slice(page * PAGE, page * PAGE + PAGE);

  return (
    <div className="space-y-4">
      <Alert tone="info">
        The party master is shared by all assessment years of this client. Mark <b>composition dealers</b> and parties supplying <b>exempt goods/services</b> once – next year's uploads classify automatically. A GSTIN here fills in entries that have no GSTIN.
      </Alert>
      {suggestions.length > 0 && (
        <Card>
          <CardHeader title={<span className="flex items-center gap-2"><Sparkles className="h-4 w-4 text-gold-500" />{suggestions.length} possible duplicate part{suggestions.length === 1 ? "y" : "ies"}</span>}
            subtitle="Similar names that may be the same supplier" action={<Button size="sm" variant="outline" onClick={() => setShowSuggest((v) => !v)}>{showSuggest ? "Hide" : "Review"}</Button>} />
          {showSuggest && (
            <ul className="divide-y divide-slate-100">
              {suggestions.slice(0, 50).map((s) => (
                <li key={s.a + s.b} className="flex flex-wrap items-center gap-3 px-5 py-3 text-sm">
                  <span className="font-medium">{s.a}</span><span className="text-slate-400">≈</span><span className="font-medium">{s.b}</span>
                  <Badge className="bg-navy-50 text-navy-800">{Math.round(s.score * 100)}% match</Badge>
                  {editable && <Button size="sm" variant="secondary" className="ml-auto" icon={<GitMerge className="h-4 w-4" />} onClick={() => setMerge(s)}>Merge</Button>}
                </li>
              ))}
            </ul>
          )}
        </Card>
      )}

      <Card>
        <div className="flex flex-col gap-2 border-b border-slate-100 p-3 sm:flex-row">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search party or GSTIN" className="pl-9" />
          </div>
          <Select value={filter} onChange={(e) => setFilter(e.target.value)} className="sm:w-56">
            <option value="used">Used in this year</option>
            <option value="all">All parties ({parties.length})</option>
            <option value="registered">Registered (valid GSTIN)</option>
            <option value="unregistered">No / invalid GSTIN</option>
            <option value="invalid">Invalid GSTIN</option>
            <option value="flagged">Composition / exempt</option>
          </Select>
        </div>
        {shown.length === 0 ? <EmptyState title="No parties" text="Parties are created automatically when you upload data." /> : (
          <div className="overflow-x-auto">
            <table className="table-pro">
              <thead><tr><th>Party</th><th>GSTIN</th><th className="text-center">Composition</th><th className="text-center">Exempt supply</th><th className="num">This year</th></tr></thead>
              <tbody>
                {pageRows.map((p) => {
                  const st = gstinStatus(p.gstin);
                  return (
                    <tr key={p.id}>
                      <td className="max-w-[260px]"><div className="truncate font-medium">{p.party_name}</div>{p.gstin && st === "valid" && <div className="text-xs text-slate-400">{GST_STATES[p.gstin.slice(0, 2)]}</div>}</td>
                      <td><GstinCell value={p.gstin} editable={editable} onSave={(g) => update(p, { gstin: g })} /></td>
                      <td className="text-center"><Toggle checked={p.is_composition} disabled={!editable || st !== "valid"} onChange={(v) => update(p, { is_composition: v, ...(v ? { is_exempt: false } : {}) })} label="Composition" /></td>
                      <td className="text-center"><Toggle checked={p.is_exempt} disabled={!editable || st !== "valid"} onChange={(v) => update(p, { is_exempt: v, ...(v ? { is_composition: false } : {}) })} label="Exempt" /></td>
                      <td className="num text-xs">{usage[p.normalized_name] ? <>{formatINR(usage[p.normalized_name].amount, { symbol: false })}<div className="text-slate-400">{usage[p.normalized_name].rows} entries</div></> : <span className="text-slate-400">—</span>}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        {shown.length > PAGE && (
          <div className="flex items-center justify-end gap-2 border-t border-slate-100 px-4 py-3 text-sm">
            <Button size="sm" variant="outline" disabled={page === 0} onClick={() => setPage((x) => x - 1)}>Prev</Button>
            <span>{page + 1} / {Math.ceil(shown.length / PAGE)}</span>
            <Button size="sm" variant="outline" disabled={(page + 1) * PAGE >= shown.length} onClick={() => setPage((x) => x + 1)}>Next</Button>
          </div>
        )}
        <p className="border-t border-slate-100 px-4 py-2 text-xs text-slate-500">Composition / exempt flags apply only to parties with a valid GSTIN – unregistered parties are always reported as unregistered.</p>
      </Card>

      {merge && parties && (
        <MergeModal suggestion={merge} parties={parties} usage={usage} onClose={() => setMerge(null)} onMerge={async (from, into) => {
          const { error } = await supabase.rpc("merge_parties", { p_client: clientId, p_from: from, p_into: into });
          if (error) { toast(errMsg(error), "error"); return; }
          await supabase.rpc("reclassify_engagement", { p_eng: engagementId });
          await logActivity(firm!.id, "party.merged", "client", clientId, { from, into });
          toast("Parties merged");
          setMerge(null); load(); onChanged();
        }} />
      )}
    </div>
  );
}

function GstinCell({ value, editable, onSave }: { value: string | null; editable: boolean; onSave: (g: string) => void }) {
  const [edit, setEdit] = useState(false);
  const [v, setV] = useState(value ?? "");
  const st = gstinStatus(v);
  if (!edit) {
    return (
      <button disabled={!editable} onClick={() => { setV(value ?? ""); setEdit(true); }} className={cn("rounded px-1 font-mono text-xs", editable && "hover:bg-slate-100", gstinStatus(value) === "invalid" && "text-red-600")}>
        {value || <span className="text-slate-400">{editable ? "+ Add GSTIN" : "—"}</span>}
      </button>
    );
  }
  return (
    <div className="flex items-center gap-1">
      <Input value={v} onChange={(e) => setV(e.target.value.toUpperCase())} maxLength={15} className={cn("h-8 w-44 font-mono text-xs", v && st !== "valid" && "border-red-400")} autoFocus
        onKeyDown={(e) => { if (e.key === "Enter" && (st === "valid" || !v)) { onSave(v); setEdit(false); } if (e.key === "Escape") setEdit(false); }} />
      <button className="rounded p-1 text-emerald-700 hover:bg-emerald-50 disabled:opacity-30" disabled={!!v && st !== "valid"} onClick={() => { onSave(v); setEdit(false); }} aria-label="Save"><Check className="h-4 w-4" /></button>
      <button className="rounded p-1 text-slate-500 hover:bg-slate-100" onClick={() => setEdit(false)} aria-label="Cancel"><X className="h-4 w-4" /></button>
    </div>
  );
}

function MergeModal({ suggestion, parties, usage, onClose, onMerge }: { suggestion: MergeSuggestion; parties: Party[]; usage: Record<string, { amount: number; rows: number }>; onClose: () => void; onMerge: (from: string, into: string) => Promise<void> }) {
  const a = parties.find((p) => p.normalized_name === suggestion.a);
  const b = parties.find((p) => p.normalized_name === suggestion.b);
  const defaultKeep = (b?.gstin && !a?.gstin) || (usage[suggestion.b]?.rows ?? 0) > (usage[suggestion.a]?.rows ?? 0) ? suggestion.b : suggestion.a;
  const [keep, setKeep] = useState(defaultKeep);
  const [busy, setBusy] = useState(false);
  const other = keep === suggestion.a ? suggestion.b : suggestion.a;
  return (
    <Modal open onClose={onClose} title="Merge parties"
      footer={<><Button variant="ghost" onClick={onClose}>Cancel</Button><Button loading={busy} onClick={async () => { setBusy(true); await onMerge(other, keep); setBusy(false); }}>Merge</Button></>}>
      <p className="mb-4 text-sm text-slate-600">Choose the name to keep. All entries of the other party (in unlocked years) move to it.</p>
      {[a, b].map((p) => p && (
        <label key={p.id} className={cn("mb-2 flex cursor-pointer items-center gap-3 rounded-xl border p-3", keep === p.normalized_name ? "border-navy-600 bg-navy-50" : "border-slate-200")}>
          <input type="radio" checked={keep === p.normalized_name} onChange={() => setKeep(p.normalized_name)} />
          <div className="flex-1"><div className="font-medium">{p.party_name}</div><div className="font-mono text-xs text-slate-500">{p.gstin ?? "No GSTIN"} · {usage[p.normalized_name]?.rows ?? 0} entries this year</div></div>
        </label>
      ))}
    </Modal>
  );
}
