// GSTIN / PAN validation used on the client (the database has the same GSTIN check).

const GST_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ";
const GSTIN_RE = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$/;
const PAN_RE = /^[A-Z]{5}[0-9]{4}[A-Z]$/;

export type GstinStatus = "valid" | "invalid" | "blank";

export function cleanGstin(v: unknown): string {
  return String(v ?? "").toUpperCase().replace(/[^0-9A-Z]/g, "");
}

export function gstinChecksum(first14: string): string {
  let total = 0;
  for (let i = 0; i < 14; i++) {
    const v = GST_CHARS.indexOf(first14[i]);
    const prod = v * (i % 2 === 1 ? 2 : 1);
    total += Math.floor(prod / 36) + (prod % 36);
  }
  return GST_CHARS[(36 - (total % 36)) % 36];
}

export function isValidGstin(v: unknown): boolean {
  const g = cleanGstin(v);
  if (!GSTIN_RE.test(g)) return false;
  return gstinChecksum(g.slice(0, 14)) === g[14];
}

export function gstinStatus(v: unknown): GstinStatus {
  const g = cleanGstin(v);
  if (!g) return "blank";
  return isValidGstin(g) ? "valid" : "invalid";
}

export function isValidPan(v: unknown): boolean {
  return PAN_RE.test(String(v ?? "").toUpperCase().trim());
}

export function panFromGstin(v: unknown): string | null {
  const g = cleanGstin(v);
  return GSTIN_RE.test(g) ? g.slice(2, 12) : null;
}

export const GST_STATES: Record<string, string> = {
  "01": "Jammu & Kashmir", "02": "Himachal Pradesh", "03": "Punjab", "04": "Chandigarh",
  "05": "Uttarakhand", "06": "Haryana", "07": "Delhi", "08": "Rajasthan", "09": "Uttar Pradesh",
  "10": "Bihar", "11": "Sikkim", "12": "Arunachal Pradesh", "13": "Nagaland", "14": "Manipur",
  "15": "Mizoram", "16": "Tripura", "17": "Meghalaya", "18": "Assam", "19": "West Bengal",
  "20": "Jharkhand", "21": "Odisha", "22": "Chhattisgarh", "23": "Madhya Pradesh", "24": "Gujarat",
  "26": "Dadra & Nagar Haveli and Daman & Diu", "27": "Maharashtra", "29": "Karnataka", "30": "Goa",
  "31": "Lakshadweep", "32": "Kerala", "33": "Tamil Nadu", "34": "Puducherry",
  "35": "Andaman & Nicobar", "36": "Telangana", "37": "Andhra Pradesh", "38": "Ladakh",
  "97": "Other Territory", "99": "Centre Jurisdiction",
};
