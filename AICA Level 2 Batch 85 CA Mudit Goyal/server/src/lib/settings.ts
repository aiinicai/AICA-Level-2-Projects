import prisma from './prisma';

/**
 * The firm's settings row.
 *
 * There is exactly one, at id 1. Reading it is an upsert so the row springs
 * into existence on first use with the column defaults — nothing has to seed
 * it, and no caller ever has to cope with it being missing.
 */
export const SETTINGS_ID = 1;

export function getSettings() {
  return prisma.settings.upsert({
    where: { id: SETTINGS_ID },
    create: { id: SETTINGS_ID },
    update: {},
  });
}
