import { describe, it, expect } from "vitest";
import { generateQrToken, qrTargetUrl } from "./qr";

describe("generateQrToken", () => {
  it("never encodes anything asset-specific — it's a bare opaque token", () => {
    const token = generateQrToken();
    // Base64url alphabet only: no characters that could leak structure.
    expect(token).toMatch(/^[A-Za-z0-9_-]+$/);
    expect(token.length).toBeGreaterThanOrEqual(20);
  });

  it("generates unique tokens across many calls", () => {
    const tokens = new Set(Array.from({ length: 1000 }, () => generateQrToken()));
    expect(tokens.size).toBe(1000);
  });
});

describe("qrTargetUrl", () => {
  it("embeds only the token in the path, not any business data", () => {
    const url = qrTargetUrl("abc123");
    expect(url).toMatch(/\/a\/abc123$/);
  });
});
