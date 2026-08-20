/**
 * App-level encryption for user-supplied API keys.
 *
 * Keys are encrypted with AES-GCM using a key derived from MIRROR_KEY_ENC_SECRET
 * before they ever reach the database, and the ciphertext row is readable only by
 * the service role. Browser code never sees either value.
 */

const encoder = new TextEncoder();
const decoder = new TextDecoder();

async function aesKey(): Promise<CryptoKey> {
  const secret = process.env["MIRROR_KEY_ENC_SECRET"];
  if (!secret) throw new Error("Key storage is not configured on the server.");
  const digest = await crypto.subtle.digest("SHA-256", encoder.encode(secret));
  return crypto.subtle.importKey("raw", digest, "AES-GCM", false, ["encrypt", "decrypt"]);
}

function toBase64(bytes: Uint8Array): string {
  let out = "";
  for (const byte of bytes) out += String.fromCharCode(byte);
  return btoa(out);
}

function fromBase64(value: string): Uint8Array<ArrayBuffer> {
  const raw = atob(value);
  const out = new Uint8Array(new ArrayBuffer(raw.length));
  for (let i = 0; i < raw.length; i += 1) out[i] = raw.charCodeAt(i);
  return out;
}

export async function encryptSecret(plain: string): Promise<string> {
  const key = await aesKey();
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const cipher = new Uint8Array(
    await crypto.subtle.encrypt({ name: "AES-GCM", iv }, key, encoder.encode(plain)),
  );
  return `${toBase64(iv)}.${toBase64(cipher)}`;
}

export async function decryptSecret(stored: string): Promise<string> {
  const [ivPart, cipherPart] = stored.split(".");
  if (!ivPart || !cipherPart) throw new Error("Stored key is unreadable.");
  const key = await aesKey();
  const plain = await crypto.subtle.decrypt(
    { name: "AES-GCM", iv: fromBase64(ivPart) },
    key,
    fromBase64(cipherPart),
  );
  return decoder.decode(plain);
}

export function last4(value: string): string {
  return value.trim().slice(-4);
}
