/**
 * Safe JSON POST helper for server-side /api/ai/* endpoints.
 * Prevents raw "Unexpected token '<', <!doctype ... is not valid JSON" errors
 * by safely inspecting response text and retrying once on transient HTML / 502-504 cold-start responses.
 */
export async function postAiJson<T extends Record<string, unknown>>(
  url: string,
  payload: unknown
): Promise<T> {
  const attempt = async (): Promise<{ ok: boolean; status: number; data: T | null; isHtml: boolean; rawText: string }> => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 35000);
    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
        credentials: 'same-origin',
        cache: 'no-store',
        body: JSON.stringify(payload),
        signal: controller.signal,
      });
      const rawText = await res.text();
      const trimmed = rawText.trim();
      const isHtml = /^<!doctype\s+html|^<html/i.test(trimmed) || trimmed.startsWith('<');
      if (isHtml || !trimmed) {
        return { ok: false, status: res.status, data: null, isHtml: true, rawText: trimmed };
      }
      try {
        const parsed = JSON.parse(trimmed) as T;
        return { ok: res.ok, status: res.status, data: parsed, isHtml: false, rawText: trimmed };
      } catch {
        return { ok: false, status: res.status, data: null, isHtml: false, rawText: trimmed };
      }
    } finally {
      clearTimeout(timer);
    }
  };

  let result = await attempt();

  // Retry once automatically on transient HTML proxy/cold-start or 502/503/504 responses
  if (!result.ok && (result.isHtml || result.status === 502 || result.status === 503 || result.status === 504)) {
    await new Promise((resolve) => setTimeout(resolve, 1400));
    result = await attempt();
  }

  if (result.data) {
    if (!result.ok || (typeof result.data.error === 'string' && result.data.error)) {
      throw new Error(
        (typeof result.data.error === 'string' && result.data.error) ||
          `AI request failed (HTTP ${result.status}).`
      );
    }
    return result.data;
  }

  if (result.isHtml) {
    throw new Error(
      'AI server was restarting or warming up and returned an HTML page instead of JSON. Please wait a moment and try again.'
    );
  }

  throw new Error(`AI service returned an unexpected response (HTTP ${result.status}). Please retry.`);
}
