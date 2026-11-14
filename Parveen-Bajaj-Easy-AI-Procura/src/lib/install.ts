// Install-and-share helpers for the published app.
//
// The browser fires `beforeinstallprompt` once, usually before the Install
// screen is opened, so the event is captured here at module load and handed to
// whoever asks for it later. Nothing in this module registers a service worker.

import { isPreviewHost } from "./pwa";

/** Canonical address of the published app. */
export const PUBLISHED_URL = "https://order-receive-pay.lovable.app";

/** App name used in shared messages and the install button. */
export const APP_NAME = "Easy AI Procura";

export type Platform = "ios" | "android" | "desktop";

export function detectPlatform(userAgent: string): Platform {
  const ua = userAgent.toLowerCase();
  if (/iphone|ipad|ipod/.test(ua)) return "ios";
  if (/android/.test(ua)) return "android";
  return "desktop";
}

/**
 * The address to hand out. A Lovable preview host and a local dev server are
 * both private addresses — one needs a Lovable login, the other only exists on
 * this machine — so the published address is used instead.
 */
export function shareUrl(hostname: string, origin: string): string {
  const host = hostname.toLowerCase();
  if (host === "localhost" || host === "127.0.0.1" || host === "[::1]" || host === "::1") {
    return PUBLISHED_URL;
  }
  return isPreviewHost(host) ? PUBLISHED_URL : origin;
}

export type Step = { title: string; body: string };

export function installSteps(platform: Platform): Step[] {
  switch (platform) {
    case "ios":
      return [
        {
          title: "Open the link in Safari",
          body: "Chrome on iPhone cannot add web apps to the Home screen.",
        },
        {
          title: "Tap the Share icon",
          body: "The square with an upward arrow at the bottom of the screen.",
        },
        {
          title: "Tap Add to Home Screen",
          body: "Scroll the Share sheet down, tap Add to Home Screen, then Add.",
        },
      ];
    case "android":
      return [
        {
          title: "Open the link in Chrome",
          body: "Wait for the page to finish loading first.",
        },
        {
          title: "Tap the ⋮ menu",
          body: "Three dots at the top right of the screen.",
        },
        {
          title: "Tap Install app",
          body: "If Install app is not offered, tap Add to Home screen instead.",
        },
      ];
    case "desktop":
      return [
        {
          title: "Open the link in Chrome or Edge",
          body: "The install icon appears at the right end of the address bar.",
        },
        {
          title: "Click the install icon",
          body: `Or open the ⋮ menu and choose Install ${APP_NAME}.`,
        },
        {
          title: "Confirm the install",
          body: "The app then opens in its own window with the P icon.",
        },
      ];
  }
}

export function shareLinks(url: string, appName = APP_NAME): { whatsapp: string; email: string } {
  return {
    whatsapp: `https://wa.me/?text=${encodeURIComponent(`${appName}: ${url}`)}`,
    email: `mailto:?subject=${encodeURIComponent(appName)}&body=${encodeURIComponent(url)}`,
  };
}

type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

let deferredPrompt: BeforeInstallPromptEvent | null = null;
const listeners = new Set<(canInstall: boolean) => void>();

function notify(canInstall: boolean): void {
  for (const listener of [...listeners]) listener(canInstall);
}

/** Subscribe to install availability; returns an unsubscribe function. */
export function onInstallAvailability(listener: (canInstall: boolean) => void): () => void {
  listeners.add(listener);
  listener(deferredPrompt !== null);
  return () => {
    listeners.delete(listener);
  };
}

export async function promptInstall(): Promise<"accepted" | "dismissed" | "unavailable"> {
  if (!deferredPrompt) return "unavailable";
  const event = deferredPrompt;
  deferredPrompt = null;
  await event.prompt();
  const { outcome } = await event.userChoice;
  notify(false);
  return outcome;
}

if (typeof window !== "undefined") {
  window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    deferredPrompt = event as BeforeInstallPromptEvent;
    notify(true);
  });
  window.addEventListener("appinstalled", () => {
    deferredPrompt = null;
    notify(false);
  });
}
