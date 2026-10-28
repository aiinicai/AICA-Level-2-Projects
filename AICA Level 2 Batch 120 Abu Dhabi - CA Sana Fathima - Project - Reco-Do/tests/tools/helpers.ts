// Shared helpers for the PDF tool tests (Node: pdf.js legacy build, tesseract.js from node_modules).
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import * as pdfjs from 'pdfjs-dist/legacy/build/pdf.mjs'
import type { PdfJsLib } from '@tools/common'

export const SAMPLES = resolve(__dirname, '../../sample-data/tools')

export function sample(name: string): ArrayBuffer {
  const b = readFileSync(resolve(SAMPLES, name))
  return b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength) as ArrayBuffer
}

export const nodePdfjs: PdfJsLib = pdfjs as unknown as PdfJsLib

export const documentParams = {
  standardFontDataUrl: resolve(__dirname, '../../node_modules/pdfjs-dist/standard_fonts') + '/'
}

/** OCR assets for Node: the package's own Node worker and core, English 4.0.0 traineddata (gzipped). All local. */
export const nodeOcr = {
  workerPath: resolve(__dirname, '../../node_modules/tesseract.js/src/worker-script/node/index.js'),
  corePath: resolve(__dirname, '../../node_modules/tesseract.js-core'),
  langPath: resolve(__dirname, '../../node_modules/@tesseract.js-data/eng/4.0.0'),
  gzip: true
}
