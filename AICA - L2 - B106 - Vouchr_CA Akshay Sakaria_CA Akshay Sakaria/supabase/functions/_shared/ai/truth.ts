// TRUTH CONTRACT — applies to every AI task in Vouchr. Non-negotiable:
//   no hallucination · no assumptions · no bias · any doubt is MARKED, never hidden.
// How it is enforced (the model's promise alone is never trusted):
//   1. Every value comes back as a Fact { value, certainty, evidence, note }.
//   2. The prompt carries TRUTH_RULES.
//   3. Code then re-checks each fact (format, checksum, membership in our own lists, quote really present in the source,
//      arithmetic) and DOWNGRADES anything that fails to 'uncertain' with the reason. It never upgrades.
//   4. The app fills a field only from 'certain' facts; 'uncertain' ones are shown amber with the reason, and a person decides.
// Pure TypeScript (no Deno / Node / browser APIs) so the Supabase function, the local test proxy and unit tests share it.

export type Certainty = 'certain' | 'uncertain' | 'not_found';
export interface Fact<T> { value: T | null; certainty: Certainty; evidence: string; note?: string }

export const TRUTH_RULES = `STRICT RULES — follow every one:
1. Use ONLY the input given here (document, audio, text, tables). Do not use outside knowledge to fill in a value.
2. If a value is not present, return value null with certainty "not_found".
3. If there is ANY doubt — blurred, cut off, overwritten, unclear handwriting, two possible readings, conflicting figures — return certainty "uncertain" and say exactly why in "note". Doubt must be marked, never resolved by guessing.
4. Use certainty "certain" only when the exact value is clearly present. "evidence" must then quote the exact characters you read or heard.
5. Never guess, round, complete or "correct" a number, name, GSTIN, PAN or date. Report what is there; if it looks wrong, mark it "uncertain" and explain.
6. Do not judge any person or business by name, community, religion, caste, region, language, gender or size. Any concern must rest only on evidence visible in the input.
7. Where the task asks for a suggestion that is not printed in the input (e.g. a likely HSN code), it is ALWAYS "uncertain" with note "suggestion — not in the document".
8. Reply only with JSON matching the schema.`;

/** JSON schema (Gemini OpenAPI subset) for one Fact. */
export const factSchema = (type: 'STRING' | 'NUMBER' | 'BOOLEAN', description?: string) => ({
  type: 'OBJECT',
  properties: {
    value: { type, nullable: true, ...(description ? { description } : {}) },
    certainty: { type: 'STRING', enum: ['certain', 'uncertain', 'not_found'] },
    evidence: { type: 'STRING', description: 'Exact text read or heard; empty if not found' },
    note: { type: 'STRING', description: 'Why uncertain, or empty' }
  },
  required: ['value', 'certainty', 'evidence']
});

const squash = (s: string) => s.toLowerCase().normalize('NFKC').replace(/[\s\-_.,:;/\\|'"`()[\]{}₹]+/g, '');

/** Makes any model output a well-formed Fact; malformed → uncertain. Never upgrades certainty. */
export function asFact<T>(raw: unknown): Fact<T> {
  const r = (raw ?? {}) as Partial<Fact<T>>;
  const certainty: Certainty = r.certainty === 'certain' || r.certainty === 'not_found' ? r.certainty : 'uncertain';
  const f: Fact<T> = { value: r.value === undefined ? null : (r.value as T | null), certainty, evidence: typeof r.evidence === 'string' ? r.evidence : '', note: typeof r.note === 'string' && r.note ? r.note : undefined };
  if (r.certainty !== 'certain' && r.certainty !== 'not_found' && r.certainty !== 'uncertain') f.note = join(f.note, 'answer was not in the expected form');
  if (f.value === null || f.value === '') { f.value = null; if (f.certainty === 'certain') { f.certainty = 'not_found'; } }
  else if (f.certainty === 'not_found') { f.certainty = 'uncertain'; f.note = join(f.note, 'a value was given but marked not found'); }
  if (f.certainty === 'certain' && !f.evidence.trim()) doubt(f, 'no evidence quoted');
  return f;
}

const join = (a: string | undefined, b: string) => (a ? `${a}; ${b}` : b);
/** Downgrade a fact to uncertain with a reason (no-op for not_found). */
export function doubt<T>(f: Fact<T>, reason: string): Fact<T> {
  if (f.certainty === 'not_found') return f;
  f.certainty = 'uncertain';
  f.note = join(f.note, reason);
  return f;
}

/** The quoted evidence must really occur in the source text (PDF text layer, transcript, bank narration…). */
export function checkEvidence<T>(f: Fact<T>, source: string | undefined): Fact<T> {
  if (f.certainty !== 'certain' || !source) return f;
  if (!squash(source).includes(squash(f.evidence))) doubt(f, 'quoted text not found in the source');
  return f;
}

// ---------------------------------------------------------------- value checks
const GSTIN_RE = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$/;
const CH = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ';
export function gstinValid(g: string): boolean {
  if (!GSTIN_RE.test(g)) return false;
  let sum = 0;
  for (let i = 0; i < 14; i++) { const p = CH.indexOf(g[i]) * (i % 2 ? 2 : 1); sum += Math.floor(p / 36) + (p % 36); }
  return CH[(36 - (sum % 36)) % 36] === g[14];
}
export const panValid = (p: string) => /^[A-Z]{5}[0-9]{4}[A-Z]$/.test(p);

export function checkGstinFact(f: Fact<string>): Fact<string> {
  if (f.value === null) return f;
  const g = String(f.value).toUpperCase().replace(/\s/g, '');
  f.value = g;
  if (!gstinValid(g)) doubt(f, 'GSTIN fails the format / check-digit test — likely misread');
  return f;
}

export function checkPanFact(f: Fact<string>): Fact<string> {
  if (f.value === null) return f;
  f.value = String(f.value).toUpperCase().replace(/\s/g, '');
  if (!panValid(f.value)) doubt(f, 'PAN format is not valid');
  return f;
}

export function checkDateFact(f: Fact<string>, today: string): Fact<string> {
  if (f.value === null) return f;
  const v = String(f.value);
  const d = new Date(`${v}T00:00:00Z`);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(v) || Number.isNaN(d.getTime()) || d.toISOString().slice(0, 10) !== v) return doubt(f, 'not a real calendar date');
  if (v > today) doubt(f, 'date is in the future');
  if (v < '2017-07-01') doubt(f, 'date is before GST began (01-07-2017)');
  return f;
}

export function checkAmountFact(f: Fact<number>): Fact<number> {
  if (f.value === null) return f;
  const n = typeof f.value === 'number' ? f.value : Number(String(f.value).replace(/[₹,\s]/g, ''));
  if (!Number.isFinite(n) || n < 0) { f.value = null; return doubt(f, 'not a valid amount'); }
  f.value = Math.round(n * 100) / 100;
  return f;
}

/** Value must be one of OUR list (expense heads, TDS codes, vendors…) — the model cannot invent a new one. */
export function checkMember(f: Fact<string>, allowed: string[], what: string): Fact<string> {
  if (f.value === null) return f;
  const hit = allowed.find((a) => a.toLowerCase() === String(f.value).toLowerCase());
  if (!hit) { f.note = join(f.note, `"${f.value}" is not in the ${what} list`); f.value = null; f.certainty = 'uncertain'; return f; }
  f.value = hit;
  return f;
}

/** taxable + CGST + SGST + IGST must equal total (±₹1 round-off) — otherwise all of them are in doubt. */
export function checkTotals(t: { taxable: Fact<number>; cgst: Fact<number>; sgst: Fact<number>; igst: Fact<number>; total: Fact<number>; other?: Fact<number> }) {
  const vals = [t.taxable, t.cgst, t.sgst, t.igst, t.total, ...(t.other ? [t.other] : [])];
  if (t.taxable.value === null || t.total.value === null) return;
  const sum = (t.taxable.value ?? 0) + (t.cgst.value ?? 0) + (t.sgst.value ?? 0) + (t.igst.value ?? 0) + (t.other?.value ?? 0);
  const diff = Math.round((t.total.value - sum) * 100) / 100;
  if (Math.abs(diff) > 1) vals.forEach((f) => doubt(f, `amounts don't add up (total differs by ₹${diff})`));
}

/** Free text written by AI may only contain numbers that exist in our data — any other number is a hallucination. */
export function strayNumbers(text: string, allowed: number[]): string[] {
  const ok = new Set(allowed.flatMap((n) => [String(n), String(Math.round(n)), n.toFixed(2)]));
  return (text.match(/\d[\d,]*(?:\.\d+)?/g) ?? []).map((x) => x.replace(/,/g, '')).filter((x) => !ok.has(x) && !ok.has(String(Number(x))));
}

export interface Checked<T> { result: T; doubts: string[]; needsHumanCheck: boolean }
/** Collects every uncertain fact (with its field path) so the UI can list all doubts in one place. */
export function collectDoubts(obj: unknown, path = ''): string[] {
  if (!obj || typeof obj !== 'object') return [];
  const o = obj as Record<string, unknown>;
  if ('certainty' in o && 'evidence' in o) return o.certainty === 'uncertain' ? [`${path}: ${o.note ?? 'uncertain'}`] : [];
  return Object.entries(o).flatMap(([k, v]) => collectDoubts(v, path ? `${path}.${k}` : k));
}
export function finish<T>(result: T, extra: string[] = []): Checked<T> {
  const doubts = [...collectDoubts(result), ...extra];
  return { result, doubts, needsHumanCheck: doubts.length > 0 };
}
