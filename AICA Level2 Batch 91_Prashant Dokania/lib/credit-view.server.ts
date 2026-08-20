import { LOW_BALANCE_USD, totalCredit, type AccountRow } from "./account.server";

/** Roughly what one typical reflection costs, used only for friendly wording. */
const TYPICAL_REFLECTION_USD = 0.04;

export type CreditView = {
  tone: "own_key" | "plenty" | "low" | "empty";
  label: string;
  approxReflectionsLeft: number;
  totalUsd: number;
  welcomeUsd: number;
  monthlyUsd: number;
  purchasedUsd: number;
  resetsAt: string;
  low: boolean;
  empty: boolean;
};

export function creditView(row: AccountRow): CreditView {
  const total = Number(totalCredit(row).toFixed(4));
  const approx = Math.max(0, Math.round(total / TYPICAL_REFLECTION_USD));
  const usingOwnKey = Boolean(row.anthropic_key_encrypted);
  const empty = !usingOwnKey && total < 0.02;
  const low = !usingOwnKey && !empty && total < LOW_BALANCE_USD;

  const label = usingOwnKey
    ? "Running on your own key"
    : empty
      ? "Out of free credit for this month"
      : low
        ? `Running low — about ${Math.max(1, approx)} more reflection${approx === 1 ? "" : "s"}`
        : "You have plenty left this month";

  return {
    tone: usingOwnKey ? "own_key" : empty ? "empty" : low ? "low" : "plenty",
    label,
    approxReflectionsLeft: approx,
    totalUsd: total,
    welcomeUsd: Number(row.welcome_credit_remaining_usd),
    monthlyUsd: Number(row.monthly_credit_remaining_usd),
    purchasedUsd: Number(row.purchased_credit_balance_usd),
    resetsAt: row.monthly_credit_resets_at,
    low,
    empty,
  };
}
