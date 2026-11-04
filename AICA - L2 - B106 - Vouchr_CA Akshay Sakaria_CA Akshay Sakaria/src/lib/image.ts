import jsQR from 'jsqr';

export async function sha256Hex(blob: Blob): Promise<string> {
  const buf = await crypto.subtle.digest('SHA-256', await blob.arrayBuffer());
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

export function loadImage(file: Blob): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => { URL.revokeObjectURL(url); resolve(img); };
    img.onerror = () => { URL.revokeObjectURL(url); reject(new Error('Could not read the photo')); };
    img.src = url;
  });
}

function draw(img: HTMLImageElement, maxSide: number): HTMLCanvasElement {
  const scale = Math.min(1, maxSide / Math.max(img.naturalWidth, img.naturalHeight));
  const c = document.createElement('canvas');
  c.width = Math.round(img.naturalWidth * scale);
  c.height = Math.round(img.naturalHeight * scale);
  c.getContext('2d')!.drawImage(img, 0, 0, c.width, c.height);
  return c;
}

/** Compressed copy for upload (production → Google Drive) and preview. */
export function compress(img: HTMLImageElement, maxSide = 1600, quality = 0.75): string {
  return draw(img, maxSide).toDataURL('image/jpeg', quality);
}

/** Try a few resolutions — e-invoice QR codes are dense and small on the page. */
export function findQr(img: HTMLImageElement): string | null {
  for (const side of [1400, 2000, 1000, 700]) {
    const c = draw(img, side);
    const data = c.getContext('2d')!.getImageData(0, 0, c.width, c.height);
    const hit = jsQR(data.data, data.width, data.height, { inversionAttempts: 'attemptBoth' });
    if (hit?.data) return hit.data;
  }
  return null;
}

/** Archive copy for Drive, made AFTER the bill has been read (OCR / QR use the full-quality original).
 *  Photos only: long side ≤ 2000 px (A4 ≈ 170 dpi — still legible for audit), JPEG quality 0.8, kept only when it
 *  saves at least 15 %. PDFs are never touched — re-saving can break the digital signature on e-invoices / e-challans.
 *  Undecodable formats (e.g. HEIC on Chrome) are stored as they are. */
export const ARCHIVE_MAX_SIDE = 2000;
export async function optimiseForArchive(file: Blob, name: string): Promise<{ blob: Blob; name: string; before: number; after: number }> {
  const keep = { blob: file, name, before: file.size, after: file.size };
  if (!/^image\/(jpeg|png|webp)$/.test(file.type) || file.size < 300 * 1024) return keep;
  try {
    const img = await loadImage(file);
    const out = await new Promise<Blob | null>((res) => draw(img, ARCHIVE_MAX_SIDE).toBlob(res, 'image/jpeg', 0.8));
    if (!out || out.size > file.size * 0.85) return keep;
    return { blob: out, name: name.replace(/\.[a-z0-9]{2,5}$/i, '') + '.jpg', before: file.size, after: out.size };
  } catch {
    return keep;
  }
}
