// Single guarded service-worker registrar. Never registers in dev, preview or iframes,
// and actively clears any legacy Workbox caches that could cause reload loops.
export async function setupServiceWorker() {
  if (typeof window === "undefined") return;

  // Always clear any legacy Workbox caches ("pages", "data", "workbox-precache*")
  if ("caches" in window) {
    try {
      const keys = await caches.keys();
      await Promise.all(
        keys
          .filter((k) => k === "pages" || k === "data" || k.startsWith("workbox-"))
          .map((k) => caches.delete(k)),
      );
    } catch {
      // Ignore cache cleanup errors
    }
  }

  if (!("serviceWorker" in navigator)) return;

  const h = window.location.hostname;
  const inIframe = (() => {
    try {
      return window.self !== window.top;
    } catch {
      return true;
    }
  })();

  const refused =
    !import.meta.env.PROD ||
    inIframe ||
    h.startsWith("id-preview--") ||
    h.startsWith("preview--") ||
    h.startsWith("ais-dev-") ||
    new URLSearchParams(window.location.search).get("sw") === "off";

  if (refused) {
    try {
      const regs = await navigator.serviceWorker.getRegistrations();
      await Promise.all(regs.map((r) => r.unregister()));
    } catch {
      // Ignore unregister errors
    }
    return;
  }

  try {
    const reg = await navigator.serviceWorker.register("/sw.js", { scope: "/" });
    reg.update().catch(() => {});
  } catch {
    // Non-fatal if SW registration is blocked by browser settings
  }
}
