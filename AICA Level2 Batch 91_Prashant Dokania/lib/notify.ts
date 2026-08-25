/**
 * A reflection can take a while, and people put the phone down. This nudges
 * them back — a real notification when they've allowed one, and a title badge
 * as the always-available fallback.
 */

const BASE_TITLE = "MIRROR — hear yourself the way others do";

export function notifyReflectionReady(summary: string) {
  if (typeof window === "undefined") return;
  if (document.visibilityState === "visible") return;

  document.title = "✦ Your reflection is ready — MIRROR";
  const restore = () => {
    if (document.visibilityState === "visible") {
      document.title = BASE_TITLE;
      document.removeEventListener("visibilitychange", restore);
    }
  };
  document.addEventListener("visibilitychange", restore);

  if (!("Notification" in window) || Notification.permission !== "granted") return;
  try {
    new Notification("Your reflection is ready", {
      body: summary.slice(0, 140) || "MIRROR has finished sitting with what you said.",
      icon: "/icon-192.png",
      tag: "mirror-reflection",
    });
  } catch {
    // Some browsers only allow notifications from a service worker; the title
    // badge above already covers the case.
  }
}

/** Asked for only once the person actually starts something long-running. */
export async function askNotificationPermission() {
  if (typeof window === "undefined" || !("Notification" in window)) return;
  if (Notification.permission !== "default") return;
  try {
    await Notification.requestPermission();
  } catch {
    /* ignore */
  }
}
