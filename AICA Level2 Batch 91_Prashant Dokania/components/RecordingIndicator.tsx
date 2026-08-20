import { useEffect, useRef, useState } from "react";
import { useRecordingState } from "@/lib/recording-state";
import { formatClock } from "@/lib/audio";

/**
 * Always-visible proof that MIRROR is recording, plus a matching system
 * notification and tab title so it stays obvious when the app is in the
 * background or the screen is off.
 */
export function RecordingIndicator() {
  const { active, startedAt } = useRecordingState();
  const [seconds, setSeconds] = useState(0);
  const notification = useRef<Notification | null>(null);
  const title = useRef<string>("");

  useEffect(() => {
    if (!active) {
      setSeconds(0);
      return;
    }
    const tick = () => setSeconds((Date.now() - startedAt) / 1000);
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [active, startedAt]);

  useEffect(() => {
    if (!active) return;
    title.current = document.title;
    document.title = "Recording · MIRROR";

    let cancelled = false;
    const show = async () => {
      if (typeof Notification === "undefined") return;
      if (Notification.permission === "default") {
        try {
          await Notification.requestPermission();
        } catch {
          return;
        }
      }
      if (cancelled || Notification.permission !== "granted") return;
      try {
        notification.current = new Notification("MIRROR is recording", {
          body: "Only your voice is recorded. Tap the app to end the session.",
          tag: "mirror-recording",
          icon: "/icon-192.png",
          requireInteraction: true,
          silent: true,
        } as NotificationOptions);
      } catch {
        /* notifications unavailable */
      }
    };
    void show();

    return () => {
      cancelled = true;
      document.title = title.current || document.title;
      notification.current?.close();
      notification.current = null;
    };
  }, [active]);

  if (!active) return null;

  return (
    <div
      className="sticky top-0 z-50 flex items-center justify-center gap-3 px-4 py-2 text-xs tracking-wide text-primary-foreground"
      style={{ background: "var(--gradient-brass)" }}
      role="status"
      aria-live="polite"
    >
      <span className="h-2 w-2 animate-pulse rounded-full bg-current" />
      <span>Recording {formatClock(seconds)}. Only your voice.</span>
    </div>
  );
}
