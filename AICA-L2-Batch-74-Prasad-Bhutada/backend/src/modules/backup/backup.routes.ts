import { Router, Request, Response, NextFunction } from 'express';
import multer from 'multer';
import os from 'os';
import * as svc from './backup.service';
import { requireTemplateAdmin } from '../../middleware/auth';

const upload = multer({ dest: os.tmpdir() });
const router = Router();

router.use(requireTemplateAdmin);

router.post('/run', async (_req: Request, res: Response, next: NextFunction) => {
  try {
    const zipPath = await svc.runBackup();
    res.json({ success: true, data: { zipPath } });
  } catch (e) {
    next(e);
  }
});

router.post('/restore', upload.single('file'), async (req: Request, res: Response, next: NextFunction) => {
  try {
    const file = req.file as Express.Multer.File;
    await svc.restoreFromBackup(file.path);
    res.json({ success: true, message: 'Restore completed. Please restart the application service.' });
  } catch (e) {
    next(e);
  }
});

export default router;
