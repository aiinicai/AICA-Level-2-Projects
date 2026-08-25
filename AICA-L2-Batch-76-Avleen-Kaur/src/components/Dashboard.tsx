import { useState } from "react";
import { useServerFn } from "@tanstack/react-start";
import { Sparkles, Loader2 } from "lucide-react";
import { formatINR, summarize, type Category, type ReconRow } from "@/lib/recon";
import { generateSummaryNote } from "@/lib/summary.functions";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { toast } from "sonner";

const accent: Record<Category, string> = {
  Matched: "border-l-matched",
  "Amount Mismatch": "border-l-mismatch",
  "Missing in 2B": "border-l-risk",
  "ITC Ineligible": "border-l-risk",
  "Missing in Books": "border-l-info",
  "Duplicate in Books": "border-l-duplicate",
  "Duplicate in 2B": "border-l-duplicate",
};

export function Dashboard({ rows }: { rows: ReconRow[] }) {
  const s = summarize(rows);
  const generate = useServerFn(generateSummaryNote);
  const [note, setNote] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onGenerate = async () => {
    setLoading(true);
    try {
      const topIssues = rows
        .filter((r) => r.category !== "Matched")
        .sort((a, b) => Math.abs(b.difference) - Math.abs(a.difference))
        .slice(0, 40)
        .map((r) => ({
          supplier: r.supplier,
          gstin: r.gstin,
          invoiceNumber: r.invoiceNumber,
          category: r.category,
          difference: Number(r.difference.toFixed(2)),
        }));
      const res = await generate({
        data: { total: s.total, counts: s.counts, itcAtRisk: Number(s.itcAtRisk.toFixed(2)), topIssues },
      });
      setNote(res.note);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not generate summary");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Card className="p-5">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Total invoices compared
          </p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-foreground">{s.total}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            {s.duplicates} duplicate row{s.duplicates === 1 ? "" : "s"} excluded from comparison
          </p>
        </Card>
        <Card className="p-5">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Matched</p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-matched">
            {s.matchedPct.toFixed(1)}%
          </p>
          <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-muted">
            <div className="h-full rounded-full bg-matched" style={{ width: `${s.matchedPct}%` }} />
          </div>
        </Card>
        <Card className="p-5">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Total ITC at risk
          </p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-risk">{formatINR(s.itcAtRisk)}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Missing in 2B + mismatches + ineligible ITC
          </p>
        </Card>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {(Object.keys(s.counts) as Category[]).map((c) => (
          <Card key={c} className={`border-l-4 p-4 ${accent[c]}`}>
            <p className="text-xs font-medium text-muted-foreground">{c}</p>
            <p className="mt-1 text-2xl font-semibold tabular-nums text-foreground">{s.counts[c]}</p>
          </Card>
        ))}
      </div>

      <Card className="p-5">
        <div className="flex flex-wrap items-center gap-3">
          <div className="mr-auto">
            <h2 className="text-lg font-semibold text-foreground">AI summary note</h2>
            <p className="text-xs text-muted-foreground">
              Plain-English risk summary and suggested follow-ups for your working papers.
            </p>
          </div>
          <Button onClick={onGenerate} disabled={loading || rows.length === 0}>
            {loading ? <Loader2 className="animate-spin" /> : <Sparkles />} Generate Summary Note
          </Button>
        </div>
        {note && (
          <p className="mt-4 rounded-md bg-accent p-4 text-sm leading-relaxed text-accent-foreground">
            {note}
          </p>
        )}
      </Card>
    </div>
  );
}
