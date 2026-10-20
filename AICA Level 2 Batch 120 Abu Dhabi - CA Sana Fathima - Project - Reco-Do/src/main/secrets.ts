// AI provider keys, one per provider, encrypted with Windows DPAPI (Electron safeStorage) and stored only in the
// user-data folder as ai-keys/<provider>.bin. The plain keys never leave the main process: the page only ever sees
// the masked form. The "Other (OpenAI-compatible)" base URL is kept here too (not secret, but the network
// allowlist trusts only what was saved through Settings).
//
// Older versions kept one Claude key in claude-api-key.bin; it is moved to ai-keys/anthropic.bin on first use.

import { app, safeStorage } from 'electron'
import { mkdir, readFile, rename, rm, stat, writeFile } from 'fs/promises'
import { join } from 'path'
import type { AiKeyStatus, AiProvider, AiSecretsStatus } from '../shared/contracts'
import { AI_PROVIDERS, checkBaseUrl, maskKey } from '../shared/aiProviders'

const KEY_DIR = 'ai-keys'
const LEGACY_KEY_FILE = 'claude-api-key.bin'
const CUSTOM_ENDPOINT_FILE = 'custom-endpoint.json'

function keyDir(): string {
  return join(app.getPath('userData'), KEY_DIR)
}

function keyPath(provider: AiProvider): string {
  return join(keyDir(), `${provider}.bin`)
}

async function exists(path: string): Promise<boolean> {
  try {
    await stat(path)
    return true
  } catch {
    return false
  }
}

/** Moves the old single Claude key into the Anthropic slot. Safe to call any number of times. */
export async function migrateLegacyKey(): Promise<void> {
  const legacy = join(app.getPath('userData'), LEGACY_KEY_FILE)
  if (!(await exists(legacy))) return
  const target = keyPath('anthropic')
  try {
    if (await exists(target)) {
      // A newer key is already in place; the old file is stale.
      await rm(legacy, { force: true })
      return
    }
    await mkdir(keyDir(), { recursive: true })
    await rename(legacy, target)
  } catch {
    // Another call may have moved it at the same moment; the key is then already in place.
  }
}

export async function readApiKey(provider: AiProvider = 'anthropic'): Promise<string | null> {
  if (provider === 'anthropic') await migrateLegacyKey()
  let encrypted: Buffer
  try {
    encrypted = await readFile(keyPath(provider))
  } catch {
    return null
  }
  if (!safeStorage.isEncryptionAvailable()) return null
  try {
    const key = safeStorage.decryptString(encrypted)
    return key || null
  } catch {
    // The file was written by another Windows user or is damaged: treat it as no key.
    return null
  }
}

async function oneStatus(provider: AiProvider): Promise<AiKeyStatus> {
  const key = await readApiKey(provider)
  return key ? { hasKey: true, masked: maskKey(key) } : { hasKey: false, masked: null }
}

export async function keyStatus(): Promise<AiSecretsStatus> {
  const list = await Promise.all(AI_PROVIDERS.map(async (p) => [p, await oneStatus(p)] as const))
  const providers = Object.fromEntries(list) as Record<AiProvider, AiKeyStatus>
  return { ...providers.anthropic, providers, customBaseUrl: await readCustomBaseUrl() }
}

export async function saveApiKey(provider: AiProvider, key: string): Promise<void> {
  if (!safeStorage.isEncryptionAvailable()) {
    throw new Error('Windows secure storage is not available, so the key cannot be saved safely on this computer.')
  }
  if (provider === 'anthropic') await migrateLegacyKey()
  await mkdir(keyDir(), { recursive: true })
  await writeFile(keyPath(provider), safeStorage.encryptString(key), { mode: 0o600 })
}

export async function forgetApiKey(provider: AiProvider = 'anthropic'): Promise<void> {
  if (provider === 'anthropic') {
    await migrateLegacyKey()
    await rm(join(app.getPath('userData'), LEGACY_KEY_FILE), { force: true })
  }
  await rm(keyPath(provider), { force: true })
}

// ───────────────────────── Custom base URL ─────────────────────────

/** In-memory copy of the saved custom origin, for the synchronous network filter. */
let customOriginCache: string | null = null

/** Origin ("http://localhost:1234") the custom provider may reach, as last read or saved; null when none. */
export function savedCustomOrigin(): string | null {
  return customOriginCache
}

export async function readCustomBaseUrl(): Promise<string | null> {
  let url: string | null = null
  try {
    const raw: unknown = JSON.parse(await readFile(join(keyDir(), CUSTOM_ENDPOINT_FILE), 'utf8'))
    const saved = typeof raw === 'object' && raw !== null ? (raw as { baseUrl?: unknown }).baseUrl : undefined
    if (typeof saved === 'string') {
      const c = checkBaseUrl(saved)
      if (c.ok) url = c.url
    }
  } catch {
    url = null
  }
  customOriginCache = url ? new URL(url).origin : null
  return url
}

/** Saves an already-checked base URL (or clears it with null). */
export async function saveCustomBaseUrl(url: string | null): Promise<void> {
  const file = join(keyDir(), CUSTOM_ENDPOINT_FILE)
  if (url === null) {
    await rm(file, { force: true })
    customOriginCache = null
    return
  }
  await mkdir(keyDir(), { recursive: true })
  await writeFile(file, JSON.stringify({ baseUrl: url }), { mode: 0o600 })
  customOriginCache = new URL(url).origin
}
