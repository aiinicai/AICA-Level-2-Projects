"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.SETTING_KEYS = void 0;
exports.ensureDefaultSettings = ensureDefaultSettings;
exports.getSetting = getSetting;
exports.getAllSettings = getAllSettings;
exports.updateSetting = updateSetting;
exports.verifyTemplatePassword = verifyTemplatePassword;
exports.setTemplatePassword = setTemplatePassword;
const prisma_1 = require("../../db/prisma");
const config_1 = require("../../config");
const bcryptjs_1 = __importDefault(require("bcryptjs"));
const fs_1 = __importDefault(require("fs"));
/**
 * All admin-configurable values live here, backed by the `Setting` table.
 * Defaults are seeded on first run from environment variables so the app
 * works out-of-the-box, but every value can subsequently be changed from
 * the Settings screen with zero code/deploy changes.
 */
exports.SETTING_KEYS = {
    TEMPLATE_FOLDER: 'templateFolder',
    GENERATED_FOLDER: 'generatedFolder',
    BACKUP_FOLDER: 'backupFolder',
    PDF_ENGINE: 'pdfEngine', // 'libreoffice' (only supported engine today, pluggable)
    TEMPLATE_PASSWORD_HASH: 'templatePasswordHash',
    BACKUP_FREQUENCY_CRON: 'backupFrequencyCron', // e.g. "0 21 * * *" = 9 PM daily
    DEFAULT_THEME: 'defaultTheme', // 'light' | 'dark'
    EXCEL_EXPORT_LOCATION: 'excelExportLocation',
};
async function ensureDefaultSettings() {
    const defaults = {
        [exports.SETTING_KEYS.TEMPLATE_FOLDER]: config_1.config.defaultTemplateFolder,
        [exports.SETTING_KEYS.GENERATED_FOLDER]: config_1.config.defaultGeneratedFolder,
        [exports.SETTING_KEYS.BACKUP_FOLDER]: config_1.config.defaultBackupFolder,
        [exports.SETTING_KEYS.PDF_ENGINE]: 'libreoffice',
        [exports.SETTING_KEYS.BACKUP_FREQUENCY_CRON]: '0 21 * * *',
        [exports.SETTING_KEYS.DEFAULT_THEME]: 'light',
        [exports.SETTING_KEYS.EXCEL_EXPORT_LOCATION]: config_1.config.defaultGeneratedFolder,
    };
    for (const [key, value] of Object.entries(defaults)) {
        const existing = await prisma_1.prisma.setting.findUnique({ where: { key } });
        if (!existing) {
            await prisma_1.prisma.setting.create({ data: { key, value } });
        }
    }
    // Seed template-management password on first run only.
    const passwordSetting = await prisma_1.prisma.setting.findUnique({
        where: { key: exports.SETTING_KEYS.TEMPLATE_PASSWORD_HASH },
    });
    if (!passwordSetting) {
        const hash = await bcryptjs_1.default.hash(config_1.config.defaultAdminPassword, 10);
        await prisma_1.prisma.setting.create({
            data: { key: exports.SETTING_KEYS.TEMPLATE_PASSWORD_HASH, value: hash },
        });
    }
    for (const dir of [
        await getSetting(exports.SETTING_KEYS.TEMPLATE_FOLDER),
        await getSetting(exports.SETTING_KEYS.GENERATED_FOLDER),
        await getSetting(exports.SETTING_KEYS.BACKUP_FOLDER),
    ]) {
        if (dir && !fs_1.default.existsSync(dir))
            fs_1.default.mkdirSync(dir, { recursive: true });
    }
}
async function getSetting(key) {
    const row = await prisma_1.prisma.setting.findUnique({ where: { key } });
    return row?.value ?? null;
}
async function getAllSettings() {
    const rows = await prisma_1.prisma.setting.findMany();
    const result = {};
    for (const r of rows) {
        // Never expose the password hash to the client
        if (r.key === exports.SETTING_KEYS.TEMPLATE_PASSWORD_HASH)
            continue;
        result[r.key] = r.value;
    }
    return result;
}
async function updateSetting(key, value) {
    await prisma_1.prisma.setting.upsert({
        where: { key },
        update: { value },
        create: { key, value },
    });
}
async function verifyTemplatePassword(candidate) {
    const hash = await getSetting(exports.SETTING_KEYS.TEMPLATE_PASSWORD_HASH);
    if (!hash)
        return false;
    return bcryptjs_1.default.compare(candidate, hash);
}
async function setTemplatePassword(newPassword) {
    const hash = await bcryptjs_1.default.hash(newPassword, 10);
    await updateSetting(exports.SETTING_KEYS.TEMPLATE_PASSWORD_HASH, hash);
}
//# sourceMappingURL=settings.service.js.map