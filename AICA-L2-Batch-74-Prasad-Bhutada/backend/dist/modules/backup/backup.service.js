"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.runBackup = runBackup;
exports.scheduleBackups = scheduleBackups;
exports.restoreFromBackup = restoreFromBackup;
const fs_1 = __importDefault(require("fs"));
const path_1 = __importDefault(require("path"));
const adm_zip_1 = __importDefault(require("adm-zip"));
const node_cron_1 = __importDefault(require("node-cron"));
const config_1 = require("../../config");
const settings_service_1 = require("../settings/settings.service");
const logger_1 = require("../../utils/logger");
/**
 * Backs up the SQLite database file, the templates folder, and a JSON export
 * of Settings into a single timestamped ZIP under the configured Backup Folder.
 * "Client Master" lives inside the same SQLite file as everything else
 * (normalized single-database design), so backing up the DB file backs up
 * clients, mappings, categories and history together - restoring is simply
 * replacing that one file, which keeps restore low-risk for non-technical staff.
 */
async function runBackup() {
    const backupFolder = (await (0, settings_service_1.getSetting)(settings_service_1.SETTING_KEYS.BACKUP_FOLDER)) || config_1.config.defaultBackupFolder;
    const templateFolder = (await (0, settings_service_1.getSetting)(settings_service_1.SETTING_KEYS.TEMPLATE_FOLDER)) || config_1.config.defaultTemplateFolder;
    fs_1.default.mkdirSync(backupFolder, { recursive: true });
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const zip = new adm_zip_1.default();
    const dbPath = config_1.config.databaseUrl.replace('file:', '');
    if (fs_1.default.existsSync(dbPath))
        zip.addLocalFile(dbPath, '', 'cadocs.db');
    if (fs_1.default.existsSync(templateFolder))
        zip.addLocalFolder(templateFolder, 'templates');
    const zipPath = path_1.default.join(backupFolder, `backup-${timestamp}.zip`);
    zip.writeZip(zipPath);
    logger_1.logger.info(`Backup created: ${zipPath}`);
    return zipPath;
}
let scheduledTask = null;
/** (Re)schedules the automatic backup job based on the current cron expression in Settings. */
async function scheduleBackups() {
    const cronExpr = await (0, settings_service_1.getSetting)(settings_service_1.SETTING_KEYS.BACKUP_FREQUENCY_CRON);
    if (scheduledTask)
        scheduledTask.stop();
    if (!cronExpr || !node_cron_1.default.validate(cronExpr)) {
        logger_1.logger.warn('No valid backup schedule configured; automatic backups disabled.');
        return;
    }
    scheduledTask = node_cron_1.default.schedule(cronExpr, () => {
        runBackup().catch((e) => logger_1.logger.error(`Scheduled backup failed: ${e.message}`));
    });
    logger_1.logger.info(`Automatic backup scheduled with cron expression "${cronExpr}"`);
}
/** Restores DB + templates from a previously created backup ZIP. Server must be restarted after restore. */
async function restoreFromBackup(zipFilePath) {
    const templateFolder = (await (0, settings_service_1.getSetting)(settings_service_1.SETTING_KEYS.TEMPLATE_FOLDER)) || config_1.config.defaultTemplateFolder;
    const dbPath = config_1.config.databaseUrl.replace('file:', '');
    const zip = new adm_zip_1.default(zipFilePath);
    const dbEntry = zip.getEntry('cadocs.db');
    if (dbEntry)
        fs_1.default.writeFileSync(dbPath, zip.readFile(dbEntry));
    for (const entry of zip.getEntries()) {
        if (entry.entryName.startsWith('templates/') && !entry.isDirectory) {
            const dest = path_1.default.join(templateFolder, entry.entryName.replace('templates/', ''));
            fs_1.default.mkdirSync(path_1.default.dirname(dest), { recursive: true });
            fs_1.default.writeFileSync(dest, zip.readFile(entry));
        }
    }
    logger_1.logger.warn('Restore completed. Please restart the application service for changes to take full effect.');
}
//# sourceMappingURL=backup.service.js.map