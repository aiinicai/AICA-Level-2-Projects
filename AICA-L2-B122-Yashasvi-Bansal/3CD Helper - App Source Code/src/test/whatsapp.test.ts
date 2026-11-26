import { describe, it, expect } from "vitest";
import { buildShareMessage, normalizeIndianMobile, waLinks } from "@/lib/whatsapp";
import { fyOfAy, matchCompany } from "@/lib/tallyConnector";

describe("WhatsApp share", () => {
  it("normalises Indian mobile numbers", () => {
    expect(normalizeIndianMobile("98765 43210")).toBe("919876543210");
    expect(normalizeIndianMobile("+91-98765-43210")).toBe("919876543210");
    expect(normalizeIndianMobile("09876543210")).toBe("919876543210");
    expect(normalizeIndianMobile("0261 2345678")).toBe("");
    expect(normalizeIndianMobile("12345")).toBe("");
    expect(normalizeIndianMobile("")).toBe("");
  });
  it("builds the message and links", () => {
    const m = buildShareMessage({ name: "Aeron Medicare Pvt. Ltd.", report: "Clause 31 report", ay: "2026-27", firm: "Yash Associates" });
    expect(m.includes("{link}")).toBe(true);
    const l = waLinks("919876543210", m.replace("{link}", "https://x/y?token=a&b=1"));
    expect(l.desktop.startsWith("whatsapp://send?phone=919876543210&text=Dear%20Aeron")).toBe(true);
    expect(l.web.includes("https%3A%2F%2Fx%2Fy%3Ftoken%3Da%26b%3D1")).toBe(true);
    expect(l.phone.startsWith("https://wa.me/919876543210?text=")).toBe(true);
  });
});

describe("Tally Connector helpers", () => {
  it("period from AY and company matching", () => {
    expect(fyOfAy("2026-27")).toEqual({ from: "2025-04-01", to: "2026-03-31" });
    const list = [{ name: "Some Other Co", booksFrom: "" }, { name: "AERON MEDICARE PVT. LTD.", booksFrom: "2025-04-01" }];
    expect(matchCompany(list, "Aeron Medicare Pvt. Ltd.")).toBe("AERON MEDICARE PVT. LTD.");
    expect(matchCompany(list, "Unknown Client")).toBe("Some Other Co");
    expect(matchCompany([], "x")).toBe("");
  });
});
