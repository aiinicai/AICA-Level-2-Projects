import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';
import prisma from '../lib/prisma';

export interface AuthRequest extends Request {
  user?: { id: number; email: string; role: string; staffId?: number };
}

export const authenticate = async (req: AuthRequest, res: Response, next: NextFunction) => {
  const token = req.headers.authorization?.split(' ')[1];
  if (!token) return res.status(401).json({ message: 'No token provided' });

  let decoded: { id: number; email: string; role: string; staffId?: number };
  try {
    decoded = jwt.verify(token, process.env.JWT_SECRET!, { algorithms: ['HS256'] }) as typeof decoded;
  } catch {
    return res.status(401).json({ message: 'Invalid token' });
  }

  try {
    // A token outlives deactivation — it stays valid until it expires — so the
    // staff record is re-checked on every request rather than trusting the
    // claim baked in at login.
    if (decoded.staffId) {
      const staff = await prisma.staff.findUnique({
        where: { id: decoded.staffId },
        select: { isActive: true },
      });
      if (!staff?.isActive) return res.status(401).json({ message: 'Account is inactive' });
    }
  } catch (err) {
    return next(err);
  }

  req.user = decoded;
  next();
};

export const requireAdmin = (req: AuthRequest, res: Response, next: NextFunction) => {
  if (req.user?.role !== 'ADMIN') {
    return res.status(403).json({ message: 'Admin access required' });
  }
  next();
};

/** Every write path needs a staff profile to attribute the row to. */
export const requireStaff = (req: AuthRequest, res: Response, next: NextFunction) => {
  if (!req.user?.staffId) {
    return res.status(400).json({ message: 'Staff profile required' });
  }
  next();
};
