import { Router } from 'express';
import { getSettingsHandler, updateSettings } from '../controllers/settingsController';
import { authenticate, requireAdmin } from '../middleware/auth';

const router = Router();
router.use(authenticate);

// Readable by anyone signed in — the invoice form needs the defaults and the
// PDF needs the letterhead. Writable only by an admin.
router.get('/', getSettingsHandler);
router.put('/', requireAdmin, updateSettings);

export default router;
