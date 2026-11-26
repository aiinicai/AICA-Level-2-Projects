// Party-name normalisation and fuzzy matching (for merge suggestions).

const NOISE = /\b(m\/s|ms|messrs|mr|mrs|shri|smt|the|a\/c|ac|account)\b/g;
const SUFFIX: [RegExp, string][] = [
  [/\bprivate\b/g, "pvt"], [/\bpvt\b/g, "pvt"], [/\blimited\b/g, "ltd"],
  [/\bcompany\b/g, "co"], [/\bcorporation\b/g, "corp"], [/\benterprises?\b/g, "ent"],
  [/\btraders?\b/g, "traders"], [/\b&\b/g, "and"],
];

export function normalizeParty(name: unknown): string {
  let s = String(name ?? "").toLowerCase();
  s = s.replace(/&/g, " and ");
  s = s.replace(/[.'`"]/g, "");          // A.B.C. -> ABC
  s = s.replace(/[^a-z0-9/ ]+/g, " ");
  s = s.replace(NOISE, " ");
  for (const [re, rep] of SUFFIX) s = s.replace(re, rep);
  s = s.replace(/\(.*?\)/g, " ");
  return s.replace(/\s+/g, " ").trim();
}

/** Core name without legal suffixes – used for similarity. */
function coreName(n: string): string {
  return n.replace(/\b(pvt|ltd|llp|co|corp|ent|inc|and sons|sons)\b/g, " ").replace(/\s+/g, " ").trim();
}

function bigrams(s: string): Map<string, number> {
  const m = new Map<string, number>();
  const t = ` ${s.replace(/\s+/g, "")} `;
  for (let i = 0; i < t.length - 1; i++) {
    const b = t.slice(i, i + 2);
    m.set(b, (m.get(b) ?? 0) + 1);
  }
  return m;
}

/** Dice coefficient on character bigrams, 0..1 */
export function similarity(a: string, b: string): number {
  const ca = coreName(a), cb = coreName(b);
  if (!ca || !cb) return 0;
  if (ca === cb) return 1;
  const A = bigrams(ca), B = bigrams(cb);
  let inter = 0, sa = 0, sb = 0;
  A.forEach((v, k) => { sa += v; inter += Math.min(v, B.get(k) ?? 0); });
  B.forEach((v) => { sb += v; });
  return (2 * inter) / (sa + sb);
}

export interface MergeSuggestion { a: string; b: string; score: number }

/** Suggest likely duplicate party names. Buckets by first letter to stay fast on large lists. */
export function suggestMerges(names: string[], threshold = 0.86, limit = 200): MergeSuggestion[] {
  const uniq = Array.from(new Set(names.filter(Boolean)));
  const buckets = new Map<string, string[]>();
  for (const n of uniq) {
    const k = coreName(n).replace(/\s/g, "").slice(0, 1) || "#";
    if (!buckets.has(k)) buckets.set(k, []);
    buckets.get(k)!.push(n);
  }
  const out: MergeSuggestion[] = [];
  buckets.forEach((list) => {
    for (let i = 0; i < list.length; i++) {
      for (let j = i + 1; j < list.length; j++) {
        const s = similarity(list[i], list[j]);
        if (s >= threshold) out.push({ a: list[i], b: list[j], score: s });
      }
    }
  });
  return out.sort((x, y) => y.score - x.score).slice(0, limit);
}
