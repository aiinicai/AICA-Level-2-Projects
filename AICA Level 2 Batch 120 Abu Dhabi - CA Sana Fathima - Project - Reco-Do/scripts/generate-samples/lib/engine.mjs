// Minimal reference implementation of the Step 3 tier rules (Master Prompt section 4), used ONLY by
// verify.mjs to prove the sample files produce the tier counts documented in sample-data/README.md.
// It is not the app's engine; it follows the same rules so the expectations are checkable.

const PREFIX = /^(CHQ|FT|INV|REF)(?=\d)/;

/** "Normalised" rule: ignore case, spaces, dashes and punctuation, prefixes like CHQ/FT/INV/REF, leading zeros. */
export function normalise(v) {
  let s = String(v ?? '').toUpperCase().replace(/[^A-Z0-9]/g, '');
  s = s.replace(PREFIX, '');
  s = s.replace(/^0+(?=.)/, '');
  return s;
}
export const normText = (v) => String(v ?? '').toUpperCase().replace(/[^A-Z0-9]/g, '');

/**
 * keys: [{ name, kind: 'ref' | 'id' | 'text' | 'amount' | 'date', identifies: bool, a: row => value, b: row => value, tol }]
 * amount values are integer cents (already sign-converted so that equal means "agrees"); dates are Excel serials.
 */
export function reconcile(A, B, keys) {
  const n = keys.length;
  const cmp = (k, va, vb) => {
    if (k.kind === 'amount') return va != null && vb != null && Math.abs(va - vb) <= (k.tol ?? 0);
    if (k.kind === 'date') return va != null && vb != null && Math.abs(va - vb) <= (k.tol ?? 0);
    const fa = k.kind === 'text' ? normText(va) : normalise(va);
    const fb = k.kind === 'text' ? normText(vb) : normalise(vb);
    return fa !== '' && fa === fb;
  };
  const keyVal = (k, v) => (k.kind === 'amount' ? (v == null ? null : String(v)) : k.kind === 'text' ? normText(v) : normalise(v));
  // Hash maps on every identifying key (never compare every row with every row)
  const idx = keys.map((k) => {
    if (!k.identifies) return null;
    const m = new Map();
    B.forEach((r, j) => {
      const v = keyVal(k, k.b(r));
      if (v === null || v === '') return;
      if (!m.has(v)) m.set(v, []);
      m.get(v).push(j);
    });
    return m;
  });
  const dateKey = keys.find((k) => k.kind === 'date');
  const amtKey = keys.find((k) => k.kind === 'amount');
  const pairs = [];
  A.forEach((ra, i) => {
    const cands = new Set();
    keys.forEach((k, ki) => {
      if (!idx[ki]) return;
      const v = keyVal(k, k.a(ra));
      if (v === null || v === '') return;
      for (const j of idx[ki].get(v) ?? []) cands.add(j);
    });
    for (const j of cands) {
      const rb = B[j];
      const pass = keys.map((k) => cmp(k, k.a(ra), k.b(rb)));
      const np = pass.filter(Boolean).length;
      let tier = null;
      if (n >= 3) {
        if (np === n) tier = 'M';
        else if (np === n - 1) tier = 'D';
        else if (np === 1 && keys[pass.indexOf(true)].identifies) tier = 'L';
      } else if (n === 2) {
        if (np === 2) tier = 'M';
        else if (np === 1 && keys[pass.indexOf(true)].identifies) tier = 'L';
      } else if (np === 1) tier = 'M';
      if (!tier) continue;
      const dd = dateKey ? Math.abs((dateKey.a(ra) ?? 0) - (dateKey.b(rb) ?? 0)) : 0;
      const ad = amtKey ? Math.abs((amtKey.a(ra) ?? 0) - (amtKey.b(rb) ?? 0)) : 0;
      pairs.push({ i, j, tier, pass, np, dd, ad });
    }
  });
  const usedA = new Map(); // i -> result
  const usedB = new Map();
  const results = [];
  const better = (p, q) => p.dd - q.dd || p.ad - q.ad || q.np - p.np;
  for (const T of ['M', 'D', 'L']) {
    const tp = pairs.filter((p) => p.tier === T && !usedA.has(p.i) && !usedB.has(p.j));
    // Rule 3: a line with 2+ equally good candidates -> Doubtful "Multiple identical candidates"
    const dupA = new Set(), dupB = new Set();
    const groupBy = (side) => {
      const g = new Map();
      for (const p of tp) {
        const key = side === 'A' ? p.i : p.j;
        if (!g.has(key)) g.set(key, []);
        g.get(key).push(p);
      }
      for (const [key, list] of g) {
        list.sort(better);
        const ties = list.filter((p) => better(p, list[0]) === 0);
        if (ties.length >= 2) {
          (side === 'A' ? dupA : dupB).add(key);
          for (const p of ties) (side === 'A' ? dupB : dupA).add(side === 'A' ? p.j : p.i);
        }
      }
    };
    groupBy('A');
    groupBy('B');
    for (const i of dupA) usedA.set(i, { tier: 'D', dup: true });
    for (const j of dupB) usedB.set(j, { tier: 'D', dup: true });
    if (dupA.size || dupB.size) results.push({ tier: 'D', dup: true, a: [...dupA], b: [...dupB] });
    tp.sort(better);
    for (const p of tp) {
      if (usedA.has(p.i) || usedB.has(p.j)) continue;
      const r = { tier: T, a: [p.i], b: [p.j], pass: p.pass, dd: p.dd, ad: p.ad };
      usedA.set(p.i, r);
      usedB.set(p.j, r);
      results.push(r);
    }
  }
  const countA = (t) => [...usedA.values()].filter((r) => r.tier === t).length;
  const countB = (t) => [...usedB.values()].filter((r) => r.tier === t).length;
  return {
    results,
    usedA,
    usedB,
    unmatchedA: A.map((_, i) => i).filter((i) => !usedA.has(i)),
    unmatchedB: B.map((_, j) => j).filter((j) => !usedB.has(j)),
    counts: {
      matched: countA('M'), doubtful: countA('D'), doubtfulB: countB('D'), likely: countA('L'),
      unmatchedA: A.length - usedA.size, unmatchedB: B.length - usedB.size,
    },
  };
}
