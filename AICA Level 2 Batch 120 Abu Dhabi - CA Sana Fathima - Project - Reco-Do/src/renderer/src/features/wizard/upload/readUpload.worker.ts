// Reads an uploaded workbook off the UI thread: SheetJS parsing of a 50,000-row file takes several seconds,
// which would otherwise freeze the window.

import { readUpload } from './loadFile'
import type { LoadedFile } from '../types'
import { WORKER_READY } from '@/lib/workerJob'

export interface ReadUploadRequest {
  name: string
  data: ArrayBuffer
}

export type ReadUploadResponse = { ok: true; file: LoadedFile } | { ok: false; message: string }

// The renderer tsconfig uses DOM types; describe the dedicated-worker scope we rely on.
const scope = self as unknown as {
  onmessage: ((e: MessageEvent<ReadUploadRequest>) => void) | null
  postMessage: (message: ReadUploadResponse | typeof WORKER_READY) => void
}

scope.onmessage = (e) => {
  try {
    scope.postMessage({ ok: true, file: readUpload(e.data.name, e.data.data) })
  } catch (err) {
    scope.postMessage({ ok: false, message: err instanceof Error && err.message ? err.message : 'The file could not be read.' })
  }
}

// Tells the page the script loaded: from now on a failure is a crash, not a failure to start.
scope.postMessage(WORKER_READY)
