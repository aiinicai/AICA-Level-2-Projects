// Read-only access to the bundled sample files ("Try with sample files").

import { app } from 'electron'
import { readdir, readFile, realpath, stat } from 'fs/promises'
import { join, resolve, sep } from 'path'
import type { SampleFile } from '../shared/contracts'
import { samplePathSegments } from './validate'

/**
 * Packaged: <install>/resources/sample-data (electron-builder extraResources). From source: the repository's
 * sample-data, found from this bundle's own location (out/main), so it does not depend on how Electron was started.
 */
function sampleRoot(): string {
  return app.isPackaged ? join(process.resourcesPath, 'sample-data') : join(__dirname, '..', '..', 'sample-data')
}

async function walk(root: string, rel: string[], out: SampleFile[]): Promise<void> {
  const entries = await readdir(join(root, ...rel), { withFileTypes: true })
  for (const entry of entries) {
    if (entry.name.startsWith('.')) continue
    const parts = [...rel, entry.name]
    if (entry.isDirectory()) {
      await walk(root, parts, out)
    } else if (entry.isFile()) {
      const info = await stat(join(root, ...parts))
      out.push({ path: parts.join('/'), name: entry.name, folder: rel.join('/'), size: info.size })
    }
  }
}

export async function listSamples(): Promise<SampleFile[]> {
  const out: SampleFile[] = []
  try {
    await walk(sampleRoot(), [], out)
  } catch {
    return []
  }
  return out.sort((a, b) => a.path.localeCompare(b.path))
}

export async function readSample(path: unknown): Promise<ArrayBuffer> {
  const segments = samplePathSegments(path)
  const root = await realpath(sampleRoot()).catch(() => {
    throw new Error('The sample files folder is missing from this installation.')
  })
  const target = resolve(root, ...segments)
  if (!target.startsWith(root + sep)) throw new Error('That sample file path is not allowed.')
  let real: string
  try {
    real = await realpath(target)
  } catch {
    throw new Error(`The sample file "${segments.join('/')}" was not found.`)
  }
  if (!real.startsWith(root + sep)) throw new Error('That sample file path is not allowed.')
  const buf = await readFile(real)
  return buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength) as ArrayBuffer
}
