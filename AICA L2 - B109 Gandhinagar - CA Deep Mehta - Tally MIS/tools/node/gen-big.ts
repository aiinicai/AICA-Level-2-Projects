import fs from 'node:fs';
import { DemoBooks } from '../src/server/demo/generator.js';
const out = process.argv[2]; fs.mkdirSync(out, { recursive: true });
const books = new DemoBooks({ from: '2010-04-01', to: '2026-09-30' });
fs.writeFileSync(`${out}/masters.xml`, books.mastersXml('2026-09-30'));
for (let y = 2010; y <= 2026; y++) fs.writeFileSync(`${out}/daybook-${y}.xml`, books.dayBookXml(`${y}-01-01`, `${y}-12-31`));
