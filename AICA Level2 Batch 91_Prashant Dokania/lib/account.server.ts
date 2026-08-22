/**
 * Account resolution and the credit ledger.
 *
 * An account is either a bare device (anonymous, zero personal data) or an
 * email login. Everything — usage credit, recordings, sessions — hangs off the
 * account row. Only this module (service-role, server-only) ever touches it.
 */

import { decryptSecret } from "./crypto.server";

export const WELCOME_GRANT_USD = 1.0;
export const MONTHLY_GRANT_USD = 0.4;
export const TOPUP_USD = 5.0;
export const LOW_BALANCE_USD = 0.1;
/** Refuse to start anything we cannot plausibly pay for. */
export const MIN_START_USD = 0.02;

export type AccountRow = {
  id: string;
  device_id: string | null;
  user_id: string | null;
  email: string | null;
  welcome_credit_remaining_usd: number;
  monthly_credit_remaining_usd: number;
  monthly_credit_resets_at: string;
  purchased_credit_balance_usd: number;
  input_language: string;
  output_language: string;
  feedback_style: string;
  challenge_level: string;
  claude_model: string;
  anthropic_key_encrypted: string | null;
  sarvam_key_encrypted: string | null;
  anthropic_key_last4: string | null;
  sarvam_key_last4: string | null;
};

export async function db() {
  const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
  return supabaseAdmin;
}

async function sha256(value: string) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("");
}

function nextMonthStart(from = new Date()) {
  return new Date(Date.UTC(from.getUTCFullYear(), from.getUTCMonth() + 1, 1)).toISOString();
}

async function logTx(input: {
  accountId: string;
  type: string;
  amountUsd: number;
  pool?: string;
  sessionType?: string;
  paymentRef?: string;
}) {
  const client = await db();
  await client.from("credit_transactions").insert({
    account_id: input.accountId,
    type: input.type,
    amount_usd: input.amountUsd,
    pool: input.pool ?? null,
    session_type: input.sessionType ?? null,
    payment_ref: input.paymentRef ?? null,
  } as never);
}

/** Monthly allowance refreshes on the calendar month and never rolls over. */
async function applyMonthlyReset(row: AccountRow): Promise<AccountRow> {
  if (new Date(row.monthly_credit_resets_at).getTime() > Date.now()) return row;
  const client = await db();
  const resets = nextMonthStart();
  const { data } = await client
    .from("accounts")
    .update({
      monthly_credit_remaining_usd: MONTHLY_GRANT_USD,
      monthly_credit_resets_at: resets,
    } as never)
    .eq("id", row.id)
    .select("*")
    .single();
  await logTx({ accountId: row.id, type: "monthly_grant", amountUsd: MONTHLY_GRANT_USD });
  return (data as AccountRow | null) ?? row;
}

async function verifiedUserId(token: string | null): Promise<{ id: string; email: string } | null> {
  if (!token) return null;
  const client = await db();
  const { data, error } = await client.auth.getUser(token);
  if (error || !data.user) return null;
  return { id: data.user.id, email: (data.user.email ?? "").toLowerCase() };
}

/**
 * Resolves the caller to an account, minting the device account (with its
 * one-time welcome allowance) on first contact.
 *
 * Shared-device privacy rule: an email login NEVER adopts an anonymous device
 * row. A returning user is recognised only by their own auth user id — that
 * lookup already returns their existing account, on any device. Any other
 * email signing in on a device with prior anonymous activity gets a clean,
 * separate account, and the anonymous history/credit stays with the device.
 */
export async function resolveAccount(input: {
  deviceId: string;
  deviceSecret: string;
  token?: string | null;
}): Promise<AccountRow> {
  const client = await db();
  const user = await verifiedUserId(input.token ?? null);
  const secretHash = input.deviceSecret ? await sha256(input.deviceSecret) : null;

  const deviceRow = input.deviceId
    ? ((await client.from("accounts").select("*").eq("device_id", input.deviceId).maybeSingle())
        .data as AccountRow | null)
    : null;

  if (deviceRow && deviceRow.device_id && secretHash && deviceRow.user_id === null) {
    // A device id without its matching secret is not this device.
    const stored = (deviceRow as unknown as { device_secret_hash: string | null })
      .device_secret_hash;
    if (stored && stored !== secretHash) throw new Error("This session could not be verified.");
  }

  if (user) {
    const existing = (
      await client.from("accounts").select("*").eq("user_id", user.id).maybeSingle()
    ).data as AccountRow | null;
    if (existing) return applyMonthlyReset(existing);

    // First login for this email: always a fresh account. Never inherit the
    // device's anonymous credit or sessions.
    const { data, error } = await client
      .from("accounts")
      .insert({
        user_id: user.id,
        email: user.email,
        monthly_credit_resets_at: nextMonthStart(),
      } as never)
      .select("*")
      .single();
    if (error) throw new Error(error.message);
    const created = data as AccountRow;
    await logTx({ accountId: created.id, type: "welcome_grant", amountUsd: WELCOME_GRANT_USD });
    return created;
  }

  if (deviceRow) return applyMonthlyReset(deviceRow);
  if (!input.deviceId) throw new Error("This session could not be verified.");

  const { data, error } = await client
    .from("accounts")
    .insert({
      device_id: input.deviceId,
      device_secret_hash: secretHash,
      monthly_credit_resets_at: nextMonthStart(),
    } as never)
    .select("*")
    .single();
  if (error) throw new Error(error.message);
  const created = data as AccountRow;
  await logTx({ accountId: created.id, type: "welcome_grant", amountUsd: WELCOME_GRANT_USD });
  return created;
}

export async function reloadAccount(accountId: string): Promise<AccountRow> {
  const client = await db();
  const { data } = await client.from("accounts").select("*").eq("id", accountId).single();
  return data as AccountRow;
}

export function totalCredit(row: AccountRow) {
  return (
    Number(row.welcome_credit_remaining_usd) +
    Number(row.monthly_credit_remaining_usd) +
    Number(row.purchased_credit_balance_usd)
  );
}

export class OutOfCreditError extends Error {
  resetsAt: string;
  constructor(resetsAt: string) {
    super("You've used this month's free reflections.");
    this.name = "OutOfCreditError";
    this.resetsAt = resetsAt;
  }
}

/** Blocks before any provider call when nothing is left to spend. */
export function assertCredit(row: AccountRow, usingOwnKey: boolean) {
  if (usingOwnKey) return;
  if (totalCredit(row) < MIN_START_USD) throw new OutOfCreditError(row.monthly_credit_resets_at);
}

/** Draws down welcome → monthly → purchased, in that order. */
export async function chargeUsage(input: {
  accountId: string;
  usd: number;
  sessionType: string;
  usingOwnKey: boolean;
}) {
  if (input.usingOwnKey || input.usd <= 0) return;
  const client = await db();
  const row = await reloadAccount(input.accountId);
  let left = input.usd;
  const pools: Array<[keyof AccountRow, string]> = [
    ["welcome_credit_remaining_usd", "welcome"],
    ["monthly_credit_remaining_usd", "monthly"],
    ["purchased_credit_balance_usd", "purchased"],
  ];
  const patch: Record<string, number> = {};

  for (const [column, pool] of pools) {
    if (left <= 0) break;
    const available = Number(row[column] ?? 0);
    if (available <= 0) continue;
    const take = Math.min(available, left);
    patch[column as string] = Number((available - take).toFixed(4));
    left = Number((left - take).toFixed(4));
    await logTx({
      accountId: input.accountId,
      type: "usage",
      amountUsd: -Number(take.toFixed(4)),
      pool,
      sessionType: input.sessionType,
    });
  }

  if (Object.keys(patch).length > 0) {
    await client
      .from("accounts")
      .update(patch as never)
      .eq("id", input.accountId);
  }
}

export async function grantPurchase(input: { accountId: string; usd: number; paymentRef: string }) {
  const client = await db();
  const row = await reloadAccount(input.accountId);
  await client
    .from("accounts")
    .update({
      purchased_credit_balance_usd: Number(
        (Number(row.purchased_credit_balance_usd) + input.usd).toFixed(4),
      ),
    } as never)
    .eq("id", input.accountId);
  await logTx({
    accountId: input.accountId,
    type: "purchase",
    amountUsd: input.usd,
    pool: "purchased",
    paymentRef: input.paymentRef,
  });
}

export type AiSettings = {
  input_language: string;
  output_language: string;
  feedback_style: string;
  challenge_level: string;
  claude_model: string;
};

export function settingsOf(row: AccountRow): AiSettings {
  return {
    input_language: row.input_language,
    output_language: row.output_language,
    feedback_style: row.feedback_style,
    challenge_level: row.challenge_level,
    claude_model: row.claude_model,
  };
}

/**
 * Platform keys are the default. A personal key is an optional, secondary
 * setting; when present it is used instead and no credit is consumed. Neither
 * value is ever returned to the browser.
 */
export async function resolveKeys(row: AccountRow): Promise<{
  anthropic: string;
  sarvam: string;
  usingOwnKey: boolean;
}> {
  const ownAnthropic = row.anthropic_key_encrypted
    ? await decryptSecret(row.anthropic_key_encrypted)
    : "";
  const ownSarvam = row.sarvam_key_encrypted ? await decryptSecret(row.sarvam_key_encrypted) : "";

  const anthropic = ownAnthropic || process.env["ANTHROPIC_API_KEY"] || "";
  const sarvam = ownSarvam || process.env["SARVAM_API_KEY"] || "";
  if (!anthropic)
    throw new Error("Reflections are temporarily unavailable. Please try again soon.");

  return { anthropic, sarvam, usingOwnKey: Boolean(ownAnthropic) };
}
