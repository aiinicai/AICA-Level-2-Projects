// Benchmark harness (Node side). Same workload as tools/benchmark.py in the Python project.
import fs from 'node:fs';
import { postAndStream, postAndCollect } from '../src/server/connectors/tally/http-client.js';
import { streamTallyRecords, type TNode } from '../src/server/connectors/tally/xml-stream.js';
import * as R from '../src/server/connectors/tally/requests.js';
import { mapCompany } from '../src/server/connectors/tally/mappers.js';
import { canonicalPaise } from '../src/server/connectors/tally/values.js';
import { monthEnd, monthsIn } from '../src/shared/periods.js';

const cfg = { tallyAllowedHosts: ['127.0.0.1'], tallyAllowedPorts: [{ from: 1, to: 65535 }] };
const ep = { host: '127.0.0.1', port: Number(process.env.PORT ?? 9000) };
const opts = { timeoutMs: 120000, retries: 0 };
const counts: Record<string, number> = {};
let nodes = 0, amounts = 0, amountSum = 0;
const walk = (n: TNode) => { nodes++; if (n.tag === 'AMOUNT') { amounts++; amountSum += canonicalPaise(n.text); } n.children.forEach(walk); };
const take = (r: TNode) => { counts[r.tag] = (counts[r.tag] ?? 0) + 1; walk(r); };

const mode = process.argv[2] ?? 'live';
const t0 = performance.now();
if (mode === 'live') {
  const to = process.env.TO ?? '2026-09-30', from = process.env.FROM ?? '2024-04-01';
  const comps = (await postAndCollect(cfg, ep, R.companyListRequest(), opts)).filter((r) => r.tag === 'COMPANY').map(mapCompany);
  const company = comps[0].name;
  let requests = 1;
  for (const xml of Object.values(R.masterRequests(company, to, comps[0].booksFrom ?? undefined))) {
    requests++; for await (const r of postAndStream(cfg, ep, xml, opts)) take(r);
  }
  for (const m of monthsIn({ from, to })) {
    requests++; for await (const r of postAndStream(cfg, ep, R.voucherRangeRequest(company, m, monthEnd(m)), opts)) take(r);
  }
  var extra: any = { requests };
} else {
  const files = process.argv.slice(3);
  var extra: any = { files: files.length };
  for (const f of files) for await (const r of streamTallyRecords(fs.createReadStream(f, { highWaterMark: 65536 }))) take(r);
}
const seconds = (performance.now() - t0) / 1000;
console.log(JSON.stringify({ impl: 'node', mode, seconds: +seconds.toFixed(3), peak_rss_mb: +(process.resourceUsage().maxRSS / 1024).toFixed(1), counts, nodes, amounts, amountSum, ...extra }));
