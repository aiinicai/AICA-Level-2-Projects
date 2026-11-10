/**
 * Works out what kind of device the app is open on and keeps it current when the
 * window is resized, the tablet is rotated or a keyboard / mouse is attached.
 *
 *   phone   — narrow screen (under 640 px), or a touch screen whose short side is under 600 px
 *   tablet  — touch screen from 600 px up (iPad, Android tablets), or any window 640–1023 px wide
 *   desktop — 1024 px and wider with a mouse / trackpad
 *
 * The result is also written to <html data-device data-touch data-orientation data-standalone>
 * so CSS can adapt (bigger touch targets, 16 px inputs on iPhone / iPad, safe areas).
 */
import { useEffect, useState } from 'react';

export type DeviceType = 'phone' | 'tablet' | 'desktop';

export interface Device {
  type: DeviceType;
  touch: boolean;
  orientation: 'portrait' | 'landscape';
  standalone: boolean;
  /** Tablet held upright (or a narrow desktop window): icon-only side rail. */
  rail: boolean;
}

const mq = (q: string) => window.matchMedia(q).matches;

export function detectDevice(): Device {
  const w = window.innerWidth;
  const h = window.innerHeight;
  const short = Math.min(w, h);
  // "pointer: coarse" = finger is the main input. iPadOS reports a desktop user agent, so rely on this.
  const touch = mq('(pointer: coarse)') || (navigator.maxTouchPoints > 1 && !mq('(pointer: fine)'));
  let type: DeviceType;
  if (w < 640 || (touch && short < 600)) type = 'phone';
  else if (touch || w < 1024) type = 'tablet';
  else type = 'desktop';
  const orientation = w >= h ? 'landscape' : 'portrait';
  const standalone = mq('(display-mode: standalone)') || (navigator as Navigator & { standalone?: boolean }).standalone === true;
  return { type, touch, orientation, standalone, rail: type === 'tablet' && w < 1024 };
}

function apply(d: Device) {
  const el = document.documentElement;
  el.dataset.device = d.type;
  el.dataset.touch = d.touch ? 'yes' : 'no';
  el.dataset.orientation = d.orientation;
  el.dataset.standalone = d.standalone ? 'yes' : 'no';
}

// Set before the first paint so CSS is right from the start.
apply(detectDevice());

export function useDevice(): Device {
  const [d, setD] = useState(detectDevice);
  useEffect(() => {
    let t = 0;
    const update = () => {
      cancelAnimationFrame(t);
      t = requestAnimationFrame(() => {
        const n = detectDevice();
        apply(n);
        setD((p) => (p.type === n.type && p.touch === n.touch && p.orientation === n.orientation && p.standalone === n.standalone && p.rail === n.rail ? p : n));
      });
    };
    window.addEventListener('resize', update);
    window.addEventListener('orientationchange', update);
    const queries = ['(pointer: coarse)', '(display-mode: standalone)'].map((q) => window.matchMedia(q));
    queries.forEach((q) => q.addEventListener('change', update));
    return () => {
      window.removeEventListener('resize', update);
      window.removeEventListener('orientationchange', update);
      queries.forEach((q) => q.removeEventListener('change', update));
    };
  }, []);
  return d;
}
