// Minimal Gemini API client (REST v1beta generateContent; field names per ai.google.dev/api/generate-content, checked 2026-10-31).
// Runtime-neutral (fetch only) — used by the Supabase Edge Function and by the local AI test proxy. The key is passed in by the
// server; it never reaches a browser.

export interface Part { text?: string; inline_data?: { mime_type: string; data: string } }
export interface GeminiOut { text: string; inTok?: number; outTok?: number; sources: { uri: string; title?: string }[]; finish?: string }

export async function callGemini(key: string, model: string, parts: Part[], opts: { schema?: unknown; search?: boolean; timeoutMs?: number } = {}): Promise<GeminiOut> {
  const body: Record<string, unknown> = { contents: [{ role: 'user', parts }] };
  if (opts.schema) body.generation_config = { response_mime_type: 'application/json', response_schema: opts.schema };
  if (opts.search) body.tools = [{ google_search: {} }];
  // Busy (503) or rate-limited (429) answers are temporary: retry twice with back-off (seen on the free tier, 2 Nov 2026)
  let res: Response | undefined;
  for (let attempt = 0; attempt < 3; attempt++) {
    res = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}:generateContent`, {
      method: 'POST', headers: { 'Content-Type': 'application/json', 'x-goog-api-key': key }, body: JSON.stringify(body),
      signal: AbortSignal.timeout(opts.timeoutMs ?? 90000)
    });
    if (res.status !== 503 && res.status !== 429) break;
    if (attempt < 2) await new Promise((r) => setTimeout(r, 4000 * 2 ** attempt));
  }
  if (!res!.ok) throw new Error(res!.status === 503 ? 'Gemini is busy right now — please try again in a minute.' : res!.status === 429 ? 'Gemini usage limit reached for this key — try later, or switch on billing (search needs the paid tier).' : `Gemini HTTP ${res!.status}: ${(await res!.text()).slice(0, 400)}`);
  const j = await res!.json();
  const cand = j.candidates?.[0];
  const text = (cand?.content?.parts ?? []).map((p: { text?: string }) => p.text ?? '').join('');
  // grounding fields as documented for generateContent; re-verify when the key is connected
  const sources = (cand?.groundingMetadata?.groundingChunks ?? []).map((c: { web?: { uri: string; title?: string } }) => c.web).filter(Boolean);
  return { text, inTok: j.usageMetadata?.promptTokenCount, outTok: j.usageMetadata?.candidatesTokenCount, sources, finish: cand?.finishReason };
}

/** Parses the model's JSON. A broken answer is an error, never "best effort" guessed. */
export function parseJson<T>(text: string): T {
  const t = text.trim().replace(/^```(?:json)?\s*/i, '').replace(/```$/, '');
  return JSON.parse(t) as T;
}
