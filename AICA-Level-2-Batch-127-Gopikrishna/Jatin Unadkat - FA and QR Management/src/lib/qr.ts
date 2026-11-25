import { randomBytes } from "crypto";
import QRCode from "qrcode";

// Opaque, high-entropy token — never the asset id, serial number, or any
// business data (design dossier, Section K). Base64url, 22 chars ~= 128 bits.
export function generateQrToken(): string {
  return randomBytes(16).toString("base64url");
}

export const QR_SIZE_PRESETS = {
  SMALL: { label: "Small", mm: 25 },
  MEDIUM: { label: "Medium", mm: 40 },
  LARGE: { label: "Large", mm: 60 },
} as const;

export type QrSizeKey = keyof typeof QR_SIZE_PRESETS | "CUSTOM";

export function baseUrl() {
  return process.env.NEXTAUTH_URL ?? "http://localhost:3000";
}

export function qrTargetUrl(token: string) {
  return `${baseUrl()}/a/${token}`;
}

export async function renderQrDataUrl(token: string, pixels = 300): Promise<string> {
  return QRCode.toDataURL(qrTargetUrl(token), {
    width: pixels,
    margin: 1,
    errorCorrectionLevel: "M",
  });
}

/** PNG bytes for embedding in a generated PDF (bulk label sheets, lib/qrPdf.ts). */
export async function renderQrPngBuffer(token: string, pixels = 300): Promise<Buffer> {
  return QRCode.toBuffer(qrTargetUrl(token), {
    width: pixels,
    margin: 1,
    errorCorrectionLevel: "M",
    type: "png",
  });
}
