/**
 * Attendance.
 *
 * A day is one Attendance row per person, summarising the AttendancePunch rows
 * beneath it. Each tap of Check In / Check Out is its own punch, so a day
 * broken by a lunch break is described honestly — the pattern is carried over
 * from the MGSG field-staff attendance module.
 */
import { Response } from 'express';
import { Prisma } from '@prisma/client';
import prisma from '../lib/prisma';
import { AuthRequest } from '../middleware/auth';
import { getISTTodayUTC, parseDateOnly, monthRange, toDateOnlyString } from '../lib/dates';
import { num } from '../lib/money';

type PunchRow = { direction: string; punchedAt: Date };

const PUNCH_FIELDS = {
  id: true, direction: true, punchedAt: true,
  latitude: true, longitude: true, locationAccuracy: true, notes: true,
} as const;

const STATUSES = ['PRESENT', 'ABSENT', 'HALF_DAY', 'WFH', 'ON_LEAVE'] as const;
type AttStatus = (typeof STATUSES)[number];

/** A second tap within this window is a stutter, not a real punch. */
const PUNCH_DEBOUNCE_MS = 60_000;

/** First IN, last OUT, and the total of the completed IN→OUT intervals. */
export function summarisePunches(punches: PunchRow[]) {
  const ordered = [...punches].sort(
    (a, b) => new Date(a.punchedAt).getTime() - new Date(b.punchedAt).getTime(),
  );

  const firstIn = ordered.find((p) => p.direction === 'IN')?.punchedAt ?? null;
  let lastOut: Date | null = null;
  for (const p of ordered) if (p.direction === 'OUT') lastOut = p.punchedAt;

  // Each IN is paired with the OUT that follows it. A trailing IN — someone
  // still at work — contributes nothing, so the total is time actually
  // completed: it never counts the lunch break, and never runs ahead of the
  // clock.
  let workedMs = 0;
  let openedAt: Date | null = null;
  for (const p of ordered) {
    if (p.direction === 'IN') {
      if (!openedAt) openedAt = p.punchedAt;
    } else if (openedAt) {
      workedMs += new Date(p.punchedAt).getTime() - new Date(openedAt).getTime();
      openedAt = null;
    }
  }

  return { firstIn, lastOut, workedMinutes: Math.max(0, Math.round(workedMs / 60000)) };
}

/** What the next tap should be, so the phone can show one honest button. */
const nextAfter = (punches: PunchRow[]): 'IN' | 'OUT' =>
  punches.length && punches[punches.length - 1].direction === 'IN' ? 'OUT' : 'IN';

/**
 * Whose attendance a user may look at: their own always, anyone's if admin.
 * Staff see only themselves — attendance is the one record where an ordinary
 * user peering at colleagues has no business justification.
 */
const canView = (user: AuthRequest['user'], staffId: number): boolean =>
  user?.role === 'ADMIN' || user?.staffId === staffId;

// ── Punches ──────────────────────────────────────────────────────────────────

export const getPunches = async (req: AuthRequest, res: Response) => {
  const { staffId: staffIdParam, date: dateParam } = req.query as Record<string, string | undefined>;

  let targetStaffId = req.user?.staffId;
  if (staffIdParam) {
    const parsed = Number(staffIdParam);
    if (!Number.isInteger(parsed)) return res.status(400).json({ message: 'Invalid staffId' });
    if (!canView(req.user, parsed)) {
      return res.status(403).json({ message: 'You can only view your own attendance' });
    }
    targetStaffId = parsed;
  }
  if (!targetStaffId) return res.status(400).json({ message: 'Staff profile required' });

  const day = dateParam ? parseDateOnly(dateParam) : getISTTodayUTC();
  if (!day) return res.status(400).json({ message: 'Invalid date' });

  try {
    const punches = await prisma.attendancePunch.findMany({
      where: { staffId: targetStaffId, date: day },
      orderBy: { punchedAt: 'asc' },
      select: PUNCH_FIELDS,
    });

    res.json({
      date: toDateOnlyString(day),
      punches,
      ...summarisePunches(punches),
      nextDirection: nextAfter(punches),
    });
  } catch (err) {
    console.error('[attendance] getPunches failed:', err);
    res.status(500).json({ message: 'Server error' });
  }
};

export const recordPunch = async (req: AuthRequest, res: Response) => {
  if (!req.user?.staffId) return res.status(400).json({ message: 'Staff profile required' });

  const staffId = req.user.staffId;
  const today = getISTTodayUTC();
  const { latitude, longitude, locationAccuracy, notes } = req.body as Record<string, unknown>;

  try {
    const existing = await prisma.attendancePunch.findMany({
      where: { staffId, date: today },
      orderBy: { punchedAt: 'asc' },
      select: PUNCH_FIELDS,
    });

    // The direction is decided here, from what is already on record, rather
    // than taken from the request. A client that thinks it is punching IN when
    // the server has an open IN would silently corrupt the day's hours, and on
    // a patchy signal a retried request is the normal case, not the edge.
    const direction = nextAfter(existing);
    const last = existing[existing.length - 1];

    // A second tap moments after the first is a double-tap or a retry of a
    // request that actually succeeded. Recording it would create a zero-length
    // shift, so report the current state instead.
    // Compared as elapsed time, not a signed difference: a punch stamped ahead
    // of the server clock would otherwise read as "just recorded" indefinitely
    // and lock the person out of punching at all.
    if (last && Math.abs(Date.now() - new Date(last.punchedAt).getTime()) < PUNCH_DEBOUNCE_MS) {
      return res.status(409).json({
        message: 'That punch was just recorded. Wait a moment before punching again.',
        date: toDateOnlyString(today),
        punches: existing,
        ...summarisePunches(existing),
        nextDirection: nextAfter(existing),
      });
    }

    const geo = {
      latitude: latitude === undefined || latitude === null ? null : new Prisma.Decimal(num(latitude)),
      longitude: longitude === undefined || longitude === null ? null : new Prisma.Decimal(num(longitude)),
      locationAccuracy:
        locationAccuracy === undefined || locationAccuracy === null
          ? null
          : new Prisma.Decimal(num(locationAccuracy)),
    };
    const punchedAt = new Date();

    // The punch and its parent day move together. A punch with no day row, or
    // a day marked present with nothing behind it, are both states the
    // attendance screens have no way to explain to whoever is looking at them.
    const result = await prisma.$transaction(async (tx) => {
      const day = await tx.attendance.upsert({
        where: { staffId_date: { staffId, date: today } },
        create: { staffId, date: today, status: 'PRESENT', checkedInAt: punchedAt },
        update: {},
      });

      await tx.attendancePunch.create({
        data: {
          attendanceId: day.id,
          staffId,
          date: today,
          direction,
          punchedAt,
          notes: String(notes ?? '').trim() || null,
          ...geo,
        },
      });

      const punches = await tx.attendancePunch.findMany({
        where: { attendanceId: day.id },
        orderBy: { punchedAt: 'asc' },
        select: PUNCH_FIELDS,
      });
      const summary = summarisePunches(punches);

      await tx.attendance.update({
        where: { id: day.id },
        data: {
          checkedInAt: summary.firstIn,
          checkOutAt: summary.lastOut,
          workedMinutes: summary.workedMinutes,
          // A day someone actually punched is present, even if it had been
          // marked otherwise by hand earlier.
          status: 'PRESENT',
        },
      });

      return { punches, summary };
    });

    res.status(201).json({
      date: toDateOnlyString(today),
      direction,
      punches: result.punches,
      ...result.summary,
      nextDirection: direction === 'IN' ? 'OUT' : 'IN',
    });
  } catch (err) {
    console.error('[attendance] recordPunch failed:', err);
    res.status(500).json({ message: 'Server error' });
  }
};

// ── Registers ────────────────────────────────────────────────────────────────

/** Everyone's attendance for one day — the register an admin looks at. */
export const getDailyRegister = async (req: AuthRequest, res: Response) => {
  const day = req.query.date ? parseDateOnly(String(req.query.date)) : getISTTodayUTC();
  if (!day) return res.status(400).json({ message: 'Invalid date' });

  try {
    const staff = await prisma.staff.findMany({
      where: { isActive: true },
      orderBy: { staffName: 'asc' },
      select: { id: true, staffName: true, designation: true },
    });

    const records = await prisma.attendance.findMany({
      where: { date: day },
      include: { punches: { orderBy: { punchedAt: 'asc' }, select: PUNCH_FIELDS } },
    });
    const byStaff = new Map(records.map((r) => [r.staffId, r]));

    // Every active person appears, with or without a record: a register that
    // silently omits whoever did not turn up is not a register.
    const rows = staff.map((s) => {
      const record = byStaff.get(s.id);
      return {
        staffId: s.id,
        staffName: s.staffName,
        designation: s.designation,
        status: record?.status ?? 'ABSENT',
        checkedInAt: record?.checkedInAt ?? null,
        checkOutAt: record?.checkOutAt ?? null,
        workedMinutes: record?.workedMinutes ?? 0,
        punchCount: record?.punches.length ?? 0,
        notes: record?.notes ?? null,
      };
    });

    res.json({
      date: toDateOnlyString(day),
      rows,
      summary: {
        total: rows.length,
        present: rows.filter((r) => r.status === 'PRESENT' || r.status === 'WFH').length,
        absent: rows.filter((r) => r.status === 'ABSENT').length,
        onLeave: rows.filter((r) => r.status === 'ON_LEAVE').length,
        halfDay: rows.filter((r) => r.status === 'HALF_DAY').length,
      },
    });
  } catch (err) {
    console.error('[attendance] getDailyRegister failed:', err);
    res.status(500).json({ message: 'Server error' });
  }
};

/** One person's month — the history screen, and the basis of the summary. */
export const getMonthlyAttendance = async (req: AuthRequest, res: Response) => {
  const year = Number(req.query.year) || new Date().getUTCFullYear();
  const month = Number(req.query.month) || new Date().getUTCMonth() + 1;
  if (month < 1 || month > 12) return res.status(400).json({ message: 'Invalid month' });

  let staffId = req.user?.staffId;
  if (req.query.staffId) {
    const parsed = Number(req.query.staffId);
    if (!Number.isInteger(parsed)) return res.status(400).json({ message: 'Invalid staffId' });
    if (!canView(req.user, parsed)) {
      return res.status(403).json({ message: 'You can only view your own attendance' });
    }
    staffId = parsed;
  }
  if (!staffId) return res.status(400).json({ message: 'Staff profile required' });

  const { start, end } = monthRange(year, month);

  try {
    const records = await prisma.attendance.findMany({
      where: { staffId, date: { gte: start, lte: end } },
      orderBy: { date: 'asc' },
      include: { punches: { orderBy: { punchedAt: 'asc' }, select: PUNCH_FIELDS } },
    });

    const days = records.map((r) => ({
      date: toDateOnlyString(r.date),
      status: r.status,
      checkedInAt: r.checkedInAt,
      checkOutAt: r.checkOutAt,
      workedMinutes: r.workedMinutes ?? 0,
      punches: r.punches,
      notes: r.notes,
    }));

    const workedMinutes = days.reduce((s, d) => s + d.workedMinutes, 0);
    const presentDays = days.filter((d) => d.status === 'PRESENT' || d.status === 'WFH').length;
    const halfDays = days.filter((d) => d.status === 'HALF_DAY').length;

    res.json({
      year,
      month,
      staffId,
      days,
      summary: {
        // A half day counts as half, which is what a payroll register needs
        // and what someone reading the screen expects the number to mean.
        daysPresent: presentDays + halfDays * 0.5,
        daysRecorded: days.length,
        onLeave: days.filter((d) => d.status === 'ON_LEAVE').length,
        workedMinutes,
        workedHours: Math.round((workedMinutes / 60) * 10) / 10,
      },
    });
  } catch (err) {
    console.error('[attendance] getMonthlyAttendance failed:', err);
    res.status(500).json({ message: 'Server error' });
  }
};

/**
 * Set a day's status by hand — leave, a holiday, a missed punch.
 *
 * Admin only, and it never touches the punches: the taps are what actually
 * happened and marking a day differently must not rewrite them.
 */
export const markAttendance = async (req: AuthRequest, res: Response) => {
  const { staffId, date, status, notes } = req.body as Record<string, unknown>;

  const id = Number(staffId);
  if (!Number.isInteger(id)) return res.status(400).json({ message: 'Invalid staffId' });

  const day = parseDateOnly(date);
  if (!day) return res.status(400).json({ message: 'Date must be YYYY-MM-DD' });
  if (day > getISTTodayUTC()) return res.status(400).json({ message: 'Cannot mark attendance for a future date' });

  const value = String(status ?? '') as AttStatus;
  if (!STATUSES.includes(value)) return res.status(400).json({ message: 'Invalid status' });

  try {
    const staff = await prisma.staff.findUnique({ where: { id } });
    if (!staff) return res.status(404).json({ message: 'Staff not found' });

    const record = await prisma.attendance.upsert({
      where: { staffId_date: { staffId: id, date: day } },
      create: { staffId: id, date: day, status: value, notes: String(notes ?? '').trim() || null },
      update: { status: value, notes: String(notes ?? '').trim() || null },
      include: { punches: { orderBy: { punchedAt: 'asc' }, select: PUNCH_FIELDS } },
    });

    res.json(record);
  } catch (err) {
    console.error('[attendance] markAttendance failed:', err);
    res.status(500).json({ message: 'Server error' });
  }
};
