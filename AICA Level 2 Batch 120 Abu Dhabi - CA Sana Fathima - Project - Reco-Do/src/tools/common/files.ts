// File-name and byte helpers shared by the tool engines.

import JSZip from 'jszip'

export interface OutputFile {
  name: string
  data: Uint8Array
}

/** "Statement Aug.pdf" → "Statement Aug". Strips any folder part too. */
export function baseName(fileName: string): string {
  const leaf = fileName.split(/[\\/]/).pop() ?? fileName
  const dot = leaf.lastIndexOf('.')
  return (dot > 0 ? leaf.slice(0, dot) : leaf).trim() || 'document'
}

/** Removes characters Windows does not allow in file names. */
export function safeFileName(name: string): string {
  const cleaned = name.replace(/[<>:"/\\|?*\u0000-\u001f]/g, '_').replace(/[. ]+$/, '').trim()
  return cleaned || 'document'
}

/** Returns a plain ArrayBuffer view-safe copy of the bytes (pdf.js may detach the buffer it is given). */
export function toUint8Copy(data: ArrayBuffer | Uint8Array): Uint8Array {
  const src = data instanceof Uint8Array ? data : new Uint8Array(data)
  const out = new Uint8Array(src.byteLength)
  out.set(src)
  return out
}

/** Makes names unique: "a.pdf", "a (2).pdf", "a (3).pdf". */
export function uniqueNames(names: string[]): string[] {
  const seen = new Map<string, number>()
  return names.map((n) => {
    const key = n.toLowerCase()
    const count = (seen.get(key) ?? 0) + 1
    seen.set(key, count)
    if (count === 1) return n
    const dot = n.lastIndexOf('.')
    return dot > 0 ? `${n.slice(0, dot)} (${count})${n.slice(dot)}` : `${n} (${count})`
  })
}

/** Packs files into a .zip (DEFLATE). Duplicate names get " (2)" suffixes. */
export async function zipFiles(files: OutputFile[]): Promise<Uint8Array> {
  const zip = new JSZip()
  const names = uniqueNames(files.map((f) => safeFileName(f.name)))
  files.forEach((f, i) => zip.file(names[i], f.data, { binary: true }))
  return zip.generateAsync({ type: 'uint8array', compression: 'DEFLATE', compressionOptions: { level: 6 } })
}
