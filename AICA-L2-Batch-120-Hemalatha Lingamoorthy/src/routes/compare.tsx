import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { listSessions, type Session } from "@/lib/db";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/compare")({
  validateSearch: (s: Record<string, unknown>) => ({ a: typeof s["a"] === "string" ? s["a"] : undefined }),
  head: () => ({
    meta: [
      { title: "Compare takes — Speakwell" },
      { name: "description", content: "Compare two takes of the same script side by side." },
      { property: "og:title", content: "Compare takes — Speakwell" },
      { property: "og:description", content: "Two takes, side by side." },
    ],
  }),
  component: Compare,
});

function Compare() {
  const { a } = Route.useSearch();
  const [all, setAll] = useState<Session[]>([]);
  const [ids, setIds] = useState<[string, string]>(["", ""]);
  useEffect(() => {
    listSessions().then((s) => {
      setAll(s);
      const first = a ?? s[0]?.id ?? "";
      const base = s.find((x) => x.id === first);
      const other = s.find((x) => x.id !== first && (!base || x.title === base.title || x.referenceText === base.referenceText)) ?? s.find((x) => x.id !== first);
      setIds([first, other?.id ?? ""]);
    });
  }, [a]);
  const [x, y] = ids.map((id) => all.find((s) => s.id === id));
  const rows: [string, (s: Session) => number, boolean][] = [
    ["Clarity", (s) => Math.round(s.analysis.clarity_score), true],
    ["Fluency", (s) => Math.round(s.analysis.fluency_score), true],
    ["WPM", (s) => s.wpm, true],
    ["Fillers / min", (s) => Math.round(s.analysis.filler_rate_per_minute * 10) / 10, false],
    ["Long pauses", (s) => s.metrics.longPauses, false],
  ];
  return (
    <main className="px-5 pt-[max(1.5rem,env(safe-area-inset-top))]">
      <h1 className="text-3xl">Compare takes</h1>
      {all.length < 2 ? <p className="mt-6 text-muted-foreground">Record two takes to compare them.</p> : (
        <>
          <div className="mt-5 grid grid-cols-2 gap-3">
            {[0, 1].map((k) => (
              <select key={k} value={ids[k]} onChange={(e) => setIds((p) => (k ? [p[0], e.target.value] : [e.target.value, p[1]]))}
                className="h-12 rounded-xl border border-input bg-card px-2 text-sm">
                {all.map((s) => <option key={s.id} value={s.id}>{s.title.slice(0, 24)} · {new Date(s.createdAt).toLocaleDateString()}</option>)}
              </select>
            ))}
          </div>
          {x && y && (
            <div className="mt-5 overflow-hidden rounded-2xl bg-card">
              {rows.map(([label, f, higher]) => {
                const va = f(x), vb = f(y);
                const better = label === "WPM" ? (Math.abs(vb - 145) < Math.abs(va - 145) ? 1 : 0) : (higher ? vb > va : vb < va) ? 1 : 0;
                return (
                  <div key={label} className="grid grid-cols-3 border-b border-border px-4 py-3 last:border-0">
                    <span className="text-muted-foreground">{label}</span>
                    <span className={cn("text-center font-display text-xl", better === 0 && va !== vb && "text-success")}>{va}</span>
                    <span className={cn("text-center font-display text-xl", better === 1 && va !== vb && "text-success")}>{vb}</span>
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}
    </main>
  );
}
