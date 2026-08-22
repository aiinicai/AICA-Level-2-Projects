/**
 * Minimal, effectively free liveness checks for user-supplied provider keys.
 * Both calls only read metadata / create an empty job, so no tokens or audio
 * minutes are billed.
 */

export type KeyCheck = { ok: true } | { ok: false; message: string };

const REJECTED = "This key wasn't accepted. Double check it's correct and active.";

export async function checkAnthropicKey(key: string): Promise<KeyCheck> {
  try {
    const res = await fetch("https://api.anthropic.com/v1/models?limit=1", {
      headers: { "x-api-key": key, "anthropic-version": "2023-06-01" },
    });
    if (res.ok) return { ok: true };
    if (res.status === 401 || res.status === 403) return { ok: false, message: REJECTED };
    if (res.status === 429)
      return { ok: false, message: "Anthropic rate limited the check. Try saving again shortly." };
    return { ok: false, message: `Anthropic could not verify this key (${res.status}).` };
  } catch {
    return { ok: false, message: "Anthropic could not be reached to verify this key." };
  }
}

export async function checkSarvamKey(key: string): Promise<KeyCheck> {
  try {
    const res = await fetch("https://api.sarvam.ai/speech-to-text/job/v1/init", {
      method: "POST",
      headers: { "api-subscription-key": key, "Content-Type": "application/json" },
      body: "{}",
    });
    if (res.ok) return { ok: true };
    if (res.status === 401 || res.status === 403) return { ok: false, message: REJECTED };
    if (res.status === 429)
      return { ok: false, message: "Sarvam rate limited the check. Try saving again shortly." };
    return { ok: false, message: `Sarvam could not verify this key (${res.status}).` };
  } catch {
    return { ok: false, message: "Sarvam could not be reached to verify this key." };
  }
}
