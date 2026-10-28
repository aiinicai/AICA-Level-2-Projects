import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowLeft, Share2, FileDown, Trash2 } from "lucide-react";
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, Tooltip } from "recharts";
import { deleteSession, getSession, type Session } from "@/lib/db";
import { paceLabel, paceSeries } from "@/lib/audio";
import { FILLERS } from "@/lib/schema";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/session/$id")({
  head: () => ({
    meta: [
      { title: "Your results — Speakwell" },
      { name: "description", content: "Clarity, fluency, pace and filler breakdown for your speech session." },
      { property: "og:title", content: "Your results — Speakwell" },
      { property: "og:description", content: "Clarity, fluency, pace and filler breakdown." },
    ],
  }),
  component: Results,
});

type Token = { text: string; start: number; kind: "filler" | "repeat" | "normal" } | { pause: number };

function buildTokens(s: Session): Token[] {
  const words = s.analysis.words.length
    ? s.analysis.words
    : s.analysis.verbatim_transcript.split(/\s+/).filter(Boolean).map((t) => ({ text: t, start: -1 }));
  const norm = (w: string) => w.toLowerCase().replace(/[^a-z']/g, "");
  const out: Token[] = [];
  const longPauses = s.metrics.pauses.filter((p) => p.duration > 1.5);
  let pi = 0;
  words.forEach((w, i) => {
    while (pi < longPauses.length && w.start >= 0 && longPauses[pi]!.start + longPauses[pi]!.duration <= w.start + 0.2) {
      out.push({ pause: longPauses[pi]!.duration });
      pi++;
    }
    const n = norm(w.text);
    const two = i > 0 ? `${norm(words[i - 1]!.text)} ${n}` : "";
    const next = words[i + 1] ? `${n} ${norm(words[i + 1]!.text)}` : "";
    const filler = FILLERS.includes(n) && !["so", "right", "like", "actually"].includes(n)
      || FILLERS.includes(two) || FILLERS.includes(next)
      || (["so", "right", "like", "actually", "basically"].includes(n) && s.analysis.fillers.some((f) => norm(f.word) === n));
    const repeat = i > 0 && n && n === norm(words[i - 1]!.text);
    out.push({ text: w.text, start: w.start, kind: repeat ? "repeat" : filler ? "filler" : "normal" });
  });
  return out;
}

function Results() {
  const { id } = Route.useParams();
  const navigate = useNavigate();
  const [s, setS] = useState<Session | null | undefined>(undefined);
  const [url, setUrl] = useState<string>();
  const audio = useRef<HTMLAudioElement>(null);
  const [view, setView] = useState<"orig" | "clean">("orig");

  useEffect(() => {
    getSession(id).then((x) => {
      setS(x ?? null);
      if (x) setUrl(URL.createObjectURL(x.audio));
    });
  }, [id]);
  useEffect(() => () => { if (url) URL.revokeObjectURL(url); }, [url]);

  const tokens = useMemo(() => (s ? buildTokens(s) : []), [s]);
  if (s === undefined) return <div className="p-8 text-muted-foreground">Loading…</div>;
  if (s === null) return <div className="p-8">Session not found. <Link to="/" className="text-primary">Go home</Link></div>;

  const a = s.analysis, m = s.metrics;
  const totalFillers = a.fillers.reduce((x, f) => x + f.count, 0);
  const totalRepeats = a.repeated_words.reduce((x, r) => x + r.count, 0);
  const pace = paceSeries(a.words, m.duration);
  const play = (t: number) => { if (audio.current && t >= 0) { audio.current.currentTime = Math.max(0, t - 0.3); audio.current.play(); } };

  const shareCard = async () => {
    const c = document.createElement("canvas");
    c.width = 1080; c.height = 1080;
    const g = c.getContext("2d")!;
    const css = getComputedStyle(document.documentElement);
    g.fillStyle = css.getPropertyValue("--background"); g.fillRect(0, 0, 1080, 1080);
    g.fillStyle = css.getPropertyValue("--primary"); g.font = "600 64px Fraunces, serif"; g.fillText("Speakwell", 80, 140);
    g.fillStyle = css.getPropertyValue("--foreground"); g.font = "500 40px Manrope, sans-serif"; g.fillText(s.title.slice(0, 40), 80, 220);
    [["Clarity", a.clarity_score], ["Fluency", a.fluency_score], ["WPM", s.wpm], ["Fillers/min", a.filler_rate_per_minute]].forEach(([l, v], i) => {
      const x = 80 + (i % 2) * 480, y = 380 + Math.floor(i / 2) * 300;
      g.font = "600 140px Fraunces, serif"; g.fillText(String(Math.round(Number(v) * 10) / 10), x, y);
      g.font = "500 40px Manrope, sans-serif"; g.fillText(String(l), x, y + 60);
    });
    const blob: Blob = await new Promise((r) => c.toBlob((b) => r(b!), "image/png"));
    const file = new File([blob], "speakwell.png", { type: "image/png" });
    if (navigator.canShare?.({ files: [file] })) await navigator.share({ files: [file], title: "My Speakwell score" }).catch(() => {});
    else { const l = document.createElement("a"); l.href = URL.createObjectURL(blob); l.download = "speakwell.png"; l.click(); }
  };

  return (
    <main className="px-5 pt-[max(1.25rem,env(safe-area-inset-top))]">
      <div className="no-print flex items-center justify-between">
        <Link to="/" className="flex h-11 w-11 items-center justify-center rounded-full bg-card" aria-label="Back"><ArrowLeft className="h-5 w-5" /></Link>
        <div className="flex gap-2">
          <button onClick={shareCard} className="flex h-11 w-11 items-center justify-center rounded-full bg-card" aria-label="Share image"><Share2 className="h-5 w-5" /></button>
          <button onClick={() => window.print()} className="flex h-11 w-11 items-center justify-center rounded-full bg-card" aria-label="Export PDF"><FileDown className="h-5 w-5" /></button>
          <button onClick={async () => { if (confirm("Delete this session?")) { await deleteSession(s.id); navigate({ to: "/" }); } }} className="flex h-11 w-11 items-center justify-center rounded-full bg-card" aria-label="Delete"><Trash2 className="h-5 w-5" /></button>
        </div>
      </div>
      <h1 className="mt-5 text-2xl">{s.title}</h1>
      <p className="text-sm text-muted-foreground">{new Date(s.createdAt).toLocaleString()} · {Math.round(m.duration)}s</p>
      {url && <audio ref={audio} src={url} controls className="no-print mt-4 w-full" />}

      <div className="mt-5 grid grid-cols-2 gap-3">
        <Score label="Clarity" value={Math.round(a.clarity_score)} suffix="/100" />
        <Score label="Fluency" value={Math.round(a.fluency_score)} suffix="/100" />
        <Score label="Pace" value={s.wpm} suffix=" wpm" note={paceLabel(s.wpm)} good={paceLabel(s.wpm) === "ideal"} />
        <Score label="Filler rate" value={Math.round(a.filler_rate_per_minute * 10) / 10} suffix="/min" good={a.filler_rate_per_minute < 3} note={a.filler_rate_per_minute < 3 ? "on goal" : "aim < 3"} />
      </div>

      {a.top_3_priorities.length > 0 && (
        <section className="mt-5 rounded-2xl border border-primary/40 bg-accent p-5">
          <h2 className="text-lg">Fix this first</h2>
          <ol className="mt-3 space-y-2">
            {a.top_3_priorities.slice(0, 3).map((p, i) => (
              <li key={i} className="flex gap-3"><span className="font-display text-primary">{i + 1}</span><span>{p}</span></li>
            ))}
          </ol>
        </section>
      )}

      <section className="mt-5 grid grid-cols-3 gap-3 text-center">
        <Count label="Fillers" n={totalFillers} cls="text-filler" />
        <Count label="Pauses" n={m.pauseCount} cls="text-pause" />
        <Count label="Repeats" n={totalRepeats} cls="text-repeat" />
      </section>

      <section className="mt-5 rounded-2xl bg-card p-5">
        <h2 className="text-lg">Breakdown</h2>
        <div className="mt-3 flex flex-wrap gap-2">
          {a.fillers.filter((f) => f.count).map((f) => (
            <button key={f.word} onClick={() => play(f.timestamps[0] ?? -1)} className="min-h-9 rounded-full bg-secondary px-3 text-sm"><span className="text-filler">{f.word}</span> × {f.count}</button>
          ))}
          {a.repeated_words.map((r, i) => <span key={i} className="rounded-full bg-secondary px-3 py-1.5 text-sm"><span className="text-repeat">{r.phrase}</span> × {r.count}</span>)}
          {!a.fillers.length && !a.repeated_words.length && <p className="text-sm text-muted-foreground">No fillers or repeats — lovely.</p>}
        </div>
        <div className="mt-4 grid grid-cols-3 gap-2 text-center text-sm">
          <div className="rounded-xl bg-secondary p-2"><b>{m.shortPauses}</b><p className="text-xs text-muted-foreground">short &lt;0.5s</p></div>
          <div className="rounded-xl bg-secondary p-2"><b>{m.naturalPauses}</b><p className="text-xs text-muted-foreground">natural</p></div>
          <div className="rounded-xl bg-secondary p-2"><b>{m.longPauses}</b><p className="text-xs text-muted-foreground">long &gt;1.5s</p></div>
        </div>
        <p className="mt-3 text-sm text-muted-foreground">
          Avg pause {m.avgPause.toFixed(2)}s · longest {m.longestPause.toFixed(1)}s · volume variation {m.volumeVariation}
          {m.monotone && <span className="text-filler"> · sounds a little monotone — vary your energy</span>}
        </p>
      </section>

      <section className="mt-5 rounded-2xl bg-card p-5">
        <div className="no-print mb-3 flex gap-2">
          {(["orig", "clean"] as const).map((v) => (
            <button key={v} onClick={() => setView(v)} className={cn("min-h-10 flex-1 rounded-xl text-sm", view === v ? "bg-accent text-primary" : "bg-secondary text-muted-foreground")}>
              {v === "orig" ? "Original" : "Cleaned"}
            </button>
          ))}
        </div>
        {view === "orig" ? (
          <p className="leading-loose">
            {tokens.map((t, i) => "pause" in t ? (
              <span key={i} className="mx-1 rounded bg-secondary px-1.5 font-mono text-xs text-pause">[..{t.pause.toFixed(1)}s..]</span>
            ) : (
              <span key={i}>
                <span onClick={() => play(t.start)} className={cn(t.kind !== "normal" && "cursor-pointer rounded px-0.5 font-semibold", t.kind === "filler" && "bg-filler/15 text-filler", t.kind === "repeat" && "bg-repeat/15 text-repeat", t.start >= 0 && "cursor-pointer")}>{t.text}</span>{" "}
              </span>
            ))}
          </p>
        ) : <p className="leading-loose">{a.rewritten_transcript}</p>}
        <p className="no-print mt-3 text-xs text-muted-foreground">Tap any word to hear that moment.</p>
      </section>

      {pace.length > 1 && (
        <section className="mt-5 rounded-2xl bg-card p-5">
          <h2 className="text-lg">Pace over time</h2>
          <div className="mt-3 h-40">
            <ResponsiveContainer>
              <LineChart data={pace}>
                <XAxis dataKey="t" tickFormatter={(v) => `${v}s`} stroke="var(--muted-foreground)" fontSize={11} />
                <YAxis domain={[60, 220]} stroke="var(--muted-foreground)" fontSize={11} width={30} />
                <Tooltip contentStyle={{ background: "var(--popover)", border: "none", borderRadius: 12 }} />
                <Line type="monotone" dataKey="wpm" stroke="var(--chart-1)" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <p className="text-xs text-muted-foreground">Target 130–160 wpm</p>
        </section>
      )}

      {(a.mispronunciations.length > 0 || a.weak_phrases.length > 0 || a.false_starts.length > 0) && (
        <section className="mt-5 space-y-3 rounded-2xl bg-card p-5 text-sm">
          {a.mispronunciations.length > 0 && <div><h3 className="mb-1 text-base">Unclear words</h3>{a.mispronunciations.map((x, i) => <p key={i}><b>{x.word}</b> → {x.suggestion}</p>)}</div>}
          {a.weak_phrases.length > 0 && <div><h3 className="mb-1 text-base">Hedging</h3><p className="text-muted-foreground">{a.weak_phrases.join(" · ")}</p></div>}
          {a.false_starts.length > 0 && <div><h3 className="mb-1 text-base">False starts</h3>{a.false_starts.map((f, i) => <p key={i} className="text-muted-foreground">“{f.text}”</p>)}</div>}
        </section>
      )}

      <section className="mt-5 rounded-2xl bg-card p-5">
        <h2 className="text-lg">Coaching</h2>
        <ul className="mt-3 space-y-2">{a.coaching_tips.map((t, i) => <li key={i} className="flex gap-2"><span className="text-primary">•</span>{t}</li>)}</ul>
      </section>

      <div className="no-print mt-5 grid grid-cols-2 gap-3 pb-6">
        <Link to="/drill" className="flex min-h-14 items-center justify-center rounded-full bg-secondary font-medium">Pause drill</Link>
        <Link to="/compare" search={{ a: s.id }} className="flex min-h-14 items-center justify-center rounded-full bg-primary font-semibold text-primary-foreground">Compare takes</Link>
      </div>
    </main>
  );
}

function Score({ label, value, suffix, note, good }: { label: string; value: number; suffix: string; note?: string; good?: boolean }) {
  return (
    <div className="rounded-2xl bg-card p-4">
      <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-1 font-display text-3xl">{value}<span className="text-sm text-muted-foreground">{suffix}</span></p>
      {note && <p className={cn("text-xs", good ? "text-success" : "text-filler")}>{note}</p>}
    </div>
  );
}
function Count({ label, n, cls }: { label: string; n: number; cls: string }) {
  return <div className="rounded-2xl bg-card p-3"><p className={cn("font-display text-2xl", cls)}>{n}</p><p className="text-xs text-muted-foreground">{label}</p></div>;
}
