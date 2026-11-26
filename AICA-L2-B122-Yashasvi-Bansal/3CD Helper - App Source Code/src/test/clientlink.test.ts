import { describe, it, expect } from "vitest";
import { clientFilePath, defaultLinkMessage, linkUrl, linksNotReady } from "@/lib/clientLink";

describe("Client upload link", () => {
  it("builds paths inside the link's folder only", () => {
    const p = clientFilePath({ firm_id: "F", engagement_id: "E" }, "tok", "../../Day Book (2025).xml", 5);
    expect(p).toBe("F/E/client/tok/5_._._Day_Book__2025_.xml");
    expect(p.includes("..")).toBe(false);
    expect(p.split("/").length).toBe(5);
  });
  it("link, message and not-ready detection", () => {
    expect(linkUrl("abc", "https://x.app")).toBe("https://x.app/u/abc");
    expect(defaultLinkMessage({ name: "A", module: "clause31", ay: "2026-27", firm: "Y" }).includes("{link}")).toBe(true);
    expect(linksNotReady({ code: "PGRST205", message: "Could not find the table 'public.upload_links' in the schema cache" })).toBe(true);
    expect(linksNotReady({ code: "42501", message: "permission denied" })).toBe(false);
  });
});
