// WhatsApp number check by one-time code. The person asks for a code in the app and sends "VERIFY 123456" FROM their
// WhatsApp to the firm's number — that proves the number is really theirs (an admin typing a wrong number, or someone
// confirming a number they don't hold, is caught). Same rules as start_whatsapp_verification() in migration 0010 and the
// whatsapp-webhook function: 6 digits, valid 15 minutes, 5 tries, only the SHA-256 of the code is stored.

export const CODE_TTL_MIN = 15;
export const MAX_TRIES = 5;

export function makeCode(): string {
  const n = new Uint32Array(1);
  crypto.getRandomValues(n);
  return String(n[0] % 1_000_000).padStart(6, '0');
}

export async function hashCode(code: string): Promise<string> {
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(code));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

/** "VERIFY 123456", "verify123456", "Verify: 123 456" → "123456". Anything else → undefined. */
export function parseVerifyText(text: string): string | undefined {
  const m = /^\s*verify\s*:?\s*(\d{3})\s*(\d{3})\s*$/i.exec(text);
  return m ? m[1] + m[2] : undefined;
}

/** wa.me link that opens WhatsApp with the message ready to send to the firm's number. */
export const verifyLink = (firmNumber: string, code: string) => `https://wa.me/${firmNumber.replace(/\D/g, '')}?text=${encodeURIComponent(`VERIFY ${code}`)}`;

export type VerifyOutcome = 'verified' | 'wrong' | 'expired' | 'too_many' | 'no_code';

export async function checkCode(entered: string, state: { hash?: string; expires?: string; tries?: number }, now = new Date()): Promise<VerifyOutcome> {
  if (!state.hash || !state.expires) return 'no_code';
  if ((state.tries ?? 0) >= MAX_TRIES) return 'too_many';
  if (new Date(state.expires) < now) return 'expired';
  return (await hashCode(entered)) === state.hash ? 'verified' : 'wrong';
}
