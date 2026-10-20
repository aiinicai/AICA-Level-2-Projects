// Entry point for `npm run samples`: generates every file in /sample-data, writes README.md and
// expected-results.json, then runs verify.mjs. Deterministic: no Math.random, no current date.
import { rm, mkdir, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, join, resolve } from 'node:path';
import { generateBank } from './bank.mjs';
import { generateAr } from './ar.mjs';
import { generateAp } from './ap.mjs';
import { generateHrPayroll, generateIntercompany } from './general.mjs';
import { generateTools } from './tools.mjs';
import { buildReadme } from './readme.mjs';
import { runVerify } from './verify.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const OUT = resolve(HERE, '..', '..', 'sample-data');

const aed = (c) => Math.round(c) / 100;
function toJson(r) {
  const o = { files: r.files, rowsA: r.rowsA, rowsB: r.rowsB, tiers: r.tiers };
  if (r.opening != null) Object.assign(o, { opening: aed(r.opening), closeA: aed(r.closeA), closeB: aed(r.closeB) });
  if (r.statement) o.statement = r.statement.map(([line, v]) => ({ line, amount: aed(v) }));
  if (r.countStatement) o.countStatement = r.countStatement.map(([line, v]) => ({ line, count: v }));
  if (r.groups) o.smartReconGroups = r.groups;
  o.planted = r.planted; // amounts inside 'planted' are integer cents
  o.plantedAmountUnit = 'integer cents';
  o.scenarios = r.scenarios.map((s) => ({ scenario: s.s, detail: s.d, expected: s.e }));
  return o;
}

async function main() {
  for (const sub of ['bank', 'ar', 'ap', 'general', 'tools']) {
    await rm(join(OUT, sub), { recursive: true, force: true });
    await mkdir(join(OUT, sub), { recursive: true });
  }
  console.log('Generating sample data into', OUT);
  const bank = await generateBank(OUT);
  console.log(`  bank/     ${bank.rowsA} bank lines, ${bank.rowsB} GL lines`);
  const ar = await generateAr(OUT);
  console.log(`  ar/       ${ar.rowsA} ours, ${ar.rowsB} theirs`);
  const ap = await generateAp(OUT);
  console.log(`  ap/       ${ap.rowsA} ours, ${ap.rowsB} theirs`);
  const hr = await generateHrPayroll(OUT);
  const ic = await generateIntercompany(OUT);
  console.log(`  general/  HR ${hr.rowsA} vs WPS ${hr.rowsB}; IC A ${ic.rowsA} vs B ${ic.rowsB}`);
  const tools = await generateTools(OUT);
  console.log('  tools/    11 files');

  const expected = { generatedBy: 'scripts/generate-samples/index.mjs', amountsIn: 'AED', bank: toJson(bank), ar: toJson(ar), ap: toJson(ap), hr: toJson(hr), intercompany: toJson(ic), tools };
  await writeFile(join(OUT, 'expected-results.json'), JSON.stringify(expected, null, 2) + '\n');
  await writeFile(join(OUT, 'README.md'), buildReadme({ bank, ar, ap, hr, ic, tools }));
  console.log('  README.md and expected-results.json written\n');

  const ok = await runVerify(OUT);
  if (!ok) process.exitCode = 1;
}

main().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
