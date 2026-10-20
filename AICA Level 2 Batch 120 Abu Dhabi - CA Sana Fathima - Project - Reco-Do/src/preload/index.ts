import { contextBridge, ipcRenderer } from 'electron'
import type { RecoDoBridge } from '../shared/contracts'
import { CLOSE_EVENTS, IPC, type IpcChannel, type IpcEnvelope } from './channels'

// The only bridge between the UI and the operating system. Every call is a typed IPC request;
// no Node.js or Electron object is ever handed to the page.

const REMOTE_PREFIX = /^Error invoking remote method '[^']+':\s*(?:Error:\s*)?/

/** Invokes a main-process handler, unwraps its envelope and throws failures as plain-English Errors. */
async function invoke<T>(channel: IpcChannel, ...args: unknown[]): Promise<T> {
  let envelope: IpcEnvelope
  try {
    envelope = (await ipcRenderer.invoke(channel, ...args)) as IpcEnvelope
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err)
    throw new Error(message.replace(REMOTE_PREFIX, ''))
  }
  if (!envelope.ok) throw new Error(envelope.error)
  return envelope.value as T
}

// Close handshake: when the user closes the window, main asks first; the page finishes its registered work
// (pending saves) and answers. Main closes anyway after a time limit, so a stuck page cannot keep it open.
const closeHandlers = new Set<() => Promise<void> | void>()
ipcRenderer.on(CLOSE_EVENTS.request, () => {
  void Promise.allSettled(Array.from(closeHandlers, (h) => Promise.resolve().then(h))).then(() => ipcRenderer.send(CLOSE_EVENTS.ready))
})

const bridge: RecoDoBridge = {
  appInfo: () => invoke(IPC.appInfo),
  openDataFolder: () => invoke(IPC.openDataFolder),
  files: {
    open: (opts) => invoke(IPC.filesOpen, opts),
    save: (opts) => invoke(IPC.filesSave, opts)
  },
  samples: {
    list: () => invoke(IPC.samplesList),
    read: (path) => invoke(IPC.samplesRead, path)
  },
  pdf: {
    fromHtml: (opts) => invoke(IPC.pdfFromHtml, opts)
  },
  secrets: {
    status: () => invoke(IPC.secretsStatus),
    // (provider, key), or the older (key) form for an Anthropic key.
    setApiKey: (providerOrKey: string, key?: string) =>
      invoke(IPC.secretsSet, key === undefined ? { provider: 'anthropic', key: providerOrKey } : { provider: providerOrKey, key }),
    forgetApiKey: (provider) => invoke(IPC.secretsForget, provider ?? 'anthropic')
  },
  ai: {
    complete: (req) => invoke(IPC.aiComplete, req),
    cancel: (requestId) => invoke(IPC.aiCancel, requestId),
    setCustomBaseUrl: (baseUrl) => invoke(IPC.aiSetCustomBaseUrl, baseUrl)
  },
  lifecycle: {
    onBeforeClose: (handler) => {
      if (typeof handler !== 'function') return () => undefined
      closeHandlers.add(handler)
      return () => {
        closeHandlers.delete(handler)
      }
    }
  }
}

contextBridge.exposeInMainWorld('recoDo', bridge)
