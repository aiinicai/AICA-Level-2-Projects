// Several chosen files are sent on as one ZIP (stored, not compressed), which the reader already
// opens file by file and combines.
const CRC = (() => {
  const t = new Uint32Array(256);
  for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; }
  return t;
})();
function crc32(b: Uint8Array): number {
  let c = 0xffffffff;
  for (let i = 0; i < b.length; i++) c = CRC[(c ^ b[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

/** A ZIP of the given files (method "stored"). Names are made unique. */
export function zipStored(files: { name: string; data: Uint8Array }[]): Uint8Array {
  const enc = new TextEncoder();
  const used = new Set<string>();
  const parts: Uint8Array[] = []; const central: Uint8Array[] = [];
  let offset = 0;
  for (const f of files) {
    let name = f.name.replace(/[\\/]/g, "_") || "file";
    for (let i = 2; used.has(name.toLowerCase()); i++) name = f.name.replace(/(\.[^.]*)?$/, (ext) => ` (${i})${ext}`);
    used.add(name.toLowerCase());
    const nb = enc.encode(name); const crc = crc32(f.data); const size = f.data.length;
    const lh = new Uint8Array(30 + nb.length); const dv = new DataView(lh.buffer);
    dv.setUint32(0, 0x04034b50, true); dv.setUint16(4, 20, true); dv.setUint16(6, 0x0800, true); dv.setUint16(8, 0, true);
    dv.setUint32(14, crc, true); dv.setUint32(18, size, true); dv.setUint32(22, size, true); dv.setUint16(26, nb.length, true);
    lh.set(nb, 30);
    const ch = new Uint8Array(46 + nb.length); const cv = new DataView(ch.buffer);
    cv.setUint32(0, 0x02014b50, true); cv.setUint16(4, 20, true); cv.setUint16(6, 20, true); cv.setUint16(8, 0x0800, true);
    cv.setUint32(16, crc, true); cv.setUint32(20, size, true); cv.setUint32(24, size, true); cv.setUint16(28, nb.length, true);
    cv.setUint32(42, offset, true); ch.set(nb, 46);
    parts.push(lh, f.data); central.push(ch);
    offset += lh.length + size;
  }
  const cdSize = central.reduce((s, c) => s + c.length, 0);
  const end = new Uint8Array(22); const ev = new DataView(end.buffer);
  ev.setUint32(0, 0x06054b50, true); ev.setUint16(8, files.length, true); ev.setUint16(10, files.length, true);
  ev.setUint32(12, cdSize, true); ev.setUint32(16, offset, true);
  const out = new Uint8Array(offset + cdSize + 22);
  let p = 0;
  for (const x of [...parts, ...central, end]) { out.set(x, p); p += x.length; }
  return out;
}

/** One file stays as it is; several become one ZIP named after them. */
export async function bundleFiles(list: FileList | File[]): Promise<File | null> {
  const files = Array.from(list);
  if (!files.length) return null;
  if (files.length === 1) return files[0];
  const data = await Promise.all(files.map(async (f) => ({ name: f.name, data: new Uint8Array(await f.arrayBuffer()) })));
  const base = files[0].name.replace(/\.[^.]+$/, "").slice(0, 40);
  return new File([zipStored(data) as BlobPart], `${base} and ${files.length - 1} more.zip`, { type: "application/zip" });
}

/** A compressed ZIP (deflate, as Windows and Excel make them) of the given files; stored if the browser cannot compress. */
export async function zipDeflate(files: { name: string; data: Uint8Array }[]): Promise<Uint8Array> {
  const CS = (globalThis as any).CompressionStream;
  if (!CS) return zipStored(files);
  const enc = new TextEncoder();
  const used = new Set<string>();
  const parts: Uint8Array[] = []; const central: Uint8Array[] = [];
  let offset = 0;
  for (const f of files) {
    let name = f.name.replace(/[\\/]/g, "_") || "file";
    for (let i = 2; used.has(name.toLowerCase()); i++) name = f.name.replace(/(\.[^.]*)?$/, (ext) => ` (${i})${ext}`);
    used.add(name.toLowerCase());
    const packed = new Uint8Array(await new Response(new Blob([f.data as BlobPart]).stream().pipeThrough(new CS("deflate-raw"))).arrayBuffer());
    const nb = enc.encode(name); const crc = crc32(f.data); const size = f.data.length;
    const lh = new Uint8Array(30 + nb.length); const dv = new DataView(lh.buffer);
    dv.setUint32(0, 0x04034b50, true); dv.setUint16(4, 20, true); dv.setUint16(6, 0x0800, true); dv.setUint16(8, 8, true);
    dv.setUint32(14, crc, true); dv.setUint32(18, packed.length, true); dv.setUint32(22, size, true); dv.setUint16(26, nb.length, true);
    lh.set(nb, 30);
    const ch = new Uint8Array(46 + nb.length); const cv = new DataView(ch.buffer);
    cv.setUint32(0, 0x02014b50, true); cv.setUint16(4, 20, true); cv.setUint16(6, 20, true); cv.setUint16(8, 0x0800, true); cv.setUint16(10, 8, true);
    cv.setUint32(16, crc, true); cv.setUint32(20, packed.length, true); cv.setUint32(24, size, true); cv.setUint16(28, nb.length, true);
    cv.setUint32(42, offset, true); ch.set(nb, 46);
    parts.push(lh, packed); central.push(ch);
    offset += lh.length + packed.length;
  }
  const cdSize = central.reduce((s, c) => s + c.length, 0);
  const end = new Uint8Array(22); const ev = new DataView(end.buffer);
  ev.setUint32(0, 0x06054b50, true); ev.setUint16(8, files.length, true); ev.setUint16(10, files.length, true);
  ev.setUint32(12, cdSize, true); ev.setUint32(16, offset, true);
  const out = new Uint8Array(offset + cdSize + 22);
  let p = 0;
  for (const x of [...parts, ...central, end]) { out.set(x, p); p += x.length; }
  return out;
}
