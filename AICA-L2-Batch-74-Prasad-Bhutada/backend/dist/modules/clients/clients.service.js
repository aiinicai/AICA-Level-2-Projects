"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.listClients = listClients;
exports.getClient = getClient;
exports.createClient = createClient;
exports.updateClient = updateClient;
exports.deleteClient = deleteClient;
exports.addClientField = addClientField;
exports.listClientFields = listClientFields;
exports.bulkImportFromExcel = bulkImportFromExcel;
exports.exportToExcel = exportToExcel;
const exceljs_1 = __importDefault(require("exceljs"));
const prisma_1 = require("../../db/prisma");
const logger_1 = require("../../utils/logger");
const SYSTEM_FIELDS = ['name', 'addressLine1', 'addressLine2', 'clientType', 'mobile', 'email'];
async function listClients(search) {
    return prisma_1.prisma.client.findMany({
        where: search
            ? { OR: [{ name: { contains: search } }, { email: { contains: search } }, { mobile: { contains: search } }] }
            : undefined,
        include: { customValues: { include: { field: true } } },
        orderBy: { name: 'asc' },
    });
}
async function getClient(id) {
    const client = await prisma_1.prisma.client.findUnique({ where: { id }, include: { customValues: { include: { field: true } } } });
    if (!client)
        throw new logger_1.AppError('Client not found.', 404);
    return client;
}
async function createClient(input) {
    if (!input.name?.trim())
        throw new logger_1.AppError('Client name is required.', 400);
    const client = await prisma_1.prisma.client.create({
        data: {
            name: input.name,
            addressLine1: input.addressLine1,
            addressLine2: input.addressLine2,
            clientType: input.clientType,
            mobile: input.mobile,
            email: input.email,
        },
    });
    if (input.customFields)
        await upsertCustomFields(client.id, input.customFields);
    return getClient(client.id);
}
async function updateClient(id, input) {
    await getClient(id);
    await prisma_1.prisma.client.update({
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
    if (input.customFields)
        await upsertCustomFields(id, input.customFields);
    return getClient(id);
}
async function upsertCustomFields(clientId, customFields) {
    for (const [fieldKey, value] of Object.entries(customFields)) {
        const field = await prisma_1.prisma.clientField.findUnique({ where: { fieldKey } });
        if (!field)
            continue; // unknown field keys are ignored, not errored, to keep imports resilient
        await prisma_1.prisma.clientCustomValue.upsert({
            where: { clientId_fieldId: { clientId, fieldId: field.id } },
            update: { value },
            create: { clientId, fieldId: field.id, value },
        });
    }
}
async function deleteClient(id) {
    await getClient(id);
    await prisma_1.prisma.client.delete({ where: { id } });
}
/** Module 4: admin can add a brand-new client-master field at runtime; it immediately becomes mappable. */
async function addClientField(input) {
    return prisma_1.prisma.clientField.create({
        data: {
            fieldKey: input.fieldKey,
            label: input.label,
            fieldType: input.fieldType,
            isRequired: input.isRequired ?? false,
        },
    });
}
async function listClientFields() {
    return prisma_1.prisma.clientField.findMany({ orderBy: { sortOrder: 'asc' } });
}
async function bulkImportFromExcel(filePath) {
    const workbook = new exceljs_1.default.Workbook();
    await workbook.xlsx.readFile(filePath);
    const sheet = workbook.worksheets[0];
    const headerRow = sheet.getRow(1).values;
    const headers = headerRow.slice(1).map((h) => String(h || '').trim());
    const customFields = await listClientFields();
    const customByLabel = new Map(customFields.map((f) => [f.label, f.fieldKey]));
    let imported = 0;
    const errors = [];
    sheet.eachRow((row, rowNumber) => {
        if (rowNumber === 1)
            return;
        const values = row.values;
        const record = {};
        headers.forEach((header, i) => {
            const v = values[i + 1];
            if (v !== undefined && v !== null)
                record[header] = String(v);
        });
        if (!record['Client Name']) {
            errors.push(`Row ${rowNumber}: missing Client Name, skipped.`);
            return;
        }
        const customFieldValues = {};
        for (const [label, key] of customByLabel.entries()) {
            if (record[label] !== undefined)
                customFieldValues[key] = record[label];
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
async function exportToExcel() {
    const clients = await listClients();
    const customFields = await listClientFields();
    const workbook = new exceljs_1.default.Workbook();
    const sheet = workbook.addWorksheet('Clients');
    sheet.columns = [
        { header: 'Client Name', key: 'name', width: 30 },
        { header: 'Address Line 1', key: 'addressLine1', width: 25 },
        { header: 'Address Line 2', key: 'addressLine2', width: 25 },
        { header: 'Client Type', key: 'clientType', width: 15 },
        { header: 'Mobile', key: 'mobile', width: 15 },
        { header: 'Email', key: 'email', width: 25 },
        ...customFields.map((f) => ({ header: f.label, key: f.fieldKey, width: 20 })),
    ];
    sheet.getRow(1).font = { bold: true };
    for (const c of clients) {
        const row = {
            name: c.name,
            addressLine1: c.addressLine1 || '',
            addressLine2: c.addressLine2 || '',
            clientType: c.clientType || '',
            mobile: c.mobile || '',
            email: c.email || '',
        };
        for (const cv of c.customValues)
            row[cv.field.fieldKey] = cv.value || '';
        sheet.addRow(row);
    }
    return workbook.xlsx.writeBuffer();
}
//# sourceMappingURL=clients.service.js.map