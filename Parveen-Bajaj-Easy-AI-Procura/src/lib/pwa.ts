// Single guarded registrar for the app's offline service worker.
//
// The worker must never register in dev, inside the Lovable preview iframe, or
// on any Lovable preview host — a stale worker there keeps serving old or
// deleted files. In every refused context we also unregister a previous
// registration so an earlier visit cannot leave one behind.

const APP_SW_PATH = "/sw.js";

// Hosts that serve Lovable previews/drafts rather than the published app.
const PREVIEW_HOST_SUFFIXES = [".lovable.app", ".gpt-eng.com", ".gptengineer.run"];
const PREVIEW_FIRST_LABELS = [
  /^(?:id-preview|preview)(?:-[a-z0-9]+)?--.+$/,
  /^project--[a-z0-9-]+-dev$/,
];
// Exact hosts of delegated previews for this project (none currently).
const DELEGATED_PREVIEW_HOSTNAMES: string[] = [];

export function isPreviewHost(hostname: string): boolean {
  const host = hostname.toLowerCase();

  if (DELEGATED_PREVIEW_HOSTNAMES.includes(host)) return true;
  if (host === "lovableproject.com" || host.endsWith(".lovableproject.com")) return true;
  if (host === "lovableproject-dev.com" || host.endsWith(".lovableproject-dev.com")) return true;
  if (host === "beta.lovable.dev" || host.endsWith(".beta.lovable.dev")) return true;

  const firstLabel = host.split(".")[0] ?? "";
  return (
    PREVIEW_HOST_SUFFIXES.some((suffix) => host.endsWith(suffix)) &&
    PREVIEW_FIRST_LABELS.some((pattern) => pattern.test(firstLabel))
  );
}

export function shouldSkipRegistration(options: {
  hostname: string;
  search: string;
  prod: boolean;
  inIframe: boolean;
}): boolean {
  if (!options.prod) return true;
  if (options.inIframe) return true;
  if (new URLSearchParams(options.search).get("sw") === "off") return true;
  return isPreviewHost(options.hostname);
}

function targetsAppWorker(registration: ServiceWorkerRegistration): boolean {
  const script =
    registration.active?.scriptURL ??
    registration.installing?.scriptURL ??
    registration.waiting?.scriptURL;
  if (!script) return false;
  try {
    return new URL(script).pathname === APP_SW_PATH;
  } catch {
    return false;
  }
}

async function unregisterAppWorker(): Promise<void> {
  if (typeof navigator === "undefined" || !("serviceWorker" in navigator)) return;
  const registrations = await navigator.serviceWorker.getRegistrations();
  await Promise.allSettled(
    registrations.filter(targetsAppWorker).map((registration) => registration.unregister()),
  );
}

export async function registerAppServiceWorker(): Promise<void> {
  if (typeof window === "undefined") return;

  if (
    shouldSkipRegistration({
      hostname: window.location.hostname.toLowerCase(),
      search: window.location.search,
      prod: import.meta.env.PROD,
      inIframe: window.self !== window.top,
    })
  ) {
    await unregisterAppWorker();
    return;
  }

  if (!("serviceWorker" in navigator)) return;
  try {
    await navigator.serviceWorker.register(APP_SW_PATH, { scope: "/" });
  } catch {
    // Offline support is an enhancement; a failed registration is not an error.
  }
}
