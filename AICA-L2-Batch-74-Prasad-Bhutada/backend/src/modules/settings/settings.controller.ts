import { Request, Response, NextFunction } from 'express';
import * as svc from './settings.service';
import { issueTemplateAdminToken } from '../../middleware/auth';
import { AppError } from '../../utils/logger';

/** Unauthenticated on purpose - this IS the login step for Template Management. */
export async function unlock(req: Request, res: Response, next: NextFunction) {
  try {
    const { password } = req.body;
    if (!password) throw new AppError('Please enter the Template Management password.', 400);
    const ok = await svc.verifyTemplatePassword(password);
    if (!ok) throw new AppError('Incorrect password.', 401);
    res.json({ success: true, data: { token: issueTemplateAdminToken() } });
  } catch (e) {
    next(e);
  }
}

export async function getSettings(_req: Request, res: Response, next: NextFunction) {
  try {
    res.json({ success: true, data: await svc.getAllSettings() });
  } catch (e) {
    next(e);
  }
}

export async function updateSettings(req: Request, res: Response, next: NextFunction) {
  try {
    const updates = req.body as Record<string, string>;
    for (const [key, value] of Object.entries(updates)) {
      await svc.updateSetting(key, value);
    }
    res.json({ success: true, data: await svc.getAllSettings() });
  } catch (e) {
    next(e);
  }
}

export async function changeTemplatePassword(req: Request, res: Response, next: NextFunction) {
  try {
    const { newPassword } = req.body;
    if (!newPassword || newPassword.length < 6) {
      throw new AppError('New password must be at least 6 characters.', 400);
    }
    await svc.setTemplatePassword(newPassword);
    res.json({ success: true, message: 'Template Management password updated.' });
  } catch (e) {
    next(e);
  }
}
