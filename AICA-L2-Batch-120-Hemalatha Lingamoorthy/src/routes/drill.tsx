import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";

export const Route = createFileRoute("/drill")({
  head: () => ({
    meta: [
      { title: "Pause drill — Speakwell" },
      { name: "description", content: "Practise replacing fillers with a deliberate silent beat." },
      { property: "og:title", content: "Pause drill — Speakwell" },
      { property: "og:description", content: "Replace fillers with a deliberate silent beat." },
    ],
  }),
  component: Drill,
});

const LINES = [
  "Today I want to talk about ‖ three ideas.",
  "The first ‖ is focus.",
  "The second ‖ is patience.",
  "And the third ‖ the one that matters most ‖ is practice.",
  "So ‖ let's begin.",
];

function Drill() {
  const [i, setI] = useState(0);
  const [beat, setBeat] = useState(false);
  useEffect(() => {
    const t = setInterval(() => setBeat((b) => !b), 800);
    return () => clearInterval(t);
  }, []);
  return (
    <main className="flex min-h-[calc(100dvh-7rem)] flex-col px-5 pt-[max(1.5rem,env(safe-area-inset-top))]">
      <h1 className="text-3xl">Pause drill</h1>
      <p className="mt-2 text-muted-foreground">Read each line aloud. At every ‖ close your mouth and take one silent beat instead of saying “um”.</p>
      <div className="flex flex-1 flex-col items-center justify-center text-center">
        <span className={`mb-8 h-4 w-4 rounded-full transition-all ${beat ? "scale-150 bg-primary" : "bg-muted"}`} />
        <p className="font-display text-3xl leading-snug">
          {LINES[i]!.split("‖").map((part, j, arr) => (
            <span key={j}>{part}{j < arr.length - 1 && <span className="mx-1 text-primary">‖</span>}</span>
          ))}
        </p>
      </div>
      <div className="grid grid-cols-2 gap-3 pb-4">
        <button disabled={i === 0} onClick={() => setI(i - 1)} className="min-h-14 rounded-full bg-secondary disabled:opacity-40">Back</button>
        <button onClick={() => setI((i + 1) % LINES.length)} className="min-h-14 rounded-full bg-primary font-semibold text-primary-foreground">Next line</button>
      </div>
    </main>
  );
}
