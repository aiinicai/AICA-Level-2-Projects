import { bytesToHex, generateSalt, hexToBytes } from './crypto';

// Enhanced PIN hashing supporting both legacy salt and unique per-vault salt
export async function hashPin(pin: string, saltHex?: string): Promise<{ hash: string; salt: string }> {
  const enc = new TextEncoder();
  const salt = saltHex || generateSalt(16);
  // We use salt + pin to produce a collision-resistant SHA-256 digest
  const data = enc.encode(`paisapal_pin_${salt}_${pin}`);
  const hashBuffer = await crypto.subtle.digest('SHA-256', data);
  const hash = bytesToHex(new Uint8Array(hashBuffer));
  return { hash, salt };
}

// Legacy PIN hash for backwards compatibility with pre-existing un-migrated installs
export async function legacyHashPin(pin: string): Promise<string> {
  const enc = new TextEncoder();
  const data = enc.encode(`paisapal_pin_salt_${pin}`);
  const hashBuffer = await crypto.subtle.digest('SHA-256', data);
  return bytesToHex(new Uint8Array(hashBuffer));
}

export async function verifyPin(pin: string, storedHash: string, saltHex?: string): Promise<boolean> {
  if (!storedHash) return false;
  // If salt is provided, check salted hash
  if (saltHex) {
    const computed = await hashPin(pin, saltHex);
    if (computed.hash === storedHash) return true;
  }
  // Check legacy hash format
  const legacy = await legacyHashPin(pin);
  return legacy === storedHash;
}

export async function checkBiometricsSupported(): Promise<boolean> {
  if (
    typeof window !== 'undefined' &&
    window.PublicKeyCredential &&
    typeof window.PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable === 'function'
  ) {
    try {
      return await window.PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
    } catch {
      return false;
    }
  }
  return false;
}
