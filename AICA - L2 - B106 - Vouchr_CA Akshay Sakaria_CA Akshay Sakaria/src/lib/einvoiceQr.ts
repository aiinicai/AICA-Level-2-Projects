// e-Invoice signed QR (from the IRP) is a JWT. Its payload carries a `data` JSON string with
// SellerGstin, BuyerGstin, DocNo, DocTyp, DocDt (dd/mm/yyyy), TotInvVal, ItemCnt, MainHsnCode, Irn, IrnDt.
// Decoding gives the details; verifyQrSignature() checks the IRP's signature with the public key the CA firm saved from
// the official e-invoice portal. Without that key the result is 'unchecked' — never assumed genuine.

export interface EInvoiceData {
  sellerGstin: string;
  buyerGstin?: string;
  docNo: string;
  docDate: string; // yyyy-mm-dd
  totalValue: number;
  mainHsn?: string;
  irn?: string;
}

function b64urlDecode(s: string): string {
  const pad = s.replace(/-/g, '+').replace(/_/g, '/') + '==='.slice((s.length + 3) % 4);
  const bin = atob(pad);
  const bytes = Uint8Array.from(bin, (c) => c.charCodeAt(0));
  return new TextDecoder().decode(bytes);
}

function ddmmyyyyToIso(d: string): string {
  const m = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(d);
  return m ? `${m[3]}-${m[2]}-${m[1]}` : d;
}

export function parseEInvoiceQr(text: string): EInvoiceData | null {
  try {
    const parts = text.trim().split('.');
    if (parts.length < 2) return null;
    const payload = JSON.parse(b64urlDecode(parts[1]));
    const data = typeof payload.data === 'string' ? JSON.parse(payload.data) : payload.data ?? payload;
    if (!data?.SellerGstin || !data?.DocNo) return null;
    return {
      sellerGstin: String(data.SellerGstin),
      buyerGstin: data.BuyerGstin ? String(data.BuyerGstin) : undefined,
      docNo: String(data.DocNo),
      docDate: ddmmyyyyToIso(String(data.DocDt ?? '')),
      totalValue: Number(data.TotInvVal ?? 0),
      mainHsn: data.MainHsnCode ? String(data.MainHsnCode) : undefined,
      irn: data.Irn ? String(data.Irn) : undefined
    };
  } catch {
    return null;
  }
}

export type QrSignature = 'valid' | 'invalid' | 'unchecked';

const b64urlBytes = (s: string) => Uint8Array.from(atob(s.replace(/-/g, '+').replace(/_/g, '/') + '==='.slice((s.length + 3) % 4)), (c) => c.charCodeAt(0));

/** RS256 check of the signed QR (header.payload.signature) against the IRP public key (PEM "BEGIN PUBLIC KEY").
 *  'unchecked' = no key saved, or the QR uses an algorithm this check does not support — shown as "not checked". */
export async function verifyQrSignature(jwt: string, publicKeyPem?: string): Promise<QrSignature> {
  if (!publicKeyPem?.includes('BEGIN PUBLIC KEY')) return 'unchecked';
  const parts = jwt.trim().split('.');
  if (parts.length !== 3) return 'invalid';
  try {
    const header = JSON.parse(b64urlDecode(parts[0]));
    if (header.alg !== 'RS256') return 'unchecked';
    const der = Uint8Array.from(atob(publicKeyPem.replace(/-----[^-]+-----/g, '').replace(/\s+/g, '')), (c) => c.charCodeAt(0));
    const key = await crypto.subtle.importKey('spki', der, { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' }, false, ['verify']);
    const ok = await crypto.subtle.verify('RSASSA-PKCS1-v1_5', key, b64urlBytes(parts[2]), new TextEncoder().encode(`${parts[0]}.${parts[1]}`));
    return ok ? 'valid' : 'invalid';
  } catch {
    return 'invalid'; // a QR that cannot even be parsed as a signed token is not a genuine IRP QR
  }
}
