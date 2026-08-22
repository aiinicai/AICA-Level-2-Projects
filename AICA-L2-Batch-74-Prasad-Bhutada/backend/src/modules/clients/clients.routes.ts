import { Router, Request, Response, NextFunction } from 'express';
import multer from 'multer';
import os from 'os';
import * as svc from './clients.service';

const upload = multer({ dest: os.tmpdir() });
const router = Router();

router.get('/', async (req: Request, res: Response, next: NextFunction) => {
  try {
    res.json({ success: true, data: await svc.listClients(req.query.search as string) });
  } catch (e) {
    next(e);
  }
});

router.get('/fields', async (_req: Request, res: Response, next: NextFunction) => {
  try {
    res.json({ success: true, data: await svc.listClientFields() });
  } catch (e) {
    next(e);
  }
});

router.post('/fields', async (req: Request, res: Response, next: NextFunction) => {
  try {
    res.status(201).json({ success: true, data: await svc.addClientField(req.body) });
  } catch (e) {
    next(e);
  }
});

router.get('/export', async (_req: Request, res: Response, next: NextFunction) => {
  try {
    const buffer = await svc.exportToExcel();
    res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
    res.setHeader('Content-Disposition', 'attachment; filename="Clients.xlsx"');
    res.send(buffer);
  } catch (e) {
    next(e);
  }
});

router.post('/import', upload.single('file'), async (req: Request, res: Response, next: NextFunction) => {
  try {
    const file = req.file as Express.Multer.File;
    res.json({ success: true, data: await svc.bulkImportFromExcel(file.path) });
  } catch (e) {
    next(e);
  }
});

router.get('/:id', async (req: Request, res: Response, next: NextFunction) => {
  try {
    res.json({ success: true, data: await svc.getClient(req.params.id) });
  } catch (e) {
    next(e);
  }
});

router.post('/', async (req: Request, res: Response, next: NextFunction) => {
  try {
    res.status(201).json({ success: true, data: await svc.createClient(req.body) });
  } catch (e) {
    next(e);
  }
});

router.put('/:id', async (req: Request, res: Response, next: NextFunction) => {
  try {
    res.json({ success: true, data: await svc.updateClient(req.params.id, req.body) });
  } catch (e) {
    next(e);
  }
});

router.delete('/:id', async (req: Request, res: Response, next: NextFunction) => {
  try {
    await svc.deleteClient(req.params.id);
    res.json({ success: true, message: 'Client deleted.' });
  } catch (e) {
    next(e);
  }
});

export default router;
