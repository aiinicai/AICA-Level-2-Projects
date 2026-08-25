"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = require("express");
const prisma_1 = require("../../db/prisma");
const logger_1 = require("../../utils/logger");
const router = (0, express_1.Router)();
/** List all known placeholders across all templates, with their current mapping (if any). */
router.get('/', async (_req, res, next) => {
    try {
        const placeholders = await prisma_1.prisma.placeholder.findMany({
            include: { mapping: true, templates: { include: { template: true } } },
            orderBy: { name: 'asc' },
        });
        res.json({
            success: true,
            data: placeholders.map((p) => ({
                id: p.id,
                name: p.name,
                validationType: p.validationType,
                isImage: p.isImage,
                mappedClientField: p.mapping?.clientFieldKey || null,
                usedInTemplates: p.templates.map((t) => t.template.name),
            })),
        });
    }
    catch (e) {
        next(e);
    }
});
/** Available client-master fields (system + custom) that a placeholder can be mapped to. */
router.get('/available-fields', async (_req, res, next) => {
    try {
        const systemFields = [
            { fieldKey: 'name', label: 'Client Name' },
            { fieldKey: 'addressLine1', label: 'Address Line 1' },
            { fieldKey: 'addressLine2', label: 'Address Line 2' },
            { fieldKey: 'clientType', label: 'Client Type' },
            { fieldKey: 'mobile', label: 'Mobile' },
            { fieldKey: 'email', label: 'Email' },
        ];
        const customFields = await prisma_1.prisma.clientField.findMany({ orderBy: { sortOrder: 'asc' } });
        res.json({
            success: true,
            data: [...systemFields, ...customFields.map((f) => ({ fieldKey: f.fieldKey, label: f.label }))],
        });
    }
    catch (e) {
        next(e);
    }
});
router.put('/:placeholderId', async (req, res, next) => {
    try {
        const { clientFieldKey } = req.body;
        if (!clientFieldKey)
            throw new logger_1.AppError('Please choose a client field to map to.', 400);
        const mapping = await prisma_1.prisma.placeholderMapping.upsert({
            where: { placeholderId: req.params.placeholderId },
            update: { clientFieldKey },
            create: { placeholderId: req.params.placeholderId, clientFieldKey },
        });
        res.json({ success: true, data: mapping });
    }
    catch (e) {
        next(e);
    }
});
router.delete('/:placeholderId', async (req, res, next) => {
    try {
        await prisma_1.prisma.placeholderMapping.deleteMany({ where: { placeholderId: req.params.placeholderId } });
        res.json({ success: true, message: 'Mapping removed.' });
    }
    catch (e) {
        next(e);
    }
});
exports.default = router;
//# sourceMappingURL=mapping.routes.js.map