/**
 * Progressive Web App support: service worker registration, the browser's install
 * prompt, and "new version available" detection.
 *
 * When is the app installable?
 * - Chrome / Edge on a computer: from http://localhost or any https:// address
 *   → "Install app" in the address bar / browser menu, and our own Install button.
 * - Chrome on Android: from https:// (or localhost) → "Install app" / "Add to Home screen".
 *   Over plain http on the office network it can only add a shortcut.
 * - Safari on iPhone / iPad: never shows a prompt → Share ▸ Add to Home Screen (https needed
 *   for the app to open full-screen and work as an installed app).
 */
import { useEffect, useState } from 'react';

interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

let deferredPrompt: BeforeInstallPromptEvent | null = null;
let installed = false;
let updateReady = false;
const subscribers = new Set<() => void>();
const notify = () => subscribers.forEach((s) => s());

window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault(); // we show our own Install button / banner instead of the mini-infobar
  deferredPrompt = e as BeforeInstallPromptEvent;
  notify();
});
window.addEventListener('appinstalled', () => {
  deferredPrompt = null;
  installed = true;
  notify();
});

export function registerServiceWorker() {
  if (!('serviceWorker' in navigator) || !import.meta.env.PROD) return;
  const hadController = !!navigator.serviceWorker.controller;
  // The new worker takes over straight away (skipWaiting); tell the user so they can reload.
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    if (!hadController) return;
    updateReady = true;
    notify();
  });
  window.addEventListener('load', () => {
    navigator.serviceWorker
      .register('./sw.js')
      .then((reg) => {
        // Look for a newer version whenever the app comes back to the foreground.
        document.addEventListener('visibilitychange', () => document.visibilityState === 'visible' && reg.update().catch(() => {}));
      })
      .catch((err) => console.warn('Service worker registration failed', err));
  });
}

export const isStandalone = () =>
  window.matchMedia('(display-mode: standalone)').matches || (navigator as Navigator & { standalone?: boolean }).standalone === true;

// iPadOS Safari reports itself as a Mac, so also check for touch points.
export const isIos = () => /iphone|ipad|ipod/i.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
export const isAndroid = () => /android/i.test(navigator.userAgent);

export function useInstallPrompt() {
  const [, force] = useState(0);
  useEffect(() => {
    const s = () => force((n) => n + 1);
    subscribers.add(s);
    return () => {
      subscribers.delete(s);
    };
  }, []);
  const standalone = isStandalone();
  return {
    canInstall: !standalone && !installed && deferredPrompt !== null,
    installed: installed || standalone,
    standalone,
    ios: isIos(),
    android: isAndroid(),
    secure: window.isSecureContext,
    updateReady,
    async install() {
      if (!deferredPrompt) return false;
      await deferredPrompt.prompt();
      const choice = await deferredPrompt.userChoice;
      deferredPrompt = null;
      notify();
      return choice.outcome === 'accepted';
    },
  };
}
