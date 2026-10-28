// Shared helpers for the data-tool tests (Merge Files, Data Cleaner).
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

export const SAMPLES = resolve(__dirname, '../../sample-data/tools')

export function sample(name: string): ArrayBuffer {
  const b = readFileSync(resolve(SAMPLES, name))
  return b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength) as ArrayBuffer
}

export const cents = (v: unknown): number => (typeof v === 'number' ? Math.round(v * 100) : NaN)
