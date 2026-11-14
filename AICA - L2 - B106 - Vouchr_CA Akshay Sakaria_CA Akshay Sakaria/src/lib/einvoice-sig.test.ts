// Signed e-invoice QR check. A key pair generated here stands in for the IRP key (the real one comes from the portal).
import { describe, expect, it } from 'vitest';
import { parseEInvoiceQr, verifyQrSignature } from './einvoiceQr';

const b64url = (b: ArrayBuffer | Uint8Array) => Buffer.from(b instanceof Uint8Array ? b : new Uint8Array(b)).toString('base64url');
const pem = (der: ArrayBuffer) => `-----BEGIN PUBLIC KEY-----\n${Buffer.from(der).toString('base64').match(/.{1,64}/g)!.join('\n')}\n-----END PUBLIC KEY-----`;

async function keyPair() {
  return crypto.subtle.generateKey({ name: 'RSASSA-PKCS1-v1_5', modulusLength: 2048, publicExponent: new Uint8Array([1, 0, 1]), hash: 'SHA-256' }, true, ['sign', 'verify']);
}
async function signedQr(priv: CryptoKey, data: Record<string, unknown>, alg = 'RS256') {
  const h = b64url(new TextEncoder().encode(JSON.stringify({ alg, typ: 'JWT' })));
  const p = b64url(new TextEncoder().encode(JSON.stringify({ data: JSON.stringify(data), iss: 'NIC' })));
  const sig = await crypto.subtle.sign('RSASSA-PKCS1-v1_5', priv, new TextEncoder().encode(`${h}.${p}`));
  return `${h}.${p}.${b64url(sig)}`;
}
const DATA = { SellerGstin: '27AAAAA0000A1Z5', DocNo: 'INV-1', DocDt: '01/10/2026', TotInvVal: 1180, Irn: 'a'.repeat(64) };

describe('signed e-invoice QR', () => {
  it('genuine QR → valid, and still decodes', async () => {
    const k = await keyPair();
    const qr = await signedQr(k.privateKey, DATA);
    expect(await verifyQrSignature(qr, pem(await crypto.subtle.exportKey('spki', k.publicKey)))).toBe('valid');
    expect(parseEInvoiceQr(qr)?.docNo).toBe('INV-1');
  });
  it('amount changed after signing → invalid', async () => {
    const k = await keyPair();
    const [h, , s] = (await signedQr(k.privateKey, DATA)).split('.');
    const forged = b64url(new TextEncoder().encode(JSON.stringify({ data: JSON.stringify({ ...DATA, TotInvVal: 11800 }) })));
    expect(await verifyQrSignature(`${h}.${forged}.${s}`, pem(await crypto.subtle.exportKey('spki', k.publicKey)))).toBe('invalid');
  });
  it('signed by another key → invalid', async () => {
    const real = await keyPair(), other = await keyPair();
    expect(await verifyQrSignature(await signedQr(other.privateKey, DATA), pem(await crypto.subtle.exportKey('spki', real.publicKey)))).toBe('invalid');
  });
  it('no key saved → unchecked (never assumed genuine)', async () => {
    const k = await keyPair();
    expect(await verifyQrSignature(await signedQr(k.privateKey, DATA), undefined)).toBe('unchecked');
  });
});
