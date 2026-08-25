"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.config = void 0;
const dotenv_1 = __importDefault(require("dotenv"));
const path_1 = __importDefault(require("path"));
dotenv_1.default.config();
/**
 * Bootstrap configuration, sourced from environment variables (.env).
 * Anything that end users/admins should change at runtime (folders, PDF engine,
 * template-management password, backup frequency, theme) lives in the `Setting`
 * DB table instead and is served by the Settings module - NOT here.
 * This file only holds values needed *before* the DB is reachable.
 */
exports.config = {
    port: parseInt(process.env.PORT || '4000', 10),
    nodeEnv: process.env.NODE_ENV || 'development',
    jwtSecret: process.env.JWT_SECRET || 'insecure-dev-secret-change-me',
    databaseUrl: process.env.DATABASE_URL || 'file:./data/cadocs.db',
    defaultTemplateFolder: path_1.default.resolve(process.env.TEMPLATE_FOLDER || './storage/templates'),
    defaultGeneratedFolder: path_1.default.resolve(process.env.GENERATED_FOLDER || './storage/generated'),
    defaultBackupFolder: path_1.default.resolve(process.env.BACKUP_FOLDER || './storage/backups'),
    sofficePath: process.env.SOFFICE_PATH || 'soffice',
    defaultAdminPassword: process.env.DEFAULT_ADMIN_PASSWORD || 'ChangeMe123!',
};
//# sourceMappingURL=index.js.map