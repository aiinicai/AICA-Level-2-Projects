// Loads XML files through the Node importer into an in-memory DB and dumps comparable figures (Phase 2 check).
import fs from 'node:fs';
import { openDb } from '../src/server/db/connection.js';
import { importXmlFiles, ensureCompany } from '../src/server/ingest/sync-service.js';
import { getConfig } from '../src/server/config.js';

const queries = JSON.parse(fs.readFileSync(new URL('./dump_queries.json', import.meta.url), 'utf8'));
const files = process.argv.slice(2);
const cfg = { ...getConfig(), storeRawRecords: false };
const db = openDb(':memory:');
const companyId = ensureCompany(db, 'Demo Trading Co (Sample Data)');
const t0 = performance.now();
const results: any = {};
for (const f of files) {
  const r = await importXmlFiles(db, cfg, { companyId, files: [{ name: f, stream: fs.createReadStream(f, { highWaterMark: 65536 }) }] });
  if (r.status !== 'succeeded') throw new Error(r.error);
}
const seconds = (performance.now() - t0) / 1000;
const out: any = { impl: 'node', seconds: +seconds.toFixed(3), peak_rss_mb: +(process.resourceUsage().maxRSS / 1024).toFixed(1), counts: {}, sums: {}, groups: {} };
for (const [k, sql] of Object.entries<string>(queries.counts)) out.counts[k] = Number((db.get<any>(sql))!.v);
for (const [k, sql] of Object.entries<string>(queries.sums)) out.sums[k] = Number((db.get<any>(sql))!.v);
for (const [k, sql] of Object.entries<string>(queries.groups)) out.groups[k] = Object.fromEntries(db.all<any>(sql).map((r) => [String(r.k), Number(r.v)]));
fs.writeFileSync(process.env.OUT ?? 'node_dump.json', JSON.stringify(out));
console.log(JSON.stringify({ impl: 'node', seconds: out.seconds, peak_rss_mb: out.peak_rss_mb, vouchers: out.counts.vouchers }));
