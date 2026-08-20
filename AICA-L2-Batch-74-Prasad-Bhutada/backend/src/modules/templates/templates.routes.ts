import { Router } from 'express';
import multer from 'multer';
import os from 'os';
import * as ctrl from './templates.controller';
import { requireTemplateAdmin } from '../../middleware/auth';

const upload = multer({ dest: os.tmpdir(), limits: { fileSize: 25 * 1024 * 1024 } });

const router = Router();

// Read-only browsing (list/preview/download) intentionally does NOT require the
// template-admin password, since staff need to browse+preview templates while
// generating documents (Module 5/6). Only structural changes are gated.
router.get('/', ctrl.list);
router.get('/:id', ctrl.getOne);
router.get('/:id/preview', ctrl.preview);
router.get('/:id/download', ctrl.download);

router.use(requireTemplateAdmin);
router.post('/import', upload.array('files', 20), ctrl.importTemplates);
router.post('/:id/replace', upload.single('file'), ctrl.replaceFile);
router.patch('/:id/rename', ctrl.rename);
router.get('/:id/dependencies', ctrl.dependencyCheck);
router.delete('/:id', ctrl.softDelete);
router.post('/:id/restore', ctrl.restore);
router.get('/recycle-bin/list', ctrl.recycleBin);

export default router;
