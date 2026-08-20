import type { Analysis } from "./mirror-types";

const FILLERS =
  /\b(um+|uh+|erm+|like|you know|i mean|basically|actually|sort of|kind of|literally|just saying)\b/gi;
const I_LANGUAGE = /\b(i|i'm|i've|i'd|i'll|me|my|mine|myself)\b/gi;
const YOU_LANGUAGE = /\b(you|you're|you've|your|yours|yourself)\b/gi;
const BLAME = /\byou (always|never|are so|need to|should|don't ever)\b/i;
const PROBLEM_OPENERS =
  /^(we need to|there's a problem|this isn't working|i have an issue|the problem|something's wrong|i'm not happy|can we talk about)/i;

function count(text: string, pattern: RegExp) {
  return (text.match(pattern) ?? []).length;
}

/**
 * Deterministic surface counts over the person's own words. These are plain
 * measurements, not judgements — the warmth lives in the written reflection.
 */
export function metricsFromTranscript(
  transcript: string,
  airtimePercent: number,
): Analysis["metrics"] {
  const text = transcript.trim();
  const firstSentence = text.split(/(?<=[.!?])\s+/)[0] ?? "";

  const ledWith: Analysis["metrics"]["ledWith"] = !firstSentence
    ? "unclear"
    : PROBLEM_OPENERS.test(firstSentence) || BLAME.test(firstSentence)
      ? "problem"
      : "context";

  return {
    airtimePercent: Math.max(0, Math.min(100, Math.round(airtimePercent))),
    questionsAsked: count(text, /\?/g),
    iLanguage: count(text, I_LANGUAGE),
    youLanguage: count(text, YOU_LANGUAGE),
    fillerWords: count(text, FILLERS),
    ledWith,
  };
}
