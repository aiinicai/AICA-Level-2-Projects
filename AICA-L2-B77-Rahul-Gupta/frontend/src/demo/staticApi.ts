/** Static-demo request handler for the GitHub Pages build.
 *
 * GETs are served from data.json — a snapshot of the real backend's responses for
 * the seeded demo (regenerate with backend/scripts/snapshot_demo.py). Simulation
 * runs through the display-only engine mirror. Session-local edits (settings,
 * preferences) mutate the in-memory snapshot so the UI stays coherent; actions
 * that genuinely need the Python backend fail with a friendly explanation.
 */
import rawData from "./data.json";
import { simulateStatic, type EngineContext } from "./simulate";

const data: Record<string, any> = JSON.parse(JSON.stringify(rawData));

const NEEDS_BACKEND =
  "This is the static GitHub Pages preview. Document upload, AI verification, the " +
  "adaptive interview, assumption changes and report generation run on the Python " +
  "backend — clone the repo and follow the README to run the full app locally.";

class StaticApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function clone<T>(v: T): T {
  return JSON.parse(JSON.stringify(v));
}

function engineContext(caseId: string): EngineContext {
  const valuation = data[`/api/valuations/${caseId}/valuation`];
  const run = valuation?.run;
  if (!run?.detail) throw new StaticApiError(422, "No valuation snapshot for this case");
  const detail = run.detail;
  return {
    inputs: detail.inputs,
    weights: detail.result.weights,
    navEquity: detail.result.methods.adjusted_nav?.equity_value ?? null,
    baseRunEv: run.enterprise_value,
  };
}

export async function staticRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const method = (options.method ?? "GET").toUpperCase();

  if (method === "GET") {
    if (path in data) return clone(data[path]) as T;
    throw new StaticApiError(404, `Not in static snapshot: ${path}`);
  }

  const body = typeof options.body === "string" ? JSON.parse(options.body) : {};

  // deterministic what-if simulation — fully client-side in the static preview
  const simMatch = path.match(/^\/api\/valuations\/([^/]+)\/simulate$/);
  if (simMatch) {
    return simulateStatic(engineContext(simMatch[1]), body.overrides ?? {}) as T;
  }

  // harmless no-ops that keep the UI coherent
  if (path.match(/\/insights\/refresh$/)) {
    const caseId = path.split("/")[3];
    return { count: (data[`/api/valuations/${caseId}/insights`] ?? []).length } as T;
  }
  if (path === "/api/settings/preferences" && method === "PUT") {
    const settings = data["/api/settings"];
    settings.preferences = { ...settings.preferences, ...body };
    return clone(settings.preferences) as T;
  }
  if (path === "/api/settings/profile" && method === "PUT") {
    const settings = data["/api/settings"];
    settings.profile = { ...settings.profile, ...body };
    return { ok: true } as T;
  }
  if (path === "/api/settings/ai" && method === "PUT") {
    if (body.api_key) throw new StaticApiError(409, NEEDS_BACKEND);
    const settings = data["/api/settings"];
    settings.ai = { ...settings.ai, ...body };
    return clone(settings.ai) as T;
  }

  // report "generation" serves the pre-generated engine report bundled with the site
  const reportMatch = path.match(/^\/api\/valuations\/([^/]+)\/reports$/);
  if (reportMatch && method === "POST") {
    const existing = data[path] ?? [];
    if (existing.length > 0) return clone(existing[0]) as T;
    throw new StaticApiError(409, NEEDS_BACKEND);
  }

  throw new StaticApiError(409, NEEDS_BACKEND);
}
