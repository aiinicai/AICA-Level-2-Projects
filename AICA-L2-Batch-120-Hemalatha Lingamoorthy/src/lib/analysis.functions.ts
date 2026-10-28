import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";
import { analysisJsonSchema, analysisSchema, type Analysis } from "./schema";

const input = z.object({
  audioBase64: z.string().min(100).max(14_000_000),
  durationSec: z.number().min(0.5).max(305),
  mode: z.string().max(40),
  referenceText: z.string().max(10_000).optional(),
});

type Result = { ok: true; analysis: Analysis } | { ok: false; error: string; retryable: boolean };

const MODEL = "google/gemini-3.8-flash";

async function callOnce(data: z.infer<typeof input>, apiKey: string): Promise<Result> {
  const ref = data.referenceText
    ? `\nThe speaker was asked to read this exact text. Flag skipped, substituted or misread words as mispronunciations with the intended word as suggestion:\n"""${data.referenceText}"""`
    : "";
  const prompt = `You are an expert speech and articulation coach. Analyse this ${data.durationSec.toFixed(1)}s recording (practice mode: ${data.mode}).
Transcribe VERBATIM including every filler (um, uh, like, you know, basically, actually, so, right, kind of, sort of), stutter, repetition and false start.
"words" must list every spoken token of the verbatim transcript in order with its approximate start time in seconds.
Filler timestamps are in seconds. repeated_words covers immediate repetitions like "I I" or "the the". weak_phrases are hedges like "I guess", "maybe".
filler_rate_per_minute = total fillers / minutes. Scores are 0-100. top_3_priorities: exactly 3 short items. coaching_tips: 3-5 short, kind, specific, actionable tips.
rewritten_transcript: clean version with fillers and repeats removed, meaning preserved.${ref}
If there is no intelligible speech, return empty arrays, empty transcript and low scores.`;

  const res = await fetch("https://ai.gateway.lovable.dev/v1/chat/completions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Lovable-API-Key": apiKey,
      Authorization: `Bearer ${apiKey}`,
      "X-Lovable-AIG-SDK": "fetch",
    },
    body: JSON.stringify({
      model: MODEL,
      stream: true,
      messages: [
        {
          role: "user",
          content: [
            { type: "text", text: prompt },
            { type: "input_audio", input_audio: { data: data.audioBase64, format: "wav" } },
          ],
        },
      ],
      response_format: {
        type: "json_schema",
        json_schema: { name: "speech_analysis", strict: true, schema: analysisJsonSchema },
      },
    }),
  });

  if (!res.ok || !res.body) {
    const body = await res.text().catch(() => "");
    console.error("AI gateway error", res.status, body.slice(0, 500));
    let msg = "Analysis failed. Please try again.";
    try { msg = JSON.parse(body)?.error?.message ?? JSON.parse(body)?.message ?? msg; } catch { /* keep */ }
    if (res.status === 402) msg = "AI credits have run out for this workspace. " + msg;
    if (res.status === 429) msg = "Too many requests right now — please wait a moment.";
    return { ok: false, error: msg, retryable: res.status === 429 || res.status >= 500 };
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  let text = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const lines = buf.split("\n");
    buf = lines.pop() ?? "";
    for (const line of lines) {
      const t = line.trim();
      if (!t.startsWith("data:")) continue;
      const payload = t.slice(5).trim();
      if (payload === "[DONE]") continue;
      try {
        const j = JSON.parse(payload);
        text += j.choices?.[0]?.delta?.content ?? "";
      } catch { /* partial */ }
    }
  }

  if (!text.trim()) return { ok: false, error: "The AI returned no analysis for this recording.", retryable: false };
  try {
    const cleaned = text.replace(/^```(?:json)?/i, "").replace(/```\s*$/, "").trim();
    const parsed = analysisSchema.safeParse(JSON.parse(cleaned));
    if (!parsed.success) {
      console.error("Schema mismatch", parsed.error.issues.slice(0, 5));
      return { ok: false, error: "The analysis came back in an unexpected shape.", retryable: true };
    }
    return { ok: true, analysis: parsed.data };
  } catch {
    return { ok: false, error: "The analysis could not be read.", retryable: true };
  }
}

export const analyzeSpeech = createServerFn({ method: "POST" })
  .inputValidator((d: unknown) => input.parse(d))
  .handler(async ({ data }): Promise<Result> => {
    const apiKey = process.env["LOVABLE_API_KEY"];
    if (!apiKey) return { ok: false, error: "AI is not configured on the server.", retryable: false };
    let last: Result = { ok: false, error: "Analysis failed.", retryable: false };
    for (let attempt = 0; attempt < 3; attempt++) {
      last = await callOnce(data, apiKey);
      if (last.ok || !last.retryable) return last;
      await new Promise((r) => setTimeout(r, 1000 * 2 ** attempt + Math.random() * 400));
    }
    return last;
  });
