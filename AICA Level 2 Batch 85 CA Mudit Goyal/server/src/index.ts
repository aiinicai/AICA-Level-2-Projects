import express, { Request, Response, NextFunction } from 'express';
import cors from 'cors';
import compression from 'compression';
import helmet from 'helmet';
import dotenv from 'dotenv';
import prisma from './lib/prisma';

import authRoutes from './routes/auth';
import staffRoutes from './routes/staff';
import invoiceRoutes from './routes/invoices';
import attendanceRoutes from './routes/attendance';
import dashboardRoutes from './routes/dashboard';
import settingsRoutes from './routes/settings';

dotenv.config();

const app = express();
// Parsed rather than `Number(...) || 5100`, which treats a deliberate PORT=0 —
// "let the OS pick a free port", which the test suite relies on so it can run
// alongside a dev server — as unset and collides on 5100.
const parsedPort = Number(process.env.PORT);
const PORT = Number.isInteger(parsedPort) && parsedPort >= 0 ? parsedPort : 5100;

if (!process.env.JWT_SECRET) {
  // Failing loudly here beats signing tokens with `undefined` and discovering
  // it when every session silently stops verifying.
  console.error('JWT_SECRET is not set. Copy .env.example to .env and fill it in.');
  process.exit(1);
}

const allowedOrigins = ['http://localhost:3000', 'http://localhost:3100', process.env.FRONTEND_URL].filter(
  Boolean,
) as string[];

app.use(compression());
// CSP is off: this is a JSON API, and the policy that matters belongs on the
// origin serving the app.
app.use(helmet({ contentSecurityPolicy: false }));
app.use(
  cors({
    origin: (origin, cb) => {
      if (!origin) return cb(null, true); // curl, the test script, server-to-server
      if (process.env.NODE_ENV !== 'production' && origin.startsWith('http://localhost')) return cb(null, true);
      if (allowedOrigins.includes(origin)) return cb(null, true);
      cb(new Error(`CORS blocked: ${origin}`));
    },
    credentials: true,
  }),
);
app.use(express.json({ limit: '1mb' }));

app.get('/api/health', async (_req: Request, res: Response) => {
  try {
    await prisma.$queryRaw`SELECT 1`;
    res.json({ status: 'ok', database: 'connected' });
  } catch {
    res.status(503).json({ status: 'degraded', database: 'unreachable' });
  }
});

app.use('/api/auth', authRoutes);
app.use('/api/staff', staffRoutes);
app.use('/api/invoices', invoiceRoutes);
app.use('/api/attendance', attendanceRoutes);
app.use('/api/dashboard', dashboardRoutes);
app.use('/api/settings', settingsRoutes);

app.use((_req: Request, res: Response) => res.status(404).json({ message: 'Not found' }));

// Last-resort handler. The message is deliberately generic — a stack trace or
// a Prisma error string handed to the browser is an information leak.
app.use((err: Error, _req: Request, res: Response, _next: NextFunction) => {
  console.error('[error]', err);
  res.status(500).json({ message: 'Server error' });
});

const server = app.listen(PORT, () => {
  const actual = server.address();
  console.log(
    `Capstone API listening on http://localhost:${typeof actual === 'object' && actual ? actual.port : PORT}`,
  );
});

// The end-to-end suite imports this module to drive the real app over HTTP, and
// needs the server it started — both to find the port (it listens on 0) and to
// close it when the run is done.
(globalThis as { __capstoneServer?: typeof server }).__capstoneServer = server;

const shutdown = async () => {
  server.close();
  await prisma.$disconnect();
  process.exit(0);
};
process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);

export default app;
