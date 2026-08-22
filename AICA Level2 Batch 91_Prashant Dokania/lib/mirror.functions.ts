import { createServerFn } from "@tanstack/react-start";
import { getRequestHeader } from "@tanstack/react-start/server";
import { z } from "zod";

const deviceSchema = z.object({
  deviceId: z.string().min(8).max(80),
  deviceSecret: z.string().min(8).max(120),
});

const withDevice = <T extends z.ZodRawShape>(shape: T) =>
  z.object({ device: deviceSchema, ...shape });

async function account(device: { deviceId: string; deviceSecret: string }) {
  const { resolveAccount } = await import("./account.server");
  const header = getRequestHeader("authorization") ?? "";
  const token = header.toLowerCase().startsWith("bearer ") ? header.slice(7) : null;
  return resolveAccount({ ...device, token });
}

/** Everything the client needs about the account, with no secrets in it. */
export const getMirrorState = createServerFn({ method: "POST" })
  .inputValidator((input: unknown) => z.object({ device: deviceSchema }).parse(input))
  .handler(async ({ data }) => {
    const row = await account(data.device);
    const { creditView } = await import("./credit-view.server");
    const { listSessions, loadPendingJob } = await import("./mirror-session.server");
    const [sessions, pending] = await Promise.all([listSessions(row), loadPendingJob(row)]);
    return {
      credit: creditView(row),
      identity: {
        anonymous: !row.user_id,
        email: row.email,
        emailVerified: Boolean(row.user_id),
      },
      ownApiKeyConfigured: Boolean(row.anthropic_key_encrypted),
      keyLast4: { anthropic: row.anthropic_key_last4, sarvam: row.sarvam_key_last4 },
      settings: {
        input_language: row.input_language,
        output_language: row.output_language,
        feedback_style: row.feedback_style,
        challenge_level: row.challenge_level,
      },
      sessions,
      pending,
    };
  });

export const startRecording = createServerFn({ method: "POST" })
  .inputValidator((input: unknown) => withDevice({ audioBase64: z.string().min(100) }).parse(input))
  .handler(async ({ data }) => {
    const row = await account(data.device);
    const { startCapture } = await import("./mirror-session.server");
    return startCapture({ account: row, audioBase64: data.audioBase64 });
  });

export const pollRecording = createServerFn({ method: "POST" })
  .inputValidator((input: unknown) => withDevice({ jobId: z.string().uuid() }).parse(input))
  .handler(async ({ data }) => {
    const row = await account(data.device);
    const { pollJob } = await import("./mirror-session.server");
    return pollJob({ account: row, jobId: data.jobId });
  });

export const confirmMyVoice = createServerFn({ method: "POST" })
  .inputValidator((input: unknown) =>
    withDevice({ jobId: z.string().uuid(), speaker: z.string().min(1).max(40) }).parse(input),
  )
  .handler(async ({ data }) => {
    const row = await account(data.device);
    const { confirmSpeaker } = await import("./mirror-session.server");
    return confirmSpeaker({ account: row, jobId: data.jobId, speaker: data.speaker });
  });

/** Explicit retry after a failed job, instead of asking the user to re-record. */
export const retryMirrorJob = createServerFn({ method: "POST" })
  .inputValidator((input: unknown) => withDevice({ jobId: z.string().uuid() }).parse(input))
  .handler(async ({ data }) => {
    const row = await account(data.device);
    const { retryJob } = await import("./mirror-session.server");
    return retryJob({ account: row, jobId: data.jobId });
  });

/** The user says the recording isn't theirs to analyse: nothing is kept. */
export const discardMirrorJob = createServerFn({ method: "POST" })
  .inputValidator((input: unknown) => withDevice({ jobId: z.string().uuid() }).parse(input))
  .handler(async ({ data }) => {
    const row = await account(data.device);
    const { discardJob } = await import("./mirror-session.server");
    return discardJob({ account: row, jobId: data.jobId });
  });


export const reflectOnText = createServerFn({ method: "POST" })
  .inputValidator((input: unknown) =>
    withDevice({ text: z.string().min(1).max(12_000) }).parse(input),
  )
  .handler(async ({ data }) => {
    const row = await account(data.device);
    const { analyzeWritten } = await import("./mirror-session.server");
    return analyzeWritten({ account: row, text: data.text });
  });

export const continueMirror = createServerFn({ method: "POST" })
  .inputValidator((input: unknown) =>
    withDevice({
      sessionId: z.string().uuid(),
      content: z.string().min(1).max(6000),
    }).parse(input),
  )
  .handler(async ({ data }) => {
    const row = await account(data.device);
    const { continueSession } = await import("./mirror-session.server");
    return continueSession({ account: row, sessionId: data.sessionId, content: data.content });
  });

export const getSessionMessages = createServerFn({ method: "POST" })
  .inputValidator((input: unknown) => withDevice({ sessionId: z.string().uuid() }).parse(input))
  .handler(async ({ data }) => {
    const row = await account(data.device);
    const { loadMessages } = await import("./mirror-session.server");
    return loadMessages(row, data.sessionId);
  });

export const getWeeklyPatterns = createServerFn({ method: "POST" })
  .inputValidator((input: unknown) => z.object({ device: deviceSchema }).parse(input))
  .handler(async ({ data }) => {
    const row = await account(data.device);
    const { weeklyPatterns } = await import("./mirror-session.server");
    return weeklyPatterns(row);
  });

const settingsSchema = withDevice({
  input_language: z.string().min(2).max(20),
  output_language: z.string().min(2).max(20),
  feedback_style: z.enum(["gentle", "balanced", "candid", "straight_talk"]),
  challenge_level: z.enum(["low", "medium", "high"]),
});

export const saveMirrorSettings = createServerFn({ method: "POST" })
  .inputValidator((input: unknown) => settingsSchema.parse(input))
  .handler(async ({ data }) => {
    const row = await account(data.device);
    const { db } = await import("./account.server");
    const client = await db();
    await client
      .from("accounts")
      .update({
        input_language: data.input_language,
        output_language: data.output_language,
        feedback_style: data.feedback_style,
        challenge_level: data.challenge_level,
      } as never)
      .eq("id", row.id);
    return { ok: true };
  });

/** Optional, secondary: bring your own key instead of using platform credit. */
export const saveOwnKeys = createServerFn({ method: "POST" })
  .inputValidator((input: unknown) =>
    withDevice({
      anthropic: z.string().trim().max(200).optional(),
      sarvam: z.string().trim().max(200).optional(),
    }).parse(input),
  )
  .handler(async ({ data }) => {
    const row = await account(data.device);
    const { db } = await import("./account.server");
    const { encryptSecret, last4 } = await import("./crypto.server");
    const { checkAnthropicKey, checkSarvamKey } = await import("./key-validation.server");
    const client = await db();
    const patch: Record<string, string | null> = {};
    const errors: Record<string, string> = {};

    if (data.anthropic) {
      const check = await checkAnthropicKey(data.anthropic);
      if (!check.ok) errors["anthropic"] = check.message;
      else {
        patch["anthropic_key_encrypted"] = await encryptSecret(data.anthropic);
        patch["anthropic_key_last4"] = last4(data.anthropic);
      }
    }
    if (data.sarvam) {
      const check = await checkSarvamKey(data.sarvam);
      if (!check.ok) errors["sarvam"] = check.message;
      else {
        patch["sarvam_key_encrypted"] = await encryptSecret(data.sarvam);
        patch["sarvam_key_last4"] = last4(data.sarvam);
      }
    }

    if (Object.keys(errors).length > 0) return { ok: false, errors };
    if (Object.keys(patch).length > 0) {
      await client
        .from("accounts")
        .update(patch as never)
        .eq("id", row.id);
    }
    return { ok: true, errors: {} };
  });

export const removeOwnKeys = createServerFn({ method: "POST" })
  .inputValidator((input: unknown) => z.object({ device: deviceSchema }).parse(input))
  .handler(async ({ data }) => {
    const row = await account(data.device);
    const { db } = await import("./account.server");
    const client = await db();
    await client
      .from("accounts")
      .update({
        anthropic_key_encrypted: null,
        sarvam_key_encrypted: null,
        anthropic_key_last4: null,
        sarvam_key_last4: null,
      } as never)
      .eq("id", row.id);
    return { ok: true };
  });

/** Records a UPI top-up submission for manual review. */
export const submitTopUp = createServerFn({ method: "POST" })
  .inputValidator((input: unknown) =>
    withDevice({
      reference: z.string().trim().min(3).max(120),
      screenshotPath: z.string().trim().max(300).optional(),
    }).parse(input),
  )
  .handler(async ({ data }) => {
    const row = await account(data.device);
    const { db, TOPUP_USD } = await import("./account.server");
    const client = await db();
    const { error } = await client.from("payments").insert({
      account_id: row.id,
      user_id: row.user_id,
      amount_inr: 450,
      credit_usd: TOPUP_USD,
      reference: data.reference,
      screenshot_path: data.screenshotPath ?? null,
      status: "pending",
    } as never);
    if (error) throw new Error(error.message);
    return { ok: true };
  });
