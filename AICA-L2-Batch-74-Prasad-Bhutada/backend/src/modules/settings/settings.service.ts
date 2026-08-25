import { prisma } from '../../db/prisma';
import { config } from '../../config';
import bcrypt from 'bcryptjs';
import fs from 'fs';

/**
 * All admin-configurable values live here, backed by the `Setting` table.
 * Defaults are seeded on first run from environment variables so the app
 * works out-of-the-box, but every value can subsequently be changed from
 * the Settings screen with zero code/deploy changes.
 */
export const SETTING_KEYS = {
  TEMPLATE_FOLDER: 'templateFolder',
  GENERATED_FOLDER: 'generatedFolder',
  BACKUP_FOLDER: 'backupFolder',
  PDF_ENGINE: 'pdfEngine', // 'libreoffice' (only supported engine today, pluggable)
  TEMPLATE_PASSWORD_HASH: 'templatePasswordHash',
  BACKUP_FREQUENCY_CRON: 'backupFrequencyCron', // e.g. "0 21 * * *" = 9 PM daily
  DEFAULT_THEME: 'defaultTheme', // 'light' | 'dark'
  EXCEL_EXPORT_LOCATION: 'excelExportLocation',
} as const;

export async function ensureDefaultSettings() {
  const defaults: Record<string, string> = {
    [SETTING_KEYS.TEMPLATE_FOLDER]: config.defaultTemplateFolder,
    [SETTING_KEYS.GENERATED_FOLDER]: config.defaultGeneratedFolder,
    [SETTING_KEYS.BACKUP_FOLDER]: config.defaultBackupFolder,
    [SETTING_KEYS.PDF_ENGINE]: 'libreoffice',
    [SETTING_KEYS.BACKUP_FREQUENCY_CRON]: '0 21 * * *',
    [SETTING_KEYS.DEFAULT_THEME]: 'light',
    [SETTING_KEYS.EXCEL_EXPORT_LOCATION]: config.defaultGeneratedFolder,
  };

  for (const [key, value] of Object.entries(defaults)) {
    const existing = await prisma.setting.findUnique({ where: { key } });
    if (!existing) {
      await prisma.setting.create({ data: { key, value } });
    }
  }

  // Seed template-management password on first run only.
  const passwordSetting = await prisma.setting.findUnique({
    where: { key: SETTING_KEYS.TEMPLATE_PASSWORD_HASH },
  });
  if (!passwordSetting) {
    const hash = await bcrypt.hash(config.defaultAdminPassword, 10);
    await prisma.setting.create({
      data: { key: SETTING_KEYS.TEMPLATE_PASSWORD_HASH, value: hash },
    });
  }

  for (const dir of [
    await getSetting(SETTING_KEYS.TEMPLATE_FOLDER),
    await getSetting(SETTING_KEYS.GENERATED_FOLDER),
    await getSetting(SETTING_KEYS.BACKUP_FOLDER),
  ]) {
    if (dir && !fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  }
}

export async function getSetting(key: string): Promise<string | null> {
  const row = await prisma.setting.findUnique({ where: { key } });
  return row?.value ?? null;
}

export async function getAllSettings(): Promise<Record<string, string>> {
  const rows = await prisma.setting.findMany();
  const result: Record<string, string> = {};
  for (const r of rows) {
    // Never expose the password hash to the client
    if (r.key === SETTING_KEYS.TEMPLATE_PASSWORD_HASH) continue;
    result[r.key] = r.value;
  }
  return result;
}

export async function updateSetting(key: string, value: string) {
  await prisma.setting.upsert({
    where: { key },
    update: { value },
    create: { key, value },
  });
}

export async function verifyTemplatePassword(candidate: string): Promise<boolean> {
  const hash = await getSetting(SETTING_KEYS.TEMPLATE_PASSWORD_HASH);
  if (!hash) return false;
  return bcrypt.compare(candidate, hash);
}

export async function setTemplatePassword(newPassword: string) {
  const hash = await bcrypt.hash(newPassword, 10);
  await updateSetting(SETTING_KEYS.TEMPLATE_PASSWORD_HASH, hash);
}
