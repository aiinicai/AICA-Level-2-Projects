import { ReactNode, useEffect, useMemo, useState } from "react";
import { Plus, Search, Trash2, ChevronLeft, ChevronRight } from "lucide-react";
import { Button, Card, EmptyState, Input, Modal, cn } from "@/components/ui";
import { useToast } from "@/components/Toast";
import { errMsg } from "@/lib/db";
import { formatINR } from "@/lib/format";

export interface GridColumn<T> {
  key: keyof T & string;
  label: string;
  type?: "text" | "number" | "date" | "select" | "bool" | "readonly";
  options?: { value: string; label: string }[];
  width?: string;
  render?: (row: T) => ReactNode;
  upper?: boolean;
  /** A value must stay (no blank choice). */
  required?: boolean;
  /** Numbers below zero are refused. */
  min0?: boolean;
}

interface Props<T extends { id: string }> {
  rows: T[];
  columns: GridColumn<T>[];
  editable: boolean;
  onPatch: (id: string, patch: Partial<T>) => Promise<void>;
  onDelete?: (ids: string[]) => Promise<void>;
  onAdd?: () => Promise<void> | void;
  addLabel?: string;
  searchKeys?: (keyof T & string)[];
  rowClass?: (row: T) => string;
  empty?: ReactNode;
  toolbar?: ReactNode;
  /** Actions on the ticked rows (shown when at least one row is ticked). */
  bulkActions?: (ids: string[], clear: () => void) => ReactNode;
}

const PAGE = 50;

/** Editable table: each cell saves on blur / change. */
export function RowsGrid<T extends { id: string }>({ rows, columns, editable, onPatch, onDelete, onAdd, addLabel = "Add row", searchKeys, rowClass, empty, toolbar, bulkActions }: Props<T>) {
  const toast = useToast();
  const [q, setQ] = useState("");
  const [page, setPage] = useState(0);
  const [sel, setSel] = useState<Set<string>>(new Set());
  const [confirm, setConfirm] = useState(false);
  const canSelect = editable && (!!onDelete || !!bulkActions);

  const filtered = useMemo(() => {
    const s = q.trim().toLowerCase();
    if (!s || !searchKeys) return rows;
    return rows.filter((r) => searchKeys.some((k) => String((r as any)[k] ?? "").toLowerCase().includes(s)));
  }, [rows, q, searchKeys]);
  const pages = Math.max(1, Math.ceil(filtered.length / PAGE));
  // after deleting rows the page may no longer exist
  useEffect(() => { if (page > pages - 1) setPage(pages - 1); }, [page, pages]);
  const shown = filtered.slice(page * PAGE, page * PAGE + PAGE);

  const save = async (id: string, key: string, value: unknown) => {
    try { await onPatch(id, { [key]: value } as Partial<T>); } catch (e) { toast(errMsg(e), "error"); }
  };

  const cell = (r: T, c: GridColumn<T>) => {
    const v = (r as any)[c.key];
    if (c.render) return c.render(r);
    if (!editable || c.type === "readonly") {
      if (c.type === "number") return <span className="tabular-nums">{v === null || v === undefined ? "" : formatINR(v, { symbol: false })}</span>;
      if (c.type === "bool") return v ? "Yes" : "No";
      if (c.type === "select") return c.options?.find((o) => o.value === v)?.label ?? v ?? "";
      return v ?? "";
    }
    const cls = "h-8 w-full rounded-md border border-transparent bg-transparent px-1.5 text-sm hover:border-slate-300 focus:border-navy-500 focus:bg-white focus:outline-none";
    switch (c.type) {
      case "bool":
        return <input type="checkbox" checked={!!v} onChange={(e) => save(r.id, c.key, e.target.checked)} className="h-4 w-4 accent-navy-800" />;
      case "select":
        return (
          <select value={v ?? ""} onChange={(e) => save(r.id, c.key, e.target.value === "" ? null : e.target.value)} className={cls}>
            {!c.required && !c.options?.some((o) => o.value === "") && <option value="">—</option>}
            {c.options?.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        );
      case "number":
        return <input key={`${r.id}-${v}`} defaultValue={v ?? ""} inputMode="decimal" className={cn(cls, "text-right tabular-nums")}
          onBlur={(e) => { const t = e.target.value.replace(/,/g, "").trim(); const n = t === "" ? 0 : Number(t); if (!isFinite(n)) { toast("Enter a number", "error"); return; } if (c.min0 && n < 0) { toast("Enter an amount of zero or more", "error"); e.target.value = String(v ?? ""); return; } if (n !== Number(v)) save(r.id, c.key, n); }} />;
      case "date":
        return <input key={`${r.id}-${v}`} type="date" defaultValue={v ?? ""} className={cls} onBlur={(e) => { const t = e.target.value || null; if (t !== (v ?? null)) save(r.id, c.key, t); }} />;
      default:
        return <input key={`${r.id}-${v}`} defaultValue={v ?? ""} className={cn(cls, c.upper && "uppercase")}
          onBlur={(e) => { const raw = c.upper ? e.target.value.trim().toUpperCase() : e.target.value.trim(); const t: string | null = raw === "" ? null : raw; if (t !== (v ?? null)) save(r.id, c.key, t); }} />;
    }
  };

  return (
    <Card>
      <div className="flex flex-wrap items-center gap-2 border-b border-slate-100 p-3">
        {searchKeys && (
          <div className="relative min-w-[200px] flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <Input value={q} onChange={(e) => { setQ(e.target.value); setPage(0); }} placeholder="Search" className="pl-9" />
          </div>
        )}
        {toolbar}
        {editable && sel.size > 0 && bulkActions?.(Array.from(sel), () => setSel(new Set()))}
        {editable && sel.size > 0 && sel.size < filtered.length && <button type="button" className="text-xs font-medium text-navy-700 hover:underline" onClick={() => setSel(new Set(filtered.map((r) => r.id)))}>Select all {filtered.length.toLocaleString("en-IN")}{q.trim() ? " found" : ""}</button>}
        {editable && sel.size > 0 && <button type="button" className="text-xs text-slate-500 hover:underline" onClick={() => setSel(new Set())}>Clear ({sel.size})</button>}
        {editable && sel.size > 0 && onDelete && <Button size="sm" variant="outline" className="text-red-600" icon={<Trash2 className="h-4 w-4" />} onClick={() => setConfirm(true)}>Delete {sel.size}</Button>}
        {editable && onAdd && <Button size="sm" icon={<Plus className="h-4 w-4" />} onClick={async () => { try { await onAdd(); } catch (e) { toast(errMsg(e), "error"); } }}>{addLabel}</Button>}
      </div>
      {filtered.length === 0 ? (empty ?? <EmptyState title="No entries yet" text="Import a file or add rows manually." />) : (
        <div className="overflow-x-auto">
          <table className="table-pro">
            <thead><tr>
              {canSelect && <th className="w-8"><input type="checkbox" checked={shown.length > 0 && shown.every((r) => sel.has(r.id))} onChange={(e) => setSel(e.target.checked ? new Set(shown.map((r) => r.id)) : new Set())} /></th>}
              {columns.map((c) => <th key={c.key} style={{ minWidth: c.width }} className={c.type === "number" ? "text-right" : ""}>{c.label}</th>)}
            </tr></thead>
            <tbody>
              {shown.map((r) => (
                <tr key={r.id} className={rowClass?.(r)}>
                  {canSelect && <td><input type="checkbox" checked={sel.has(r.id)} onChange={() => setSel((s) => { const n = new Set(s); n.has(r.id) ? n.delete(r.id) : n.add(r.id); return n; })} /></td>}
                  {columns.map((c) => <td key={c.key} className={cn("!py-1", c.type === "number" && "text-right")}>{cell(r, c)}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {filtered.length > PAGE && (
        <div className="flex items-center justify-end gap-2 border-t border-slate-100 px-4 py-2 text-sm">
          <Button size="sm" variant="outline" disabled={page === 0} onClick={() => setPage((p) => p - 1)}><ChevronLeft className="h-4 w-4" /></Button>
          <span>{page + 1} / {pages}</span>
          <Button size="sm" variant="outline" disabled={page + 1 >= pages} onClick={() => setPage((p) => p + 1)}><ChevronRight className="h-4 w-4" /></Button>
        </div>
      )}
      <div className="border-t border-slate-100 px-4 py-2 text-xs text-slate-500">{filtered.length.toLocaleString("en-IN")} rows{editable ? " · changes save automatically" : ""}</div>
      {confirm && onDelete && (
        <Modal open onClose={() => setConfirm(false)} title={`Delete ${sel.size} rows?`}
          footer={<><Button variant="ghost" onClick={() => setConfirm(false)}>Cancel</Button><Button variant="danger" onClick={async () => {
            try { await onDelete(Array.from(sel)); setSel(new Set()); toast("Deleted"); } catch (e) { toast(errMsg(e), "error"); }
            setConfirm(false);
          }}>Delete</Button></>}>
          <p className="text-sm">This cannot be undone.</p>
        </Modal>
      )}
    </Card>
  );
}
