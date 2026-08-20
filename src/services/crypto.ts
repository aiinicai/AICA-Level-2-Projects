/**
 * Secure Encryption & Key Masking Utility for Multi-Tenant Credentials
 */

// Internal master entropy salt for tenant-isolated encryption
const MASTER_SALT = 'KILITRADE_SECURE_ENCLAVE_2026_AES_KEY';

/**
 * Encrypts a plaintext secret string using XOR + salted character substitution + Base64 encoding.
 * Stored safely in the database state as an encrypted payload.
 */
export function encryptSecret(plaintext: string, companyId: string = 'global'): string {
  if (!plaintext || plaintext.trim() === '') return '';
  
  const combinedSalt = `${MASTER_SALT}::${companyId}`;
  const textBytes = new TextEncoder().encode(plaintext);
  const saltBytes = new TextEncoder().encode(combinedSalt);
  
  const encryptedBytes = new Uint8Array(textBytes.length);
  for (let i = 0; i < textBytes.length; i++) {
    const saltByte = saltBytes[i % saltBytes.length];
    // XOR with position-dependent shift
    encryptedBytes[i] = textBytes[i] ^ saltByte ^ ((i * 17) % 256);
  }
  
  // Convert to base64
  let binary = '';
  for (let i = 0; i < encryptedBytes.byteLength; i++) {
    binary += String.fromCharCode(encryptedBytes[i]);
  }
  const base64Enc = btoa(binary);
  return `enc:v1:${base64Enc}`;
}

/**
 * Decrypts an encrypted ciphertext payload back to plaintext.
 */
export function decryptSecret(ciphertext: string, companyId: string = 'global'): string {
  if (!ciphertext || !ciphertext.startsWith('enc:v1:')) return '';
  
  try {
    const base64Data = ciphertext.replace('enc:v1:', '');
    const binary = atob(base64Data);
    const encryptedBytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      encryptedBytes[i] = binary.charCodeAt(i);
    }
    
    const combinedSalt = `${MASTER_SALT}::${companyId}`;
    const saltBytes = new TextEncoder().encode(combinedSalt);
    
    const decryptedBytes = new Uint8Array(encryptedBytes.length);
    for (let i = 0; i < encryptedBytes.length; i++) {
      const saltByte = saltBytes[i % saltBytes.length];
      decryptedBytes[i] = encryptedBytes[i] ^ saltByte ^ ((i * 17) % 256);
    }
    
    return new TextDecoder().decode(decryptedBytes);
  } catch (err) {
    console.error('Failed to decrypt credential:', err);
    return '';
  }
}

/**
 * Generates a standard masked preview for API keys (e.g. "sk-ant••••••••••••••••c28f" or "••••••••••••••••").
 * Never reveals the full secret.
 */
export function maskSecret(secret: string): string {
  if (!secret) return '';
  const trimmed = secret.trim();
  if (trimmed.length <= 8) {
    return '••••••••';
  }
  
  // Show prefix (first 4 chars) and suffix (last 4 chars)
  const prefix = trimmed.slice(0, 4);
  const suffix = trimmed.slice(-4);
  const maskLength = Math.min(16, Math.max(8, trimmed.length - 8));
  return `${prefix}${'•'.repeat(maskLength)}${suffix}`;
}
