import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { logAudit, run, uid } from "@/lib/db";
import { inr, type ReconResult } from "@/lib/recon";
import type { ReconItem } from "@/lib/types";
import { useRefresh } from "@/lib/useData";

const KEY_SECTIONS = ["Turnover", "Tax Liability", "Input Tax Credit", "Nature of Supply", "GSTR-9 Table-wise", "GSTR-9C Reconciliation"];

export function ReviewPage({ clientId, res, saved }: { clientId: string; res: ReconResult; saved: ReconItem[] }) {
  const rows = res.summaries.filter((s) => KEY_SECTIONS.includes(s.section));
  const refresh = useRefresh();
  const [draft, setDraft] = useState<Record<string, { explanation: string; treatment: string; final: string }>>({});

  useEffect(() => {
    const d: Record<string, { explanation: string; treatment: string; final: string }> = {};
    for (const r of rows) {
      const k = `Final Review|${r.section} — ${r.label}`;
      const s = saved.find((x) => `${x.section}|${x.key_label}` === k);
      d[k] = {
        explanation: s?.remarks ?? "",
        treatment: s?.proposed_treatment ?? "",
        final: String(s?.adjustment ?? r.books),
      };
    }
    setDraft(d);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [saved.length, res.summaries.length]);

  async function saveAll() {
    for (const r of rows) {
      const key = `${r.section} — ${r.label}`;
      const k = `Final Review|${key}`;
      const v = draft[k];
      if (!v) continue;
      const existing = saved.find((x) => `${x.section}|${x.key_label}` === k);
      const id = existing?.id ?? uid();
      await run("DELETE FROM recon_items WHERE id=?", [id]);
      await run(
        `INSERT INTO recon_items (id, client_id, section, key_label, party, status, books_taxable, books_tax,
          gst_taxable, gst_tax, remarks, adjustment, proposed_treatment, resolved) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)`,
        [id, clientId, "Final Review", key, "", Math.abs(r.diff) > 1 ? "value_mismatch" : "matched", r.books, 0, r.gst, 0,
          v.explanation, Number(v.final) || 0, v.treatment, 1],
      );
    }
    await logAudit(clientId, "Final review updated", `${rows.length} line(s) saved`);
    refresh(["recon", "audit"]);
    toast.success("Final review saved.");
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Final figures to be considered while preparing GSTR-9 / GSTR-9C. Amounts are in rupees.
        </p>
        <Button onClick={saveAll}>Save final review</Button>
      </div>
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[280px]">Particulars</TableHead>
                <TableHead className="num">Books figure</TableHead>
                <TableHead className="num">GST return figure</TableHead>
                <TableHead className="num">Difference</TableHead>
                <TableHead>Explanation</TableHead>
                <TableHead>Proposed treatment</TableHead>
                <TableHead className="w-[150px]">Final figure</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((r) => {
                const k = `Final Review|${r.section} — ${r.label}`;
                const v = draft[k] ?? { explanation: "", treatment: "", final: String(r.books) };
                const set = (patch: Partial<typeof v>) => setDraft((d) => ({ ...d, [k]: { ...v, ...patch } }));
                return (
                  <TableRow key={k}>
                    <TableCell>
                      <div className="text-xs uppercase tracking-wide text-muted-foreground">{r.section}</div>
                      {r.label}
                    </TableCell>
                    <TableCell className="num">{inr(r.books)}</TableCell>
                    <TableCell className="num">{inr(r.gst)}</TableCell>
                    <TableCell className={`num ${Math.abs(r.diff) > 1 ? "text-destructive" : "text-success"}`}>{inr(r.diff)}</TableCell>
                    <TableCell><Input value={v.explanation} onChange={(e) => set({ explanation: e.target.value })} placeholder="Reason for difference" /></TableCell>
                    <TableCell><Input value={v.treatment} onChange={(e) => set({ treatment: e.target.value })} placeholder="e.g. Pay through DRC-03" /></TableCell>
                    <TableCell><Input className="num" value={v.final} onChange={(e) => set({ final: e.target.value })} /></TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
