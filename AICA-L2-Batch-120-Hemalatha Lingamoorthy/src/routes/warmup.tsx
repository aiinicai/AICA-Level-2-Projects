import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { WARMUP } from "@/lib/content";

export const Route = createFileRoute("/warmup")({
  head: () => ({
    meta: [
      { title: "2-minute warm-up — Speakwell" },
      { name: "description", content: "A guided daily vocal warm-up: breathing, lip trills and tongue twisters." },
      { property: "og:title", content: "2-minute warm-up — Speakwell" },
      { property: "og:description", content: "Guided daily vocal warm-up in two minutes." },
    ],
  }),
  component: Warmup,
});

function Warmup() {
  const [step, setStep] = useState(-1);
  const [left, setLeft] = useState(0);
  useEffect(() => {
    if (step < 0 || step >= WARMUP.length) return;
    setLeft(WARMUP[step]!.seconds);
    const t = setInterval(() => setLeft((l) => {
      if (l <= 1) { clearInterval(t); setStep((s) => s + 1); return 0; }
      return l - 1;
    }), 1000);
    return () => clearInterval(t);
  }, [step]);

  const cur = WARMUP[step];
  return (
    <main className="flex min-h-[calc(100dvh-7rem)] flex-col px-5 pt-[max(1.5rem,env(safe-area-inset-top))]">
      <h1 className="text-3xl">Warm-up</h1>
      <p className="text-muted-foreground">Two minutes. Five moves.</p>
      {step < 0 && (
        <>
          <ol className="mt-6 space-y-2">
            {WARMUP.map((w, i) => (
              <li key={i} className="flex justify-between rounded-xl bg-card px-4 py-3"><span>{w.title}</span><span className="text-muted-foreground">{w.seconds}s</span></li>
            ))}
          </ol>
          <button onClick={() => setStep(0)} className="mt-8 min-h-14 rounded-full bg-primary text-lg font-semibold text-primary-foreground">Start</button>
          <Link to="/drill" className="mt-3 flex min-h-14 items-center justify-center rounded-full bg-secondary font-medium">Pause-practice drill</Link>
        </>
      )}
      {cur && (
        <div className="flex flex-1 flex-col items-center justify-center text-center">
          <p className="text-sm text-muted-foreground">Step {step + 1} of {WARMUP.length}</p>
          <div className="relative my-8 flex h-40 w-40 items-center justify-center">
            <span className="absolute inset-0 rounded-full bg-primary/20 breathe" />
            <span className="relative font-display text-5xl">{left}</span>
          </div>
          <h2 className="text-2xl">{cur.title}</h2>
          <p className="mt-3 text-lg text-muted-foreground">{cur.body}</p>
          <button onClick={() => setStep((s) => s + 1)} className="mt-8 min-h-12 rounded-full bg-secondary px-6">Skip</button>
        </div>
      )}
      {step >= WARMUP.length && (
        <div className="flex flex-1 flex-col items-center justify-center text-center">
          <h2 className="text-3xl">Warmed up ✓</h2>
          <Link to="/" className="mt-6 flex min-h-14 w-full items-center justify-center rounded-full bg-primary font-semibold text-primary-foreground">Start practising</Link>
        </div>
      )}
    </main>
  );
}
