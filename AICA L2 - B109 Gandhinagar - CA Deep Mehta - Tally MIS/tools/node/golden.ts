// Copy tests/golden/golden_requests.json and tools/dump_queries.json next to this file inside the Node project's scripts/ folder first.
// Runs the real Node API routes (read-only demo mode, no sign-in) on XML files and saves every JSON answer.
import fs from 'node:fs';
import path from 'node:path';
import { openDb } from '../src/server/db/connection.js';
import { importXmlFiles, ensureCompany } from '../src/server/ingest/sync-service.js';
import { getConfig } from '../src/server/config.js';
import { buildApp } from '../src/server/app.js';

const [outDir, ...files] = process.argv.slice(2);
const reqs = JSON.parse(fs.readFileSync(new URL('./golden_requests.json', import.meta.url), 'utf8'));
const cfg = { ...getConfig(), storeRawRecords: false, demoMode: true };
const db = openDb(':memory:');
const companyId = ensureCompany(db, 'Demo Trading Co (Sample Data)');
for (const f of files) {
  const r = await importXmlFiles(db, cfg, { companyId, files: [{ name: f, stream: fs.createReadStream(f, { highWaterMark: 65536 }) }] });
  if (r.status !== 'succeeded') throw new Error(r.error);
}
const app = await buildApp(db, cfg, {});
fs.mkdirSync(outDir, { recursive: true });
const times: Record<string, number> = {};
for (const q of reqs) {
  const t0 = performance.now();
  const res = await app.inject({ method: 'GET', url: q.url });
  times[q.name] = Math.round(performance.now() - t0);
  fs.writeFileSync(path.join(outDir, q.name + '.json'), JSON.stringify({ status: res.statusCode, body: res.json() }));
}
fs.writeFileSync(path.join(outDir, '_times.json'), JSON.stringify(times));
console.log('wrote', reqs.length, 'answers; total ms', Object.values(times).reduce((a, b) => a + b, 0));
await app.close();
