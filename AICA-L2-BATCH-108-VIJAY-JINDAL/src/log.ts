import { logger } from 'firebase-functions';

const FORBIDDEN_KEYS = /phone|mobile|pan|dob|dateOfBirth|address|email|secret|key|token|password|otp/i;

/** Structured logging that strips personal data and secrets. Use for ALL function logging. */
export function safeLog(level: 'info' | 'warn' | 'error', msg: string, meta: Record<string, unknown> = {}): void {
  const clean: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(meta)) clean[k] = FORBIDDEN_KEYS.test(k) ? '[redacted]' : v;
  logger[level](msg, clean);
}
