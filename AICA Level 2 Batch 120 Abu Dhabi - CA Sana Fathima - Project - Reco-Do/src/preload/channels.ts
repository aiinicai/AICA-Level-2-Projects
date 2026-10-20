// IPC channel names shared by the preload bridge and the main-process handlers.
// One channel per RecoDoBridge method; nothing else crosses the boundary.

export const IPC = {
  appInfo: 'app:info',
  openDataFolder: 'app:open-data-folder',
  filesOpen: 'files:open',
  filesSave: 'files:save',
  samplesList: 'samples:list',
  samplesRead: 'samples:read',
  pdfFromHtml: 'pdf:from-html',
  secretsStatus: 'secrets:status',
  secretsSet: 'secrets:set',
  secretsForget: 'secrets:forget',
  aiComplete: 'ai:complete',
  aiCancel: 'ai:cancel',
  aiSetCustomBaseUrl: 'ai:set-custom-base-url'
} as const

/** One-way messages for the close handshake (main asks, the page answers once pending work is saved). */
export const CLOSE_EVENTS = {
  request: 'app:close-request',
  ready: 'app:close-ready'
} as const

export type IpcChannel = (typeof IPC)[keyof typeof IPC]

/** Every handler answers with this envelope; the preload unwraps it and throws `error` as a plain Error. */
export type IpcEnvelope = { ok: true; value: unknown } | { ok: false; error: string }
