// Reads the Smart Recon AI choice (provider, model, base URL) out of Settings. Pure, so it is unit-tested.

import type { AiProvider } from '@shared/contracts'
import { AI_PROVIDER_INFO, checkBaseUrl, isAiProvider, providerHost } from '@shared/aiProviders'
import { modelFor } from '@engine/smart/ai'

/** The Settings fields this module reads (a subset of lib/db Settings). */
export interface AiSettingsFields {
  aiModel?: string
  aiProvider?: string
  aiModels?: Partial<Record<AiProvider, string>>
  aiBaseUrl?: string
}

export interface ActiveAi {
  provider: AiProvider
  /** Model actually used (the provider's default when the field is empty; '' only for an unset custom model). */
  model: string
  /** Cleaned base URL for 'custom' ('' when not set or not valid); '' for the other providers. */
  baseUrl: string
  /** Host the rows go to, e.g. "api.openai.com" (null for 'custom' without a valid base URL). */
  host: string | null
  /** Picker label, e.g. "OpenAI (ChatGPT)". */
  label: string
  /** Short name, e.g. "OpenAI"; for 'custom' the host. */
  shortName: string
}

/** The model typed in Settings for a provider ('' when none). The Anthropic model lives in the older aiModel field. */
export function storedModel(s: AiSettingsFields, provider: AiProvider): string {
  const m = s.aiModels?.[provider]
  if (typeof m === 'string' && m.trim()) return m.trim()
  return provider === 'anthropic' ? (s.aiModel ?? '').trim() : ''
}

export function activeAi(s: AiSettingsFields): ActiveAi {
  const provider: AiProvider = isAiProvider(s.aiProvider) ? s.aiProvider : 'anthropic'
  const check = provider === 'custom' && s.aiBaseUrl ? checkBaseUrl(s.aiBaseUrl) : null
  const baseUrl = check && check.ok ? check.url : ''
  const host = providerHost(provider, baseUrl)
  return {
    provider,
    model: modelFor(provider, storedModel(s, provider)),
    baseUrl,
    host,
    label: AI_PROVIDER_INFO[provider].label,
    shortName: provider === 'custom' ? (host ?? 'Custom service') : AI_PROVIDER_INFO[provider].name
  }
}
