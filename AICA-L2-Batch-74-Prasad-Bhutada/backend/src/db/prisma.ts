import { PrismaClient } from '@prisma/client';

// Singleton Prisma client - avoids exhausting SQLite connections under
// concurrent LAN usage (Express dev-reload also benefits from this pattern).
declare global {
  // eslint-disable-next-line no-var
  var __prisma: PrismaClient | undefined;
}

export const prisma = global.__prisma || new PrismaClient();

if (process.env.NODE_ENV !== 'production') {
  global.__prisma = prisma;
}
