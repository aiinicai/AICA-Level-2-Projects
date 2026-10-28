/// <reference types="vite/client" />
import type { RecoDoBridge } from '@shared/contracts'

declare global {
  /** ISO date and time of the build (electron.vite.config.ts, renderer `define`). */
  const __RECODO_BUILD_DATE__: string
  interface Window {
    recoDo: RecoDoBridge
  }
}
