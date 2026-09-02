import { Card, CardContent } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { inr, type ReconResult } from "@/lib/recon";

function Stat({ label, value, tone }: { label: string; value: string; tone?: "warn" | "bad" | "ok" }) {
  const color = tone === "bad" ? "text-destructive" : tone === "warn" ? "text-warning" : tone === "ok" ? "text-success" : "text-foreground";
  return (
    <Card>
      <CardContent className="p-4">
        <div className="text-xs uppercase tracking-wide text-muted-foreground">{label}</div>
        <div className={`mt-1 text-xl font-semibold tabular-nums ${color}`}>{value}</div>
      </CardContent>
    </Card>
  );
}

export function Dashboard({ res }: { res: ReconResult }) {
  const t = res.totals;
  const sections = Array.from(new Set(res.summaries.map((s) => s.section)));
  return (
    <div className="space-y-6">
      <div className="grid gap-3 md:grid-cols-4">
        <Stat label="Total turnover (books)" value={`₹ ${inr(t.turnover)}`} />
        <Stat label="Tax liability (books)" value={`₹ ${inr(t.liability)}`} />
        <Stat label="ITC claimed" value={`₹ ${inr(t.itc)}`} />
        <Stat label="Total variance" value={`₹ ${inr(t.variance)}`} tone={t.variance > 0 ? "warn" : "ok"} />
        <Stat label="Unreconciled transactions" value={String(t.unreconciled)} tone={t.unreconciled > 0 ? "warn" : "ok"} />
        <Stat label="Potential additional tax liability" value={`₹ ${inr(t.additionalTax)}`} tone={t.additionalTax > 0 ? "bad" : "ok"} />
        <Stat label="Potential unclaimed ITC" value={`₹ ${inr(t.unclaimedItc)}`} tone={t.unclaimedItc > 0 ? "warn" : "ok"} />
        <Stat label="Summary lines prepared" value={String(res.summaries.length)} />
      </div>

      {sections.map((sec) => (
        <Card key={sec}>
          <CardContent className="p-0">
            <div className="border-b border-border bg-secondary/60 px-4 py-2 text-sm font-semibold">{sec}</div>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Particulars</TableHead>
                  <TableHead className="num">As per books</TableHead>
                  <TableHead className="num">As per GST return</TableHead>
                  <TableHead className="num">Difference</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {res.summaries.filter((s) => s.section === sec).map((r, i) => (
                  <TableRow key={i}>
                    <TableCell>
                      {r.label}
                      {r.note && <div className="text-xs text-muted-foreground">{r.note}</div>}
                    </TableCell>
                    <TableCell className="num">{inr(r.books)}</TableCell>
                    <TableCell className="num">{inr(r.gst)}</TableCell>
                    <TableCell className={`num font-medium ${Math.abs(r.diff) > 1 ? "text-destructive" : "text-success"}`}>
                      {inr(r.diff)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
