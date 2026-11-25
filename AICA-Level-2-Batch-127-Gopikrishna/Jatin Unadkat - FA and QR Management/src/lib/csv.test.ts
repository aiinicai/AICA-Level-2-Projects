import { describe, it, expect } from "vitest";
import { toCsv } from "./csv";

describe("toCsv", () => {
  it("joins headers and rows with commas and CRLF", () => {
    const csv = toCsv(["A", "B"], [["1", "2"]]);
    expect(csv).toBe("A,B\r\n1,2");
  });

  it("quotes a field containing a comma", () => {
    const csv = toCsv(["Description"], [["Laptop, 15-inch"]]);
    expect(csv).toContain('"Laptop, 15-inch"');
  });

  it("escapes embedded double quotes by doubling them", () => {
    const csv = toCsv(["Note"], [['She said "hello"']]);
    expect(csv).toContain('"She said ""hello"""');
  });

  it("quotes a field containing a newline", () => {
    const csv = toCsv(["Note"], [["line one\nline two"]]);
    expect(csv).toContain('"line one\nline two"');
  });

  it("renders null and undefined as an empty cell, not the literal string", () => {
    const csv = toCsv(["A"], [[null], [undefined]]);
    expect(csv).toBe("A\r\n\r\n");
  });
});
