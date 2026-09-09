import { Request, Response } from 'express';
import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import prisma from '../lib/prisma';
import { AuthRequest } from '../middleware/auth';

const TOKEN_TTL = '12h';

const signToken = (user: { id: number; email: string; role: string; staffId: number | null }) =>
  jwt.sign(
    { id: user.id, email: user.email, role: user.role, staffId: user.staffId ?? undefined },
    process.env.JWT_SECRET!,
    { expiresIn: TOKEN_TTL, algorithm: 'HS256' },
  );

export const login = async (req: Request, res: Response) => {
  const { email, password } = req.body as { email?: string; password?: string };
  if (typeof email !== 'string' || typeof password !== 'string') {
    return res.status(400).json({ message: 'Email and password are required' });
  }

  try {
    const user = await prisma.user.findUnique({
      where: { email: email.trim().toLowerCase() },
      include: { staff: true },
    });
    // One generic message for every failure below, so this endpoint can't be
    // used to work out which emails have accounts.
    if (!user) return res.status(401).json({ message: 'Invalid credentials' });

    const valid = await bcrypt.compare(password, user.password);
    if (!valid) return res.status(401).json({ message: 'Invalid credentials' });
    if (user.staff && !user.staff.isActive) return res.status(401).json({ message: 'Invalid credentials' });

    res.json({
      token: signToken(user),
      user: {
        id: user.id,
        email: user.email,
        role: user.role,
        staffId: user.staffId,
        staffName: user.staff?.staffName ?? null,
      },
    });
  } catch (err) {
    console.error('[auth] login failed:', err);
    res.status(500).json({ message: 'Server error' });
  }
};

export const profile = async (req: AuthRequest, res: Response) => {
  try {
    const user = await prisma.user.findUnique({
      where: { id: req.user!.id },
      include: { staff: true },
    });
    if (!user) return res.status(404).json({ message: 'User not found' });

    res.json({
      id: user.id,
      email: user.email,
      role: user.role,
      staffId: user.staffId,
      staffName: user.staff?.staffName ?? null,
      designation: user.staff?.designation ?? null,
    });
  } catch (err) {
    console.error('[auth] profile failed:', err);
    res.status(500).json({ message: 'Server error' });
  }
};

export const changePassword = async (req: AuthRequest, res: Response) => {
  const { currentPassword, newPassword } = req.body as Record<string, string | undefined>;
  if (typeof newPassword !== 'string' || newPassword.length < 8) {
    return res.status(400).json({ message: 'New password must be at least 8 characters' });
  }

  try {
    const user = await prisma.user.findUnique({ where: { id: req.user!.id } });
    if (!user) return res.status(404).json({ message: 'User not found' });

    const valid = await bcrypt.compare(currentPassword ?? '', user.password);
    if (!valid) return res.status(401).json({ message: 'Current password is incorrect' });

    await prisma.user.update({
      where: { id: user.id },
      data: { password: await bcrypt.hash(newPassword, 10) },
    });
    res.json({ message: 'Password changed' });
  } catch (err) {
    console.error('[auth] changePassword failed:', err);
    res.status(500).json({ message: 'Server error' });
  }
};
