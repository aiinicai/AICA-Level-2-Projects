// Clause 44 – step after a Tally file (with masters) is read: choose the expense and Fixed Asset ledgers.
import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, CheckCircle2, ChevronDown, ChevronRight, FileSpreadsheet, Table2 } from "lucide-react";
import { useFirm } from "@/contexts/FirmContext";
import { useToast } from "@/components/Toast";
import { Alert, Badge, Button, Card, Select, Spinner, cn } from "@/components/ui";
import { formatINR } from "@/lib/format";
import { errMsg, logActivity } from "@/lib/db";
import { KIND_LABEL, exemptTax, type Books, type LedgerKind } from "@/lib/c44/books";
import { DEFAULT_SETTINGS, ledgerChosen, ledgerTax, prepareImport, type C44Settings, type StoredLedger } from "@/lib/c44/ledgerMethod";
import { loadSettings, saveImport } from "@/lib/c44/ledgerStore";

interface Props {
  engagement: { id: string; assessment_year: string; clause_answers?: any };
  clientId: string; file: File; books: Books; software: string;
  onDone: () => void; onBack: () => void; onUseColumns: () => void;
}

const amt = (n: number) => formatINR(n, { symbol: false });

export function LedgerPicker({ engagement, clientId, file, books, software, onDone, onBack, onUseColumns }: Props) {
  const { firm } = useFirm();
  const toast = useToast();
  const [s, setS] = useState<C44Settings | null>(null);
  const [open, setOpen] = useState<Record<string, boolean>>({});
  const [saving, setSaving] = useState("");
  const [err, setErr] = useState("");
  const [showEmpty, setShowEmpty] = useState(false);
  const [detail, setDetail] = useState(false);
  useEffect(() => { loadSettings(clientId).then((r) => setS(r.settings)).catch(() => setS({ ...DEFAULT_SETTINGS })); }, [clientId]);

  // ledgers of the books with their amounts (independent of the choice)
  const ledgers = useMemo(() => prepareImport(books, DEFAULT_SETTINGS, { upload_id: "", file: "" }).books.ledgers, [books]);
  const tree = useMemo(() => {
    const out: Record<LedgerKind, { group: string; items: [string, StoredLedger][] }[]> = { revenue: [], capital: [] };
    for (const [name, l] of Object.entries(ledgers)) {
      const g = l.p + (l.g && l.g !== l.p ? ` › ${l.g}` : "");
      let grp = out[l.k].find((x) => x.group === g);
      if (!grp) { grp = { group: g, items: [] }; out[l.k].push(grp); }
      grp.items.push([name, l]);
    }
    (Object.keys(out) as LedgerKind[]).forEach((k) => { out[k].sort((a, b) => a.group.localeCompare(b.group)); out[k].forEach((g) => g.items.sort((a, b) => Math.abs(b[1].total) - Math.abs(a[1].total))); });
    return out;
  }, [ledgers]);

  if (!s) return <Card className="flex justify-center p-10"><Spinner /></Card>;
  const chosen = (n: string) => ledgerChosen(n, ledgers[n], s);
  const setSel = (names: string[], v: boolean) => setS({ ...s, sel: { ...s.sel, ...Object.fromEntries(names.map((n) => [n.toLowerCase(), v])) } });
  const setTax = (n: string, v: "taxable" | "exempt") => setS({ ...s, tax: { ...s.tax, [n.toLowerCase()]: v } });
  const total = (k: LedgerKind) => Object.entries(ledgers).filter(([n, l]) => l.k === k && chosen(n)).reduce((t, [, l]) => t + l.total, 0);
  const count = Object.keys(ledgers).filter(chosen).length;
  const leftMap = new Map<string, [number, number]>();
  Object.entries(ledgers).forEach(([n, l]) => { if (!chosen(n) && Math.abs(l.total) >= 0.005) { const why = l.x ?? "Left out by you"; const e = leftMap.get(why) ?? [0, 0]; leftMap.set(why, [e[0] + l.total, e[1] + 1]); } });
  const leftOut = Array.from(leftMap.entries()).map(([w, [a, n]]) => [w, a, n] as [string, number, number]).sort((a, b) => b[1] - a[1]);

  const save = async () => {
    if (!firm) return;
    setErr("");
    try {
      const r = await saveImport({ firmId: firm.id, clientId, eng: engagement as any, file, software, books, settings: s, progress: setSaving });
      await logActivity(firm.id, "upload.created", "engagement", engagement.id, { file: file.name, rows: r.rows, software, method: "ledgers" });
      toast(`${r.chosen} ledgers and ${r.parties} parties prepared`);
      onDone();
    } catch (e) { setErr(errMsg(e)); }
    setSaving("");
  };

  return (
    <Card className="p-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-sm"><FileSpreadsheet className="h-4 w-4 text-navy-600" /><b>{file.name}</b><Badge className="bg-navy-50 text-navy-800">{software}</Badge>
          <span className="text-xs text-slate-500">{books.vouchers.length.toLocaleString("en-IN")} vouchers · {books.ledgers.length.toLocaleString("en-IN")} ledgers</span></div>
        <div className="flex gap-1">
          <Button variant="ghost" size="sm" icon={<Table2 className="h-4 w-4" />} onClick={onUseColumns} disabled={!!saving}>Map columns instead</Button>
          <Button variant="ghost" size="sm" icon={<ArrowLeft className="h-4 w-4" />} onClick={onBack} disabled={!!saving}>Choose another file</Button>
        </div>
      </div>
      <div className="mb-1 text-base font-semibold">Which ledgers go into Clause 44?</div>
      <p className="mb-4 text-sm text-slate-600">Chosen for you from the Tally groups. Prepare straight away, or open the list to change anything.</p>
      {!books.vouchers.length && <Alert tone="warn" className="mb-3">This file has the ledger masters but no vouchers. Choose the masters and the Day Book together (several files at once), or bring the data with the Tally Connector.</Alert>}
      <div className="mb-4 grid gap-3 sm:grid-cols-2">
        <div className="rounded-xl border border-emerald-200 bg-emerald-50/60 p-4">
          <div className="text-xs font-semibold uppercase tracking-wide text-emerald-800">Goes into Clause 44</div>
          <div className="mt-1 text-2xl font-semibold tabular-nums">{formatINR(total("revenue") + total("capital"))}</div>
          <div className="mt-1 text-sm text-slate-700">Expenses of P&L {amt(total("revenue"))} · Fixed Asset additions {amt(total("capital"))}</div>
          <div className="text-xs text-slate-500">{count} ledgers</div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-600">Left out</div>
          {leftOut.length ? <ul className="mt-1 space-y-0.5 text-sm">{leftOut.map(([why, a, n]) => <li key={why} className="flex justify-between gap-3"><span>{why} <span className="text-xs text-slate-400">({n})</span></span><span className="tabular-nums">{amt(a)}</span></li>)}</ul>
            : <p className="mt-1 text-sm text-slate-500">Nothing.</p>}
        </div>
      </div>
      {engagement.clause_answers?.c44_books?.upload_id && <Alert tone="info" className="mb-3">This replaces the earlier Tally import of this year ({engagement.clause_answers.c44_books.file}). Files uploaded by mapping columns stay as they are.</Alert>}
      {err && <Alert tone="error" className="mb-3">{err}</Alert>}
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <Button variant="outline" size="sm" icon={detail ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />} onClick={() => setDetail(!detail)} disabled={!!saving}>{detail ? "Hide the ledger list" : `See or change ledgers (${Object.keys(ledgers).filter((n) => Math.abs(ledgers[n].total) >= 0.005 || ledgers[n].out).length})`}</Button>
        <Button icon={saving ? undefined : <CheckCircle2 className="h-4 w-4" />} loading={!!saving} disabled={!count || !books.vouchers.length} onClick={save}>{saving || "Prepare Clause 44"}</Button>
      </div>
      {detail && <>
      {(() => { const empty = Object.values(ledgers).filter((l) => Math.abs(l.total) < 0.005 && !l.out).length; return empty ? (
        <label className="mb-3 flex items-center gap-2 text-xs text-slate-500"><input type="checkbox" className="h-3.5 w-3.5" checked={showEmpty} onChange={(e) => setShowEmpty(e.target.checked)} />Show {empty} ledgers with no entries in this period</label>) : null; })()}
      {(["revenue", "capital"] as LedgerKind[]).map((k) => (
        <div key={k} className="mb-5">
          <div className="mb-2 flex items-center justify-between border-b border-slate-200 pb-1">
            <div className="text-sm font-semibold uppercase tracking-wide text-slate-600">{KIND_LABEL[k]}</div>
            <div className="text-sm tabular-nums text-slate-600">Chosen: <b>{amt(total(k))}</b></div>
          </div>
          {!tree[k].length && <p className="text-sm text-slate-500">None in these books.</p>}
          <div className="space-y-2">
            {tree[k].map((g) => {
              const names = g.items.map(([n]) => n);
              const on = names.filter(chosen).length;
              const isOpen = open[g.group] ?? g.items.length <= 25;
              return (
                <div key={g.group} className="rounded-xl border border-slate-200">
                  <div className="flex items-center gap-2 bg-slate-50 px-3 py-2">
                    <input type="checkbox" aria-label={`All of ${g.group}`} className="h-4 w-4 accent-navy-900" checked={on === names.length} ref={(el) => { if (el) el.indeterminate = on > 0 && on < names.length; }}
                      disabled={!!saving} onChange={(e) => setSel(names, e.target.checked)} />
                    <button type="button" className="flex flex-1 items-center gap-1 text-left text-sm font-semibold" onClick={() => setOpen({ ...open, [g.group]: !isOpen })}>
                      {isOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}{g.group}
                      <span className="ml-1 text-xs font-normal text-slate-500">{on} of {names.length} chosen</span>
                    </button>
                    <span className="text-sm tabular-nums">{amt(g.items.filter(([n]) => chosen(n)).reduce((t, [, l]) => t + l.total, 0))}</span>
                  </div>
                  {isOpen && (
                    <table className="table-pro">
                      <tbody>{g.items.filter(([n, l]) => showEmpty || Math.abs(l.total) >= 0.005 || l.out).map(([n, l]) => {
                        const c = chosen(n);
                        const t = ledgerTax(n, l, s);
                        return (
                          <tr key={n} className={cn(!c && "text-slate-400")}>
                            <td className="w-8"><input type="checkbox" aria-label={n} className="h-4 w-4 accent-navy-900" checked={c} disabled={!!saving} onChange={(e) => setSel([n], e.target.checked)} /></td>
                            <td className="font-medium">{n}{l.x && <Badge className={cn("ml-2", c ? "bg-amber-50 text-amber-700" : "bg-slate-100 text-slate-500")}>{l.x}</Badge>}
                              {l.out ? <span className="ml-2 text-[11px] text-slate-400">({amt(l.out)} sale / depreciation not counted)</span> : null}</td>
                            <td className="w-40">
                              <Select aria-label={`GST of ${n}`} className="h-8 text-xs" value={exemptTax(t) ? "exempt" : "taxable"} disabled={!!saving || !c} onChange={(e) => setTax(n, e.target.value as "taxable" | "exempt")}>
                                <option value="taxable">Taxable</option><option value="exempt">Exempt / nil / non-GST</option>
                              </Select></td>
                            <td className="num w-36">{amt(l.total)}</td>
                          </tr>);
                      })}</tbody>
                    </table>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      ))}

      </>}
      {detail && <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4">
        <span className="text-sm text-slate-600"><b>{count}</b> ledgers · Clause 44 total <b className="tabular-nums">{formatINR(total("revenue") + total("capital"))}</b></span>
        <Button icon={saving ? undefined : <CheckCircle2 className="h-4 w-4" />} loading={!!saving} disabled={!count || !books.vouchers.length} onClick={save}>{saving || "Prepare Clause 44"}</Button>
      </div>}
    </Card>
  );
}
