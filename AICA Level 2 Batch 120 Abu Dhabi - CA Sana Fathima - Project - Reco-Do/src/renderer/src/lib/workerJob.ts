// Runs one job in a dedicated Web Worker. The worker posts WORKER_READY as soon as its script has loaded.
// Only when the worker cannot START (construction fails, or its script fails before it is ready) does the job
// run on the UI thread instead. A crash while the job runs (for example running out of memory on a huge file)
// is reported as a plain-English error: repeating the same job on the UI thread would freeze the window.

export const WORKER_READY = '__reco-do-worker-ready__'

export interface WorkerJob<Req, Res, V> {
  /** Creates the worker (may throw when workers are unavailable). */
  start: () => Worker
  request: Req
  /** Turns the worker's answer into the value, throwing a plain-English Error for a failed job. */
  unwrap: (res: Res) => V
  /** Same job on the UI thread, used only when the worker could not start. */
  onMainThread: () => Promise<V>
  /** Shown when the worker crashed mid-job. */
  crashMessage: string
}

export function runWorkerJob<Req, Res, V>(job: WorkerJob<Req, Res, V>): Promise<V> {
  let worker: Worker
  try {
    worker = job.start()
  } catch {
    return job.onMainThread()
  }
  return new Promise<V>((resolve, reject) => {
    let settled = false
    let ready = false
    const finish = (): void => {
      settled = true
      worker.terminate()
    }
    worker.onmessage = (e: MessageEvent<Res | typeof WORKER_READY>) => {
      if (settled) return
      if (e.data === WORKER_READY) {
        ready = true
        return
      }
      finish()
      try {
        resolve(job.unwrap(e.data as Res))
      } catch (err) {
        reject(err instanceof Error ? err : new Error(job.crashMessage))
      }
    }
    worker.onmessageerror = () => {
      if (settled) return
      finish()
      reject(new Error(job.crashMessage))
    }
    worker.onerror = (e) => {
      if (settled) return
      e.preventDefault()
      finish()
      if (!ready) job.onMainThread().then(resolve, reject)
      else reject(new Error(job.crashMessage))
    }
    // Copied, not transferred, so the UI-thread fallback can still use the request.
    worker.postMessage(job.request)
  })
}
