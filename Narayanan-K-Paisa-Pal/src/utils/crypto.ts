// WebCrypto AES-GCM 256-bit encryption with PBKDF2 key derivation and emergency recovery keys

// Get crypto object regardless of browser or Node.js environment
function getSubtleCrypto(): SubtleCrypto {
  if (typeof window !== 'undefined' && window.crypto && window.crypto.subtle) {
    return window.crypto.subtle;
  }
  if (typeof globalThis !== 'undefined' && (globalThis as any).crypto?.subtle) {
    return (globalThis as any).crypto.subtle;
  }
  try {
    // Node.js fallback
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { webcrypto } = require('node:crypto');
    return webcrypto.subtle;
  } catch {
    throw new Error('WebCrypto subtle not available in this environment');
  }
}

function getRandomValues(array: Uint8Array): Uint8Array {
  if (typeof window !== 'undefined' && window.crypto) {
    window.crypto.getRandomValues(array as any);
    return array;
  }
  if (typeof globalThis !== 'undefined' && (globalThis as any).crypto) {
    (globalThis as any).crypto.getRandomValues(array as any);
    return array;
  }
  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { webcrypto } = require('node:crypto');
    webcrypto.getRandomValues(array as any);
    return array;
  } catch {
    for (let i = 0; i < array.length; i++) {
      array[i] = Math.floor(Math.random() * 256);
    }
    return array;
  }
}

// Convert bytes to hex string
export function bytesToHex(bytes: Uint8Array): string {
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}

// Convert hex string to bytes
export function hexToBytes(hex: string): Uint8Array {
  const clean = hex.trim();
  const bytes = new Uint8Array(clean.length / 2);
  for (let i = 0; i < bytes.length; i++) {
    bytes[i] = parseInt(clean.substring(i * 2, i * 2 + 2), 16);
  }
  return bytes;
}

// Convert string to Base64
export function stringToBase64(str: string): string {
  const bytes = new TextEncoder().encode(str);
  let binary = '';
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  if (typeof btoa !== 'undefined') {
    return btoa(binary);
  }
  return Buffer.from(binary, 'binary').toString('base64');
}

// Convert Base64 to string
export function base64ToString(base64: string): string {
  let binary: string;
  if (typeof atob !== 'undefined') {
    binary = atob(base64);
  } else {
    binary = Buffer.from(base64, 'base64').toString('binary');
  }
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return new TextDecoder().decode(bytes);
}

// Convert ArrayBuffer to Base64
export function bufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  if (typeof btoa !== 'undefined') {
    return btoa(binary);
  }
  return Buffer.from(binary, 'binary').toString('base64');
}

// Convert Base64 to ArrayBuffer
export function base64ToBuffer(base64: string): ArrayBuffer {
  let binary: string;
  if (typeof atob !== 'undefined') {
    binary = atob(base64);
  } else {
    binary = Buffer.from(base64, 'base64').toString('binary');
  }
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes.buffer;
}

// Generate random salt in hex format
export function generateSalt(byteLength = 16): string {
  const arr = new Uint8Array(byteLength);
  getRandomValues(arr);
  return bytesToHex(arr);
}

// Derive a 256-bit AES-GCM CryptoKey using PBKDF2-SHA-256 with 100,000 iterations
export async function deriveKeyFromSecret(
  secret: string,
  saltHex: string,
  iterations = 100000
): Promise<CryptoKey> {
  const subtle = getSubtleCrypto();
  const enc = new TextEncoder();
  const secretKeyMaterial = await subtle.importKey(
    'raw',
    enc.encode(secret),
    { name: 'PBKDF2' },
    false,
    ['deriveKey']
  );

  const saltBytes = hexToBytes(saltHex);

  return subtle.deriveKey(
    {
      name: 'PBKDF2',
      salt: saltBytes as any,
      iterations,
      hash: 'SHA-256',
    },
    secretKeyMaterial,
    { name: 'AES-GCM', length: 256 },
    false,
    ['encrypt', 'decrypt']
  );
}

// AES-GCM Encrypt
export async function encryptText(
  plaintext: string,
  key: CryptoKey
): Promise<{ iv: string; ciphertext: string }> {
  const subtle = getSubtleCrypto();
  const ivBytes = new Uint8Array(12); // 96-bit standard IV for AES-GCM
  getRandomValues(ivBytes);

  const enc = new TextEncoder();
  const encodedPlaintext = enc.encode(plaintext);

  const encryptedBuffer = await subtle.encrypt(
    {
      name: 'AES-GCM',
      iv: ivBytes as any,
    },
    key,
    encodedPlaintext
  );

  return {
    iv: bytesToHex(ivBytes),
    ciphertext: bufferToBase64(encryptedBuffer),
  };
}

// AES-GCM Decrypt
export async function decryptText(
  ciphertextBase64: string,
  ivHex: string,
  key: CryptoKey
): Promise<string> {
  const subtle = getSubtleCrypto();
  const ivBytes = hexToBytes(ivHex);
  const cipherBuffer = base64ToBuffer(ciphertextBase64);

  const decryptedBuffer = await subtle.decrypt(
    {
      name: 'AES-GCM',
      iv: ivBytes as any,
    },
    key,
    cipherBuffer
  );

  return new TextDecoder().decode(decryptedBuffer);
}

// Generate human-friendly, high-entropy 16-character Emergency Recovery Key
// Format: XXXX-XXXX-XXXX-XXXX using unambiguous characters (no 0/O, 1/I/L)
const SAFE_CHARS = '23456789ABCDEFGHJKMNPQRSTUVWXYZ';
export function generateEmergencyRecoveryKey(): string {
  const randomBytes = new Uint8Array(16);
  getRandomValues(randomBytes);
  const parts: string[] = [];

  for (let p = 0; p < 4; p++) {
    let segment = '';
    for (let i = 0; i < 4; i++) {
      const idx = randomBytes[p * 4 + i] % SAFE_CHARS.length;
      segment += SAFE_CHARS[idx];
    }
    parts.push(segment);
  }

  return parts.join('-');
}

// Normalize user-entered recovery key (remove spaces/hyphens, uppercase)
export function normalizeRecoveryKey(input: string): string {
  return input.toUpperCase().replace(/[^A-Z0-9]/g, '');
}

// Hash recovery key with SHA-256 and salt
export async function hashRecoveryKey(recoveryKey: string, saltHex: string): Promise<string> {
  const subtle = getSubtleCrypto();
  const normalized = normalizeRecoveryKey(recoveryKey);
  const enc = new TextEncoder();
  const data = enc.encode(`paisa_pal_rec_${saltHex}_${normalized}`);
  const hashBuffer = await subtle.digest('SHA-256', data);
  return bytesToHex(new Uint8Array(hashBuffer));
}

// Verify recovery key
export async function verifyRecoveryKey(
  recoveryKey: string,
  saltHex: string,
  storedHash: string
): Promise<boolean> {
  const computed = await hashRecoveryKey(recoveryKey, saltHex);
  return computed === storedHash;
}

// Canary token used to check whether a key decrypts correctly
export const VAULT_CANARY = 'PAISA_PAL_VAULT_ACTIVE_2026';
