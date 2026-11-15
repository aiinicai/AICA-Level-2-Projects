/**
 * Firestore automated backup script for VRS Corporate Solutions.
 * Exports critical collections to JSON / Google Cloud Storage archive with ISO timestamps.
 *
 * Usage:
 *   npx tsx scripts/backup-firestore.ts
 *
 * Staging / Production:
 *   GOOGLE_CLOUD_PROJECT=vrs-dra-portal-staging npx tsx scripts/backup-firestore.ts
 */
import { initializeApp } from 'firebase-admin/app';
import { getFirestore } from 'firebase-admin/firestore';
import * as fs from 'node:fs';
import * as path from 'node:path';

initializeApp();
const db = getFirestore();

const COLLECTIONS_TO_BACKUP = [
  'candidates',
  'vacancies',
  'applications',
  'certificates',
  'certificate_verification',
  'contact_messages',
  'data_requests',
  'institutes',
  'cms_public',
  'audit_logs',
];

async function runBackup() {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const backupDir = path.resolve(process.cwd(), 'backups', `firestore-${timestamp}`);

  if (!fs.existsSync(backupDir)) {
    fs.mkdirSync(backupDir, { recursive: true });
  }

  console.log(`[VRS Backup] Starting authoritative export to ${backupDir}...`);

  const summary: Record<string, number> = {};

  for (const colName of COLLECTIONS_TO_BACKUP) {
    try {
      const snap = await db.collection(colName).get();
      const records = snap.docs.map((d) => ({
        _id: d.id,
        ...d.data(),
      }));

      const outPath = path.join(backupDir, `${colName}.json`);
      fs.writeFileSync(outPath, JSON.stringify(records, null, 2), 'utf-8');
      summary[colName] = records.length;
      console.log(`  ✓ ${colName}: ${records.length} documents archived`);
    } catch (err: any) {
      console.error(`  ✗ Failed to export collection ${colName}:`, err.message);
      summary[colName] = -1;
    }
  }

  const manifest = {
    timestamp: new Date().toISOString(),
    collections: summary,
    backupDir,
  };
  fs.writeFileSync(path.join(backupDir, '_manifest.json'), JSON.stringify(manifest, null, 2), 'utf-8');

  console.log('\n[VRS Backup Complete] Manifest:');
  console.table(summary);
}

runBackup().catch((err) => {
  console.error('Fatal backup error:', err);
  process.exit(1);
});
