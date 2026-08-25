/**
 * Central configuration for future backend connectivity.
 *
 * Stage 1: no backend is connected. All data is served by local mock services.
 * A later stage will point these values at a Google Apps Script web API.
 */

export const GOOGLE_APPS_SCRIPT_URL = "";

export const API_CONFIG = {
  /** Base URL of the Google Apps Script web app. Intentionally blank in Stage 1. */
  GOOGLE_APPS_SCRIPT_URL,
  /** When false, the application resolves all data through mock services. */
  useRemoteApi: false,
  requestTimeoutMs: 20000,
} as const;

export type ApiConfig = typeof API_CONFIG;
