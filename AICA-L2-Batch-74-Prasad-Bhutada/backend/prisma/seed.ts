import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

const DEFAULT_CATEGORIES = [
  'Income Tax',
  'GST',
  'Audit',
  'ROC',
  'Certificates',
  'Engagement Letters',
  'Miscellaneous',
];

// The six built-in Client Master columns (name/address x2/type/mobile/email) cover
// generic contact info, but a CA office needs statutory identifiers on essentially
// every client from day one. These are seeded as ClientField rows (the same
// extensible mechanism an admin uses to add further fields later via Settings) so
// they're immediately available for placeholder mapping and the client form,
// without requiring an admin to manually configure them before the app is useful.
const DEFAULT_CLIENT_FIELDS: { fieldKey: string; label: string; fieldType: string; sortOrder: number }[] = [
  { fieldKey: 'pan', label: 'PAN', fieldType: 'PAN', sortOrder: 1 },
  { fieldKey: 'gstin', label: 'GSTIN', fieldType: 'GSTIN', sortOrder: 2 },
  { fieldKey: 'tan', label: 'TAN', fieldType: 'Text', sortOrder: 3 },
  { fieldKey: 'cin', label: 'CIN / Registration No.', fieldType: 'Text', sortOrder: 4 },
  { fieldKey: 'dateOfIncorporation', label: 'Date of Incorporation / Birth', fieldType: 'Date', sortOrder: 5 },
];

async function main() {
  for (const name of DEFAULT_CATEGORIES) {
    await prisma.category.upsert({
      where: { name },
      update: {},
      create: { name, isSystem: true },
    });
  }
  console.log(`Seeded ${DEFAULT_CATEGORIES.length} default categories.`);

  for (const field of DEFAULT_CLIENT_FIELDS) {
    await prisma.clientField.upsert({
      where: { fieldKey: field.fieldKey },
      update: {},
      create: { ...field, isSystem: false },
    });
  }
  console.log(`Seeded ${DEFAULT_CLIENT_FIELDS.length} default Client Master fields (PAN, GSTIN, TAN, CIN, DOB/DOI).`);
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(() => prisma.$disconnect());
