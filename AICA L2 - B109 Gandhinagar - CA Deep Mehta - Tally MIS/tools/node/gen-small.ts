import fs from 'node:fs';
import { DemoBooks } from '../src/server/demo/generator.js';
import { monthEnd, monthsIn } from '../src/shared/periods.js';
const out = process.argv[2]; fs.mkdirSync(out, { recursive: true });
const books = new DemoBooks({ from: '2024-04-01', to: '2026-09-30' });
fs.writeFileSync(`${out}/01-masters.xml`, books.mastersXml('2026-09-30'));
fs.writeFileSync(`${out}/02-daybook.xml`, books.dayBookXml('2024-04-01', '2026-09-30'));
let i = 3;
for (const m of monthsIn({ from: '2024-04-01', to: '2026-09-30' })) fs.writeFileSync(`${out}/${String(i++).padStart(2, '0')}-stockval-${monthEnd(m)}.xml`, books.stockValuationXml(monthEnd(m)));
