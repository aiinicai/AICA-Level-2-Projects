import { Router } from 'express';
import * as ctrl from './settings.controller';
import { requireTemplateAdmin } from '../../middleware/auth';

const router = Router();

router.post('/unlock', ctrl.unlock); // password check -> issues short-lived token

router.use(requireTemplateAdmin);
router.get('/', ctrl.getSettings);
router.put('/', ctrl.updateSettings);
router.post('/change-password', ctrl.changeTemplatePassword);

export default router;
