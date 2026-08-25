/**
 * The single MIRROR pipeline.
 *
 * One experience: audio or text goes in, the session type and relationship
 * context are inferred rather than asked, and a reflection comes back. Only the
 * user's own speech is ever transcribed or analysed.
 */

import { callClaude, parseJsonBlock } from "./claude.server";
import {
  REFLECTION_SYSTEM_PROMPT,
  SAFETY_OVERRIDE,
  languageRule,
  mirrorPrompt,
  themeBlock,
} from "./prompts";

import { fetchSarvamResult, groupSpeakers, startSarvamJob } from "./sarvam.server";
import { metricsFromTranscript } from "./metrics";
import { checkSpokenAudio, checkWrittenText, NO_SPEECH_MESSAGE } from "./speech-check";
import type { Analysis, Pattern } from "./mirror-types";
import {
  assertCredit,
  chargeUsage,
  db,
  resolveKeys,
  settingsOf,
  type AccountRow,
} from "./account.server";

/** Sarvam batch speech-to-text, per audio minute. */
const SARVAM_USD_PER_MINUTE = 0.006;
/** 16 kHz mono 16-bit PCM. */
const BYTES_PER_SECOND = 32_000;

export type SpeakerChoice = { speaker: string; sample: string; seconds: number };

export type MirrorResult = {
  sessionId: string;
  sessionType: "conversation" | "recap" | "rehearsal" | "reflection";
  relationshipContext: string;
  analysis: Analysis;
  reflection: string;
};

export type JobView = {
  id: string;
  status: string;
  stageMessage: string | null;
  speakers: SpeakerChoice[];
  result: MirrorResult | null;
  error: string | null;
};

type StoredSpeaker = { speaker: string; sample: string; seconds: number; text: string };

function shortTitle(text: string) {
  return text
    .replace(/^[^A-Za-z0-9]+/, "")
    .split(/\s+/)
    .slice(0, 6)
    .join(" ")
    .replace(/[.,;:]$/, "");
}

function audioMinutes(base64: string) {
  return (base64.length * 0.75) / BYTES_PER_SECOND / 60;
}

function toView(row: Record<string, unknown>): JobView {
  const stored = (row["speaker_samples"] as StoredSpeaker[] | null) ?? [];
  const analysis = row["analysis"] as (Analysis & { reflection?: string }) | null;
  return {
    id: String(row["id"]),
    status: String(row["status"]),
    stageMessage: (row["stage_message"] as string | null) ?? null,
    speakers: stored.map((s) => ({ speaker: s.speaker, sample: s.sample, seconds: s.seconds })),
    result: analysis
      ? {
          sessionId: String(row["session_id"] ?? ""),
          sessionType: (String(row["session_type"] ?? "reflection") ||
            "reflection") as MirrorResult["sessionType"],
          relationshipContext: String(row["inferred_persona"] ?? "none"),
          analysis,
          reflection: analysis.reflection ?? "",
        }
      : null,
    error: (row["error"] as string | null) ?? null,
  };
}

/** Starts transcription for a recording. The RMS speech gate runs first. */
export async function startCapture(input: {
  account: AccountRow;
  audioBase64: string;
}): Promise<JobView> {
  if (!checkSpokenAudio(input.audioBase64).ok) throw new Error(NO_SPEECH_MESSAGE);

  const keys = await resolveKeys(input.account);
  assertCredit(input.account, keys.usingOwnKey);
  if (!keys.sarvam) throw new Error("Recording is temporarily unavailable. Try writing instead.");

  const client = await db();
  const created = await client
    .from("conversation_jobs")
    .insert({
      account_id: input.account.id,
      user_id: input.account.user_id,
      persona: "",
      goal: "",
      status: "uploading",
      stage_message: "Sending your recording for transcription",
    } as never)
    .select("*")
    .single();
  if (created.error) throw new Error(created.error.message);
  const row = created.data as Record<string, unknown>;
  const jobId = String(row["id"]);

  try {
    const sarvamJobId = await startSarvamJob({
      apiKey: keys.sarvam,
      audioBase64: input.audioBase64,
      languageCode: input.account.input_language,
    });
    await chargeUsage({
      accountId: input.account.id,
      usd: Number((audioMinutes(input.audioBase64) * SARVAM_USD_PER_MINUTE).toFixed(4)),
      sessionType: "transcription",
      usingOwnKey: keys.usingOwnKey,
    });
    const updated = await client
      .from("conversation_jobs")
      .update({
        sarvam_job_id: sarvamJobId,
        status: "transcribing",
        stage_message: "Listening for which voice is yours",
      } as never)
      .eq("id", jobId)
      .select("*")
      .single();
    return toView((updated.data ?? row) as Record<string, unknown>);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Transcription could not be started.";
    await client
      .from("conversation_jobs")
      .update({ status: "failed", error: message } as never)
      .eq("id", jobId);
    throw new Error(message);
  }
}

async function loadJob(account: AccountRow, jobId: string) {
  const client = await db();
  const { data } = await client
    .from("conversation_jobs")
    .select("*")
    .eq("id", jobId)
    .eq("account_id", account.id)
    .maybeSingle();
  if (!data) throw new Error("That recording could not be found.");
  return data as Record<string, unknown>;
}

/**
 * Diarisation decides the path. Two or more distinct speakers means someone
 * else was present, and the speaker-confirmation step is required before any
 * analysis. One speaker goes straight through as a solo session.
 */
export async function pollJob(input: { account: AccountRow; jobId: string }): Promise<JobView> {
  const client = await db();
  const row = await loadJob(input.account, input.jobId);
  if (String(row["status"]) !== "transcribing") return toView(row);

  const keys = await resolveKeys(input.account);
  const result = await fetchSarvamResult({
    apiKey: keys.sarvam,
    jobId: String(row["sarvam_job_id"] ?? ""),
  });
  if (result.state === "running") return toView(row);

  if (result.state === "failed") {
    const { data } = await client
      .from("conversation_jobs")
      .update({ status: "failed", error: result.error } as never)
      .eq("id", input.jobId)
      .select("*")
      .single();
    return toView(data as Record<string, unknown>);
  }

  const grouped = groupSpeakers(result.segments);
  if (grouped.length === 0) {
    const { data } = await client
      .from("conversation_jobs")
      .update({ status: "no_speech", error: NO_SPEECH_MESSAGE } as never)
      .eq("id", input.jobId)
      .select("*")
      .single();
    return toView(data as Record<string, unknown>);
  }


  // Held only long enough to render the confirmation screen. The other
  // speaker's text is deleted the moment the user confirms. A single speaker
  // still gets a confirmation — a lightweight "that's you, right?" — so nothing
  // is ever analysed without the person saying yes to it.
  const stored: StoredSpeaker[] = grouped.map((g) => ({
    speaker: g.speaker,
    sample: g.sample,
    seconds: Math.round(g.seconds),
    text: g.text,
  }));

  const solo = stored.length === 1;
  const { data } = await client
    .from("conversation_jobs")
    .update({
      status: solo ? "needs_solo_confirmation" : "needs_speaker_confirmation",
      stage_message: solo ? "Only one voice — confirm it's you" : "Confirm which voice is yours",
      speaker_samples: stored,
      guessed_speaker: stored[0]?.speaker ?? null,
    } as never)
    .eq("id", input.jobId)
    .select("*")
    .single();
  return toView(data as Record<string, unknown>);
}

/** The user declined the recording at the confirmation step: nothing is analysed. */
export async function discardJob(input: { account: AccountRow; jobId: string }) {
  const client = await db();
  await loadJob(input.account, input.jobId);
  await client
    .from("conversation_jobs")
    .update({
      status: "discarded",
      stage_message: null,
      transcript: null,
      speaker_samples: [],
    } as never)
    .eq("id", input.jobId);
  return { ok: true };
}

/**
 * Picks up a failed job where it stopped: re-analyse when the transcript
 * survived, otherwise re-poll the transcription job.
 */
export async function retryJob(input: { account: AccountRow; jobId: string }): Promise<JobView> {
  const client = await db();
  const row = await loadJob(input.account, input.jobId);
  const transcript = String(row["transcript"] ?? "").trim();

  if (transcript) {
    await client
      .from("conversation_jobs")
      .update({ status: "analyzing", error: null, stage_message: "Writing your reflection" } as never)
      .eq("id", input.jobId);
    return analyzeJob({
      account: input.account,
      jobId: input.jobId,
      transcript,
      airtime: 100,
      hadOtherSpeaker: Boolean(row["confirmed_speaker"]) && String(row["session_type"] ?? "") === "conversation",
      written: false,
    });
  }

  if (row["sarvam_job_id"]) {
    await client
      .from("conversation_jobs")
      .update({
        status: "transcribing",
        error: null,
        stage_message: "Listening for which voice is yours",
      } as never)
      .eq("id", input.jobId);
    return pollJob(input);
  }

  throw new Error("That recording didn't reach us — record it again and we'll pick it up.");
}


export async function confirmSpeaker(input: {
  account: AccountRow;
  jobId: string;
  speaker: string;
}): Promise<JobView> {
  const client = await db();
  const row = await loadJob(input.account, input.jobId);
  const stored = (row["speaker_samples"] as StoredSpeaker[] | null) ?? [];
  const mine = stored.find((s) => s.speaker === input.speaker);
  if (!mine) throw new Error("Pick which voice is yours to continue.");

  const totalSeconds = stored.reduce((sum, s) => sum + s.seconds, 0) || 1;
  const airtime = Math.min(100, Math.max(1, Math.round((mine.seconds / totalSeconds) * 100)));
  const transcript = mine.text.trim();

  // Everything belonging to the other speaker is discarded here, permanently.
  await client
    .from("conversation_jobs")
    .update({
      status: "analyzing",
      stage_message: "Writing your reflection",
      confirmed_speaker: input.speaker,
      transcript,
      speaker_samples: [],
    } as never)
    .eq("id", input.jobId);

  return analyzeJob({
    account: input.account,
    jobId: input.jobId,
    transcript,
    airtime,
    // One voice on the tape is a solo session, not a conversation.
    hadOtherSpeaker: stored.length > 1,
    written: false,
  });

}

/**
 * Continuity without re-injecting history: a handful of short theme phrases are
 * kept per person and carried into the next session's prompt.
 */
async function readThemes(account: AccountRow): Promise<string[]> {
  if (!account.user_id) return [];
  const client = await db();
  const { data } = await client
    .from("reflection_themes")
    .select("recent_themes")
    .eq("user_id", account.user_id)
    .maybeSingle();
  const raw = (data as { recent_themes?: unknown } | null)?.recent_themes;
  return Array.isArray(raw) ? raw.filter((t): t is string => typeof t === "string").slice(0, 6) : [];
}

async function writeThemes(account: AccountRow, previous: string[], fresh: string[]) {
  if (!account.user_id) return;
  const cleaned = fresh
    .filter((t) => typeof t === "string" && t.trim().length > 0)
    .map((t) => t.trim().slice(0, 60));
  if (cleaned.length === 0) return;
  const merged: string[] = [];
  for (const theme of [...cleaned, ...previous]) {
    if (!merged.some((m) => m.toLowerCase() === theme.toLowerCase())) merged.push(theme);
  }
  const client = await db();
  await client
    .from("reflection_themes")
    .upsert(
      { user_id: account.user_id, recent_themes: merged.slice(0, 6), updated_at: new Date().toISOString() } as never,
      { onConflict: "user_id" },
    );
}

async function runMirrorCall(input: {
  account: AccountRow;
  transcript: string;
  airtime: number;
  hadOtherSpeaker: boolean;
  written: boolean;
}): Promise<MirrorResult> {
  const keys = await resolveKeys(input.account);
  assertCredit(input.account, keys.usingOwnKey);
  const settings = settingsOf(input.account);
  const previousThemes = await readThemes(input.account);

  const { text, usage } = await callClaude({
    apiKey: keys.anthropic,
    model: settings.claude_model,
    system: `You are MIRROR: warm, observational, never scoring or shaming. You return only valid JSON when asked for JSON.\n\n${SAFETY_OVERRIDE}`,
    messages: [
      {
        role: "user",
        content: mirrorPrompt({
          hadOtherSpeaker: input.hadOtherSpeaker,
          written: input.written,
          transcript: input.transcript,
          outputLanguage: settings.output_language,
          feedbackStyle: settings.feedback_style,
          challengeLevel: settings.challenge_level,
          recentThemes: previousThemes,
        }),
      },
    ],
  });

  const parsed = parseJsonBlock<{
    session_type?: string;
    relationship_context?: string;
    summary?: string;
    strengths?: string[];
    growth_areas?: Array<{ observation: string; suggestion: string }>;
    reflection?: string;
    themes?: string[];
  }>(text);

  await writeThemes(input.account, previousThemes, parsed.themes ?? []);


  await chargeUsage({
    accountId: input.account.id,
    usd: usage.usd,
    sessionType: parsed.session_type ?? "unknown",
    usingOwnKey: keys.usingOwnKey,
  });

  const patterns: Pattern[] = [
    ...(parsed.strengths ?? []).slice(0, 3).map((entry) => ({
      title: shortTitle(entry),
      observation: entry,
      suggestion: "",
      tone: "strength" as const,
    })),
    ...(parsed.growth_areas ?? []).slice(0, 3).map((item) => ({
      title: shortTitle(item.observation),
      observation: item.observation,
      suggestion: item.suggestion,
      tone: "growth" as const,
    })),
  ];

  const sessionType = (["conversation", "recap", "rehearsal", "reflection"] as const).includes(
    parsed.session_type as never,
  )
    ? (parsed.session_type as MirrorResult["sessionType"])
    : input.hadOtherSpeaker
      ? "conversation"
      : "reflection";

  const analysis: Analysis = {
    transcript: input.transcript,
    summary: parsed.summary ?? "",
    goalReflection: "",
    metrics: metricsFromTranscript(input.transcript, input.airtime),
    patterns,
  };

  // The session row is what lets the conversation continue afterwards.
  const client = await db();
  const { data: session } = await client
    .from("reflection_sessions")
    .insert({
      account_id: input.account.id,
      user_id: input.account.user_id,
      label: shortTitle(parsed.summary ?? input.transcript) || "Reflection",
      session_type: sessionType,
    } as never)
    .select("id")
    .single();
  const sessionId = String((session as { id?: string } | null)?.id ?? "");

  const opening = parsed.reflection?.trim() || parsed.summary?.trim() || "";
  if (sessionId) {
    await client.from("reflection_messages").insert([
      {
        session_id: sessionId,
        account_id: input.account.id,
        user_id: input.account.user_id,
        role: "user",
        content: input.transcript,
      },
      {
        session_id: sessionId,
        account_id: input.account.id,
        user_id: input.account.user_id,
        role: "assistant",
        content: opening,
      },
    ] as never);
  }

  return {
    sessionId,
    sessionType,
    relationshipContext: parsed.relationship_context ?? "none",
    analysis,
    reflection: opening,
  };
}

async function analyzeJob(input: {
  account: AccountRow;
  jobId: string;
  transcript: string;
  airtime: number;
  hadOtherSpeaker: boolean;
  written: boolean;
}): Promise<JobView> {
  const client = await db();
  try {
    const result = await runMirrorCall(input);
    const { data } = await client
      .from("conversation_jobs")
      .update({
        status: "ready",
        stage_message: null,
        analysis: { ...result.analysis, reflection: result.reflection },
        session_type: result.sessionType,
        inferred_persona: result.relationshipContext,
        persona: result.relationshipContext,
      } as never)
      .eq("id", input.jobId)
      .select("*")
      .single();
    const view = toView(data as Record<string, unknown>);
    return { ...view, result };
  } catch (error) {
    const message = error instanceof Error ? error.message : "The reflection could not be written.";
    const { data } = await client
      .from("conversation_jobs")
      .update({ status: "failed", error: message } as never)
      .eq("id", input.jobId)
      .select("*")
      .single();
    const view = toView(data as Record<string, unknown>);
    if ((error as { name?: string }).name === "OutOfCreditError") throw error;
    return view;
  }
}

/** Typed input takes the same route, minus transcription. */
export async function analyzeWritten(input: {
  account: AccountRow;
  text: string;
}): Promise<MirrorResult> {
  if (!checkWrittenText(input.text).ok) {
    throw new Error("There isn't quite enough there yet to reflect back. Add a little more.");
  }
  return runMirrorCall({
    account: input.account,
    transcript: input.text.trim(),
    airtime: 100,
    hadOtherSpeaker: false,
    written: true,
  });
}

export type MirrorMessage = { id: string; role: "user" | "assistant"; content: string };

export async function loadMessages(
  account: AccountRow,
  sessionId: string,
): Promise<MirrorMessage[]> {
  const client = await db();
  const { data } = await client
    .from("reflection_messages")
    .select("id, role, content")
    .eq("account_id", account.id)
    .eq("session_id", sessionId)
    .order("created_at", { ascending: true });
  return ((data ?? []) as Array<Record<string, unknown>>).map((row) => ({
    id: String(row["id"]),
    role: row["role"] === "assistant" ? "assistant" : "user",
    content: String(row["content"]),
  }));
}

/** Follow-up turns inside a session stay in open-reflection mode. */
export async function continueSession(input: {
  account: AccountRow;
  sessionId: string;
  content: string;
}): Promise<MirrorMessage> {
  const keys = await resolveKeys(input.account);
  assertCredit(input.account, keys.usingOwnKey);
  const settings = settingsOf(input.account);
  const client = await db();
  const history = await loadMessages(input.account, input.sessionId);

  await client.from("reflection_messages").insert({
    session_id: input.sessionId,
    account_id: input.account.id,
    user_id: input.account.user_id,
    role: "user",
    content: input.content,
  } as never);

  const themes = await readThemes(input.account);
  const style = `The user's reflection style for this session:
input_language: ${settings.input_language}
feedback_style: ${settings.feedback_style}
challenge_level: ${settings.challenge_level}

${languageRule(settings.output_language)}
${themeBlock(themes)}`;

  const { text, usage } = await callClaude({
    apiKey: keys.anthropic,
    model: settings.claude_model,
    system: `${REFLECTION_SYSTEM_PROMPT}\n\n${style}\n\n${SAFETY_OVERRIDE}`,
    messages: [
      ...history.map((m) => ({ role: m.role, content: m.content })),
      // Repeated last so the language rule can't be drowned out by a long
      // history that may itself be in another language.
      {
        role: "user" as const,
        content: `${input.content}\n\n[${languageRule(settings.output_language)}]`,
      },
    ],
    maxTokens: 900,
  });


  await chargeUsage({
    accountId: input.account.id,
    usd: usage.usd,
    sessionType: "follow_up",
    usingOwnKey: keys.usingOwnKey,
  });

  const inserted = await client
    .from("reflection_messages")
    .insert({
      session_id: input.sessionId,
      account_id: input.account.id,
      user_id: input.account.user_id,
      role: "assistant",
      content: text,
    } as never)
    .select("id")
    .single();

  return {
    id: String((inserted.data as { id?: string } | null)?.id ?? crypto.randomUUID()),
    role: "assistant",
    content: text,
  };
}

export type SessionSummary = {
  id: string;
  label: string;
  sessionType: string;
  createdAt: string;
};

/**
 * Browsable history exists for email accounts only. Anonymous accounts are
 * device-bound, so a scrollable list would sit open for whoever uses the device
 * next — they get the current session and one "last reflection" callback.
 */
export async function listSessions(account: AccountRow): Promise<SessionSummary[]> {
  if (!account.user_id) return [];
  const client = await db();
  const { data } = await client
    .from("reflection_sessions")
    .select("id, label, session_type, created_at")
    .eq("account_id", account.id)
    .order("created_at", { ascending: false })
    .limit(60);
  return ((data ?? []) as Array<Record<string, unknown>>).map((row) => ({
    id: String(row["id"]),
    label: String(row["label"]),
    sessionType: String(row["session_type"] ?? "reflection"),
    createdAt: String(row["created_at"]),
  }));
}

/** Weekly patterns, grouped by inferred context. Email accounts only. */
export async function weeklyPatterns(account: AccountRow) {
  if (!account.user_id) return [];
  const client = await db();
  const since = new Date(Date.now() - 7 * 86_400_000).toISOString();
  const { data } = await client
    .from("conversation_jobs")
    .select("session_type, inferred_persona, analysis, created_at")
    .eq("account_id", account.id)
    .eq("status", "ready")
    .gte("created_at", since)
    .order("created_at", { ascending: false });

  const groups = new Map<
    string,
    { context: string; count: number; strengths: string[]; growth: string[] }
  >();
  for (const row of (data ?? []) as Array<Record<string, unknown>>) {
    const context = String(row["inferred_persona"] ?? "none") || "none";
    const analysis = row["analysis"] as Analysis | null;
    const group = groups.get(context) ?? { context, count: 0, strengths: [], growth: [] };
    group.count += 1;
    for (const pattern of analysis?.patterns ?? []) {
      if (pattern.tone === "strength") group.strengths.push(pattern.observation);
      else group.growth.push(pattern.suggestion || pattern.observation);
    }
    groups.set(context, group);
  }

  return [...groups.values()].map((group) => ({
    context: group.context,
    count: group.count,
    strengths: group.strengths.slice(0, 3),
    growth: group.growth.slice(0, 1),
  }));
}

export async function loadPendingJob(account: AccountRow): Promise<JobView | null> {
  const client = await db();
  const { data } = await client
    .from("conversation_jobs")
    .select("*")
    .eq("account_id", account.id)
    .in("status", [
      "uploading",
      "transcribing",
      "needs_speaker_confirmation",
      "needs_solo_confirmation",
      "analyzing",
      "failed",
    ])

    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();
  return data ? toView(data as Record<string, unknown>) : null;
}
