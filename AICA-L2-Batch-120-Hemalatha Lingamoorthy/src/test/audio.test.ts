import { describe, it, expect } from "vitest";
import { computeMetrics, paceLabel, wpm } from "@/lib/audio";

function tone(sec: number, rate: number) {
  return Float32Array.from({ length: sec * rate }, (_, i) => 0.3 * Math.sin(i / 5));
}
function concat(...parts: Float32Array[]) {
  const out = new Float32Array(parts.reduce((a, p) => a + p.length, 0));
  let o = 0;
  for (const p of parts) { out.set(p, o); o += p.length; }
  return out;
}

describe("pause buckets", () => {
  it("classifies a 2s silence as long and 0.8s as natural", () => {
    const r = 8000;
    const s = concat(tone(1, r), new Float32Array(2 * r), tone(1, r), new Float32Array(0.8 * r), tone(1, r));
    const m = computeMetrics(s, r);
    expect(m.longPauses).toBe(1);
    expect(m.naturalPauses).toBe(1);
    expect(m.longestPause).toBeGreaterThan(1.9);
  });
});

describe("pace", () => {
  it("ideal range is 130-160 wpm", () => {
    expect(paceLabel(129)).toBe("slow");
    expect(paceLabel(130)).toBe("ideal");
    expect(paceLabel(160)).toBe("ideal");
    expect(paceLabel(161)).toBe("fast");
  });
  it("computes wpm from word count and duration", () => {
    expect(wpm(150, 60)).toBe(150);
  });
});
