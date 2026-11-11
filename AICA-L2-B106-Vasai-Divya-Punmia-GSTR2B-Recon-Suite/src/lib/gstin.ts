const GSTIN_RE = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$/;
const CHARS = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ';
const VALID_STATE_CODES = new Set([...Array.from({ length: 38 }, (_, i) => i + 1), 97, 99]);

export const STATES: Record<string, string> = {
  '01': 'Jammu & Kashmir',
  '02': 'Himachal Pradesh',
  '03': 'Punjab',
  '04': 'Chandigarh',
  '05': 'Uttarakhand',
  '06': 'Haryana',
  '07': 'Delhi',
  '08': 'Rajasthan',
  '09': 'Uttar Pradesh',
  '10': 'Bihar',
  '11': 'Sikkim',
  '12': 'Arunachal Pradesh',
  '13': 'Nagaland',
  '14': 'Manipur',
  '15': 'Mizoram',
  '16': 'Tripura',
  '17': 'Meghalaya',
  '18': 'Assam',
  '19': 'West Bengal',
  '20': 'Jharkhand',
  '21': 'Odisha',
  '22': 'Chhattisgarh',
  '23': 'Madhya Pradesh',
  '24': 'Gujarat',
  '25': 'Daman & Diu',
  '26': 'Dadra & Nagar Haveli and Daman & Diu',
  '27': 'Maharashtra',
  '28': 'Andhra Pradesh (old)',
  '29': 'Karnataka',
  '30': 'Goa',
  '31': 'Lakshadweep',
  '32': 'Kerala',
  '33': 'Tamil Nadu',
  '34': 'Puducherry',
  '35': 'Andaman & Nicobar Islands',
  '36': 'Telangana',
  '37': 'Andhra Pradesh',
  '38': 'Ladakh',
  '97': 'Other Territory',
  '99': 'Centre Jurisdiction',
};

/** Format, state code and mod-36 check digit validation of a GSTIN. */
export function checkGstin(raw: string): { valid: true } | { valid: false; error: string } {
  const g = String(raw || '').trim().toUpperCase();
  if (!g) return { valid: false, error: 'GSTIN is empty' };
  if (g.length !== 15) return { valid: false, error: `Length is ${g.length} characters (must be 15)` };
  if (!GSTIN_RE.test(g)) return { valid: false, error: 'Not in GSTIN format (2 digits + PAN + entity code + Z + check digit)' };
  const state = parseInt(g.slice(0, 2), 10);
  if (!VALID_STATE_CODES.has(state)) return { valid: false, error: `Invalid state code ${g.slice(0, 2)}` };
  let sum = 0;
  for (let i = 0; i < 14; i++) {
    const v = CHARS.indexOf(g[i]) * (i % 2 === 0 ? 1 : 2);
    sum += Math.floor(v / 36) + (v % 36);
  }
  const expected = CHARS[(36 - (sum % 36)) % 36];
  if (expected !== g[14]) return { valid: false, error: `Check digit wrong (expected ${expected}, found ${g[14]})` };
  return { valid: true };
}

export const looksLikeGstin = (v: unknown) => GSTIN_RE.test(String(v ?? '').trim().toUpperCase());

export const stateOf = (gstin: string) => STATES[String(gstin).slice(0, 2)] || 'Unknown / overseas';
