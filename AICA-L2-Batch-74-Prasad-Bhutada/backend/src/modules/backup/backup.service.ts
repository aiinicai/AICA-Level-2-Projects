import fs from 'fs';
import path from 'path';
import AdmZip from 'adm-zip';
import cron from 'node-cron';
import { config } from '../../config';
import { getSetting, SETTING_KEYS } from '../settings/settings.service';
import { logger } from '../../utils/logger';

/**
 * Backs up the SQLite database file, the templates folder, and a JSON export
 * of Settings into a single timestamped ZIP under the configured Backup Folder.
 * "Client Master" lives inside the same SQLite file as everything else
 * (normalized single-database design), so backing up the DB file backs up
 * clients, mappings, categories and history together - restoring is simply
 * replacing that one file, which keeps restore low-risk for non-technical staff.
 */
export async function runBackup(): Promise<string> {
  const backupFolder = (await getSetting(SETTING_KEYS.BACKUP_FOLDER)) || config.defaultBackupFolder;
  const templateFolder = (await getSetting(SETTING_KEYS.TEMPLATE_FOLDER)) || config.defaultTemplateFolder;
  fs.mkdirSync(backupFolder, { recursive: true });

  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const zip = new AdmZip();

  const dbPath = config.databaseUrl.replace('file:', '');
  if (fs.existsSync(dbPath)) zip.addLocalFile(dbPath, '', 'cadocs.db');
  if (fs.existsSync(templateFolder)) zip.addLocalFolder(templateFolder, 'templates');

  const zipPath = path.join(backupFolder, `backup-${timestamp}.zip`);
  zip.writeZip(zipPath);
  logger.info(`Backup created: ${zipPath}`);
  return zipPath;
}

let scheduledTask: cron.ScheduledTask | null = null;

/** (Re)schedules the automatic backup job based on the current cron expression in Settings. */
export async function scheduleBackups() {
  const cronExpr = await getSetting(SETTING_KEYS.BACKUP_FREQUENCY_CRON);
  if (scheduledTask) scheduledTask.stop();
  if (!cronExpr || !cron.validate(cronExpr)) {
    logger.warn('No valid backup schedule configured; automatic backups disabled.');
    return;
  }
  scheduledTask = cron.schedule(cronExpr, () => {
    runBackup().catch((e) => logger.error(`Scheduled backup failed: ${e.message}`));
  });
  logger.info(`Automatic backup scheduled with cron expression "${cronExpr}"`);
}

/** Restores DB + templates from a previously created backup ZIP. Server must be restarted after restore. */
export async function restoreFromBackup(zipFilePath: string) {
  const templateFolder = (await getSetting(SETTING_KEYS.TEMPLATE_FOLDER)) || config.defaultTemplateFolder;
  const dbPath = config.databaseUrl.replace('file:', '');

  const zip = new AdmZip(zipFilePath);
  const dbEntry = zip.getEntry('cadocs.db');
  if (dbEntry) fs.writeFileSync(dbPath, zip.readFile(dbEntry) as Buffer);

  for (const entry of zip.getEntries()) {
    if (entry.entryName.startsWith('templates/') && !entry.isDirectory) {
      const dest = path.join(templateFolder, entry.entryName.replace('templates/', ''));
      fs.mkdirSync(path.dirname(dest), { recursive: true });
      fs.writeFileSync(dest, zip.readFile(entry) as Buffer);
    }
  }
  logger.warn('Restore completed. Please restart the application service for changes to take full effect.');
}
