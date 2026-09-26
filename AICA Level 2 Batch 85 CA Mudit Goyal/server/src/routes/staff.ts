import { Router } from 'express';
import { getStaff, createStaff, updateStaff, toggleActive, resetPassword } from '../controllers/staffController';
import { authenticate, requireAdmin } from '../middleware/auth';

const router = Router();
router.use(authenticate);

router.get('/', getStaff);
router.post('/', requireAdmin, createStaff);
router.put('/:id', requireAdmin, updateStaff);
router.put('/:id/toggle-active', requireAdmin, toggleActive);
router.post('/:id/reset-password', requireAdmin, resetPassword);

export default router;
