import { apiCall } from "./api.functions";

const TOKEN_KEY = "sethauto_token";
const USER_KEY = "sethauto_user";

export const tokenStore = {
  get(): string | null {
    if (typeof window === "undefined") return null;
    return window.localStorage.getItem(TOKEN_KEY);
  },
  set(token: string) {
    window.localStorage.setItem(TOKEN_KEY, token);
  },
  clear() {
    window.localStorage.removeItem(TOKEN_KEY);
    window.localStorage.removeItem(USER_KEY);
  },
};

export const USER_STORAGE_KEY = USER_KEY;

type FetchInit = {
  method?: string;
  headers?: Record<string, string>;
  body?: string;
};

export type ApiResult = {
  ok: boolean;
  status: number;
  json: () => Promise<any>;
};

/**
 * Drop-in replacement for `fetch("/api/...")` that routes the request through a
 * TanStack server function instead of a public HTTP endpoint.
 */
export async function apiFetch(path: string, init?: FetchInit): Promise<ApiResult> {
  const method = (init?.method ?? "GET").toUpperCase();
  let body: unknown = undefined;
  if (init?.body) {
    try {
      body = JSON.parse(init.body);
    } catch {
      body = undefined;
    }
  }

  try {
    const res = await apiCall({
      data: { path, method, body, token: tokenStore.get() },
    });
    const parsed = res.json ? JSON.parse(res.json) : null;
    return {
      ok: res.status >= 200 && res.status < 300,
      status: res.status,
      json: async () => parsed,
    };
  } catch (err) {
    return {
      ok: false,
      status: 500,
      json: async () => ({ error: err instanceof Error ? err.message : "Network error" }),
    };
  }
}
