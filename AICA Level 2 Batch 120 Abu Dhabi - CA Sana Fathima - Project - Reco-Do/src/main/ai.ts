// The app's only network call: one AI provider's API, made from the main process with the user's own key.
// Each provider runs in its own session that may reach that provider's official API origin and nothing else (for
// "Other (OpenAI-compatible)", only the base URL saved in Settings). The app window's session has all network
// access blocked.

import { session } from 'electron'
import type { AiProvider, AiRequest, AiResult } from '../shared/contracts'
import { AI_PROVIDER_INFO } from '../shared/aiProviders'
import { aiMessages, errorResult, networkResult, successResult, timeoutResult } from './aiErrors'
import { buildProviderRequest } from './aiHttp'
import { readApiKey, readCustomBaseUrl, savedCustomOrigin } from './secrets'
import { isAllowedAiRequest } from './security'

/** Long batches on current models (which think before answering) can take a few minutes without streaming. */
const TIMEOUT_MS = 300_000
const CANCELLED: AiResult = { ok: false, code: 'api', message: 'The Smart Recon request was cancelled.' }

const readySessions = new Set<AiProvider>()

function partitionFor(provider: AiProvider): string {
  // The Anthropic session keeps its original name.
  return provider === 'anthropic' ? 'reco-do-ai' : `reco-do-ai-${provider}`
}

function aiSession(provider: AiProvider): Electron.Session {
  const ses = session.fromPartition(partitionFor(provider), { cache: false })
  if (!readySessions.has(provider)) {
    // Every request (including redirects) is checked against this provider's allowed origin.
    ses.webRequest.onBeforeRequest((details, callback) => callback({ cancel: !isAllowedAiRequest(details.url, provider, savedCustomOrigin()) }))
    ses.setPermissionRequestHandler((_wc, _permission, callback) => callback(false))
    readySessions.add(provider)
  }
  return ses
}

/** Requests in flight by the renderer's request id, so Cancel can stop them. */
const inFlight = new Map<string, AbortController>()

/** Aborts the request with this id, if it is still running. */
export function cancelAi(requestId: string): void {
  inFlight.get(requestId)?.abort()
}

function isAbort(err: unknown): boolean {
  return err instanceof Error && (err.name === 'TimeoutError' || err.name === 'AbortError')
}

export async function completeAi(req: AiRequest): Promise<AiResult> {
  const provider: AiProvider = req.provider ?? 'anthropic'
  let baseUrl: string | null = null
  if (provider === 'custom') {
    baseUrl = await readCustomBaseUrl()
    if (!baseUrl || req.baseUrl !== baseUrl) {
      return {
        ok: false,
        code: 'api',
        message: 'The address of the AI service has not been saved. Open Settings & API Key, enter the base URL and click Save AI settings.'
      }
    }
  }
  const key = await readApiKey(provider)
  if (!key && AI_PROVIDER_INFO[provider].keyRequired) return { ok: false, code: 'no-key', message: aiMessages(provider)['no-key'] }

  const http = buildProviderRequest(req, key, baseUrl)
  const cancel = new AbortController()
  if (req.requestId) inFlight.set(req.requestId, cancel)
  const signal = AbortSignal.any([cancel.signal, AbortSignal.timeout(TIMEOUT_MS)])
  try {
    let response: Response
    try {
      response = await aiSession(provider).fetch(http.url, { method: 'POST', headers: http.headers, body: JSON.stringify(http.body), signal })
    } catch (err) {
      if (cancel.signal.aborted) return CANCELLED
      if (isAbort(err)) return timeoutResult(provider, baseUrl)
      return networkResult(provider, baseUrl)
    }

    let json: unknown = null
    try {
      json = await response.json()
    } catch (err) {
      if (cancel.signal.aborted) return CANCELLED
      if (isAbort(err)) return timeoutResult(provider, baseUrl)
      json = null
    }
    return response.ok ? successResult(json, provider, baseUrl) : errorResult(response.status, json, provider, baseUrl)
  } finally {
    if (req.requestId && inFlight.get(req.requestId) === cancel) inFlight.delete(req.requestId)
  }
}
