import { Router } from 'express';
import {
  getPunches, recordPunch, getDailyRegister, getMonthlyAttendance, markAttendance,
} from '../controllers/attendanceController';
import { authenticate, requireAdmin, requireStaff } from '../middleware/auth';

const router = Router();
router.use(authenticate);

router.get('/punches', getPunches);
router.post('/punch', requireStaff, recordPunch);
router.get('/monthly', getMonthlyAttendance);
router.get('/register', requireAdmin, getDailyRegister);
router.post('/mark', requireAdmin, markAttendance);

export default router;
