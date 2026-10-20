import { z } from "zod";

export const analysisSchema = z.object({
  verbatim_transcript: z.string(),
  fillers: z.array(z.object({ word: z.string(), count: z.number(), timestamps: z.array(z.number()) })),
  repeated_words: z.array(z.object({ phrase: z.string(), count: z.number(), context: z.string() })),
  false_starts: z.array(z.object({ text: z.string() })),
  mispronunciations: z.array(z.object({ word: z.string(), suggestion: z.string() })),
  weak_phrases: z.array(z.string()),
  filler_rate_per_minute: z.number(),
  clarity_score: z.number().min(0).max(100),
  fluency_score: z.number().min(0).max(100),
  top_3_priorities: z.array(z.string()),
  rewritten_transcript: z.string(),
  coaching_tips: z.array(z.string()),
  words: z.array(z.object({ text: z.string(), start: z.number() })),
});
export type Analysis = z.infer<typeof analysisSchema>;

const str = { type: "string" };
const num = { type: "number" };
const obj = (props: Record<string, unknown>) => ({
  type: "object",
  properties: props,
  required: Object.keys(props),
  additionalProperties: false,
});
const arr = (items: unknown) => ({ type: "array", items });

export const analysisJsonSchema = obj({
  verbatim_transcript: str,
  fillers: arr(obj({ word: str, count: num, timestamps: arr(num) })),
  repeated_words: arr(obj({ phrase: str, count: num, context: str })),
  false_starts: arr(obj({ text: str })),
  mispronunciations: arr(obj({ word: str, suggestion: str })),
  weak_phrases: arr(str),
  filler_rate_per_minute: num,
  clarity_score: num,
  fluency_score: num,
  top_3_priorities: arr(str),
  rewritten_transcript: str,
  coaching_tips: arr(str),
  words: arr(obj({ text: str, start: num })),
});

export const FILLERS = ["um", "uh", "like", "you know", "basically", "actually", "so", "right", "kind of", "sort of"];
