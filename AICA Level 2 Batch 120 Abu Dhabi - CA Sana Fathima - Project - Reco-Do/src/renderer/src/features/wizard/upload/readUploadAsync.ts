// Reads an uploaded file in a Web Worker so large workbooks never freeze the window. Only if the worker cannot
// start does it read on the UI thread (after yielding a frame); a crash mid-read is reported, not repeated.

import { runWorkerJob } from '@/lib/workerJob'
import type { LoadedFile } from '../types'
import { readUpload } from './loadFile'
import type { ReadUploadRequest, ReadUploadResponse } from './readUpload.worker'

function onMainThread(req: ReadUploadRequest): Promise<LoadedFile> {
  return new Promise((resolve, reject) => {
    // Let the spinner paint before SheetJS parses (synchronous).
    window.setTimeout(() => {
      try {
        resolve(readUpload(req.name, req.data))
      } catch (err) {
        reject(err instanceof Error ? err : new Error('The file could not be read.'))
      }
    }, 20)
  })
}

export function readUploadAsync(name: string, data: ArrayBuffer): Promise<LoadedFile> {
  const req: ReadUploadRequest = { name, data }
  return runWorkerJob<ReadUploadRequest, ReadUploadResponse, LoadedFile>({
    start: () => new Worker(new URL('./readUpload.worker.ts', import.meta.url), { type: 'module' }),
    request: req,
    unwrap: (res) => {
      if (res.ok) return res.file
      throw new Error(res.message)
    },
    onMainThread: () => onMainThread(req),
    crashMessage: `"${name}" could not be read: reading stopped unexpectedly, possibly because the file is too large for the memory available. Close other programs and try again, or save a smaller copy of the file.`
  })
}
