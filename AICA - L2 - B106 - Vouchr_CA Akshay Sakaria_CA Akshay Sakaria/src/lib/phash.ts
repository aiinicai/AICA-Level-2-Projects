// J — look-alike photos, step 1 (free, on the device): a difference hash (dHash) of each bill thumbnail.
// Catches the same photo sent twice, screenshots and re-saved copies. A fresh photo from another angle may NOT be caught —
// step 2 is the optional AI comparison of a chosen pair, which must quote matching details from both bills.

/** 64-bit dHash from a 9×8 grayscale grid (row-major, 72 values 0–255) as 16 hex chars. */
export function dHashFromGray(gray: number[]): string {
  let bits = '';
  for (let y = 0; y < 8; y++) for (let x = 0; x < 8; x++) bits += gray[y * 9 + x] > gray[y * 9 + x + 1] ? '1' : '0';
  let hex = '';
  for (let i = 0; i < 64; i += 4) hex += parseInt(bits.slice(i, i + 4), 2).toString(16);
  return hex;
}

export function hamming(a: string, b: string): number {
  let d = 0;
  for (let i = 0; i < a.length; i++) { let x = parseInt(a[i], 16) ^ parseInt(b[i], 16); while (x) { d += x & 1; x >>= 1; } }
  return d;
}

/** Browser only: hash of an image (data URL). */
export async function dHashOf(src: string): Promise<string> {
  const img = new Image();
  await new Promise<void>((res, rej) => { img.onload = () => res(); img.onerror = () => rej(new Error('image')); img.src = src; });
  const c = document.createElement('canvas');
  c.width = 9; c.height = 8;
  const g = c.getContext('2d')!;
  g.drawImage(img, 0, 0, 9, 8);
  const d = g.getImageData(0, 0, 9, 8).data;
  const gray: number[] = [];
  for (let i = 0; i < d.length; i += 4) gray.push(0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2]);
  return dHashFromGray(gray);
}

/** Pairs to look at: near-identical images (≤ 8 of 64 bits differ). */
export const LOOKALIKE_MAX_BITS = 8;
