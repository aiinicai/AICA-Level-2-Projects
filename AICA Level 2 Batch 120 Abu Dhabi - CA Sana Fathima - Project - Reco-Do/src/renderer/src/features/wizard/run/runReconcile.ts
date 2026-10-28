// Runs a reconciliation in a Web Worker so 50,000-row files never freeze the window. Only if the worker cannot
// start does it run on the UI thread (after yielding a frame); a crash mid-run is reported, not repeated.

import type { ParsedTable, ReconConfig, ReconResult } from '@shared/contracts'
import { reconcile } from '@engine/index'
import { runWorkerJob } from '@/lib/workerJob'
import type { ReconcileRequest, ReconcileResponse } from '../reconcile.worker'

function onMainThread(req: ReconcileRequest): Promise<ReconResult> {
  return new Promise((resolve, reject) => {
    // Let the progress state paint before the synchronous run starts.
    window.setTimeout(() => {
      try {
        resolve(reconcile(req.tableA, req.tableB, req.config))
      } catch (err) {
        reject(err instanceof Error ? err : new Error('The reconciliation could not be completed.'))
      }
    }, 30)
  })
}

export function runReconcile(tableA: ParsedTable, tableB: ParsedTable, config: ReconConfig): Promise<ReconResult> {
  const req: ReconcileRequest = { tableA, tableB, config }
  return runWorkerJob<ReconcileRequest, ReconcileResponse, ReconResult>({
    start: () => new Worker(new URL('../reconcile.worker.ts', import.meta.url), { type: 'module' }),
    request: req,
    unwrap: (res) => {
      if (res.ok) return res.result
      throw new Error(res.message)
    },
    onMainThread: () => onMainThread(req),
    crashMessage:
      'The reconciliation stopped unexpectedly, possibly because the files are too large for the memory available. Close other programs and try again, or split the files into smaller periods.'
  })
}
