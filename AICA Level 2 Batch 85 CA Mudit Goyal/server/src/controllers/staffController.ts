import { Response } from 'express';
import bcrypt from 'bcryptjs';
import prisma from '../lib/prisma';
import { AuthRequest } from '../middleware/auth';
import { parseDateOnly } from '../lib/dates';

const SELECT = {
  id: true, staffName: true, email: true, phone: true, designation: true,
  joiningDate: true, isActive: true,
  user: { select: { id: true, email: true, role: true } },
} as const;

export const getStaff = async (req: AuthRequest, res: Response) => {
  try {
    // Everyone can see the roster (attendance screens need names); only an
    // admin can change it.
    const staff = await prisma.staff.findMany({ orderBy: { staffName: 'asc' }, select: SELECT });
    res.json(staff);
  } catch (err) {
    console.error('[staff] getStaff failed:', err);
    res.status(500).json({ message: 'Server error' });
  }
};

export const createStaff = async (req: AuthRequest, res: Response) => {
  const { staffName, email, phone, designation, joiningDate, role, password } =
    req.body as Record<string, string | undefined>;

  if (!staffName?.trim()) return res.status(400).json({ message: 'Name is required' });
  if (!email?.trim()) return res.status(400).json({ message: 'Email is required' });
  if (!password || password.length < 8) {
    return res.status(400).json({ message: 'Password must be at least 8 characters' });
  }
  if (role && !['ADMIN', 'STAFF'].includes(role)) {
    return res.status(400).json({ message: 'Role must be ADMIN or STAFF' });
  }

  const normalisedEmail = email.trim().toLowerCase();

  try {
    if (await prisma.staff.findUnique({ where: { email: normalisedEmail } })) {
      return res.status(409).json({ message: 'A staff member with that email already exists' });
    }
    if (await prisma.user.findUnique({ where: { email: normalisedEmail } })) {
      return res.status(409).json({ message: 'A login with that email already exists' });
    }

    // The staff record and its login are created together: a staff row with no
    // login can't sign in to punch attendance, which is the whole point of the
    // record existing.
    const staff = await prisma.$transaction(async (tx) => {
      const created = await tx.staff.create({
        data: {
          staffName: staffName.trim(),
          email: normalisedEmail,
          phone: phone?.trim() || null,
          designation: designation?.trim() || null,
          joiningDate: parseDateOnly(joiningDate),
        },
      });
      await tx.user.create({
        data: {
          email: normalisedEmail,
          password: await bcrypt.hash(password, 10),
          role: (role as 'ADMIN' | 'STAFF') || 'STAFF',
          staffId: created.id,
        },
      });
      return tx.staff.findUnique({ where: { id: created.id }, select: SELECT });
    });

    res.status(201).json(staff);
  } catch (err) {
    console.error('[staff] createStaff failed:', err);
    res.status(500).json({ message: 'Server error' });
  }
};

export const updateStaff = async (req: AuthRequest, res: Response) => {
  const id = Number(req.params.id);
  if (!Number.isInteger(id)) return res.status(400).json({ message: 'Invalid id' });

  const { staffName, phone, designation, joiningDate, role } = req.body as Record<string, string | undefined>;

  try {
    const existing = await prisma.staff.findUnique({ where: { id } });
    if (!existing) return res.status(404).json({ message: 'Staff not found' });

    const staff = await prisma.$transaction(async (tx) => {
      await tx.staff.update({
        where: { id },
        data: {
          staffName: staffName?.trim() || existing.staffName,
          phone: phone === undefined ? undefined : phone.trim() || null,
          designation: designation === undefined ? undefined : designation.trim() || null,
          joiningDate: joiningDate === undefined ? undefined : parseDateOnly(joiningDate),
        },
      });
      if (role && ['ADMIN', 'STAFF'].includes(role)) {
        await tx.user.updateMany({ where: { staffId: id }, data: { role: role as 'ADMIN' | 'STAFF' } });
      }
      return tx.staff.findUnique({ where: { id }, select: SELECT });
    });

    res.json(staff);
  } catch (err) {
    console.error('[staff] updateStaff failed:', err);
    res.status(500).json({ message: 'Server error' });
  }
};

export const toggleActive = async (req: AuthRequest, res: Response) => {
  const id = Number(req.params.id);
  if (!Number.isInteger(id)) return res.status(400).json({ message: 'Invalid id' });

  try {
    const staff = await prisma.staff.findUnique({ where: { id } });
    if (!staff) return res.status(404).json({ message: 'Staff not found' });

    // Deactivating yourself locks you out of the app you are using.
    if (req.user?.staffId === id && staff.isActive) {
      return res.status(400).json({ message: 'You cannot deactivate your own account' });
    }

    const updated = await prisma.staff.update({
      where: { id },
      data: { isActive: !staff.isActive },
      select: SELECT,
    });
    res.json(updated);
  } catch (err) {
    console.error('[staff] toggleActive failed:', err);
    res.status(500).json({ message: 'Server error' });
  }
};

export const resetPassword = async (req: AuthRequest, res: Response) => {
  const id = Number(req.params.id);
  const { newPassword } = req.body as { newPassword?: string };
  if (!Number.isInteger(id)) return res.status(400).json({ message: 'Invalid id' });
  if (!newPassword || newPassword.length < 8) {
    return res.status(400).json({ message: 'Password must be at least 8 characters' });
  }

  try {
    const user = await prisma.user.findUnique({ where: { staffId: id } });
    if (!user) return res.status(404).json({ message: 'No login found for this staff member' });

    await prisma.user.update({
      where: { id: user.id },
      data: { password: await bcrypt.hash(newPassword, 10) },
    });
    res.json({ message: 'Password reset' });
  } catch (err) {
    console.error('[staff] resetPassword failed:', err);
    res.status(500).json({ message: 'Server error' });
  }
};
