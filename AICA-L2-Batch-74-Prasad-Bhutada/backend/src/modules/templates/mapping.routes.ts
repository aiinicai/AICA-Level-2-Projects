import { Router, Request, Response, NextFunction } from 'express';
import { prisma } from '../../db/prisma';
import { AppError } from '../../utils/logger';

const router = Router();

/** List all known placeholders across all templates, with their current mapping (if any). */
router.get('/', async (_req: Request, res: Response, next: NextFunction) => {
  try {
    const placeholders = await prisma.placeholder.findMany({
      include: { mapping: true, templates: { include: { template: true } } },
      orderBy: { name: 'asc' },
    });
    res.json({
      success: true,
      data: placeholders.map((p: any) => ({
        id: p.id,
        name: p.name,
        validationType: p.validationType,
        isImage: p.isImage,
        mappedClientField: p.mapping?.clientFieldKey || null,
        usedInTemplates: p.templates.map((t: any) => t.template.name),
      })),
    });
  } catch (e) {
    next(e);
  }
});

/** Available client-master fields (system + custom) that a placeholder can be mapped to. */
router.get('/available-fields', async (_req: Request, res: Response, next: NextFunction) => {
  try {
    const systemFields = [
      { fieldKey: 'name', label: 'Client Name' },
      { fieldKey: 'addressLine1', label: 'Address Line 1' },
      { fieldKey: 'addressLine2', label: 'Address Line 2' },
      { fieldKey: 'clientType', label: 'Client Type' },
      { fieldKey: 'mobile', label: 'Mobile' },
      { fieldKey: 'email', label: 'Email' },
    ];
    const customFields = await prisma.clientField.findMany({ orderBy: { sortOrder: 'asc' } });
    res.json({
      success: true,
      data: [...systemFields, ...customFields.map((f: any) => ({ fieldKey: f.fieldKey, label: f.label }))],
    });
  } catch (e) {
    next(e);
  }
});

router.put('/:placeholderId', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const { clientFieldKey } = req.body;
    if (!clientFieldKey) throw new AppError('Please choose a client field to map to.', 400);
    const mapping = await prisma.placeholderMapping.upsert({
      where: { placeholderId: req.params.placeholderId },
      update: { clientFieldKey },
      create: { placeholderId: req.params.placeholderId, clientFieldKey },
    });
    res.json({ success: true, data: mapping });
  } catch (e) {
    next(e);
  }
});

router.delete('/:placeholderId', async (req: Request, res: Response, next: NextFunction) => {
  try {
    await prisma.placeholderMapping.deleteMany({ where: { placeholderId: req.params.placeholderId } });
    res.json({ success: true, message: 'Mapping removed.' });
  } catch (e) {
    next(e);
  }
});

export default router;
