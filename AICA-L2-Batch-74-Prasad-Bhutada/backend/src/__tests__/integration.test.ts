import fs from 'fs';
import os from 'os';
import path from 'path';
import { execSync } from 'child_process';

// Integration test: spins up the Express app against a throwaway SQLite DB
// (created fresh via `prisma migrate deploy`) to verify the HTTP layer wires
// together correctly end-to-end, not just individual services in isolation.

const testDbDir = fs.mkdtempSync(path.join(os.tmpdir(), 'cadocs-int-'));
const testDbPath = path.join(testDbDir, 'test.db');
process.env.DATABASE_URL = `file:${testDbPath}`;
process.env.TEMPLATE_FOLDER = path.join(testDbDir, 'templates');
process.env.GENERATED_FOLDER = path.join(testDbDir, 'generated');
process.env.BACKUP_FOLDER = path.join(testDbDir, 'backups');
process.env.JWT_SECRET = 'test-secret';
process.env.DEFAULT_ADMIN_PASSWORD = 'TestPassword123';

beforeAll(() => {
  // `db push` (not `migrate deploy`/`migrate dev`) to mirror exactly what setup.bat
  // does in production: sync schema.prisma directly to a fresh SQLite file, no
  // migration-history files required. See setup.bat and docs/ARCHITECTURE.md for why.
  execSync('npx prisma db push --skip-generate', {
    cwd: path.join(__dirname, '..', '..'),
    env: process.env,
    stdio: 'inherit',
  });
});

afterAll(() => {
  fs.rmSync(testDbDir, { recursive: true, force: true });
});

describe('Categories + Settings API (integration)', () => {
  it('lists seeded-free empty categories, then creates one', async () => {
    // Import after env vars + migration are set up so Prisma reads the test DB
    const { prisma } = require('../db/prisma');
    const svc = require('../modules/settings/settings.service');
    await svc.ensureDefaultSettings();

    const category = await prisma.category.create({ data: { name: 'Income Tax Test' } });
    expect(category.name).toBe('Income Tax Test');

    const found = await prisma.category.findMany();
    expect(found.length).toBe(1);

    await prisma.$disconnect();
  });

  it('unlocking Manage Formats with the seeded default password succeeds, wrong password fails', async () => {
    const svc = require('../modules/settings/settings.service');
    const ok = await svc.verifyTemplatePassword('TestPassword123');
    expect(ok).toBe(true);
    const bad = await svc.verifyTemplatePassword('WrongPassword');
    expect(bad).toBe(false);
  });
});
