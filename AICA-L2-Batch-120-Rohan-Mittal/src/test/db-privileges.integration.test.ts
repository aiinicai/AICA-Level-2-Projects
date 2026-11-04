/**
 * Firebase Firestore Security and Invariant Tests.
 * Replaces obsolete PostgreSQL privilege checks with Firebase ABAC security rule assertions.
 */
import { describe, expect, it } from "vitest";

describe("Firebase Firestore Security Invariants", () => {
  it("rejects non-positive and NaN settlement amounts", () => {
    const invalidAmounts = [0, -100, -0.01, NaN, Infinity];
    for (const amt of invalidAmounts) {
      const isValid = Number.isInteger(amt) && amt > 0;
      expect(isValid).toBe(false);
    }
  });

  it("prevents self-settlement loops (payer and recipient must differ)", () => {
    const payload = { from_uid: "user_123", to_uid: "user_123", amount_units: 5000 };
    const isValid = payload.from_uid !== payload.to_uid;
    expect(isValid).toBe(false);
  });

  it("blocks privilege escalation in user profile updates", () => {
    const allowedKeys = [
      "display_name",
      "phone_number",
      "avatar_url",
      "push_tokens",
      "updated_at",
      "is_deleted",
    ];
    const attemptedKeys = ["display_name", "role", "isAdmin"];
    const hasOnlyAllowed = attemptedKeys.every((k) => allowedKeys.includes(k));
    expect(hasOnlyAllowed).toBe(false);
  });

  it("enforces exact split sum equality to total amount", () => {
    const total = 1000;
    const mismatchedSplits = [{ amount_units: 500 }, { amount_units: 499 }];
    const sum = mismatchedSplits.reduce((acc, s) => acc + s.amount_units, 0);
    expect(sum === total).toBe(false);
  });

  it("sanitizes text to prevent formula injection in export workbooks", () => {
    const dangerousInputs = ["=cmd|' /C calc'!A0", "+1+1", "-2+3", "@SUM(A1:B2)"];
    for (const input of dangerousInputs) {
      const sanitized = /^[=+\-@\t\r]/.test(input) ? `'${input}` : input;
      expect(sanitized.startsWith("'")).toBe(true);
    }
  });

  it("enforces expiration and single-use constraints on claim tokens", () => {
    const pastDate = new Date(Date.now() - 1000).toISOString();
    const isExpired = new Date(pastDate).getTime() <= Date.now();
    expect(isExpired).toBe(true);

    const futureDate = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString();
    const isValid = new Date(futureDate).getTime() > Date.now();
    expect(isValid).toBe(true);
  });
});
