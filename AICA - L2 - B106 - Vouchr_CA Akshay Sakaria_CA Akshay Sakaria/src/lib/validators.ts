// Free, offline checks. They prove a number is well-formed, NOT that it is live/registered —
// that needs the paid GSTIN / PAN verification APIs.

const GSTIN_CHARS = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ';
const GSTIN_RE = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$/;
const PAN_RE = /^[A-Z]{3}[ABCFGHJLPT][A-Z][0-9]{4}[A-Z]$/;

export const PAN_ENTITY: Record<string, string> = {
  P: 'Individual',
  H: 'HUF',
  C: 'Company',
  F: 'Firm / LLP',
  A: 'AOP',
  B: 'BOI',
  T: 'Trust',
  L: 'Local authority',
  J: 'Artificial juridical person',
  G: 'Government'
};

export function gstinCheckChar(first14: string): string {
  let sum = 0;
  for (let i = 0; i < 14; i++) {
    const v = GSTIN_CHARS.indexOf(first14[i]);
    const p = v * (i % 2 === 0 ? 1 : 2);
    sum += Math.floor(p / 36) + (p % 36);
  }
  return GSTIN_CHARS[(36 - (sum % 36)) % 36];
}

export interface GstinCheck {
  ok: boolean;
  reason?: string;
  stateCode?: string;
  pan?: string;
}

export function checkGstin(raw: string): GstinCheck {
  const g = raw.trim().toUpperCase();
  if (g.length !== 15) return { ok: false, reason: 'GSTIN must be 15 characters' };
  if (!GSTIN_RE.test(g)) return { ok: false, reason: 'GSTIN format is not valid' };
  const state = Number(g.slice(0, 2));
  if (state < 1 || state > 38 && state !== 97 && state !== 99) {
    return { ok: false, reason: 'Unknown state code' };
  }
  if (gstinCheckChar(g.slice(0, 14)) !== g[14]) {
    return { ok: false, reason: 'Check digit does not match — likely a typo' };
  }
  return { ok: true, stateCode: g.slice(0, 2), pan: g.slice(2, 12) };
}

export interface PanCheck {
  ok: boolean;
  reason?: string;
  entityCode?: string;
  entityType?: string;
}

export function checkPan(raw: string): PanCheck {
  const p = raw.trim().toUpperCase();
  if (!PAN_RE.test(p)) return { ok: false, reason: 'PAN format is not valid (e.g. ABCPE1234F)' };
  return { ok: true, entityCode: p[3], entityType: PAN_ENTITY[p[3]] };
}

export const isIndividualOrHuf = (pan?: string) => !!pan && (pan[3] === 'P' || pan[3] === 'H');
