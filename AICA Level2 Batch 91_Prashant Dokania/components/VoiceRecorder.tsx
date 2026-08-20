import { useEffect, useRef, useState } from "react";
import { startRecorder, formatClock, toBase64, type Recorder } from "@/lib/audio";
import { setRecordingActive } from "@/lib/recording-state";

export function VoiceRecorder({
  label,
  minSeconds = 3,
  allowUpload = false,
  busy = false,
  onReady,
}: {
  label: string;
  minSeconds?: number;
  allowUpload?: boolean;
  busy?: boolean;
  onReady: (base64: string, seconds: number) => void | Promise<void>;
}) {
  const recorder = useRef<Recorder | null>(null);
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [level, setLevel] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!recording) return;
    const id = setInterval(() => {
      setSeconds((s) => s + 0.25);
      setLevel(recorder.current?.level() ?? 0);
    }, 250);
    return () => clearInterval(id);
  }, [recording]);

  useEffect(
    () => () => {
      recorder.current?.cancel();
      setRecordingActive(false);
    },
    [],
  );

  async function begin() {
    setError(null);
    try {
      recorder.current = await startRecorder();
      setSeconds(0);
      setRecording(true);
      setRecordingActive(true);
    } catch {
      setError("Microphone access is needed to record. Allow it in your browser and try again.");
    }
  }

  async function finish() {
    const active = recorder.current;
    if (!active) return;
    setRecording(false);
    setRecordingActive(false);
    recorder.current = null;
    const result = await active.stop();
    if (result.captureFailed) {
      setError(
        "We didn't receive any audio from your microphone. Close other apps using the mic, then start a new recording.",
      );
      return;
    }
    if (result.seconds < minSeconds) {
      setError(`That was very short — try at least ${minSeconds} seconds.`);
      return;
    }

    await onReady(result.base64, result.seconds);
  }

  return (
    <div className="panel p-8 text-center">
      <div className="relative mx-auto flex h-40 w-40 items-center justify-center">
        <span
          className={`absolute inset-0 rounded-full ${recording ? "" : "breathe"}`}
          style={{
            background: "var(--gradient-brass)",
            opacity: recording ? 0.25 + level * 0.5 : undefined,
            transform: recording ? `scale(${1 + level * 0.18})` : undefined,
            transition: "transform 200ms ease, opacity 200ms ease",
            filter: "blur(18px)",
          }}
        />
        <div className="relative flex h-28 w-28 flex-col items-center justify-center rounded-full border border-primary/40 bg-surface">
          <span className="font-display text-2xl">{formatClock(seconds)}</span>
          <span className="mt-1 text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
            {busy ? "reflecting" : recording ? "listening" : "ready"}
          </span>
        </div>
      </div>

      <p className="mt-6 text-sm text-muted-foreground">{label}</p>

      {recording ? (
        <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
          Keep recording while you lock the screen or use another app. It only stops when you tap
          end.
        </p>
      ) : null}

      <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
        <button
          type="button"
          disabled={busy}
          onClick={recording ? finish : begin}
          className="rounded-full px-7 py-2.5 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-50"
          style={{ background: "var(--gradient-brass)" }}
        >
          {recording ? "End recording" : busy ? "Working…" : "Start recording"}
        </button>

        {allowUpload && !recording ? (
          <label className="cursor-pointer rounded-full border border-border px-6 py-2.5 text-sm text-muted-foreground transition-colors hover:text-foreground">
            Upload audio
            <input
              type="file"
              accept="audio/*"
              className="hidden"
              disabled={busy}
              onChange={async (e) => {
                const file = e.target.files?.[0];
                if (!file) return;
                setError(null);
                await onReady(await toBase64(file), 0);
              }}
            />
          </label>
        ) : null}
      </div>

      {error ? (
        <p className="mt-5 text-sm" style={{ color: "var(--rust)" }}>
          {error}
        </p>
      ) : null}
    </div>
  );
}
