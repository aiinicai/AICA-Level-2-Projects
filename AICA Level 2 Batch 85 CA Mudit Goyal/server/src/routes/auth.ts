import { Router } from 'express';
import { login, profile, changePassword } from '../controllers/authController';
import { authenticate } from '../middleware/auth';

const router = Router();

router.post('/login', login);
router.get('/profile', authenticate, profile);
router.post('/change-password', authenticate, changePassword);

export default router;
