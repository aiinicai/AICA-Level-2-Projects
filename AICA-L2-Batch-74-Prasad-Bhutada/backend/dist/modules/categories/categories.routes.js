"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = require("express");
const prisma_1 = require("../../db/prisma");
const logger_1 = require("../../utils/logger");
const router = (0, express_1.Router)();
router.get('/', async (_req, res, next) => {
    try {
        res.json({ success: true, data: await prisma_1.prisma.category.findMany({ orderBy: { name: 'asc' } }) });
    }
    catch (e) {
        next(e);
    }
});
router.post('/', async (req, res, next) => {
    try {
        const { name } = req.body;
        if (!name?.trim())
            throw new logger_1.AppError('Category name is required.', 400);
        const category = await prisma_1.prisma.category.create({ data: { name: name.trim() } });
        res.status(201).json({ success: true, data: category });
    }
    catch (e) {
        if (e.code === 'P2002')
            return next(new logger_1.AppError('A category with this name already exists.', 400));
        next(e);
    }
});
router.delete('/:id', async (req, res, next) => {
    try {
        const category = await prisma_1.prisma.category.findUnique({ where: { id: req.params.id } });
        if (!category)
            throw new logger_1.AppError('Category not found.', 404);
        if (category.isSystem)
            throw new logger_1.AppError('Default categories cannot be deleted.', 400);
        const inUse = await prisma_1.prisma.template.count({ where: { categoryId: category.id, status: 'Active' } });
        if (inUse > 0)
            throw new logger_1.AppError(`Cannot delete: ${inUse} template(s) still use this category.`, 400);
        await prisma_1.prisma.category.delete({ where: { id: req.params.id } });
        res.json({ success: true, message: 'Category deleted.' });
    }
    catch (e) {
        next(e);
    }
});
exports.default = router;
//# sourceMappingURL=categories.routes.js.map