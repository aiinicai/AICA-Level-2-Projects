/** Anthropic Claude calls, on platform keys by default. */

export type ClaudeMessage = { role: "user" | "assistant"; content: string };
export type ClaudeUsage = { inputTokens: number; outputTokens: number; usd: number };

/** Sonnet-class pricing, per million tokens. */
const IN_PER_MTOK = 3;
const OUT_PER_MTOK = 15;

export function claudeCostUsd(inputTokens: number, outputTokens: number) {
  return Number(
    ((inputTokens / 1_000_000) * IN_PER_MTOK + (outputTokens / 1_000_000) * OUT_PER_MTOK).toFixed(
      6,
    ),
  );
}

export async function callClaude(input: {
  apiKey: string;
  model: string;
  system: string;
  messages: ClaudeMessage[];
  maxTokens?: number;
}): Promise<{ text: string; usage: ClaudeUsage }> {
  const res = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-api-key": input.apiKey,
      "anthropic-version": "2023-06-01",
    },
    body: JSON.stringify({
      model: input.model,
      max_tokens: input.maxTokens ?? 1400,
      system: input.system,
      messages: input.messages,
    }),
  });

  const body = await res.text();
  if (!res.ok) {
    let message = body.slice(0, 400);
    try {
      const parsed = JSON.parse(body) as { error?: { message?: string } };
      if (parsed.error?.message) message = parsed.error.message;
    } catch {
      /* keep raw body */
    }
    console.error(`Claude call failed [${res.status}]: ${message}`);
    if (res.status === 401) throw new Error(`The reflection service rejected the key: ${message}`);
    if (res.status === 429) throw new Error("Things are busy right now. Try again in a moment.");
    throw new Error(`The reflection could not be written (${res.status}).`);
  }

  const parsed = JSON.parse(body) as {
    content?: Array<{ type: string; text?: string }>;
    usage?: { input_tokens?: number; output_tokens?: number };
  };
  const inputTokens = parsed.usage?.input_tokens ?? 0;
  const outputTokens = parsed.usage?.output_tokens ?? 0;

  return {
    text: (parsed.content ?? [])
      .filter((part) => part.type === "text")
      .map((part) => part.text ?? "")
      .join("")
      .trim(),
    usage: { inputTokens, outputTokens, usd: claudeCostUsd(inputTokens, outputTokens) },
  };
}

export function parseJsonBlock<T>(raw: string): T {
  const cleaned = raw
    .replace(/^```(?:json)?/i, "")
    .replace(/```$/, "")
    .trim();
  const start = cleaned.indexOf("{");
  const end = cleaned.lastIndexOf("}");
  if (start === -1 || end === -1) throw new Error("The reflection came back unreadable.");
  return JSON.parse(cleaned.slice(start, end + 1)) as T;
}
