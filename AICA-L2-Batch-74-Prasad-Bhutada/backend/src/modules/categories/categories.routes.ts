import { Router, Request, Response, NextFunction } from 'express';
import { prisma } from '../../db/prisma';
import { AppError } from '../../utils/logger';

const router = Router();

router.get('/', async (_req: Request, res: Response, next: NextFunction) => {
  try {
    res.json({ success: true, data: await prisma.category.findMany({ orderBy: { name: 'asc' } }) });
  } catch (e) {
    next(e);
  }
});

router.post('/', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const { name } = req.body;
    if (!name?.trim()) throw new AppError('Category name is required.', 400);
    const category = await prisma.category.create({ data: { name: name.trim() } });
    res.status(201).json({ success: true, data: category });
  } catch (e: any) {
    if (e.code === 'P2002') return next(new AppError('A category with this name already exists.', 400));
    next(e);
  }
});

router.delete('/:id', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const category = await prisma.category.findUnique({ where: { id: req.params.id } });
    if (!category) throw new AppError('Category not found.', 404);
    if (category.isSystem) throw new AppError('Default categories cannot be deleted.', 400);
    const inUse = await prisma.template.count({ where: { categoryId: category.id, status: 'Active' } });
    if (inUse > 0) throw new AppError(`Cannot delete: ${inUse} template(s) still use this category.`, 400);
    await prisma.category.delete({ where: { id: req.params.id } });
    res.json({ success: true, message: 'Category deleted.' });
  } catch (e) {
    next(e);
  }
});

export default router;
