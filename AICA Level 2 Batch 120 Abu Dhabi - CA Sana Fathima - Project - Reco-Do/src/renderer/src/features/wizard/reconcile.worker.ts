// Runs the matching engine off the UI thread so large files (50,000 rows a side) never freeze the window.

import type { ParsedTable, ReconConfig, ReconResult } from '@shared/contracts'
import { reconcile } from '@engine/index'
import { WORKER_READY } from '@/lib/workerJob'

export interface ReconcileRequest {
  tableA: ParsedTable
  tableB: ParsedTable
  config: ReconConfig
}

export type ReconcileResponse = { ok: true; result: ReconResult } | { ok: false; message: string }

// The renderer tsconfig uses DOM types; describe the dedicated-worker scope we rely on.
const scope = self as unknown as {
  onmessage: ((e: MessageEvent<ReconcileRequest>) => void) | null
  postMessage: (message: ReconcileResponse | typeof WORKER_READY) => void
}

scope.onmessage = (e) => {
  try {
    const { tableA, tableB, config } = e.data
    scope.postMessage({ ok: true, result: reconcile(tableA, tableB, config) })
  } catch (err) {
    scope.postMessage({ ok: false, message: err instanceof Error && err.message ? err.message : 'The reconciliation could not be completed.' })
  }
}

// Tells the page the script loaded: from now on a failure is a crash, not a failure to start.
scope.postMessage(WORKER_READY)
