"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = __importDefault(require("express"));
const cors_1 = __importDefault(require("cors"));
const helmet_1 = __importDefault(require("helmet"));
const morgan_1 = __importDefault(require("morgan"));
const path_1 = __importDefault(require("path"));
const fs_1 = __importDefault(require("fs"));
const config_1 = require("./config");
const logger_1 = require("./utils/logger");
const errorHandler_1 = require("./middleware/errorHandler");
const settings_service_1 = require("./modules/settings/settings.service");
const backup_service_1 = require("./modules/backup/backup.service");
const templates_routes_1 = __importDefault(require("./modules/templates/templates.routes"));
const mapping_routes_1 = __importDefault(require("./modules/templates/mapping.routes"));
const categories_routes_1 = __importDefault(require("./modules/categories/categories.routes"));
const clients_routes_1 = __importDefault(require("./modules/clients/clients.routes"));
const generation_routes_1 = __importDefault(require("./modules/generation/generation.routes"));
const history_routes_1 = __importDefault(require("./modules/history/history.routes"));
const settings_routes_1 = __importDefault(require("./modules/settings/settings.routes"));
const backup_routes_1 = __importDefault(require("./modules/backup/backup.routes"));
async function bootstrap() {
    await (0, settings_service_1.ensureDefaultSettings)();
    await (0, backup_service_1.scheduleBackups)();
    const app = (0, express_1.default)();
    app.use((0, helmet_1.default)({ contentSecurityPolicy: false })); // CSP disabled: this serves our own bundled frontend, not third-party content
    app.use((0, cors_1.default)()); // kept permissive for LAN deployment flexibility (e.g. accessing the API directly from another PC)
    app.use(express_1.default.json({ limit: '5mb' }));
    app.use((0, morgan_1.default)('combined', {
        stream: { write: (message) => logger_1.logger.info(message.trim()) },
    }));
    app.get('/api/health', (_req, res) => res.json({ success: true, status: 'ok' }));
    app.use('/api/templates', templates_routes_1.default);
    app.use('/api/placeholder-mappings', mapping_routes_1.default);
    app.use('/api/categories', categories_routes_1.default);
    app.use('/api/clients', clients_routes_1.default);
    app.use('/api/generation', generation_routes_1.default);
    app.use('/api/history', history_routes_1.default);
    app.use('/api/settings', settings_routes_1.default);
    app.use('/api/backup', backup_routes_1.default);
    // --- Serve the built frontend from this SAME process/port -----------------
    // This is the whole point: one program to run, one address to open, no
    // separate frontend server and no "which URL does the frontend call"
    // configuration to get wrong. `setup.bat` copies the frontend's production
    // build into backend/public before first run. Since the frontend is served
    // from the same origin as the API, it always calls relative "/api/..." with
    // zero configuration - the class of bug where the frontend can't find the
    // backend simply can't happen with this layout.
    const publicDir = path_1.default.join(__dirname, '..', 'public');
    if (fs_1.default.existsSync(publicDir)) {
        app.use(express_1.default.static(publicDir));
        // SPA fallback: any non-API GET request that isn't a real static file
        // gets index.html, so React Router's client-side routes (e.g. /clients,
        // /history) work correctly on a full page load/refresh, not just when
        // navigated to from within the app.
        app.get(/^(?!\/api).*/, (_req, res) => {
            res.sendFile(path_1.default.join(publicDir, 'index.html'));
        });
    }
    else {
        logger_1.logger.warn('No frontend build found at backend/public. Run setup.bat first, or see docs/INSTALLATION.md.');
    }
    app.use(errorHandler_1.notFoundHandler);
    app.use(errorHandler_1.errorHandler);
    app.listen(config_1.config.port, () => {
        logger_1.logger.info(`CA Docs is running: open http://localhost:${config_1.config.port} in a browser (${config_1.config.nodeEnv})`);
    });
}
bootstrap().catch((err) => {
    // eslint-disable-next-line no-console
    console.error('Fatal startup error:', err);
    process.exit(1);
});
//# sourceMappingURL=server.js.map