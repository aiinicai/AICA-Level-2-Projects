const CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ";
const PATTERN = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$/;

export function gstinCheckDigit(first14: string): string {
  let sum = 0;
  for (let i = 0; i < 14; i++) {
    const v = CHARS.indexOf(first14[i] ?? "0");
    const p = v * (i % 2 === 0 ? 1 : 2);
    sum += Math.floor(p / 36) + (p % 36);
  }
  return CHARS[(36 - (sum % 36)) % 36]!;
}

export type GstinCheck = { valid: boolean; reason?: string };

export function validateGstin(raw: string): GstinCheck {
  const g = raw.trim().toUpperCase();
  if (g.length !== 15) return { valid: false, reason: "A GSTIN has exactly 15 characters." };
  if (!PATTERN.test(g)) return { valid: false, reason: "The format doesn't look like a GSTIN (state code + PAN + entity + Z + check digit)." };
  const sc = Number(g.slice(0, 2));
  if (sc < 1 || sc > 38) return { valid: false, reason: "The first two digits must be a valid state code." };
  if (gstinCheckDigit(g.slice(0, 14)) !== g[14]) return { valid: false, reason: "The last character (check digit) doesn't match — please re-check for a typo." };
  return { valid: true };
}

export function makeGstin(state: string, pan: string, entity = "1"): string {
  const base = `${state}${pan}${entity}Z`;
  return base + gstinCheckDigit(base);
}
