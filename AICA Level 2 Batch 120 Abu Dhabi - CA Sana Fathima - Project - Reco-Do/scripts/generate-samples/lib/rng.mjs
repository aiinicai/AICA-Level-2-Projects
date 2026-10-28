// Deterministic pseudo-random number generator (mulberry32).
// Never use Math.random in the sample generators: every file must be byte-for-byte reproducible.

export function mulberry32(seed) {
  let a = seed >>> 0;
  return function next() {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export class Rng {
  constructor(seed) {
    this.next = mulberry32(seed);
  }
  float() {
    return this.next();
  }
  /** Integer in [min, max] inclusive. */
  int(min, max) {
    return min + Math.floor(this.next() * (max - min + 1));
  }
  chance(p) {
    return this.next() < p;
  }
  pick(arr) {
    return arr[Math.floor(this.next() * arr.length)];
  }
  /** Fisher-Yates shuffle returning a new array. */
  shuffle(arr) {
    const out = arr.slice();
    for (let i = out.length - 1; i > 0; i--) {
      const j = Math.floor(this.next() * (i + 1));
      [out[i], out[j]] = [out[j], out[i]];
    }
    return out;
  }
  /** Random amount in integer cents within [minAed, maxAed]; avoids looking artificially round. */
  cents(minAed, maxAed) {
    const lo = Math.round(minAed * 100);
    const hi = Math.round(maxAed * 100);
    let c = lo + Math.floor(this.next() * (hi - lo + 1));
    // Realistic mix: ~20% end in .00, ~15% end in .50, rest arbitrary cents.
    const r = this.next();
    if (r < 0.2) c = Math.round(c / 100) * 100;
    else if (r < 0.35) c = Math.floor(c / 100) * 100 + 50;
    return Math.max(lo, c);
  }
  digits(n) {
    let s = '';
    for (let i = 0; i < n; i++) s += String(this.int(0, 9));
    return s;
  }
  letters(n) {
    const A = 'ABCDEFGHJKLMNPQRSTUVWXYZ';
    let s = '';
    for (let i = 0; i < n; i++) s += A[this.int(0, A.length - 1)];
    return s;
  }
}

/** Registry that guarantees an amount (in cents) is used only once per reconciliation. */
export class UniqueAmounts {
  constructor(rng) {
    this.rng = rng;
    this.used = new Set();
  }
  reserve(c) {
    if (this.used.has(c)) throw new Error(`Amount ${c / 100} already used`);
    this.used.add(c);
    return c;
  }
  take(minAed, maxAed) {
    for (;;) {
      const c = this.rng.cents(minAed, maxAed);
      if (!this.used.has(c)) {
        this.used.add(c);
        return c;
      }
    }
  }
}
