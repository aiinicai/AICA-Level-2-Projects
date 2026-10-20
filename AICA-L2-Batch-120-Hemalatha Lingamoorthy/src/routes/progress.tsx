import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, Tooltip } from "recharts";
import { listSessions, streak, type Session } from "@/lib/db";

export const Route = createFileRoute("/progress")({
  head: () => ({
    meta: [
      { title: "Progress — Speakwell" },
      { name: "description", content: "Track filler rate, pace and clarity trends across your practice sessions." },
      { property: "og:title", content: "Progress — Speakwell" },
      { property: "og:description", content: "Your speaking trends, streaks and goals." },
    ],
  }),
  component: Progress,
});

function Progress() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [goal, setGoal] = useState(3);
  useEffect(() => {
    listSessions().then(setSessions).catch(() => {});
    setGoal(Number(localStorage.getItem("speakwell-goal") ?? 3));
  }, []);
  const data = [...sessions].reverse().map((s, i) => ({
    n: i + 1,
    filler: Math.round(s.analysis.filler_rate_per_minute * 10) / 10,
    wpm: s.wpm,
    clarity: Math.round(s.analysis.clarity_score),
  }));
  const best = sessions.reduce<Session | null>((b, s) => (!b || s.analysis.clarity_score > b.analysis.clarity_score ? s : b), null);
  const metGoal = sessions.filter((s) => s.analysis.filler_rate_per_minute < goal).length;

  return (
    <main className="px-5 pt-[max(1.5rem,env(safe-area-inset-top))]">
      <h1 className="text-3xl">Progress</h1>
      <div className="mt-5 grid grid-cols-3 gap-3 text-center">
        <Stat label="Streak" v={`${streak(sessions)}d`} />
        <Stat label="Sessions" v={String(sessions.length)} />
        <Stat label="Best clarity" v={best ? String(Math.round(best.analysis.clarity_score)) : "–"} />
      </div>

      <section className="mt-5 rounded-2xl bg-card p-5">
        <h2 className="text-lg">Goal</h2>
        <div className="mt-2 flex items-center gap-3">
          <span className="text-muted-foreground">Fewer than</span>
          <input type="number" min={1} max={20} value={goal} onChange={(e) => { setGoal(Number(e.target.value)); localStorage.setItem("speakwell-goal", e.target.value); }}
            className="h-11 w-16 rounded-xl border border-input bg-background text-center" />
          <span className="text-muted-foreground">fillers / min</span>
        </div>
        <p className="mt-2 text-sm">Met in <b className="text-success">{metGoal}</b> of {sessions.length} sessions</p>
      </section>

      {data.length < 2 ? (
        <p className="mt-8 text-center text-muted-foreground">Record at least two sessions to see trends.</p>
      ) : (
        <>
          <Chart title="Filler rate / min" data={data} k="filler" color="var(--chart-2)" />
          <Chart title="Words per minute" data={data} k="wpm" color="var(--chart-3)" />
          <Chart title="Clarity" data={data} k="clarity" color="var(--chart-1)" />
        </>
      )}

      <h2 className="mb-3 mt-8 text-lg">History</h2>
      <div className="space-y-2 pb-6">
        {sessions.map((s) => (
          <Link key={s.id} to="/session/$id" params={{ id: s.id }} className="flex min-h-14 items-center justify-between rounded-xl bg-card px-4 py-3">
            <div className="min-w-0"><p className="truncate font-medium">{s.title}</p><p className="text-xs text-muted-foreground">{new Date(s.createdAt).toLocaleDateString()} · {s.wpm} wpm</p></div>
            <span className="font-display text-xl text-primary">{Math.round(s.analysis.clarity_score)}</span>
          </Link>
        ))}
      </div>
    </main>
  );
}

function Stat({ label, v }: { label: string; v: string }) {
  return <div className="rounded-2xl bg-card p-3"><p className="font-display text-2xl">{v}</p><p className="text-xs text-muted-foreground">{label}</p></div>;
}
function Chart({ title, data, k, color }: { title: string; data: Record<string, number>[]; k: string; color: string }) {
  return (
    <section className="mt-5 rounded-2xl bg-card p-5">
      <h2 className="text-lg">{title}</h2>
      <div className="mt-3 h-36">
        <ResponsiveContainer>
          <LineChart data={data}>
            <XAxis dataKey="n" stroke="var(--muted-foreground)" fontSize={11} />
            <YAxis stroke="var(--muted-foreground)" fontSize={11} width={30} />
            <Tooltip contentStyle={{ background: "var(--popover)", border: "none", borderRadius: 12 }} />
            <Line type="monotone" dataKey={k} stroke={color} strokeWidth={2} dot={{ r: 3 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
