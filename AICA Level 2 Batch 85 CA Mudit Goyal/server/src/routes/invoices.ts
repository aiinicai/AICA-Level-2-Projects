import { Router } from 'express';
import {
  listInvoices, getInvoice, createInvoice, updateInvoice,
  issueInvoice, cancelInvoice, deleteInvoice, addPayment, deletePayment,
} from '../controllers/invoiceController';
import { authenticate, requireStaff } from '../middleware/auth';

const router = Router();
router.use(authenticate);

router.get('/', listInvoices);
router.get('/:id', getInvoice);
router.post('/', requireStaff, createInvoice);
router.put('/:id', requireStaff, updateInvoice);
router.post('/:id/issue', requireStaff, issueInvoice);
router.post('/:id/cancel', requireStaff, cancelInvoice);
router.delete('/:id', requireStaff, deleteInvoice);
router.post('/:id/payments', requireStaff, addPayment);
router.delete('/payments/:paymentId', requireStaff, deletePayment);

export default router;
