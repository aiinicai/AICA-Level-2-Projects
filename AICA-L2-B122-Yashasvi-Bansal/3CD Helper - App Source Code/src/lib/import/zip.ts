// Minimal ZIP reader (no dependency). Uses the browser's DecompressionStream("deflate-raw"),
// available in current Chrome, Edge, Firefox and Safari, and in workers.
export const MAX_ZIP_MB = 200;

export interface ZipEntry { name: string; data: ArrayBuffer }

const isZipName = (n: string) => /\.zip$/i.test(n);
/** Office files (.xlsx, .ods …) are ZIPs inside, so they are read as workbooks, never unpacked. */
const OFFICE_EXT = /\.(xlsx|xlsm|xlsb|xltx|xltm|ods|docx|pptx)$/i;
export const isZip = (name: string, buf?: ArrayBuffer) =>
  isZipName(name) || (!OFFICE_EXT.test(name) && !!buf && buf.byteLength > 4 && new DataView(buf).getUint32(0, true) === 0x04034b50);

async function inflateRaw(data: Uint8Array): Promise<ArrayBuffer> {
  const ds = new DecompressionStream("deflate-raw");
  const stream = new Blob([data as unknown as BlobPart]).stream().pipeThrough(ds);
  return await new Response(stream).arrayBuffer();
}

/** Files inside a ZIP (folders, hidden macOS entries and nested ZIPs' own folders skipped). Nested ZIPs are opened too. */
export async function unzip(buf: ArrayBuffer, depth = 0): Promise<ZipEntry[]> {
  const dv = new DataView(buf);
  const bytes = new Uint8Array(buf);
  // End of central directory: search backwards (comment can be up to 64 KB)
  let eocd = -1;
  for (let i = buf.byteLength - 22; i >= Math.max(0, buf.byteLength - 65557); i--) {
    if (dv.getUint32(i, true) === 0x06054b50) { eocd = i; break; }
  }
  if (eocd < 0) throw new Error("This ZIP file could not be read (it may be damaged or split into parts).");
  const count = dv.getUint16(eocd + 10, true);
  let p = dv.getUint32(eocd + 16, true);
  const out: ZipEntry[] = [];
  const dec = new TextDecoder();
  for (let n = 0; n < count; n++) {
    if (dv.getUint32(p, true) !== 0x02014b50) throw new Error("This ZIP file could not be read.");
    const flags = dv.getUint16(p + 8, true);
    const method = dv.getUint16(p + 10, true);
    const compSize = dv.getUint32(p + 20, true);
    const nameLen = dv.getUint16(p + 28, true), extraLen = dv.getUint16(p + 30, true), commentLen = dv.getUint16(p + 32, true);
    const local = dv.getUint32(p + 42, true);
    const name = dec.decode(bytes.subarray(p + 46, p + 46 + nameLen));
    p += 46 + nameLen + extraLen + commentLen;
    if (name.endsWith("/") || /(^|\/)(__MACOSX|\.DS_Store)/.test(name)) continue;
    if (flags & 1) throw new Error(`"${name}" is password-protected. Please make the ZIP without a password.`);
    const lNameLen = dv.getUint16(local + 26, true), lExtraLen = dv.getUint16(local + 28, true);
    const start = local + 30 + lNameLen + lExtraLen;
    const raw = bytes.subarray(start, start + compSize);
    let data: ArrayBuffer;
    if (method === 0) data = raw.slice().buffer;
    else if (method === 8) data = await inflateRaw(raw);
    else throw new Error(`"${name}" uses an unsupported compression method. Please re-create the ZIP with standard compression.`);
    const short = name.split("/").pop() || name;
    if (isZipName(short) && depth < 2) { (await unzip(data, depth + 1)).forEach((e) => out.push({ name: `${short}/${e.name}`, data: e.data })); continue; }
    out.push({ name: short, data });
  }
  return out;
}
