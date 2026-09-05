/**
 * Invoicing.
 *
 * A cut-down version of the MGSG invoicing module. With no clients or tasks
 * module in this subset, the customer's details are typed onto the invoice at
 * billing time and live on the invoice row itself.
 */
import { Response } from 'express';
import { Prisma } from '@prisma/client';
import prisma from '../lib/prisma';
import { AuthRequest } from '../middleware/auth';
import { financialYear, parseDateOnly, getISTTodayUTC } from '../lib/dates';
import { computeTax, num, r2, TaxType } from '../lib/money';
import { getSettings } from '../lib/settings';

const INVOICE_INCLUDE = {
  lineItems: { orderBy: { slNo: 'asc' as const } },
  payments: { orderBy: { paymentDate: 'asc' as const } },
  createdBy: { select: { id: true, staffName: true } },
};

type InvoiceWithRelations = Prisma.InvoiceGetPayload<{ include: typeof INVOICE_INCLUDE }>;

/**
 * What a payment transaction hands back: either a refusal with the status code
 * to send, or the updated invoice. Spelled out as a discriminated union so the
 * `error` branch narrows — inferred, TypeScript merges the two shapes and the
 * status code widens to `number | undefined`.
 */
type PaymentOutcome =
  | { error: number; message: string; invoice?: never }
  | { error?: never; message?: never; invoice: InvoiceWithRelations };

const TAX_TYPES: TaxType[] = ['CGST_SGST', 'IGST', 'NONE'];
const STATUSES = ['DRAFT', 'SENT', 'PARTIALLY_PAID', 'PAID', 'CANCELLED'] as const;
type Status = (typeof STATUSES)[number];

/**
 * Next invoice number for the financial year the invoice falls in, e.g.
 * MGSG/26-27/0007.
 *
 * The counter is bumped inside the caller's transaction with an atomic
 * increment, so two people billing at the same moment cannot be handed the
 * same number. The row is seeded at 2 on creation because it is handing out
 * number 1 in the same breath.
 *
 * The prefix is read at the moment of issue rather than stored, so changing it
 * in Settings affects invoices raised from then on and leaves every number
 * already issued exactly as it was printed.
 */
async function nextInvoiceNumber(
  tx: Prisma.TransactionClient,
  invoiceDate: Date,
  prefix: string,
): Promise<string> {
  const fy = financialYear(invoiceDate);
  const seq = await tx.invoiceSequence.upsert({
    where: { financialYear: fy },
    create: { financialYear: fy, nextNumber: 2 },
    update: { nextNumber: { increment: 1 } },
  });
  const issued = seq.nextNumber - 1;
  return `${prefix}/${fy}/${String(issued).padStart(4, '0')}`;
}

/**
 * The status an invoice should be in given what has been paid against it.
 *
 * DRAFT and CANCELLED are held deliberately: a draft stays a draft until it is
 * issued, and a cancelled invoice never comes back to life on its own.
 */
function statusForPayments(current: Status, total: number, paid: number): Status {
  if (current === 'CANCELLED' || current === 'DRAFT') return current;
  if (paid <= 0) return 'SENT';
  // A rupee either way counts as settled — chasing 40 paise of rounding is not
  // a receivable.
  if (paid >= total - 1) return 'PAID';
  return 'PARTIALLY_PAID';
}

interface ParsedLine {
  slNo: number;
  description: string;
  hsnSac: string | null;
  quantity: number;
  rate: number;
  amount: number;
}

/** Validate the line items and total them. Returns an error string, never throws. */
function parseLineItems(raw: unknown): { lines: ParsedLine[]; amount: number } | { error: string } {
  if (!Array.isArray(raw) || raw.length === 0) {
    return { error: 'At least one line item is required' };
  }
  const lines: ParsedLine[] = [];
  for (const [i, item] of raw.entries()) {
    const row = item as Record<string, unknown>;
    const description = String(row?.description ?? '').trim();
    if (!description) return { error: `Line ${i + 1}: description is required` };

    const quantity = num(row?.quantity ?? 1);
    const rate = num(row?.rate);
    if (quantity <= 0) return { error: `Line ${i + 1}: quantity must be greater than zero` };
    if (rate < 0) return { error: `Line ${i + 1}: rate cannot be negative` };

    lines.push({
      slNo: i + 1,
      description,
      hsnSac: String(row?.hsnSac ?? '').trim() || null,
      quantity: r2(quantity),
      rate: r2(rate),
      amount: r2(quantity * rate),
    });
  }
  const amount = r2(lines.reduce((sum, l) => sum + l.amount, 0));
  if (amount <= 0) return { error: 'Invoice value must be greater than zero' };
  return { lines, amount };
}

// ── READ ─────────────────────────────────────────────────────────────────────

export const listInvoices = async (req: AuthRequest, res: Response) => {
  const { search, status, from, to } = req.query as Record<string, string | undefined>;

  const where: Prisma.InvoiceWhereInput = { deletedAt: null };
  if (status && STATUSES.includes(status as Status)) where.status = status as Status;
  if (search?.trim()) {
    const s = search.trim();
    where.OR = [
      { invoiceNumber: { contains: s, mode: 'insensitive' } },
      { clientName: { contains: s, mode: 'insensitive' } },
      { clientGstin: { contains: s, mode: 'insensitive' } },
    ];
  }
  const fromDate = parseDateOnly(from);
  const toDate = parseDateOnly(to);
  if (fromDate || toDate) {
    where.invoiceDate = { ...(fromDate ? { gte: fromDate } : {}), ...(toDate ? { lte: toDate } : {}) };
  }

  try {
    const invoices = await prisma.invoice.findMany({
      where,
      orderBy: [{ invoiceDate: 'desc' }, { id: 'desc' }],
      include: INVOICE_INCLUDE,
    });

    // Totals cover the filtered set, so the tiles always agree with the list
    // underneath them. Cancelled invoices are left out — a voided bill is
    // neither revenue nor a receivable.
    const live = invoices.filter((i) => i.status !== 'CANCELLED');
    const billed = r2(live.reduce((s, i) => s + num(i.totalAmount), 0));
    const collected = r2(live.reduce((s, i) => s + num(i.paidAmount), 0));

    res.json({
      invoices,
      summary: {
        count: invoices.length,
        billed,
        collected,
        outstanding: r2(billed - collected),
      },
    });
  } catch (err) {
    console.error('[invoices] list failed:', err);
    res.status(500).json({ message: 'Server error' });
  }
};

export const getInvoice = async (req: AuthRequest, res: Response) => {
  const id = Number(req.params.id);
  if (!Number.isInteger(id)) return res.status(400).json({ message: 'Invalid id' });

  try {
    const invoice = await prisma.invoice.findFirst({
      where: { id, deletedAt: null },
      include: INVOICE_INCLUDE,
    });
    if (!invoice) return res.status(404).json({ message: 'Invoice not found' });
    res.json(invoice);
  } catch (err) {
    console.error('[invoices] get failed:', err);
    res.status(500).json({ message: 'Server error' });
  }
};

// ── WRITE ────────────────────────────────────────────────────────────────────

export const createInvoice = async (req: AuthRequest, res: Response) => {
  const {
    clientName, clientGstin, clientAddress, clientState, clientEmail,
    invoiceDate, dueDate, taxType, gstRate, notes, lineItems, status,
  } = req.body as Record<string, unknown>;

  if (!String(clientName ?? '').trim()) return res.status(400).json({ message: 'Client name is required' });

  const invDate = parseDateOnly(invoiceDate) ?? getISTTodayUTC();
  const due = parseDateOnly(dueDate);
  if (due && due < invDate) return res.status(400).json({ message: 'Due date cannot be before the invoice date' });

  const tax = (taxType ?? 'NONE') as TaxType;
  if (!TAX_TYPES.includes(tax)) return res.status(400).json({ message: 'Invalid tax type' });

  const rate = num(gstRate);
  if (tax !== 'NONE' && (rate <= 0 || rate > 100)) {
    return res.status(400).json({ message: 'GST rate must be between 0 and 100' });
  }

  const parsed = parseLineItems(lineItems);
  if ('error' in parsed) return res.status(400).json({ message: parsed.error });

  const breakup = computeTax(parsed.amount, tax, rate);
  const requestedStatus: Status = status === 'SENT' ? 'SENT' : 'DRAFT';

  try {
    // Read outside the transaction: it is only the prefix, and holding the
    // settings read inside would widen the window the sequence row is locked
    // for with nothing gained.
    const { invoicePrefix } = await getSettings();

    const invoice = await prisma.$transaction(async (tx) => {
      const invoiceNumber = await nextInvoiceNumber(tx, invDate, invoicePrefix);
      return tx.invoice.create({
        data: {
          invoiceNumber,
          clientName: String(clientName).trim(),
          clientGstin: String(clientGstin ?? '').trim().toUpperCase() || null,
          clientAddress: String(clientAddress ?? '').trim() || null,
          clientState: String(clientState ?? '').trim() || null,
          clientEmail: String(clientEmail ?? '').trim().toLowerCase() || null,
          invoiceDate: invDate,
          dueDate: due,
          amount: parsed.amount,
          taxType: tax,
          ...breakup,
          status: requestedStatus,
          notes: String(notes ?? '').trim() || null,
          createdById: req.user?.staffId ?? null,
          lineItems: { create: parsed.lines },
        },
        include: INVOICE_INCLUDE,
      });
    });

    res.status(201).json(invoice);
  } catch (err) {
    console.error('[invoices] create failed:', err);
    res.status(500).json({ message: 'Server error' });
  }
};

export const updateInvoice = async (req: AuthRequest, res: Response) => {
  const id = Number(req.params.id);
  if (!Number.isInteger(id)) return res.status(400).json({ message: 'Invalid id' });

  const {
    clientName, clientGstin, clientAddress, clientState, clientEmail,
    invoiceDate, dueDate, taxType, gstRate, notes, lineItems,
  } = req.body as Record<string, unknown>;

  try {
    const existing = await prisma.invoice.findFirst({ where: { id, deletedAt: null } });
    if (!existing) return res.status(404).json({ message: 'Invoice not found' });

    // Once money has been received against a bill its value is part of the
    // customer's ledger — correcting it is a credit note, not an edit.
    if (num(existing.paidAmount) > 0) {
      return res.status(409).json({ message: 'This invoice has payments recorded and can no longer be edited' });
    }
    if (existing.status === 'CANCELLED') {
      return res.status(409).json({ message: 'A cancelled invoice cannot be edited' });
    }

    const invDate = parseDateOnly(invoiceDate) ?? existing.invoiceDate;
    const due = dueDate === undefined ? existing.dueDate : parseDateOnly(dueDate);
    if (due && due < invDate) return res.status(400).json({ message: 'Due date cannot be before the invoice date' });

    const tax = (taxType ?? existing.taxType) as TaxType;
    if (!TAX_TYPES.includes(tax)) return res.status(400).json({ message: 'Invalid tax type' });

    // Falls back to the rate already on the invoice, so an edit that does not
    // touch tax cannot silently re-rate it.
    const existingRate = num(existing.igstRate) || num(existing.cgstRate) * 2;
    const rate = gstRate === undefined ? existingRate : num(gstRate);
    if (tax !== 'NONE' && (rate <= 0 || rate > 100)) {
      return res.status(400).json({ message: 'GST rate must be between 0 and 100' });
    }

    const parsed = parseLineItems(lineItems);
    if ('error' in parsed) return res.status(400).json({ message: parsed.error });

    const breakup = computeTax(parsed.amount, tax, rate);

    const invoice = await prisma.$transaction(async (tx) => {
      // Lines are replaced wholesale — reconciling an edited list row by row
      // buys nothing here and gets the serial numbers wrong.
      await tx.invoiceLineItem.deleteMany({ where: { invoiceId: id } });
      return tx.invoice.update({
        where: { id },
        data: {
          clientName: String(clientName ?? existing.clientName).trim(),
          clientGstin: String(clientGstin ?? '').trim().toUpperCase() || null,
          clientAddress: String(clientAddress ?? '').trim() || null,
          clientState: String(clientState ?? '').trim() || null,
          clientEmail: String(clientEmail ?? '').trim().toLowerCase() || null,
          invoiceDate: invDate,
          dueDate: due,
          amount: parsed.amount,
          taxType: tax,
          ...breakup,
          notes: String(notes ?? '').trim() || null,
          lineItems: { create: parsed.lines },
        },
        include: INVOICE_INCLUDE,
      });
    });

    res.json(invoice);
  } catch (err) {
    console.error('[invoices] update failed:', err);
    res.status(500).json({ message: 'Server error' });
  }
};

/** Issue a draft — the point at which it becomes a real bill in the ledger. */
export const issueInvoice = async (req: AuthRequest, res: Response) => {
  const id = Number(req.params.id);
  if (!Number.isInteger(id)) return res.status(400).json({ message: 'Invalid id' });

  try {
    const existing = await prisma.invoice.findFirst({ where: { id, deletedAt: null } });
    if (!existing) return res.status(404).json({ message: 'Invoice not found' });
    if (existing.status !== 'DRAFT') return res.status(409).json({ message: 'Only a draft can be issued' });

    const invoice = await prisma.invoice.update({
      where: { id },
      data: { status: 'SENT' },
      include: INVOICE_INCLUDE,
    });
    res.json(invoice);
  } catch (err) {
    console.error('[invoices] issue failed:', err);
    res.status(500).json({ message: 'Server error' });
  }
};

export const cancelInvoice = async (req: AuthRequest, res: Response) => {
  const id = Number(req.params.id);
  if (!Number.isInteger(id)) return res.status(400).json({ message: 'Invalid id' });

  try {
    const existing = await prisma.invoice.findFirst({ where: { id, deletedAt: null } });
    if (!existing) return res.status(404).json({ message: 'Invoice not found' });
    if (num(existing.paidAmount) > 0) {
      return res.status(409).json({ message: 'An invoice with payments cannot be cancelled' });
    }

    // Cancelling keeps the row in the register as a voided bill, so the number
    // is never reused and the series has no unexplained gap.
    const invoice = await prisma.invoice.update({
      where: { id },
      data: { status: 'CANCELLED' },
      include: INVOICE_INCLUDE,
    });
    res.json(invoice);
  } catch (err) {
    console.error('[invoices] cancel failed:', err);
    res.status(500).json({ message: 'Server error' });
  }
};

export const deleteInvoice = async (req: AuthRequest, res: Response) => {
  const id = Number(req.params.id);
  if (!Number.isInteger(id)) return res.status(400).json({ message: 'Invalid id' });

  try {
    const existing = await prisma.invoice.findFirst({ where: { id, deletedAt: null } });
    if (!existing) return res.status(404).json({ message: 'Invoice not found' });
    if (num(existing.paidAmount) > 0) {
      return res.status(409).json({ message: 'An invoice with payments cannot be deleted' });
    }

    await prisma.invoice.update({ where: { id }, data: { deletedAt: new Date() } });
    res.json({ message: 'Invoice deleted' });
  } catch (err) {
    console.error('[invoices] delete failed:', err);
    res.status(500).json({ message: 'Server error' });
  }
};

// ── Payments ─────────────────────────────────────────────────────────────────

export const addPayment = async (req: AuthRequest, res: Response) => {
  const id = Number(req.params.id);
  if (!Number.isInteger(id)) return res.status(400).json({ message: 'Invalid id' });

  const { amount, paymentDate, mode, reference, notes } = req.body as Record<string, unknown>;
  const value = r2(num(amount));
  if (value <= 0) return res.status(400).json({ message: 'Payment amount must be greater than zero' });

  const modes = ['CASH', 'BANK', 'CHEQUE', 'UPI', 'OTHER'];
  const payMode = String(mode ?? 'BANK');
  if (!modes.includes(payMode)) return res.status(400).json({ message: 'Invalid payment mode' });

  try {
    const result = await prisma.$transaction(async (tx): Promise<PaymentOutcome> => {
      const invoice = await tx.invoice.findFirst({ where: { id, deletedAt: null } });
      if (!invoice) return { error: 404 as const, message: 'Invoice not found' };
      if (invoice.status === 'CANCELLED') {
        return { error: 409 as const, message: 'A cancelled invoice cannot take payments' };
      }
      if (invoice.status === 'DRAFT') {
        return { error: 409 as const, message: 'Issue the invoice before recording a payment' };
      }

      const total = num(invoice.totalAmount);
      const alreadyPaid = num(invoice.paidAmount);
      // Overpayment is refused rather than absorbed: a receipt larger than the
      // bill is a data-entry slip far more often than a real advance, and
      // silently accepting it corrupts the outstanding figure.
      if (r2(alreadyPaid + value) > r2(total) + 1) {
        return {
          error: 400 as const,
          message: `Payment exceeds the outstanding amount of ${r2(total - alreadyPaid)}`,
        };
      }

      await tx.payment.create({
        data: {
          invoiceId: id,
          amount: value,
          paymentDate: parseDateOnly(paymentDate) ?? getISTTodayUTC(),
          mode: payMode as Prisma.PaymentCreateInput['mode'],
          reference: String(reference ?? '').trim() || null,
          notes: String(notes ?? '').trim() || null,
          createdById: req.user?.staffId ?? null,
        },
      });

      const paid = r2(alreadyPaid + value);
      return {
        invoice: await tx.invoice.update({
          where: { id },
          data: { paidAmount: paid, status: statusForPayments(invoice.status as Status, total, paid) },
          include: INVOICE_INCLUDE,
        }),
      };
    });

    if (result.error !== undefined) return res.status(result.error).json({ message: result.message });
    res.status(201).json(result.invoice);
  } catch (err) {
    console.error('[invoices] addPayment failed:', err);
    res.status(500).json({ message: 'Server error' });
  }
};

export const deletePayment = async (req: AuthRequest, res: Response) => {
  const paymentId = Number(req.params.paymentId);
  if (!Number.isInteger(paymentId)) return res.status(400).json({ message: 'Invalid id' });

  try {
    const result = await prisma.$transaction(async (tx): Promise<PaymentOutcome> => {
      const payment = await tx.payment.findUnique({ where: { id: paymentId }, include: { invoice: true } });
      if (!payment) return { error: 404 as const, message: 'Payment not found' };

      await tx.payment.delete({ where: { id: paymentId } });

      // Re-summed from the rows that remain rather than subtracted, so the
      // header can never drift away from the payments behind it.
      const remaining = await tx.payment.findMany({ where: { invoiceId: payment.invoiceId } });
      const paid = r2(remaining.reduce((s, p) => s + num(p.amount), 0));
      const total = num(payment.invoice.totalAmount);

      return {
        invoice: await tx.invoice.update({
          where: { id: payment.invoiceId },
          data: { paidAmount: paid, status: statusForPayments(payment.invoice.status as Status, total, paid) },
          include: INVOICE_INCLUDE,
        }),
      };
    });

    if (result.error !== undefined) return res.status(result.error).json({ message: result.message });
    res.json(result.invoice);
  } catch (err) {
    console.error('[invoices] deletePayment failed:', err);
    res.status(500).json({ message: 'Server error' });
  }
};
