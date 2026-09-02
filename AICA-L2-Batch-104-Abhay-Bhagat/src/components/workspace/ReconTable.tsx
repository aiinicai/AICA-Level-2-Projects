import { useMemo, useState } from "react";
import { toast } from "sonner";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { logAudit, run, uid } from "@/lib/db";
import { inr, type MatchItem, type ReconResult } from "@/lib/recon";
import { STATUS_LABEL, type MismatchStatus, type ReconItem } from "@/lib/types";
import { useRefresh } from "@/lib/useData";

const tone: Record<MismatchStatus, string> = {
  matched: "bg-success/10 text-success border-success/30",
  missing_in_tally: "bg-destructive/10 text-destructive border-destructive/30",
  missing_in_return: "bg-destructive/10 text-destructive border-destructive/30",
  value_mismatch: "bg-warning/15 text-warning-foreground border-warning/40",
  tax_mismatch: "bg-warning/15 text-warning-foreground border-warning/40",
  gstin_mismatch: "bg-warning/15 text-warning-foreground border-warning/40",
  invoice_no_mismatch: "bg-warning/15 text-warning-foreground border-warning/40",
  timing_difference: "bg-accent text-accent-foreground border-border",
  manual_review: "bg-secondary text-secondary-foreground border-border",
};

export function ReconTable({
  clientId,
  res,
  saved,
}: {
  clientId: string;
  res: ReconResult;
  saved: ReconItem[];
}) {
  const [q, setQ] = useState("");
  const [status, setStatus] = useState<string>("all");
  const [section, setSection] = useState<string>("all");
  const [showResolved, setShowResolved] = useState("all");
  const [edit, setEdit] = useState<MatchItem | null>(null);
  const [form, setForm] = useState({ remarks: "", adjustment: "0", proposed_treatment: "", resolved: false });
  const refresh = useRefresh();

  const savedMap = useMemo(() => new Map(saved.map((s) => [`${s.section}|${s.key_label}`, s])), [saved]);
  const sections = Array.from(new Set(res.items.map((i) => i.section)));

  const rows = res.items.filter((i) => {
    const s = savedMap.get(`${i.section}|${i.key_label}`);
    if (status !== "all" && i.status !== status) return false;
    if (section !== "all" && i.section !== section) return false;
    if (showResolved === "resolved" && !s?.resolved) return false;
    if (showResolved === "open" && s?.resolved) return false;
    if (q && !`${i.key_label} ${i.party}`.toLowerCase().includes(q.toLowerCase())) return false;
    return true;
  });

  function open(i: MatchItem) {
    const s = savedMap.get(`${i.section}|${i.key_label}`);
    setForm({
      remarks: s?.remarks ?? "",
      adjustment: String(s?.adjustment ?? 0),
      proposed_treatment: s?.proposed_treatment ?? "",
      resolved: !!s?.resolved,
    });
    setEdit(i);
  }

  async function save() {
    if (!edit) return;
    const key = `${edit.section}|${edit.key_label}`;
    const existing = savedMap.get(key);
    const id = existing?.id ?? uid();
    await run("DELETE FROM recon_items WHERE id=?", [id]);
    await run(
      `INSERT INTO recon_items (id, client_id, section, key_label, party, status, books_taxable, books_tax,
        gst_taxable, gst_tax, remarks, adjustment, proposed_treatment, resolved) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)`,
      [
        id, clientId, edit.section, edit.key_label, edit.party, edit.status, edit.books_taxable, edit.books_tax,
        edit.gst_taxable, edit.gst_tax, form.remarks, Number(form.adjustment) || 0, form.proposed_treatment,
        form.resolved ? 1 : 0,
      ],
    );
    await logAudit(clientId, "Adjustment recorded", `${edit.key_label}: ${form.remarks || "remark updated"}`);
    refresh(["recon", "audit"]);
    setEdit(null);
    toast.success("Saved.");
  }

  const counts = res.items.reduce<Record<string, number>>((a, i) => ({ ...a, [i.status]: (a[i.status] ?? 0) + 1 }), {});

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {Object.entries(STATUS_LABEL).map(([k, label]) => (
          <button
            key={k}
            onClick={() => setStatus(status === k ? "all" : k)}
            className={`rounded border px-2.5 py-1 text-xs ${tone[k as MismatchStatus]} ${status === k ? "ring-2 ring-ring" : ""}`}
          >
            {label} · {counts[k] ?? 0}
          </button>
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <Input placeholder="Search invoice number or party" value={q} onChange={(e) => setQ(e.target.value)} className="max-w-xs" />
        <Select value={section} onValueChange={setSection}>
          <SelectTrigger className="w-64"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All sections</SelectItem>
            {sections.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={showResolved} onValueChange={setShowResolved}>
          <SelectTrigger className="w-44"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All items</SelectItem>
            <SelectItem value="open">Open only</SelectItem>
            <SelectItem value="resolved">Resolved only</SelectItem>
          </SelectContent>
        </Select>
        <span className="text-sm text-muted-foreground">{rows.length} of {res.items.length} transactions</span>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Document</TableHead>
                <TableHead>Party</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="num">Books taxable</TableHead>
                <TableHead className="num">Books tax</TableHead>
                <TableHead className="num">Return taxable</TableHead>
                <TableHead className="num">Return tax</TableHead>
                <TableHead className="num">Difference</TableHead>
                <TableHead>Remarks</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.slice(0, 500).map((i, n) => {
                const s = savedMap.get(`${i.section}|${i.key_label}`);
                const diff = i.books_taxable - i.gst_taxable;
                return (
                  <TableRow key={n} className={s?.resolved ? "opacity-60" : ""}>
                    <TableCell className="font-medium">{i.key_label}</TableCell>
                    <TableCell className="text-muted-foreground">{i.party}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className={tone[i.status]}>{STATUS_LABEL[i.status]}</Badge>
                    </TableCell>
                    <TableCell className="num">{inr(i.books_taxable)}</TableCell>
                    <TableCell className="num">{inr(i.books_tax)}</TableCell>
                    <TableCell className="num">{inr(i.gst_taxable)}</TableCell>
                    <TableCell className="num">{inr(i.gst_tax)}</TableCell>
                    <TableCell className={`num ${Math.abs(diff) > 1 ? "text-destructive" : ""}`}>{inr(diff)}</TableCell>
                    <TableCell className="max-w-[220px] truncate text-xs text-muted-foreground">{s?.remarks}</TableCell>
                    <TableCell>
                      <Button size="sm" variant="outline" onClick={() => open(i)}>Review</Button>
                    </TableCell>
                  </TableRow>
                );
              })}
              {rows.length === 0 && (
                <TableRow><TableCell colSpan={10} className="py-10 text-center text-sm text-muted-foreground">No transactions match the current filters.</TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={!!edit} onOpenChange={(o) => !o && setEdit(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>{edit?.key_label} — {edit && STATUS_LABEL[edit.status]}</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-2 rounded bg-secondary/60 p-3 text-sm">
              <div>Books taxable: <b>{inr(edit?.books_taxable ?? 0)}</b></div>
              <div>Return taxable: <b>{inr(edit?.gst_taxable ?? 0)}</b></div>
              <div>Books tax: <b>{inr(edit?.books_tax ?? 0)}</b></div>
              <div>Return tax: <b>{inr(edit?.gst_tax ?? 0)}</b></div>
            </div>
            <div className="space-y-1">
              <Label>Remarks</Label>
              <Textarea value={form.remarks} onChange={(e) => setForm({ ...form, remarks: e.target.value })} rows={3} />
            </div>
            <div className="space-y-1">
              <Label>Proposed adjustment amount (₹)</Label>
              <Input value={form.adjustment} onChange={(e) => setForm({ ...form, adjustment: e.target.value })} />
            </div>
            <div className="space-y-1">
              <Label>Proposed treatment</Label>
              <Input
                value={form.proposed_treatment}
                onChange={(e) => setForm({ ...form, proposed_treatment: e.target.value })}
                placeholder="e.g. Report in Table 10 of GSTR-9"
              />
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={form.resolved} onChange={(e) => setForm({ ...form, resolved: e.target.checked })} />
              Mark this item as resolved
            </label>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEdit(null)}>Cancel</Button>
            <Button onClick={save}>Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
