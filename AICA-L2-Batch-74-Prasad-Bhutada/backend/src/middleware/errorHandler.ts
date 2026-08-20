import { Request, Response, NextFunction } from 'express';
import { AppError, logger } from '../utils/logger';

export function errorHandler(err: unknown, req: Request, res: Response, _next: NextFunction) {
  if (err instanceof AppError) {
    logger.warn(`AppError on ${req.method} ${req.path}: ${err.message}`);
    return res.status(err.statusCode).json({ success: false, message: err.userMessage });
  }

  const error = err as Error;
  logger.error(`Unhandled error on ${req.method} ${req.path}: ${error.stack || error.message}`);
  return res.status(500).json({
    success: false,
    message: 'Something went wrong on our end. The issue has been logged - please try again or contact IT support.',
  });
}

export function notFoundHandler(req: Request, res: Response) {
  res.status(404).json({ success: false, message: 'The requested resource was not found.' });
}
