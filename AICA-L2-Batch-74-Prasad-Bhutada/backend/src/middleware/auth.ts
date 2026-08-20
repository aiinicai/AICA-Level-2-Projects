import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';
import { config } from '../config';
import { AppError } from '../utils/logger';

export interface AuthedRequest extends Request {
  isTemplateAdmin?: boolean;
}

/**
 * Guards Template Management ("Manage Formats") endpoints only.
 * Everyday document-generation/client-management usage requires NO login,
 * per functional requirement: "No authentication required for daily users."
 */
export function requireTemplateAdmin(req: AuthedRequest, res: Response, next: NextFunction) {
  const header = req.headers.authorization;
  if (!header || !header.startsWith('Bearer ')) {
    return next(new AppError('Template management access required. Please unlock with the password.', 401));
  }
  const token = header.substring('Bearer '.length);
  try {
    const payload = jwt.verify(token, config.jwtSecret) as { scope: string };
    if (payload.scope !== 'template-admin') {
      throw new Error('wrong scope');
    }
    req.isTemplateAdmin = true;
    next();
  } catch {
    next(new AppError('Your session has expired. Please unlock Template Management again.', 401));
  }
}

export function issueTemplateAdminToken(): string {
  return jwt.sign({ scope: 'template-admin' }, config.jwtSecret, { expiresIn: '4h' });
}
