import { useCallback, useEffect, useRef, useState } from "react";
import { MAX_SECONDS, pickMimeType } from "@/lib/audio";

export type RecState = "idle" | "requesting" | "denied" | "unsupported" | "recording";

export function useRecorder(onDone: (blob: Blob, mime: string, seconds: number) => void) {
  const [state, setState] = useState<RecState>("idle");
  const [elapsed, setElapsed] = useState(0);
  const [level, setLevel] = useState<number[]>([]);
  const [liveWords, setLiveWords] = useState(0);
  const mr = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const ctx = useRef<AudioContext | null>(null);
  const raf = useRef(0);
  const startAt = useRef(0);
  const chunks = useRef<Blob[]>([]);
  const syllables = useRef(0);
  const doneRef = useRef(onDone);
  doneRef.current = onDone;

  const cleanup = useCallback(() => {
    cancelAnimationFrame(raf.current);
    stream.current?.getTracks().forEach((t) => t.stop());
    ctx.current?.close().catch(() => {});
    stream.current = null;
    ctx.current = null;
  }, []);

  const stop = useCallback(() => {
    if (mr.current && mr.current.state !== "inactive") mr.current.stop();
  }, []);

  const start = useCallback(async () => {
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setState("unsupported");
      return;
    }
    setState("requesting");
    try {
      const s = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
      stream.current = s;
      const mime = pickMimeType();
      const rec = new MediaRecorder(s, mime ? { mimeType: mime } : undefined);
      chunks.current = [];
      rec.ondataavailable = (e) => e.data.size && chunks.current.push(e.data);
      rec.onstop = () => {
        const secs = (performance.now() - startAt.current) / 1000;
        const type = rec.mimeType || mime || "audio/mp4";
        cleanup();
        setState("idle");
        doneRef.current(new Blob(chunks.current, { type }), type, secs);
      };
      const Ctx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      const ac = new Ctx();
      ctx.current = ac;
      const an = ac.createAnalyser();
      an.fftSize = 1024;
      ac.createMediaStreamSource(s).connect(an);
      const data = new Float32Array(an.fftSize);
      let wasLoud = false;
      syllables.current = 0;
      const tick = () => {
        an.getFloatTimeDomainData(data);
        let sum = 0;
        for (const v of data) sum += v * v;
        const r = Math.sqrt(sum / data.length);
        // crude syllable-onset counter for live pace feedback
        const loud = r > 0.03;
        if (loud && !wasLoud) syllables.current++;
        wasLoud = loud;
        setLevel((l) => [...l.slice(-59), Math.min(1, r * 8)]);
        const t = (performance.now() - startAt.current) / 1000;
        setElapsed(t);
        setLiveWords(syllables.current / 1.4);
        if (t >= MAX_SECONDS) { stop(); return; }
        raf.current = requestAnimationFrame(tick);
      };
      mr.current = rec;
      startAt.current = performance.now();
      rec.start(1000);
      setState("recording");
      tick();
    } catch (e) {
      cleanup();
      const name = (e as DOMException)?.name;
      setState(name === "NotAllowedError" || name === "SecurityError" ? "denied" : "unsupported");
    }
  }, [cleanup, stop]);

  useEffect(() => () => { if (mr.current?.state === "recording") { mr.current.onstop = null; mr.current.stop(); } cleanup(); }, [cleanup]);

  return { state, setState, elapsed, level, liveWpm: elapsed > 5 ? Math.round((liveWords / elapsed) * 60) : 0, start, stop };
}
