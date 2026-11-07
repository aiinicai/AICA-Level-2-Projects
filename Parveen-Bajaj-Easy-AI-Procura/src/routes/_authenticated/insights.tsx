import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useServerFn } from "@tanstack/react-start";
import { PageHeader } from "@/components/procurement/PageHeader";
import { Button } from "@/components/ui/button";
import { analyseProcurement, type InsightFocus } from "@/lib/insights.functions";

export const Route = createFileRoute("/_authenticated/insights")({
  head: () => ({
    meta: [
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
      { title: "AI Insights — Easy AI Procura" },
      { name: "description", content: "AI-powered analysis of spend, suppliers, price variance and compliance." },
      { property: "og:title", content: "AI Insights — Easy AI Procura" },
      { property: "og:description", content: "AI-powered analysis of spend, suppliers, price variance and compliance." },
    ],
  }),
  component: Insights,
});

const TOOLS: { id: InsightFocus; title: string; desc: string }[] = [
  { id: "overview", title: "Executive overview", desc: "Spend, pipeline and bottlenecks at a glance" },
  { id: "suppliers", title: "Supplier risk", desc: "Concentration and dependency analysis" },
  { id: "variance", title: "Price variance audit", desc: "Invoice vs LPO price overcharging check" },
  { id: "compliance", title: "Compliance check", desc: "Maker–checker & cycle times vs ISO 20400" },
  { id: "forecast", title: "Spend forecast", desc: "Next month's spend and budget advice" },
];

function Insights() {
  const analyse = useServerFn(analyseProcurement);
  const [focus, setFocus] = useState<InsightFocus>("overview");
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function run(f: InsightFocus) {
    setFocus(f);
    setBusy(true);
    setError("");
    setResult("");
    try {
      const r = await analyse({ data: { focus: f, question: question.trim() || undefined } });
      setResult(r.analysis);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader title="AI Insights" subtitle="AI-powered analysis of your live procurement data." />
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {TOOLS.map((t) => (
          <button
            key={t.id}
            disabled={busy}
            onClick={() => run(t.id)}
            className={`rounded-lg border bg-card p-4 text-left transition-colors hover:border-primary/50 disabled:opacity-60 ${
              focus === t.id ? "border-primary" : "border-border"
            }`}
          >
            <p className="text-sm font-semibold text-foreground">{t.title}</p>
            <p className="mt-1 text-xs text-muted-foreground">{t.desc}</p>
          </button>
        ))}
      </div>

      <div className="mt-4 flex flex-col gap-2 sm:flex-row">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          maxLength={500}
          placeholder="Optional: ask a specific question, e.g. Which supplier is most expensive?"
          className="h-10 flex-1 rounded-md border border-input bg-background px-3 text-sm text-foreground"
        />
        <Button disabled={busy} onClick={() => run(focus)}>
          {busy ? "Analysing…" : "Ask AI"}
        </Button>
      </div>

      <section className="mt-6 min-h-48 rounded-lg border border-border bg-card p-6">
        {busy ? <p className="animate-pulse text-sm text-muted-foreground">Reading your data and thinking…</p> : null}
        {error ? <p className="text-sm text-destructive">{error}</p> : null}
        {result ? <Markdownish text={result} /> : null}
        {!busy && !error && !result ? (
          <p className="text-sm text-muted-foreground">Pick an analysis tool above to get started.</p>
        ) : null}
      </section>
    </div>
  );
}

function Markdownish({ text }: { text: string }) {
  const inline = (s: string) =>
    s.split(/(\*\*[^*]+\*\*)/g).map((p, i) =>
      p.startsWith("**") ? <strong key={i} className="text-foreground">{p.slice(2, -2)}</strong> : p,
    );
  return (
    <div className="space-y-2 text-sm leading-relaxed text-card-foreground">
      {text.split("\n").map((line, i) => {
        const t = line.trim();
        if (!t) return null;
        if (t.startsWith("#")) return <h3 key={i} className="pt-2 text-base font-semibold text-primary">{t.replace(/^#+\s*/, "")}</h3>;
        if (/^[-*]\s|^\d+\.\s/.test(t)) return <p key={i} className="pl-4">• {inline(t.replace(/^([-*]|\d+\.)\s*/, ""))}</p>;
        return <p key={i}>{inline(t)}</p>;
      })}
    </div>
  );
}
