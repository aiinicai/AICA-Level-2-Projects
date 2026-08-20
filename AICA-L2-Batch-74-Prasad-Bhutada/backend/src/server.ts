import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import morgan from 'morgan';
import path from 'path';
import fs from 'fs';
import { config } from './config';
import { logger } from './utils/logger';
import { errorHandler, notFoundHandler } from './middleware/errorHandler';
import { ensureDefaultSettings } from './modules/settings/settings.service';
import { scheduleBackups } from './modules/backup/backup.service';

import templatesRoutes from './modules/templates/templates.routes';
import mappingRoutes from './modules/templates/mapping.routes';
import categoriesRoutes from './modules/categories/categories.routes';
import clientsRoutes from './modules/clients/clients.routes';
import generationRoutes from './modules/generation/generation.routes';
import historyRoutes from './modules/history/history.routes';
import settingsRoutes from './modules/settings/settings.routes';
import backupRoutes from './modules/backup/backup.routes';

async function bootstrap() {
  await ensureDefaultSettings();
  await scheduleBackups();

  const app = express();
  app.use(helmet({ contentSecurityPolicy: false })); // CSP disabled: this serves our own bundled frontend, not third-party content
  app.use(cors()); // kept permissive for LAN deployment flexibility (e.g. accessing the API directly from another PC)
  app.use(express.json({ limit: '5mb' }));
  app.use(
    morgan('combined', {
      stream: { write: (message: string) => logger.info(message.trim()) },
    }),
  );

  app.get('/api/health', (_req, res) => res.json({ success: true, status: 'ok' }));

  app.use('/api/templates', templatesRoutes);
  app.use('/api/placeholder-mappings', mappingRoutes);
  app.use('/api/categories', categoriesRoutes);
  app.use('/api/clients', clientsRoutes);
  app.use('/api/generation', generationRoutes);
  app.use('/api/history', historyRoutes);
  app.use('/api/settings', settingsRoutes);
  app.use('/api/backup', backupRoutes);

  // --- Serve the built frontend from this SAME process/port -----------------
  // This is the whole point: one program to run, one address to open, no
  // separate frontend server and no "which URL does the frontend call"
  // configuration to get wrong. `setup.bat` copies the frontend's production
  // build into backend/public before first run. Since the frontend is served
  // from the same origin as the API, it always calls relative "/api/..." with
  // zero configuration - the class of bug where the frontend can't find the
  // backend simply can't happen with this layout.
  const publicDir = path.join(__dirname, '..', 'public');
  if (fs.existsSync(publicDir)) {
    app.use(express.static(publicDir));
    // SPA fallback: any non-API GET request that isn't a real static file
    // gets index.html, so React Router's client-side routes (e.g. /clients,
    // /history) work correctly on a full page load/refresh, not just when
    // navigated to from within the app.
    app.get(/^(?!\/api).*/, (_req, res) => {
      res.sendFile(path.join(publicDir, 'index.html'));
    });
  } else {
    logger.warn(
      'No frontend build found at backend/public. Run setup.bat first, or see docs/INSTALLATION.md.',
    );
  }

  app.use(notFoundHandler);
  app.use(errorHandler);

  app.listen(config.port, () => {
    logger.info(`CA Docs is running: open http://localhost:${config.port} in a browser (${config.nodeEnv})`);
  });
}

bootstrap().catch((err) => {
  // eslint-disable-next-line no-console
  console.error('Fatal startup error:', err);
  process.exit(1);
});
