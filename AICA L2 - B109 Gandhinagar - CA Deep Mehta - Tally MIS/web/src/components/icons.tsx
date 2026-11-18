import type { ReactNode } from 'react';

// The NOVEX App launcher icons: flat artwork on a 56×56 canvas, two or three bright fills, rounded shapes,
// no gradients. `tally` is the same tile as on the client portal. Decorative: the label beside each carries the meaning.

export type AppIconName =
  | 'tally' | 'overview' | 'insights' | 'pnl' | 'balance' | 'arap' | 'inventory'
  | 'quality' | 'sources' | 'company' | 'mapping' | 'kpis' | 'vouchers' | 'users';

const SHAPES: Record<AppIconName, ReactNode> = {
  tally: (
    <>
      <rect x="6" y="6" width="44" height="44" rx="10" fill="#0F766E" />
      <rect x="14" y="30" width="6" height="14" rx="2" fill="#fff" />
      <rect x="25" y="22" width="6" height="22" rx="2" fill="#fff" />
      <rect x="36" y="14" width="6" height="30" rx="2" fill="#fff" />
    </>
  ),
  overview: (
    <>
      <rect x="7" y="30" width="10" height="20" rx="3" fill="#FB923C" />
      <rect x="21" y="20" width="10" height="30" rx="3" fill="#EC4899" />
      <rect x="35" y="10" width="10" height="40" rx="3" fill="#8B5CF6" />
      <circle cx="46" cy="10" r="5" fill="#FACC15" />
    </>
  ),
  insights: (
    <>
      <path d="M28 6a16 16 0 0 0-9 29.2V39a3 3 0 0 0 3 3h12a3 3 0 0 0 3-3v-3.8A16 16 0 0 0 28 6z" fill="#FACC15" />
      <rect x="21" y="45" width="14" height="5" rx="2.5" fill="#6D4AE0" />
      <path d="M28 16v13" stroke="#fff" strokeWidth="3.5" strokeLinecap="round" />
      <circle cx="28" cy="35" r="2.4" fill="#fff" />
    </>
  ),
  pnl: (
    <>
      <rect x="8" y="6" width="40" height="44" rx="7" fill="#22C55E" />
      <path d="M16 36l8-9 6 5 10-13" fill="none" stroke="#fff" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="40" cy="19" r="4.5" fill="#FACC15" />
    </>
  ),
  balance: (
    <>
      <rect x="26" y="8" width="4" height="36" rx="2" fill="#6D4AE0" />
      <rect x="15" y="44" width="26" height="6" rx="3" fill="#6D4AE0" />
      <rect x="9" y="13" width="38" height="4" rx="2" fill="#6D4AE0" />
      <path d="M3 32h20a10 10 0 0 1-20 0z" fill="#0EA5E9" />
      <path d="M33 32h20a10 10 0 0 1-20 0z" fill="#FB923C" />
      <path d="M13 15L5 32M13 15l8 17M43 15l-8 17M43 15l8 17" stroke="#6D4AE0" strokeWidth="1.8" fill="none" />
    </>
  ),
  arap: (
    <>
      <rect x="5" y="9" width="46" height="17" rx="8.5" fill="#0EA5E9" />
      <path d="M17 17.5h19M30 12.5l6 5-6 5" fill="none" stroke="#fff" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      <rect x="5" y="30" width="46" height="17" rx="8.5" fill="#F97366" />
      <path d="M39 38.500H20M26 33.500l-6 5 6 5" fill="none" stroke="#fff" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
    </>
  ),
  inventory: (
    <>
      <path d="M28 5l21 11-21 11L7 16z" fill="#F59E0B" />
      <path d="M7 20l19 10v21L7 41z" fill="#FB923C" />
      <path d="M49 20L30 30v21l19-10z" fill="#14B8A6" />
    </>
  ),
  quality: (
    <>
      <path d="M28 5l20 7v14c0 12.5-8 21-20 25C16 47 8 38.5 8 26V12z" fill="#2563EB" />
      <path d="M19 28l7 7 12-14" fill="none" stroke="#fff" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
    </>
  ),
  sources: (
    <>
      <ellipse cx="28" cy="12" rx="19" ry="7" fill="#14B8A6" />
      <path d="M9 18c0 3.9 8.5 7 19 7s19-3.1 19-7v9c0 3.9-8.5 7-19 7S9 30.9 9 27z" fill="#0EA5E9" />
      <path d="M9 33c0 3.9 8.5 7 19 7s19-3.1 19-7v9c0 3.9-8.5 7-19 7S9 45.9 9 42z" fill="#8B5CF6" />
    </>
  ),
  company: (
    <>
      <rect x="6" y="20" width="14" height="30" rx="4" fill="#14B8A6" />
      <rect x="21" y="8" width="16" height="42" rx="4" fill="#6D4AE0" />
      <rect x="38" y="26" width="12" height="24" rx="4" fill="#F59E0B" />
      <rect x="25" y="16" width="3" height="4" rx="1" fill="#fff" />
      <rect x="30" y="16" width="3" height="4" rx="1" fill="#fff" />
      <rect x="25" y="25" width="3" height="4" rx="1" fill="#fff" />
      <rect x="30" y="25" width="3" height="4" rx="1" fill="#fff" />
    </>
  ),
  mapping: (
    <>
      <path d="M17 14h9a8 8 0 0 1 8 8v12a8 8 0 0 0 8 8" fill="none" stroke="#94A3B8" strokeWidth="3.5" />
      <path d="M17 14h22" fill="none" stroke="#94A3B8" strokeWidth="3.5" />
      <circle cx="13" cy="14" r="8" fill="#EC4899" />
      <circle cx="43" cy="14" r="8" fill="#0EA5E9" />
      <circle cx="43" cy="42" r="8" fill="#22C55E" />
    </>
  ),
  kpis: (
    <>
      <path d="M6 40a22 22 0 0 1 44 0z" fill="#E2E8F0" />
      <path d="M6 40a22 22 0 0 1 22-22v22z" fill="#22C55E" />
      <path d="M28 18a22 22 0 0 1 15.5 6.400L28 40z" fill="#FACC15" />
      <path d="M28 40l13-13" stroke="#1b1f2a" strokeWidth="3.5" strokeLinecap="round" />
      <circle cx="28" cy="40" r="4.5" fill="#1b1f2a" />
    </>
  ),
  vouchers: (
    <>
      <rect x="10" y="6" width="30" height="40" rx="6" fill="#F97366" />
      <rect x="16" y="15" width="18" height="3.5" rx="1.75" fill="#fff" />
      <rect x="16" y="23" width="14" height="3.5" rx="1.75" fill="#fff" />
      <rect x="16" y="31" width="10" height="3.5" rx="1.75" fill="#fff" />
      <circle cx="40" cy="40" r="11" fill="#2563EB" />
      <path d="M35.5 40.500l3 3 6-6.5" fill="none" stroke="#fff" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
    </>
  ),
  users: (
    <>
      <circle cx="20" cy="17" r="8" fill="#0EA5E9" />
      <path d="M5 46c0-9 6.5-15 15-15s15 6 15 15z" fill="#0EA5E9" />
      <circle cx="38" cy="22" r="6.5" fill="#22C55E" />
      <path d="M27 48c0-7.5 4.8-12.5 11-12.500S49 40.5 49 48z" fill="#22C55E" />
    </>
  ),
};

export function AppIcon({ name, className }: { name: AppIconName; className?: string }) {
  return (
    <svg viewBox="0 0 56 56" aria-hidden="true" focusable="false" className={className}>
      {SHAPES[name]}
    </svg>
  );
}

const LINE = { width: 17, height: 17, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 2, strokeLinecap: 'round', strokeLinejoin: 'round', 'aria-hidden': true } as const;

export const GridIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
    <rect x="3" y="3" width="7" height="7" rx="2" /><rect x="14" y="3" width="7" height="7" rx="2" />
    <rect x="3" y="14" width="7" height="7" rx="2" /><rect x="14" y="14" width="7" height="7" rx="2" />
  </svg>
);
export const ChevronDownIcon = () => <svg {...LINE} width="15" height="15"><path d="M6 9l6 6 6-6" /></svg>;
export const SignOutIcon = () => <svg {...LINE}><path d="M15 4h4a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1h-4M10 17l-5-5 5-5M5 12h11" /></svg>;
export const KeyIcon = () => <svg {...LINE}><circle cx="8" cy="15" r="4" /><path d="M11 12l9-9M16 7l3 3" /></svg>;
export const ThemeIcon = () => <svg {...LINE}><path d="M21 12.800A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.800z" /></svg>;
