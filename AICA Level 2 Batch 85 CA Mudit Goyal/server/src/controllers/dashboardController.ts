import { Response } from 'express';
import prisma from '../lib/prisma';
import { AuthRequest } from '../middleware/auth';
import { getISTTodayUTC, monthRange, toDateOnlyString } from '../lib/dates';
import { num, r2 } from '../lib/money';

/**
 * The landing screen: what was billed and collected this month, what is still
 * owed, and who is in today.
 */
export const getDashboard = async (req: AuthRequest, res: Response) => {
  const today = getISTTodayUTC();
  const { start, end } = monthRange(today.getUTCFullYear(), today.getUTCMonth() + 1);

  try {
    const [monthInvoices, openInvoices, todayAttendance, activeStaff, recentInvoices] =
      await Promise.all([
        prisma.invoice.findMany({
          where: { deletedAt: null, status: { not: 'CANCELLED' }, invoiceDate: { gte: start, lte: end } },
          select: { totalAmount: true, paidAmount: true },
        }),
        // Everything still owed, whenever it was raised — a receivable does not
        // stop being one because the month rolled over.
        prisma.invoice.findMany({
          where: { deletedAt: null, status: { in: ['SENT', 'PARTIALLY_PAID'] } },
          select: { totalAmount: true, paidAmount: true, dueDate: true },
        }),
        prisma.attendance.findMany({
          where: { date: today },
          select: { status: true, workedMinutes: true },
        }),
        prisma.staff.count({ where: { isActive: true } }),
        prisma.invoice.findMany({
          where: { deletedAt: null },
          orderBy: { id: 'desc' },
          take: 5,
          select: {
            id: true, invoiceNumber: true, clientName: true,
            totalAmount: true, paidAmount: true, status: true, invoiceDate: true,
          },
        }),
      ]);

    const billedThisMonth = r2(monthInvoices.reduce((s, i) => s + num(i.totalAmount), 0));
    const collectedThisMonth = r2(monthInvoices.reduce((s, i) => s + num(i.paidAmount), 0));
    const outstanding = r2(openInvoices.reduce((s, i) => s + num(i.totalAmount) - num(i.paidAmount), 0));
    const overdue = r2(
      openInvoices
        .filter((i) => i.dueDate && i.dueDate < today)
        .reduce((s, i) => s + num(i.totalAmount) - num(i.paidAmount), 0),
    );

    const presentToday = todayAttendance.filter(
      (a) => a.status === 'PRESENT' || a.status === 'WFH' || a.status === 'HALF_DAY',
    ).length;

    res.json({
      date: toDateOnlyString(today),
      invoicing: {
        billedThisMonth,
        collectedThisMonth,
        outstanding,
        overdue,
        openCount: openInvoices.length,
      },
      attendance: {
        activeStaff,
        presentToday,
        absentToday: Math.max(0, activeStaff - presentToday),
        hoursToday: Math.round((todayAttendance.reduce((s, a) => s + (a.workedMinutes ?? 0), 0) / 60) * 10) / 10,
      },
      recentInvoices,
    });
  } catch (err) {
    console.error('[dashboard] failed:', err);
    res.status(500).json({ message: 'Server error' });
  }
};
