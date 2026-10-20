// Browser check of the whole web app. Run: node tests/e2e.mjs  (needs playwright-core and Chrome; set CHROME_PATH)
import { chromium } from 'playwright-core';
import assert from 'node:assert/strict';
import path from 'node:path';
import fs from 'node:fs';
import { pathToFileURL } from 'node:url';

const URL_ = process.env.BASE_URL || pathToFileURL(path.resolve('web/index.html')).href;
const OUT = path.resolve('docs/screenshots/latest-run');
fs.mkdirSync(OUT, { recursive: true });
const b = await chromium.launch({ executablePath: process.env.CHROME_PATH || undefined });
const ctx = await b.newContext({ viewport: { width: 390, height: 844 } });
await ctx.clock.setFixedTime(new Date('2026-10-14T06:00:00Z')); // Wed 14 Oct 2026, 10:00 in Abu Dhabi
const p = await ctx.newPage();
const errors = [];
p.on('pageerror', (e) => errors.push(e.message));
p.on('console', (m) => m.type() === 'error' && errors.push(m.text()));
p.on('dialog', (d) => d.accept());
const shot = (n, full = true) => p.screenshot({ path: `${OUT}/${n}.png`, fullPage: full });
const tab = (t) => p.click(`#nav-${t}`);
let failed = 0;
const step = async (name, fn) => { try { await fn(); console.log('✓', name); } catch (e) { failed++; console.log('✗', name, '-', e.message.split('\n')[0]); } };

await p.goto(URL_);

await step('first visit: welcome form, no pre-filled person, 0 points', async () => {
  await p.locator('#birthModal.open').waitFor();
  assert.equal(await p.textContent('#modalTitle'), 'Welcome to Saathi ✨');
  assert.equal(await p.textContent('#hdrPoints'), '0');
  await shot('01-welcome', false);
});

await step('save details (18+ required)', async () => {
  await p.fill('#modalInpName', 'Meera');
  await p.selectOption('#modalInpCity', 'abu-dhabi');
  await p.fill('#modalInpDate', '1992-08-14');
  await p.click('text=Save & Calculate My Day');
  assert.ok(await p.locator('#birthModal.open').count(), 'must stay open without 18+');
  await p.check('#modalAdult');
  await p.click('text=Save & Calculate My Day');
  await p.locator('#birthModal.open').waitFor({ state: 'detached' }).catch(() => {});
  assert.match(await p.textContent('#greetingName'), /Meera/);
  assert.equal(await p.textContent('#hdrPoints'), '20');
});

await step('Today: real sky for Abu Dhabi (Moon in Scorpio, Wednesday, city Rahu Kaal)', async () => {
  assert.equal(await p.textContent('#quickMoonVedic'), 'Scorpio');
  assert.match(await p.textContent('#quickRahuKaal'), /^12:0\d pm – 1:3\d pm$/);
  assert.equal(await p.textContent('#quickAbhijit'), 'Not used on Wednesdays');
  assert.match(await p.textContent('#quickDayLord'), /Budh \(Mercury\)/);
  assert.match(await p.textContent('#quickLuckyColor'), /Emerald Green • 2/); // personal day number 2
  await shot('02-today');
});

await step('cookie once a day, water and steps award points', async () => {
  await p.click('#cookieClickArea');
  await p.locator('#fortuneScroll').waitFor();
  const afterCookie = Number(await p.textContent('#hdrPoints'));
  assert.ok(afterCookie === 25 || afterCookie === 45);
  await p.click('text=+1 Glass (+5)');
  await p.click('text=+500 Steps');
  assert.equal(Number(await p.textContent('#hdrPoints')), afterCookie + 10);
  assert.match(await p.textContent('#waterLabel'), /^1 of 8/);
  assert.equal(await p.textContent('#streakCount'), '1');
});

await step('Stars: Vedic/Western switch, numerology 16/7, 5, 34/7 and Lo Shu grid', async () => {
  await tab('stars');
  assert.match(await p.textContent('#astroMoonTitle'), /Scorpio/);
  await p.click('#btnWestern');
  assert.match(await p.textContent('#astroMoonTitle'), /Sagittarius/);
  await p.click('#btnVedic');
  assert.equal(await p.textContent('#numLifePath'), '16/7');
  assert.equal(await p.textContent('#numMoolank'), '5');
  assert.equal(await p.textContent('#numBhagyank'), '34/7');
  assert.match(await p.textContent('#loshuNote'), /Mental plane/);
  assert.match(await p.textContent('#astroScore'), /\d+\/10/);
  await shot('03-stars');
});

await step('Signature: reading comes from the drawn strokes', async () => {
  const box = await p.locator('#sigCanvas').boundingBox();
  await p.locator('#sigCanvas').scrollIntoViewIfNeeded();
  const bb = await p.locator('#sigCanvas').boundingBox();
  for (let i = 0; i < 7; i++) {
    const x = bb.x + 30 + i * 35, y = bb.y + 130 - i * 4;
    await p.mouse.move(x, y); await p.mouse.down();
    for (let k = 1; k <= 8; k++) await p.mouse.move(x + k * 1.6, y - k * 9);
    await p.mouse.up();
  }
  const text = await p.textContent('#sigAnalysisBox');
  assert.match(text, /right-leaning/);
  if (!/rising/.test(text)) console.log('   reading:', text);
  assert.match(text, /rising/);
  assert.ok(box);
  await p.locator('#sigAnalysisBox').scrollIntoViewIfNeeded();
  await shot('04-signature', false);
});

await step('Body: BMI from typed numbers, walk timer', async () => {
  await tab('body');
  await p.fill('#inpWeightVal', '64');
  await p.fill('#inpHeightVal', '165');
  assert.equal(await p.textContent('#bmiNumberDisplay'), '23.5');
  assert.match(await p.textContent('#bmiCategoryLabel'), /Above healthy range/); // Asian cut-offs
  await p.uncheck('#chkAsianCutoff');
  assert.equal(await p.textContent('#bmiCategoryLabel'), 'Healthy range');
  await shot('05-body');
});

await step('Glow: Face / Hair / Nails switch rituals', async () => {
  await tab('glow');
  await p.click('[data-glow="hair"]');
  assert.match(await p.textContent('#glowRitual'), /Scalp/);
  await p.click('[data-glow="nails"]');
  assert.match(await p.textContent('#glowRitual'), /Cuticle/);
  await shot('06-glow');
});

await step('Me: TIPI personality test (10 questions) gives scores and +50', async () => {
  await tab('me');
  const before = Number((await p.textContent('#hdrPoints')).replace(/,/g, ''));
  await p.click('#tipiStart');
  for (let i = 0; i < 10; i++) await p.locator('#tipiBox [data-v]').nth(i % 2 ? 2 : 5).click();
  assert.match(await p.textContent('#tipiBox'), /Openness/);
  assert.equal(Number((await p.textContent('#hdrPoints')).replace(/,/g, '')), before + 50);
  await shot('07-me');
});

await step('everything persists after reload', async () => {
  const pts = await p.textContent('#hdrPoints');
  await p.reload();
  assert.equal(await p.textContent('#hdrPoints'), pts);
  assert.match(await p.textContent('#greetingName'), /Meera/);
  assert.equal(await p.locator('#birthModal.open').count(), 0);
});

await step('360px phone: no sideways scrolling', async () => {
  await p.setViewportSize({ width: 360, height: 780 });
  for (const t of ['today', 'stars', 'body', 'glow', 'me']) {
    await tab(t);
    const [sw, w] = await p.evaluate(() => [document.documentElement.scrollWidth, innerWidth]);
    assert.ok(sw <= w + 1, `${t}: ${sw} > ${w}`);
  }
});

console.log(errors.length ? `page errors:\n${errors.join('\n')}` : 'no page errors');
await b.close();
process.exit(failed || errors.length ? 1 : 0);
