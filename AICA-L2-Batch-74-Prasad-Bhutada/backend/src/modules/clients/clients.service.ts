import ExcelJS from 'exceljs';
import { prisma } from '../../db/prisma';
import { AppError } from '../../utils/logger';

const SYSTEM_FIELDS = ['name', 'addressLine1', 'addressLine2', 'clientType', 'mobile', 'email'] as const;

export async function listClients(search?: string) {
  return prisma.client.findMany({
    where: search
      ? { OR: [{ name: { contains: search } }, { email: { contains: search } }, { mobile: { contains: search } }] }
      : undefined,
    include: { customValues: { include: { field: true } } },
    orderBy: { name: 'asc' },
  });
}

export async function getClient(id: string) {
  const client = await prisma.client.findUnique({ where: { id }, include: { customValues: { include: { field: true } } } });
  if (!client) throw new AppError('Client not found.', 404);
  return client;
}

export interface ClientInput {
  name: string;
  addressLine1?: string;
  addressLine2?: string;
  clientType?: string;
  mobile?: string;
  email?: string;
  customFields?: Record<string, string>; // fieldKey -> value
}

export async function createClient(input: ClientInput) {
  if (!input.name?.trim()) throw new AppError('Client name is required.', 400);
  const client = await prisma.client.create({
    data: {
      name: input.name,
      addressLine1: input.addressLine1,
      addressLine2: input.addressLine2,
      clientType: input.clientType,
      mobile: input.mobile,
      email: input.email,
    },
  });
  if (input.customFields) await upsertCustomFields(client.id, input.customFields);
  return getClient(client.id);
}

export async function updateClient(id: string, input: ClientInput) {
  await getClient(id);
  await prisma.client.update({
    where: { id },
    data: {
      name: input.name,
      addressLine1: input.addressLine1,
      addressLine2: input.addressLine2,
      clientType: input.clientType,
      mobile: input.mobile,
      email: input.email,
    },
  });
  if (input.customFields) await upsertCustomFields(id, input.customFields);
  return getClient(id);
}

async function upsertCustomFields(clientId: string, customFields: Record<string, string>) {
  for (const [fieldKey, value] of Object.entries(customFields)) {
    const field = await prisma.clientField.findUnique({ where: { fieldKey } });
    if (!field) continue; // unknown field keys are ignored, not errored, to keep imports resilient
    await prisma.clientCustomValue.upsert({
      where: { clientId_fieldId: { clientId, fieldId: field.id } },
      update: { value },
      create: { clientId, fieldId: field.id, value },
    });
  }
}

export async function deleteClient(id: string) {
  await getClient(id);
  await prisma.client.delete({ where: { id } });
}

/** Module 4: admin can add a brand-new client-master field at runtime; it immediately becomes mappable. */
export async function addClientField(input: { fieldKey: string; label: string; fieldType: string; isRequired?: boolean }) {
  return prisma.clientField.create({
    data: {
      fieldKey: input.fieldKey,
      label: input.label,
      fieldType: input.fieldType,
      isRequired: input.isRequired ?? false,
    },
  });
}

export async function listClientFields() {
  return prisma.clientField.findMany({ orderBy: { sortOrder: 'asc' } });
}

export async function bulkImportFromExcel(filePath: string) {
  const workbook = new ExcelJS.Workbook();
  await workbook.xlsx.readFile(filePath);
  const sheet = workbook.worksheets[0];
  const headerRow = sheet.getRow(1).values as (string | undefined)[];
  const headers = headerRow.slice(1).map((h) => String(h || '').trim());

  const customFields = await listClientFields();
  const customByLabel = new Map(customFields.map((f: any) => [f.label, f.fieldKey]));

  let imported = 0;
  const errors: string[] = [];

  sheet.eachRow((row, rowNumber) => {
    if (rowNumber === 1) return;
    const values = row.values as (string | number | undefined)[];
    const record: Record<string, string> = {};
    headers.forEach((header, i) => {
      const v = values[i + 1];
      if (v !== undefined && v !== null) record[header] = String(v);
    });
    if (!record['Client Name']) {
      errors.push(`Row ${rowNumber}: missing Client Name, skipped.`);
      return;
    }
    const customFieldValues: Record<string, string> = {};
    for (const [label, key] of customByLabel.entries() as IterableIterator<[string, string]>) {
      if (record[label] !== undefined) customFieldValues[key] = record[label];
    }
    createClient({
      name: record['Client Name'],
      addressLine1: record['Address Line 1'],
      addressLine2: record['Address Line 2'],
      clientType: record['Client Type'],
      mobile: record['Mobile'],
      email: record['Email'],
      customFields: customFieldValues,
    })
      .then(() => imported++)
      .catch((e) => errors.push(`Row ${rowNumber}: ${e.message}`));
  });

  return { imported, errors };
}

export async function exportToExcel(): Promise<ExcelJS.Buffer> {
  const clients = await listClients();
  const customFields = await listClientFields();

  const workbook = new ExcelJS.Workbook();
  const sheet = workbook.addWorksheet('Clients');
  sheet.columns = [
    { header: 'Client Name', key: 'name', width: 30 },
    { header: 'Address Line 1', key: 'addressLine1', width: 25 },
    { header: 'Address Line 2', key: 'addressLine2', width: 25 },
    { header: 'Client Type', key: 'clientType', width: 15 },
    { header: 'Mobile', key: 'mobile', width: 15 },
    { header: 'Email', key: 'email', width: 25 },
    ...customFields.map((f: any) => ({ header: f.label, key: f.fieldKey, width: 20 })),
  ];
  sheet.getRow(1).font = { bold: true };

  for (const c of clients) {
    const row: Record<string, string> = {
      name: c.name,
      addressLine1: c.addressLine1 || '',
      addressLine2: c.addressLine2 || '',
      clientType: c.clientType || '',
      mobile: c.mobile || '',
      email: c.email || '',
    };
    for (const cv of c.customValues) row[cv.field.fieldKey] = cv.value || '';
    sheet.addRow(row);
  }

  return workbook.xlsx.writeBuffer();
}
