// Run: npm test   (uses Node's built-in test runner; astronomy-engine is only used to check accuracy)
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import * as Astronomy from 'astronomy-engine';
const require = createRequire(import.meta.url);
const S = require('../web/js/saathi-core.js');

const angDiff = (a, b) => Math.abs(((a - b + 540) % 360) - 180);
const rand = (() => { let s = 42; return () => (s = (s * 1103515245 + 12345) % 2147483648) / 2147483648; })();
const dates = Array.from({ length: 500 }, () => new Date(Date.UTC(1950, 0, 1) + rand() * 100 * 365.25 * 86400000));

test('Moon longitude within 0.1° of astronomy-engine over 1950–2050 (500 dates)', () => {
  let worst = 0;
  for (const d of dates) worst = Math.max(worst, angDiff(S.moonLongitude(d), Astronomy.EclipticGeoMoon(d).lon));
  assert.ok(worst < 0.1, `worst ${worst.toFixed(3)}°`);
});

test('Sun longitude within 0.02° of astronomy-engine', () => {
  let worst = 0;
  for (const d of dates) worst = Math.max(worst, angDiff(S.sunLongitude(d), Astronomy.SunPosition(d).elon));
  assert.ok(worst < 0.02, `worst ${worst.toFixed(4)}°`);
});

test('Sunrise and sunset within 3 minutes of astronomy-engine for every city', () => {
  for (const c of S.CITIES) {
    const key = '2026-10-18';
    const st = S.sunTimes(key, c);
    const obs = new Astronomy.Observer(c.lat, c.lon, 0);
    const start = S.localToUtc(key, 0, 0, c.tz);
    const rise = Astronomy.SearchRiseSet(Astronomy.Body.Sun, obs, +1, start, 1).date;
    const set = Astronomy.SearchRiseSet(Astronomy.Body.Sun, obs, -1, start, 1).date;
    assert.ok(Math.abs(st.sunrise - rise) < 180000, `${c.name} sunrise off by ${(st.sunrise - rise) / 60000} min`);
    assert.ok(Math.abs(st.sunset - set) < 180000, `${c.name} sunset off by ${(st.sunset - set) / 60000} min`);
  }
});

test('Day card: Abu Dhabi, Wed 14 Oct 2026 → Moon in Scorpio (Vedic) / Sagittarius (Western), Rahu Kaal ~12:08–1:35 pm', () => {
  const now = new Date(Date.UTC(2026, 9, 14, 6));
  const v = S.dayCard({ now, cityId: 'abu-dhabi', system: 'Vedic' });
  assert.equal(v.weekday, 'Wednesday');
  assert.equal(v.moonSignVedic, 'Scorpio');
  assert.equal(v.moonSignWestern, 'Sagittarius');
  assert.match(v.rahuKaal, /^12:0\d pm – 1:3\d pm$/);
  assert.equal(v.abhijit, 'Not used on Wednesdays');
  assert.equal(v.vara.lord, 'Budh (Mercury)');
});

test('Sunday is ruled by the Sun (not Mercury) and Rahu Kaal is the last eighth of daylight', () => {
  const v = S.dayCard({ now: new Date(Date.UTC(2026, 9, 18, 6)), cityId: 'dubai' });
  assert.equal(v.weekday, 'Sunday');
  assert.equal(v.vara.lord, 'Surya (Sun)');
  assert.match(v.rahuKaal, /^4:\d\d pm – 5:\d\d pm$/);
});

test('Numerology worked example: 14 Aug 1992', () => {
  assert.deepEqual(S.lifePath('1992-08-14'), { compound: 16, value: 7 });
  assert.equal(S.moolank('1992-08-14'), 5);
  assert.deepEqual(S.bhagyank('1992-08-14'), { compound: 34, value: 7 });
  assert.equal(S.personalDay('1992-08-14', '2026-10-14'), 2);
  const g = S.loShu('1992-08-14');
  assert.deepEqual([g.counts[1], g.counts[2], g.counts[4], g.counts[8], g.counts[9], g.counts[5]], [2, 1, 1, 1, 2, 0]);
  assert.ok(g.complete.some((p) => p.name === 'Mental plane'));
});

test('Master numbers 11/22/33 are kept, other compounds reduce', () => {
  assert.equal(S.lifePath('2000-11-11').value, 6); // 11 + 11 + 2 = 24 → 6
  assert.equal(S.lifePath('1987-11-29').value, 11); // 11 + 11(29→11) + 25→7 = 29 → 11
});

test('Signature: measured from strokes, not preset', () => {
  const mk = (lean, rise) => {
    const strokes = [];
    for (let i = 0; i < 8; i++) {
      const x = 30 + i * 30, base = 120 - i * 30 * Math.tan((rise * Math.PI) / 180);
      const s = [];
      for (let k = 0; k <= 10; k++) s.push({ x: x + k * 6 * Math.tan((lean * Math.PI) / 180), y: base - k * 6 });
      strokes.push(s);
    }
    return strokes;
  };
  const right = S.analyseSignature(mk(15, 4), 320, 160);
  const left = S.analyseSignature(mk(-12, -4), 320, 160);
  assert.equal(right.slantClass, 'right-leaning');
  assert.equal(right.baselineClass, 'rising');
  assert.equal(left.slantClass, 'left-leaning');
  assert.equal(left.baselineClass, 'falling');
  assert.ok(Math.abs(right.slantDeg - 105) <= 3, 'slant within 3°');
  assert.ok(Math.abs(right.baselineDeg - 4) <= 1.5, `baseline ${right.baselineDeg} within 1.5° of 4°`);
  assert.ok(Math.abs(left.baselineDeg + 4) <= 1.5, 'falling baseline within 1.5°');
  assert.equal(S.analyseSignature([[{ x: 1, y: 1 }]], 320, 160), null);
});

test('TIPI scoring (Gosling et al., 2003) with reverse-keyed items', () => {
  const r = S.scoreTipi([7, 1, 7, 1, 7, 1, 7, 1, 7, 1]);
  for (const v of Object.values(r.pct)) assert.equal(v, 100);
  assert.equal(S.scoreTipi([4, 4, 4]), null);
});

test('Fortune is stable per person per day; streak counts consecutive days', () => {
  assert.deepEqual(S.dailyFortune('a', '2026-10-18'), S.dailyFortune('a', '2026-10-18'));
  assert.equal(S.streak(['2026-10-16', '2026-10-17', '2026-10-18'], '2026-10-18'), 3);
  assert.equal(S.streak(['2026-10-16', '2026-10-17'], '2026-10-18'), 2);
  assert.equal(S.streak(['2026-10-15'], '2026-10-18'), 0);
  assert.equal(S.levelFor(0).name, 'Spark');
});
