import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useSearch } from "@tanstack/react-router";
import { Plus, Search, Users, Upload, Download, Archive, ChevronRight, Trash2 } from "lucide-react";
import { supabase } from "@/integrations/supabase/client";
import { useFirm } from "@/contexts/FirmContext";
import { useTeam } from "@/hooks/useTeam";
import { useToast } from "@/components/Toast";
import { Alert, Badge, Button, Card, EmptyState, Input, Modal, PageHeader, Select, Spinner } from "@/components/ui";
import { ClientForm, ClientRecord, emptyClient } from "@/components/ClientForm";
import { canEdit, isAdmin, errMsg, fetchAll, logActivity, CLIENT_STATUSES } from "@/lib/db";
import { deleteClientData } from "@/components/DeleteClientDialog";
import { parseFile, ACCEPTED_FILES } from "@/lib/import/parseFile";
import { isValidPan, cleanGstin } from "@/lib/validators";
import { downloadClientTemplate } from "@/lib/export";
import { formatDate } from "@/lib/format";

export default function Clients() {
  const { firm, role } = useFirm();
  const { nameOf } = useTeam();
  const toast = useToast();
  const nav = useNavigate();
  const search = useSearch({ strict: false }) as { new?: string };
  const [list, setList] = useState<(ClientRecord & { engagements: { count: number }[] })[]>([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [showArchived, setShowArchived] = useState(false);
  const [editing, setEditing] = useState<ClientRecord | null>(search.new ? emptyClient() : null);
  const [importOpen, setImportOpen] = useState(false);

  // delete straight from the list: tick one or many, one confirmation
  const [sel, setSel] = useState<Set<string>>(new Set());
  const [del, setDel] = useState<ClientRecord[] | null>(null);
  const askDelete = (c: ClientRecord) => setDel([c]);
  const toggle = (id: string) => setSel((s) => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n; });
  const load = async () => {
    if (!firm) return;
    setLoading(true);
    try {
      const rows = await fetchAll<any>((from, to) => supabase.from("clients").select("*, engagements(count)").eq("firm_id", firm.id).order("name").range(from, to));
      setList(rows);
    } catch (e) { toast(errMsg(e), "error"); }
    setLoading(false);
  };
  useEffect(() => { load(); }, [firm?.id]);

  const filtered = useMemo(() => {
    const s = q.trim().toLowerCase();
    return list.filter((c) =>
      (showArchived ? c.archived : !c.archived) &&
      (!status || c.status === status) &&
      (!s || c.name.toLowerCase().includes(s) || (c.pan ?? "").toLowerCase().includes(s) || (c.gstins ?? []).some((g) => g.toLowerCase().includes(s)) || (c.contact_person ?? "").toLowerCase().includes(s)));
  }, [list, q, status, showArchived]);

  const closeForm = () => { setEditing(null); if (search.new) { nav({ to: "/app/clients", search: {}, replace: true }); } };

  return (
    <>
      <PageHeader
        title="Clients"
        subtitle={`${list.filter((c) => !c.archived).length} active clients`}
        actions={canEdit(role) && (
          <>
            <Button variant="outline" icon={<Upload className="h-4 w-4" />} onClick={() => setImportOpen(true)}>Import</Button>
            <Button icon={<Plus className="h-4 w-4" />} onClick={() => setEditing(emptyClient())}>Add client</Button>
          </>
        )}
      />
      {isAdmin(role) && sel.size > 0 && (
        <div className="mb-3 flex flex-wrap items-center gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-2 text-sm">
          <span><b>{sel.size}</b> {sel.size === 1 ? "client" : "clients"} ticked</span>
          <Button size="sm" variant="danger" icon={<Trash2 className="h-4 w-4" />} onClick={() => setDel(list.filter((c) => sel.has(c.id!)))}>Delete {sel.size}</Button>
          <button type="button" className="text-xs text-slate-600 hover:underline" onClick={() => setSel(new Set())}>Clear</button>
        </div>
      )}
      <Card className="mb-4 p-3">
        <div className="flex flex-col gap-2 sm:flex-row">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search name, PAN, GSTIN, contact…" className="pl-9" />
          </div>
          <Select value={status} onChange={(e) => setStatus(e.target.value)} className="sm:w-44">
            <option value="">All statuses</option>
            {CLIENT_STATUSES.map((s) => <option key={s}>{s}</option>)}
          </Select>
          <Button variant={showArchived ? "secondary" : "ghost"} icon={<Archive className="h-4 w-4" />} onClick={() => setShowArchived((v) => !v)}>
            {showArchived ? "Showing archived" : "Archived"}
          </Button>
        </div>
      </Card>

      <Card>
        {loading ? <div className="flex justify-center py-12"><Spinner /></div> :
          filtered.length === 0 ? (
            <EmptyState icon={<Users className="h-7 w-7" />} title={list.length ? "No matching clients" : "Add your first client"}
              text={list.length ? "Try a different search." : "Clients hold assessment years, a party master and uploaded ledgers."}
              action={!list.length && canEdit(role) && <Button icon={<Plus className="h-4 w-4" />} onClick={() => setEditing(emptyClient())}>Add client</Button>} />
          ) : (
            <>
              {/* Mobile cards */}
              <ul className="divide-y divide-slate-100 md:hidden">
                {filtered.map((c) => (
                  <li key={c.id}>
                    <Link to="/app/clients/$clientId" params={{ clientId: c.id! }} className="flex items-center gap-3 px-4 py-3.5">
                      <div className="min-w-0 flex-1">
                        <div className="truncate font-medium">{c.name}</div>
                        <div className="text-xs text-slate-500">{c.pan || "No PAN"} · {c.status} · {c.engagements?.[0]?.count ?? 0} AY</div>
                      </div>
                      {isAdmin(role) && <button type="button" aria-label={`Delete ${c.name}`} className="p-2 text-slate-300 hover:text-red-600" onClick={(e) => { e.preventDefault(); e.stopPropagation(); askDelete(c); }}><Trash2 className="h-4 w-4" /></button>}
                      <ChevronRight className="h-4 w-4 text-slate-400" />
                    </Link>
                  </li>
                ))}
              </ul>
              {/* Desktop table */}
              <div className="hidden overflow-x-auto md:block">
                <table className="table-pro">
                  <thead><tr>{isAdmin(role) && <th className="w-8"><input type="checkbox" aria-label="Tick all" checked={filtered.length > 0 && filtered.every((c) => sel.has(c.id!))} onChange={(e) => setSel(e.target.checked ? new Set(filtered.map((c) => c.id!)) : new Set())} /></th>}<th>Client</th><th>PAN</th><th>Status</th><th>GSTIN</th><th>Years</th><th>Created by</th><th></th></tr></thead>
                  <tbody>
                    {filtered.map((c) => (
                      <tr key={c.id} className="cursor-pointer" onClick={() => nav({ to: "/app/clients/$clientId", params: { clientId: c.id! } })}>
                        {isAdmin(role) && <td onClick={(e) => e.stopPropagation()}><input type="checkbox" aria-label={`Tick ${c.name}`} checked={sel.has(c.id!)} onChange={() => toggle(c.id!)} /></td>}
                        <td><div className="font-medium text-slate-900">{c.name}</div>{c.contact_person && <div className="text-xs text-slate-500">{c.contact_person}</div>}</td>
                        <td className="font-mono text-xs">{c.pan || <span className="text-slate-400">—</span>}</td>
                        <td><Badge>{c.status}</Badge></td>
                        <td className="font-mono text-xs">{c.gstins?.[0] || <span className="text-slate-400">—</span>}{(c.gstins?.length ?? 0) > 1 && <span className="ml-1 text-slate-500">+{c.gstins.length - 1}</span>}</td>
                        <td>{c.engagements?.[0]?.count ?? 0}</td>
                        <td className="text-xs text-slate-500">{nameOf(c.created_by)}<div>{formatDate(c.created_at)}</div></td>
                        <td className="whitespace-nowrap text-right">
                          {isAdmin(role) && <button type="button" title="Delete client" aria-label={`Delete ${c.name}`} className="mr-2 rounded p-1 text-slate-300 hover:bg-red-50 hover:text-red-600" onClick={(e) => { e.stopPropagation(); askDelete(c); }}><Trash2 className="inline h-4 w-4" /></button>}
                          <ChevronRight className="inline h-4 w-4 text-slate-400" /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
      </Card>

      {editing && (
        <ClientForm
          client={editing}
          onClose={closeForm}
          onSaved={(id, isNew) => { closeForm(); load(); if (isNew) nav({ to: "/app/clients/$clientId", params: { clientId: id } }); }}
        />
      )}
      <ImportClients open={importOpen} onClose={() => setImportOpen(false)} onDone={() => { setImportOpen(false); load(); }} />
      {del && <QuickDelete clients={del} onClose={() => setDel(null)} onDone={() => { setDel(null); setSel(new Set()); load(); }} />}
    </>
  );
}

function ImportClients({ open, onClose, onDone }: { open: boolean; onClose: () => void; onDone: () => void }) {
  const { firm } = useFirm();
  const toast = useToast();
  const ref = useRef<HTMLInputElement>(null);
  const [rows, setRows] = useState<any[]>([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const pick = async (f: File) => {
    setErr(""); setBusy(true);
    try {
      const parsed = await parseFile(f);
      // the sheet with a "Client Name" heading in its first 10 rows (title rows above the headings are fine)
      const isNameHead = (h: unknown) => { const t = String(h ?? "").trim().toLowerCase(); return t.includes("client") || t === "name" || t.includes("party name"); };
      let m = parsed.sheets[0].rows;
      let hr = -1;
      for (const sh of parsed.sheets) {
        const i = sh.rows.slice(0, 10).findIndex((r) => (r ?? []).some(isNameHead));
        if (i >= 0) { m = sh.rows; hr = i; break; }
      }
      if (hr < 0) {
        const seen = (m[0] ?? []).map((h) => String(h ?? "").trim()).filter(Boolean).slice(0, 8).join(", ");
        throw new Error(`A 'Client Name' column is required.${seen ? ` The first row of the file has: ${seen}.` : " The file's first row is empty or could not be read – save it again in Excel and retry."}`);
      }
      const header = m[hr].map((h) => String(h ?? "").toLowerCase());
      const col = (...names: string[]) => header.findIndex((h) => names.some((n) => h.includes(n)));
      const ci = { name: header.findIndex(isNameHead), pan: col("pan"), gstin: col("gst"), status: col("status", "constitution"), contact: col("contact"), email: col("email", "mail"), mobile: col("mobile", "phone"), address: col("address") };
      const out = m.slice(hr + 1).filter((r) => String(r[ci.name] ?? "").trim()).map((r) => {
        const v = (i: number) => (i >= 0 ? String(r[i] ?? "").trim() : "");
        const st = CLIENT_STATUSES.find((s) => s.toLowerCase() === v(ci.status).toLowerCase()) ?? "Other";
        const pan = v(ci.pan).toUpperCase();
        return {
          name: v(ci.name), pan: pan || null, gstins: v(ci.gstin) ? v(ci.gstin).split(/[,;\s]+/).map(cleanGstin).filter(Boolean) : [],
          status: v(ci.status) ? st : "Individual", contact_person: v(ci.contact) || null, email: v(ci.email) || null, mobile: v(ci.mobile) || null, address: v(ci.address) || null,
          _warn: pan && !isValidPan(pan) ? "PAN format looks wrong" : "",
        };
      });
      setRows(out);
    } catch (e) { setErr(errMsg(e)); }
    setBusy(false);
  };

  const save = async () => {
    if (!firm) return;
    setBusy(true);
    const payload = rows.map(({ _warn, ...r }) => ({ ...r, firm_id: firm.id }));
    for (let i = 0; i < payload.length; i += 200) {
      const { error } = await supabase.from("clients").insert(payload.slice(i, i + 200));
      if (error) { setErr(errMsg(error)); setBusy(false); return; }
    }
    await logActivity(firm.id, "client.imported", "client", undefined, { count: payload.length });
    toast(`${payload.length} clients imported`);
    setRows([]); setBusy(false); onDone();
  };

  return (
    <Modal open={open} onClose={onClose} title="Import clients from Excel" wide
      footer={<><Button variant="ghost" onClick={onClose}>Cancel</Button><Button onClick={save} disabled={!rows.length} loading={busy}>Import {rows.length || ""} clients</Button></>}>
      <div className="space-y-4">
        <Alert tone="info">Columns: Client Name (required), PAN, GSTIN, Status, Contact Person, Email, Mobile, Address. <button className="font-semibold underline" onClick={downloadClientTemplate}><Download className="mr-1 inline h-3.5 w-3.5" />Download template</button></Alert>
        <input ref={ref} type="file" accept={ACCEPTED_FILES} className="hidden" onChange={(e) => e.target.files?.[0] && pick(e.target.files[0])} />
        <Button variant="outline" icon={<Upload className="h-4 w-4" />} onClick={() => ref.current?.click()} loading={busy && !rows.length}>Choose file</Button>
        {err && <Alert tone="error">{err}</Alert>}
        {rows.length > 0 && (
          <div className="max-h-80 overflow-auto rounded-lg border">
            <table className="table-pro">
              <thead><tr><th>Name</th><th>PAN</th><th>Status</th><th>GSTIN</th><th>Check</th></tr></thead>
              <tbody>{rows.slice(0, 200).map((r, i) => (
                <tr key={i}><td>{r.name}</td><td className="font-mono text-xs">{r.pan}</td><td>{r.status}</td><td className="font-mono text-xs">{r.gstins.join(", ")}</td><td className="text-xs text-amber-700">{r._warn}</td></tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </div>
    </Modal>
  );
}

/** Delete one or many clients with one confirmation. Years marked Final (locked) are not deleted. */
function QuickDelete({ clients, onClose, onDone }: { clients: ClientRecord[]; onClose: () => void; onDone: () => void }) {
  const { firm } = useFirm();
  const toast = useToast();
  const [engs, setEngs] = useState<Record<string, { id: string; assessment_year: string; locked: boolean }[]> | null>(null);
  const [busy, setBusy] = useState("");
  useEffect(() => {
    supabase.from("engagements").select("id, client_id, assessment_year, locked").in("client_id", clients.map((c) => c.id!)).then(({ data, error }) => {
      if (error) { toast(errMsg(error), "error"); onClose(); return; }
      const m: Record<string, any[]> = {};
      (data ?? []).forEach((e: any) => { (m[e.client_id] ||= []).push(e); });
      setEngs(m);
    });
  }, []);
  const locked = engs ? clients.filter((c) => (engs[c.id!] ?? []).some((e) => e.locked)) : [];
  const go = engs ? clients.filter((c) => !locked.includes(c)) : [];
  const run = async () => {
    let n = 0;
    for (const c of go) {
      setBusy(`Deleting ${c.name} (${n + 1} of ${go.length})…`);
      try { await deleteClientData(firm!.id, { id: c.id!, name: c.name }, engs![c.id!] ?? []); n++; }
      catch (e) { toast(`${c.name}: ${errMsg(e)}`, "error"); }
    }
    setBusy("");
    toast(`${n} ${n === 1 ? "client" : "clients"} deleted`);
    onDone();
  };
  return (
    <Modal open onClose={busy ? () => {} : onClose} title={clients.length === 1 ? `Delete ${clients[0].name}?` : `Delete ${clients.length} clients?`}
      footer={<><Button variant="ghost" onClick={onClose} disabled={!!busy}>Cancel</Button>
        <Button variant="danger" icon={<Trash2 className="h-4 w-4" />} disabled={!engs || !go.length} loading={!!busy} onClick={run}>{busy || `Delete ${go.length}`}</Button></>}>
      {!engs ? <div className="py-4 text-center text-sm text-slate-500">Checking…</div> : (
        <div className="space-y-3 text-sm">
          <p>Each client is removed with all its assessment years, entries, party master and uploaded files. This cannot be undone.</p>
          <ul className="max-h-60 space-y-1 overflow-auto rounded-lg border border-slate-200 p-2">
            {go.map((c) => <li key={c.id} className="flex justify-between gap-3"><span>{c.name}</span><span className="text-xs text-slate-500">{(engs[c.id!] ?? []).length} year(s)</span></li>)}
          </ul>
          {locked.length > 0 && <Alert tone="warn">Not deleted – a year is Final and locked: {locked.map((c) => c.name).join(", ")}. Unlock the year first.</Alert>}
        </div>
      )}
    </Modal>
  );
}
