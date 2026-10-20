// Builds a small PDF protected only by an owner password (RC4 40-bit, standard security handler R2) with an
// empty user password: it opens in any reader without a password but is marked as protected against editing.
// pdf-lib cannot write encryption, so the file is assembled by hand for the tests.
import { createHash } from 'node:crypto'

const PAD = Buffer.from('28BF4E5E4E758A4164004E56FFFA01082E2E00B6D0683E802F0CA9FE6453697A', 'hex')

function rc4(key: Buffer, data: Buffer): Buffer {
  const s = Array.from({ length: 256 }, (_, i) => i)
  let j = 0
  for (let i = 0; i < 256; i++) {
    j = (j + s[i] + key[i % key.length]) & 255
    ;[s[i], s[j]] = [s[j], s[i]]
  }
  const out = Buffer.alloc(data.length)
  let i = 0
  j = 0
  for (let k = 0; k < data.length; k++) {
    i = (i + 1) & 255
    j = (j + s[i]) & 255
    ;[s[i], s[j]] = [s[j], s[i]]
    out[k] = data[k] ^ s[(s[i] + s[j]) & 255]
  }
  return out
}

const md5 = (...parts: Buffer[]): Buffer => createHash('md5').update(Buffer.concat(parts)).digest()

function padPassword(pw: string): Buffer {
  return Buffer.concat([Buffer.from(pw, 'latin1'), PAD]).subarray(0, 32)
}

/** Text drawn at (x, y) in PDF points (origin bottom-left), Helvetica 9 pt. */
export interface PdfText {
  text: string
  x: number
  y: number
}

/** A one-page A4 PDF holding `texts`, encrypted with an owner password only (no password needed to open it). */
export function ownerProtectedPdf(texts: PdfText[]): Uint8Array {
  const id = createHash('md5').update('reco-do-test').digest()
  const P = -44 // print + copy allowed, changes not allowed
  const pBytes = Buffer.alloc(4)
  pBytes.writeInt32LE(P)
  const O = rc4(md5(padPassword('owner-secret')).subarray(0, 5), padPassword(''))
  const key = md5(padPassword(''), O, pBytes, id).subarray(0, 5)
  const U = rc4(key, PAD)
  const objectKey = (num: number, gen = 0): Buffer =>
    md5(key, Buffer.from([num & 255, (num >> 8) & 255, (num >> 16) & 255, gen & 255, (gen >> 8) & 255])).subarray(0, 10)

  const content = texts.map((t) => `BT /F1 9 Tf ${t.x} ${t.y} Td (${t.text.replace(/[()\\]/g, (c) => `\\${c}`)}) Tj ET`).join('\n')
  const stream = rc4(objectKey(4), Buffer.from(content, 'latin1'))

  const chunks: Buffer[] = []
  const offsets: number[] = []
  let length = 0
  const push = (b: Buffer | string): void => {
    const buf = typeof b === 'string' ? Buffer.from(b, 'latin1') : b
    chunks.push(buf)
    length += buf.length
  }
  const obj = (num: number, body: Buffer | string): void => {
    offsets[num] = length
    push(`${num} 0 obj\n`)
    push(body)
    push('\nendobj\n')
  }
  push('%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
  obj(1, '<< /Type /Catalog /Pages 2 0 R >>')
  obj(2, '<< /Type /Pages /Kids [3 0 R] /Count 1 >>')
  obj(3, '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>')
  obj(4, Buffer.concat([Buffer.from(`<< /Length ${stream.length} >>\nstream\n`, 'latin1'), stream, Buffer.from('\nendstream', 'latin1')]))
  obj(5, '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>')
  obj(6, `<< /Filter /Standard /V 1 /R 2 /O <${O.toString('hex')}> /U <${U.toString('hex')}> /P ${P} >>`)
  const xref = length
  push(`xref\n0 7\n0000000000 65535 f \n`)
  for (let n = 1; n <= 6; n++) push(`${String(offsets[n]).padStart(10, '0')} 00000 n \n`)
  push(`trailer\n<< /Size 7 /Root 1 0 R /Encrypt 6 0 R /ID [<${id.toString('hex')}> <${id.toString('hex')}>] >>\nstartxref\n${xref}\n%%EOF\n`)
  return new Uint8Array(Buffer.concat(chunks))
}

/** A simple statement table laid out for `ownerProtectedPdf` / rotated-page tests. */
export const STATEMENT_ROWS = [
  ['Date', 'Description', 'Debit', 'Credit', 'Balance'],
  ['01/09/2026', 'Opening salary transfer', '', '10,000.00', '10,000.00'],
  ['02/09/2026', 'DEWA bill payment', '450.00', '', '9,550.00'],
  ['03/09/2026', 'Card purchase CARREFOUR', '1,234.56', '', '8,315.44']
]
export const STATEMENT_XS = [40, 120, 330, 410, 490]
