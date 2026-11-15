/**
 * Imports districts/cities from a CSV exported from the official Local Government Directory (lgdirectory.gov.in).
 * CSV columns: state_code,district,city   (state_code must match shared/src/geo/states.ts, e.g. PB)
 *   GOOGLE_CLOUD_PROJECT=... npx tsx scripts/seed-geo.ts data/districts.csv
 */
import { readFileSync } from 'node:fs';
import { initializeApp } from 'firebase-admin/app';
import { getFirestore } from 'firebase-admin/firestore';
import { isValidStateCode } from '../shared/src/geo/states.js';

const file = process.argv[2];
if (!file) { console.error('Usage: seed-geo.ts <csv>'); process.exit(1); }
initializeApp();
const db = getFirestore();
const byDistrict = new Map<string, { stateCode: string; district: string; cities: Set<string> }>();
let bad = 0;
for (const line of readFileSync(file, 'utf8').split(/\r?\n/).slice(1)) {
  const [stateCode, district, city] = line.split(',').map((s) => s?.trim() ?? '');
  if (!stateCode || !district || !isValidStateCode(stateCode)) { if (line.trim()) bad++; continue; }
  const id = `${stateCode}_${district.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`;
  const e = byDistrict.get(id) ?? { stateCode, district, cities: new Set<string>() };
  if (city) e.cities.add(city);
  byDistrict.set(id, e);
}
let batch = db.batch(); let n = 0;
for (const [id, e] of byDistrict) {
  batch.set(db.doc(`geo_districts/${id}`), { stateCode: e.stateCode, district: e.district, cities: [...e.cities].sort(), status: 'approved' });
  if (++n % 400 === 0) { await batch.commit(); batch = db.batch(); }
}
await batch.commit();
console.log(`Imported ${byDistrict.size} districts. Skipped ${bad} invalid rows.`);
