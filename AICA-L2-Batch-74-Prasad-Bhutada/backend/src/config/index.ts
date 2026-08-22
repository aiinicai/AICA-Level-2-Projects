import dotenv from 'dotenv';
import path from 'path';

dotenv.config();

/**
 * Bootstrap configuration, sourced from environment variables (.env).
 * Anything that end users/admins should change at runtime (folders, PDF engine,
 * template-management password, backup frequency, theme) lives in the `Setting`
 * DB table instead and is served by the Settings module - NOT here.
 * This file only holds values needed *before* the DB is reachable.
 */
export const config = {
  port: parseInt(process.env.PORT || '4000', 10),
  nodeEnv: process.env.NODE_ENV || 'development',
  jwtSecret: process.env.JWT_SECRET || 'insecure-dev-secret-change-me',
  databaseUrl: process.env.DATABASE_URL || 'file:./data/cadocs.db',

  defaultTemplateFolder: path.resolve(process.env.TEMPLATE_FOLDER || './storage/templates'),
  defaultGeneratedFolder: path.resolve(process.env.GENERATED_FOLDER || './storage/generated'),
  defaultBackupFolder: path.resolve(process.env.BACKUP_FOLDER || './storage/backups'),

  sofficePath: process.env.SOFFICE_PATH || 'soffice',
  defaultAdminPassword: process.env.DEFAULT_ADMIN_PASSWORD || 'ChangeMe123!',
};
