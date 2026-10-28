import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Mic, Square, Shuffle, Flame, Trophy, MicOff, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useRecorder } from "@/hooks/use-recorder";
import { MODES, PASSAGES, TOPICS, TWISTERS, pick, type Mode } from "@/lib/content";
import { listSessions, streak, type Session } from "@/lib/db";
import { processRecording } from "@/lib/process";
import { MAX_SECONDS, paceLabel } from "@/lib/audio";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Speakwell — Practice clear speech" },
      { name: "description", content: "Record yourself and get instant AI coaching on fillers, pauses, pace and clarity." },
      { property: "og:title", content: "Speakwell — Practice clear speech" },
      { property: "og:description", content: "Record yourself and get AI coaching on fillers, pauses, pace and clarity." },
    ],
  }),
  component: Home,
});

const fmt = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

function Home() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<Mode>("free");
  const [topic, setTopic] = useState(TOPICS[0]!);
  const [passage, setPassage] = useState(PASSAGES[0]!);
  const [level, setLevel] = useState<1 | 2 | 3>(1);
  const [twister, setTwister] = useState(TWISTERS[0]!.text);
  const [script, setScript] = useState("");
  const [sessions, setSessions] = useState<Session[]>([]);
  const [analysing, setAnalysing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastRec, setLastRec] = useState<{ blob: Blob; mime: string } | null>(null);
  const [explained, setExplained] = useState(true);

  useEffect(() => {
    listSessions().then(setSessions).catch(() => {});
    setExplained(localStorage.getItem("speakwell-mic-ok") === "1");
    setTopic(pick(TOPICS));
  }, []);

  const reference = mode === "read" ? passage : mode === "twister" ? twister : mode === "script" ? script : undefined;
  const title = mode === "topic" ? topic : mode === "free" ? "Free speak" : MODES.find((m) => m.id === mode)!.label;

  const analyse = async (blob: Blob, mime: string) => {
    setLastRec({ blob, mime });
    setError(null);
    setAnalysing(true);
    try {
      const s = await processRecording({ blob, mime, mode, title, referenceText: reference });
      navigate({ to: "/session/$id", params: { id: s.id } });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setAnalysing(false);
    }
  };

  const rec = useRecorder((blob, mime) => analyse(blob, mime));
  const limit = mode === "topic" ? 60 : MAX_SECONDS;
  useEffect(() => {
    if (rec.state === "recording" && rec.elapsed >= limit) rec.stop();
  }, [rec.elapsed, rec.state, limit, rec]);

  const onRecord = () => {
    if (rec.state === "recording") return rec.stop();
    if (mode === "script" && script.trim().length < 10) return toast("Paste your script first.");
    if (!explained) return;
    rec.start();
  };

  if (analysing) return <Analysing />;

  if (!explained && rec.state !== "recording")
    return (
      <Screen>
        <div className="flex flex-1 flex-col items-center justify-center text-center">
          <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-accent"><Mic className="h-9 w-9 text-primary" /></div>
          <h1 className="text-3xl">Allow microphone</h1>
          <p className="mt-3 text-muted-foreground">Speakwell listens only while you hold a session. Your phone will ask for permission — tap <b className="text-foreground">Allow</b>.</p>
          <p className="mt-2 text-sm text-muted-foreground">Recordings stay on this device. Only the audio for analysis is sent, then discarded.</p>
          <button
            className="mt-8 min-h-14 w-full rounded-full bg-primary text-lg font-semibold text-primary-foreground"
            onClick={() => { localStorage.setItem("speakwell-mic-ok", "1"); setExplained(true); rec.start(); }}
          >
            Continue
          </button>
        </div>
      </Screen>
    );

  if (rec.state === "denied" || rec.state === "unsupported")
    return (
      <Screen>
        <div className="flex flex-1 flex-col items-center justify-center text-center">
          <MicOff className="mb-4 h-12 w-12 text-destructive" />
          <h1 className="text-2xl">{rec.state === "denied" ? "Microphone blocked" : "Recording not available"}</h1>
          <p className="mt-3 text-muted-foreground">
            {rec.state === "denied"
              ? "On iPhone: open Settings › Safari › Microphone and choose Allow, or tap “aA” in the address bar › Website Settings › Microphone."
              : "This browser can't record audio. Try Safari on iPhone or Chrome."}
          </p>
          <button className="mt-8 min-h-14 w-full rounded-full bg-secondary font-semibold" onClick={() => rec.setState("idle")}>Back</button>
        </div>
      </Screen>
    );

  const recording = rec.state === "recording";
  const st = streak(sessions);
  const best = sessions.length ? Math.max(...sessions.map((s) => s.analysis.clarity_score)) : 0;

  return (
    <Screen>
      <header className="flex items-center justify-between">
        <h1 className="text-3xl">Speakwell</h1>
        <div className="flex gap-2 text-sm">
          <span className="flex items-center gap-1 rounded-full bg-card px-3 py-1.5"><Flame className="h-4 w-4 text-filler" />{st}d</span>
          <span className="flex items-center gap-1 rounded-full bg-card px-3 py-1.5"><Trophy className="h-4 w-4 text-primary" />{Math.round(best)}</span>
        </div>
      </header>

      {!recording && (
        <div className="-mx-5 mt-6 flex gap-2 overflow-x-auto px-5 pb-1">
          {MODES.map((m) => (
            <button
              key={m.id}
              onClick={() => setMode(m.id)}
              className={cn("min-h-11 shrink-0 rounded-full border px-4 text-sm font-medium", mode === m.id ? "border-primary bg-primary text-primary-foreground" : "border-border bg-card text-muted-foreground")}
            >
              {m.label}
            </button>
          ))}
        </div>
      )}

      <section className="mt-5 rounded-2xl bg-card p-5">
        {mode === "free" && <p className="text-muted-foreground">Talk about anything for up to 5 minutes. Speak naturally — we'll find the fillers.</p>}
        {mode === "topic" && (
          <div className="flex items-start gap-3">
            <p className="flex-1 font-display text-xl">{topic}</p>
            {!recording && <IconBtn onClick={() => setTopic(pick(TOPICS))}><Shuffle className="h-4 w-4" /></IconBtn>}
          </div>
        )}
        {mode === "read" && (
          <div className="flex items-start gap-3">
            <p className="flex-1 text-lg leading-relaxed">{passage}</p>
            {!recording && <IconBtn onClick={() => setPassage(pick(PASSAGES))}><Shuffle className="h-4 w-4" /></IconBtn>}
          </div>
        )}
        {mode === "twister" && (
          <>
            {!recording && (
              <div className="mb-3 flex gap-2">
                {([1, 2, 3] as const).map((l) => (
                  <button key={l} onClick={() => { setLevel(l); setTwister(pick(TWISTERS.filter((t) => t.level === l)).text); }}
                    className={cn("min-h-10 flex-1 rounded-xl text-sm", level === l ? "bg-accent text-primary" : "bg-secondary text-muted-foreground")}>
                    {(["Easy", "Medium", "Hard"] as const)[l - 1]}
                  </button>
                ))}
              </div>
            )}
            <div className="flex items-start gap-3">
              <p className="flex-1 font-display text-xl">{twister}</p>
              {!recording && <IconBtn onClick={() => setTwister(pick(TWISTERS.filter((t) => t.level === level)).text)}><Shuffle className="h-4 w-4" /></IconBtn>}
            </div>
          </>
        )}
        {mode === "script" && (recording ? <p className="max-h-64 overflow-y-auto whitespace-pre-wrap text-lg leading-relaxed">{script}</p> : (
          <textarea value={script} onChange={(e) => setScript(e.target.value)} rows={5} placeholder="Paste your voice-over script…"
            className="w-full resize-none rounded-xl border border-input bg-background p-3 text-base outline-none focus:border-primary" />
        ))}
      </section>

      <div className="mt-8 flex flex-col items-center">
        <Waveform level={rec.level} active={recording} />
        <div className="mt-2 font-mono text-lg tabular-nums text-muted-foreground">
          {fmt(rec.elapsed * (recording ? 1 : 0))} <span className="text-sm">/ {fmt(limit)}</span>
        </div>
        {recording && rec.liveWpm > 0 && (
          <div className={cn("mt-2 rounded-full px-3 py-1 text-sm", paceLabel(rec.liveWpm) === "ideal" ? "bg-accent text-success" : "bg-secondary text-filler")}>
            ~{rec.liveWpm} wpm · {paceLabel(rec.liveWpm) === "ideal" ? "great pace" : paceLabel(rec.liveWpm) === "fast" ? "slow down a little" : "pick up a little"}
          </div>
        )}
        <button
          onClick={onRecord}
          disabled={rec.state === "requesting"}
          aria-label={recording ? "Stop recording" : "Start recording"}
          className="relative mt-6 flex h-28 w-28 items-center justify-center rounded-full record-btn text-primary-foreground active:scale-95"
        >
          {recording && <span className="absolute inset-0 rounded-full border-2 border-primary pulse-ring" />}
          {rec.state === "requesting" ? <Loader2 className="h-10 w-10 animate-spin" /> : recording ? <Square className="h-10 w-10 fill-current" /> : <Mic className="h-11 w-11" />}
        </button>
        <p className="mt-3 text-sm text-muted-foreground">{recording ? "Tap to finish" : "Tap to record"}</p>
      </div>

      {error && (
        <div className="mt-6 rounded-2xl border border-destructive/50 bg-card p-4 text-sm">
          <p>{error}</p>
          {lastRec && <button className="mt-3 min-h-11 rounded-full bg-secondary px-4 font-medium" onClick={() => analyse(lastRec.blob, lastRec.mime)}>Try analysis again</button>}
        </div>
      )}

      {!recording && sessions.length > 0 && (
        <section className="mt-10">
          <h2 className="mb-3 text-lg">Recent</h2>
          <div className="space-y-2">
            {sessions.slice(0, 3).map((s) => (
              <Link key={s.id} to="/session/$id" params={{ id: s.id }} className="flex min-h-14 items-center justify-between rounded-xl bg-card px-4 py-3">
                <div className="min-w-0">
                  <p className="truncate font-medium">{s.title}</p>
                  <p className="text-xs text-muted-foreground">{new Date(s.createdAt).toLocaleString()}</p>
                </div>
                <span className="font-display text-xl text-primary">{Math.round(s.analysis.clarity_score)}</span>
              </Link>
            ))}
          </div>
        </section>
      )}
    </Screen>
  );
}

function Screen({ children }: { children: React.ReactNode }) {
  return <main className="flex min-h-[calc(100dvh-7rem)] flex-col px-5 pt-[max(1.5rem,env(safe-area-inset-top))]">{children}</main>;
}

function IconBtn({ children, onClick }: { children: React.ReactNode; onClick: () => void }) {
  return <button onClick={onClick} aria-label="Shuffle" className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-secondary">{children}</button>;
}

function Waveform({ level, active }: { level: number[]; active: boolean }) {
  const bars = Array.from({ length: 60 }, (_, i) => level[level.length - 60 + i] ?? 0);
  return (
    <div className="flex h-20 w-full items-center justify-center gap-[3px]">
      {bars.map((v, i) => (
        <span key={i} className={cn("w-1 rounded-full transition-[height] duration-75", active ? "bg-primary" : "bg-muted")} style={{ height: `${Math.max(6, v * 100)}%` }} />
      ))}
    </div>
  );
}

function Analysing() {
  return (
    <main className="flex min-h-[80dvh] flex-col items-center justify-center px-8 text-center">
      <div className="relative flex h-32 w-32 items-center justify-center">
        <span className="absolute inset-0 rounded-full bg-primary/20 breathe" />
        <span className="absolute inset-4 rounded-full bg-primary/30 breathe [animation-delay:400ms]" />
        <Mic className="relative h-10 w-10 text-primary" />
      </div>
      <h1 className="mt-8 text-2xl">Analysing your speech</h1>
      <p className="mt-2 text-muted-foreground">Listening for fillers, pauses and pace…</p>
    </main>
  );
}
