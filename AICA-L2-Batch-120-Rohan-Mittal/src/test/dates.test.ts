import { afterEach, describe, expect, it, vi } from "vitest";
import { formatDay, today } from "@/lib/app";

describe("local dates", () => {
  afterEach(() => vi.useRealTimers());
  it("today() uses the local calendar day, not UTC", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 9, 12, 1, 30)); // 01:30 local on 12 Oct
    expect(today()).toBe("2026-10-12");
  });
  it("formatDay does not shift a stored date across timezones", () => {
    expect(formatDay("2026-10-12", { day: "numeric" })).toBe("12");
  });
});
