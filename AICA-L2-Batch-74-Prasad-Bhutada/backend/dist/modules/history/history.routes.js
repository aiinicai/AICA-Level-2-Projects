"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = require("express");
const exceljs_1 = __importDefault(require("exceljs"));
const prisma_1 = require("../../db/prisma");
const router = (0, express_1.Router)();
function buildWhere(query) {
    const where = {};
    if (query.clientId)
        where.clientId = query.clientId;
    if (query.templateId)
        where.templates = { some: { templateId: query.templateId } };
    if (query.dateFrom || query.dateTo) {
        where.generatedAt = {};
        if (query.dateFrom)
            where.generatedAt.gte = new Date(query.dateFrom);
        if (query.dateTo)
            where.generatedAt.lte = new Date(query.dateTo);
    }
    return where;
}
router.get('/', async (req, res, next) => {
    try {
        const where = buildWhere(req.query);
        const rows = await prisma_1.prisma.generationHistory.findMany({
            where,
            include: { templates: { include: { template: true } }, client: true },
            orderBy: { generatedAt: 'desc' },
            take: 500,
        });
        res.json({ success: true, data: rows });
    }
    catch (e) {
        next(e);
    }
});
router.get('/export', async (req, res, next) => {
    try {
        const where = buildWhere(req.query);
        const rows = await prisma_1.prisma.generationHistory.findMany({
            where,
            include: { templates: { include: { template: true } } },
            orderBy: { generatedAt: 'desc' },
        });
        const workbook = new exceljs_1.default.Workbook();
        const sheet = workbook.addWorksheet('Generation History');
        sheet.columns = [
            { header: 'Date', key: 'date', width: 14 },
            { header: 'Time', key: 'time', width: 12 },
            { header: 'Client Name', key: 'client', width: 28 },
            { header: 'Templates', key: 'templates', width: 40 },
            { header: 'Placeholder Values', key: 'values', width: 60 },
        ];
        sheet.getRow(1).font = { bold: true };
        for (const r of rows) {
            sheet.addRow({
                date: r.generatedAt.toISOString().slice(0, 10),
                time: r.generatedAt.toISOString().slice(11, 19),
                client: r.clientNameSnapshot,
                templates: r.templates.map((t) => t.template.name).join(', '),
                values: r.placeholderValuesJson,
            });
        }
        const buffer = await workbook.xlsx.writeBuffer();
        res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
        res.setHeader('Content-Disposition', 'attachment; filename="Generation-History.xlsx"');
        res.send(buffer);
    }
    catch (e) {
        next(e);
    }
});
exports.default = router;
//# sourceMappingURL=history.routes.js.map