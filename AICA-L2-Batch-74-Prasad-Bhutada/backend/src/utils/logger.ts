import winston from 'winston';
import DailyRotateFile from 'winston-daily-rotate-file';
import path from 'path';

const logDir = path.resolve('./logs');

export const logger = winston.createLogger({
  level: process.env.NODE_ENV === 'production' ? 'info' : 'debug',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json(),
  ),
  transports: [
    new DailyRotateFile({
      dirname: logDir,
      filename: 'cadocs-%DATE%.log',
      datePattern: 'YYYY-MM-DD',
      maxFiles: '30d',
      maxSize: '20m',
    }),
    new winston.transports.Console({
      format: winston.format.combine(winston.format.colorize(), winston.format.simple()),
    }),
  ],
});

/** Custom error carrying a safe, user-facing message separate from internal detail. */
export class AppError extends Error {
  public readonly statusCode: number;
  public readonly userMessage: string;

  constructor(userMessage: string, statusCode = 400, internalMessage?: string) {
    super(internalMessage || userMessage);
    this.userMessage = userMessage;
    this.statusCode = statusCode;
  }
}
