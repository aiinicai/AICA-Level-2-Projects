// Runs the Smart Recon AI batches one after another through the bridge. No React and no DOM, so it is unit-tested
// with a mocked `complete` function. Partial results are kept: a later failure never throws away earlier batches.

import type { AiErrorCode, AiProvider, AiRequest, AiResult, ReconResult, Suggestion } from '@shared/contracts'
import { AiResponseError, parseAiResponseDetailed, SMART_RECON_EFFORT, toAiRequest, type AiRequestBody, type DiscardReason } from '@engine/smart/ai'

export type RunStopCode = AiErrorCode | 'cancelled'

export interface RunProgress {
  /** Batches finished so far. */
  done: number
  total: number
}

export interface RunOutcome {
  suggestions: Suggestion[]
  /** Batches that returned a reply (readable or not). */
  completed: number
  total: number
  /** Batches whose reply could not be read as JSON (skipped, the run continues). */
  unreadable: number
  discarded: Partial<Record<DiscardReason, number>>
  usage: { inputTokens: number; outputTokens: number }
  /** Why the run stopped early, or null when every batch was sent. */
  stop: { code: RunStopCode; message: string } | null
}

export interface RunArgs {
  batches: AiRequestBody[]
  model: string
  /** AI service from Settings (default Anthropic). */
  provider?: AiProvider
  /** Saved base URL, for provider 'custom'. */
  baseUrl?: string
  result: ReconResult
  maskMap: Map<string, string>
  includeDoubtful: boolean
  complete: (req: AiRequest) => Promise<AiResult>
  /** Stops a request in flight in the main process (so Cancel also stops the API call, not just the wait). */
  cancel?: (requestId: string) => Promise<void> | void
  onProgress?: (p: RunProgress) => void
  signal?: AbortSignal
}

function newRequestId(): string {
  return globalThis.crypto.randomUUID()
}

const CANCELLED = 'Smart Recon was cancelled. Suggestions from finished batches are kept.'

/** Resolves with the bridge result, or with null as soon as the run is cancelled (then `onAbort` runs too). */
function untilAbort<T>(p: Promise<T>, signal?: AbortSignal, abortRequest?: () => void): Promise<T | null> {
  if (!signal) return p
  if (signal.aborted) {
    abortRequest?.()
    return Promise.resolve(null)
  }
  return new Promise<T | null>((resolve, reject) => {
    const onAbort = (): void => {
      abortRequest?.()
      resolve(null)
    }
    signal.addEventListener('abort', onAbort, { once: true })
    p.then(
      (v) => {
        signal.removeEventListener('abort', onAbort)
        resolve(v)
      },
      (e: unknown) => {
        signal.removeEventListener('abort', onAbort)
        reject(e)
      }
    )
  })
}

export async function runSmartReconBatches(args: RunArgs): Promise<RunOutcome> {
  const total = args.batches.length
  const out: RunOutcome = { suggestions: [], completed: 0, total, unreadable: 0, discarded: {}, usage: { inputTokens: 0, outputTokens: 0 }, stop: null }
  const used = new Set<string>()
  args.onProgress?.({ done: 0, total })
  for (const batch of args.batches) {
    if (args.signal?.aborted) {
      out.stop = { code: 'cancelled', message: CANCELLED }
      break
    }
    let res: AiResult | null
    try {
      const requestId = newRequestId()
      const req: AiRequest = { ...toAiRequest(batch, args.model, { effort: SMART_RECON_EFFORT, provider: args.provider, baseUrl: args.baseUrl }), requestId }
      const stop = (): void => {
        // Best effort: the run is already over for the user, whatever the main process answers.
        Promise.resolve()
          .then(() => args.cancel?.(requestId))
          .catch(() => undefined)
      }
      res = await untilAbort(args.complete(req), args.signal, stop)
    } catch (e) {
      // The bridge rejects only when the request itself was refused (e.g. an invalid model name in Settings).
      res = { ok: false, code: 'api', message: e instanceof Error && e.message ? e.message : 'The Smart Recon request could not be sent. Please try again.' }
    }
    if (res === null) {
      out.stop = { code: 'cancelled', message: CANCELLED }
      break
    }
    if (!res.ok) {
      out.stop = { code: res.code, message: res.message }
      break
    }
    out.completed++
    out.usage.inputTokens += res.response.inputTokens
    out.usage.outputTokens += res.response.outputTokens
    try {
      const parsed = parseAiResponseDetailed(res.response.text, args.result, args.maskMap, { includeDoubtful: args.includeDoubtful })
      for (const [k, n] of Object.entries(parsed.discarded) as Array<[DiscardReason, number]>) out.discarded[k] = (out.discarded[k] ?? 0) + n
      for (const s of parsed.suggestions) {
        const ids = [...s.aIds, ...s.bIds]
        if (ids.some((id) => used.has(id))) {
          out.discarded.reused = (out.discarded.reused ?? 0) + 1
          continue
        }
        for (const id of ids) used.add(id)
        out.suggestions.push(s)
      }
    } catch (e) {
      if (!(e instanceof AiResponseError)) throw e
      out.unreadable++
    }
    args.onProgress?.({ done: out.completed, total })
  }
  return out
}

const DISCARD_TEXT: Record<DiscardReason, string> = {
  'invalid-shape': 'malformed entry',
  'unknown-id': 'unknown line ids',
  'duplicate-id': 'line listed twice',
  'empty-side': 'lines on one side only',
  'not-available': 'line already matched',
  reused: 'line reused in another suggestion',
  unbalanced: "totals don't reconcile",
  'low-confidence': 'confidence below 50%'
}

/** "4 AI proposals were discarded by the app's checks: totals don't reconcile (3); line already matched (1)." */
export function describeDiscarded(d: Partial<Record<DiscardReason, number>>): string | null {
  const parts = (Object.entries(d) as Array<[DiscardReason, number]>).filter(([, n]) => n > 0)
  if (parts.length === 0) return null
  const total = parts.reduce((s, [, n]) => s + n, 0)
  return `${total} AI ${total === 1 ? 'proposal was' : 'proposals were'} discarded by the app's checks: ${parts.map(([k, n]) => `${DISCARD_TEXT[k]} (${n})`).join('; ')}.`
}
