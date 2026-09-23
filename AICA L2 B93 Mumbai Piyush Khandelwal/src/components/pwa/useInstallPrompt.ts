import { useEffect, useState } from "react";

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

export type InstallState = "available" | "installing" | "installed" | "unavailable";

export type Platform = "ios" | "android" | "desktop";

export function detectPlatform(): Platform {
  if (typeof navigator === "undefined") return "desktop";
  const ua = navigator.userAgent;
  if (/iPad|iPhone|iPod/.test(ua) || (/Macintosh/.test(ua) && "ontouchend" in document)) return "ios";
  if (/Android/.test(ua)) return "android";
  return "desktop";
}

export function isStandalone() {
  if (typeof window === "undefined") return false;
  const displayMode = window.matchMedia?.("(display-mode: standalone)").matches;
  const iosStandalone = (window.navigator as Navigator & { standalone?: boolean }).standalone === true;
  return Boolean(displayMode || iosStandalone);
}

/**
 * Captures the browser's own install capability.
 * We never claim installation is possible unless the browser told us so, or
 * the platform has a documented manual flow (iOS Safari).
 */
export function useInstallPrompt() {
  const [deferred, setDeferred] = useState<BeforeInstallPromptEvent | null>(null);
  const [state, setState] = useState<InstallState>("unavailable");
  const [platform, setPlatform] = useState<Platform>("desktop");

  useEffect(() => {
    setPlatform(detectPlatform());
    if (isStandalone()) setState("installed");

    const onBeforeInstall = (e: Event) => {
      e.preventDefault();
      setDeferred(e as BeforeInstallPromptEvent);
      setState((s) => (s === "installed" ? s : "available"));
    };
    const onInstalled = () => {
      setDeferred(null);
      setState("installed");
    };
    const media = window.matchMedia("(display-mode: standalone)");
    const onDisplayChange = () => setState(media.matches ? "installed" : "unavailable");

    window.addEventListener("beforeinstallprompt", onBeforeInstall);
    window.addEventListener("appinstalled", onInstalled);
    media.addEventListener?.("change", onDisplayChange);
    return () => {
      window.removeEventListener("beforeinstallprompt", onBeforeInstall);
      window.removeEventListener("appinstalled", onInstalled);
      media.removeEventListener?.("change", onDisplayChange);
    };
  }, []);

  const promptInstall = async (): Promise<"accepted" | "dismissed" | "unavailable"> => {
    if (!deferred) return "unavailable";
    setState("installing");
    try {
      await deferred.prompt();
      const { outcome } = await deferred.userChoice;
      setDeferred(null);
      setState(outcome === "accepted" ? "installed" : "available");
      return outcome;
    } catch {
      setState("available");
      return "dismissed";
    }
  };

  return { state, platform, promptInstall, canPrompt: Boolean(deferred) };
}
