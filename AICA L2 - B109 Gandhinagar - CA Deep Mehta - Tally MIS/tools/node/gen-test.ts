import fs from 'node:fs';
import { DemoBooks } from '../src/server/demo/generator.js';
const out = process.argv[2]; fs.mkdirSync(out, { recursive: true });
const books = new DemoBooks({ from: '2024-04-01', to: '2024-06-30' });
fs.writeFileSync(`${out}/masters.xml`, books.mastersXml('2024-06-30'));
fs.writeFileSync(`${out}/daybook-2024-04.xml`, books.dayBookXml('2024-04-01', '2024-04-30'));
fs.writeFileSync(`${out}/daybook-2024-05.xml`, books.dayBookXml('2024-05-01', '2024-05-31'));
