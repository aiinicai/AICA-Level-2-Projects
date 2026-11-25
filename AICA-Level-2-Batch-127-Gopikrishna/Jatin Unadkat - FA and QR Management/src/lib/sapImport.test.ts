import { describe, it, expect } from "vitest";
import { validateColumns, parseAndValidateRows, EXPECTED_COLUMNS, parseWorkbook } from "./sapImport";

describe("validateColumns", () => {
  it("passes when every expected column is present, in any order", () => {
    const shuffled = [...EXPECTED_COLUMNS].reverse();
    const { missing, unexpected } = validateColumns(shuffled);
    expect(missing).toHaveLength(0);
    expect(unexpected).toHaveLength(0);
  });

  it("reports a missing standard column without flagging the rest", () => {
    const headers = EXPECTED_COLUMNS.filter((c) => c !== "Gross Book Value");
    const { missing } = validateColumns(headers);
    expect(missing).toEqual(["Gross Book Value"]);
  });

  it("reports extra columns as unexpected, not as missing", () => {
    const headers = [...EXPECTED_COLUMNS, "Some Extra SAP Column"];
    const { missing, unexpected } = validateColumns(headers);
    expect(missing).toHaveLength(0);
    expect(unexpected).toEqual(["Some Extra SAP Column"]);
  });
});

describe("parseAndValidateRows — blank values never block a row", () => {
  const baseRow = () =>
    Object.fromEntries(EXPECTED_COLUMNS.map((c) => [c, ""])) as Record<string, string>;

  it("accepts a row where every optional SAP field is blank", () => {
    const row = baseRow();
    row["Asset Number"] = "FA-000900";
    const result = parseAndValidateRows([row], new Set());
    expect(result.errors).toHaveLength(0);
    expect(result.validRows).toHaveLength(1);
    expect(result.validRows[0].serialNumber).toBeNull();
    expect(result.validRows[0].netBookValue).toBeNull();
  });

  it("rejects a row with a blank Asset Number, but doesn't fail the whole batch", () => {
    const good = baseRow();
    good["Asset Number"] = "FA-000901";
    const bad = baseRow(); // Asset Number left blank
    const result = parseAndValidateRows([bad, good], new Set());
    expect(result.validRows).toHaveLength(1);
    expect(result.errors.some((e) => e.errorType === "MISSING_ASSET_NUMBER")).toBe(true);
  });

  it("flags a non-numeric Net Book Value as an invalid row instead of silently coercing it", () => {
    const row = baseRow();
    row["Asset Number"] = "FA-000902";
    row["Net Book Value"] = "not-a-number";
    const result = parseAndValidateRows([row], new Set());
    expect(result.validRows).toHaveLength(0);
    expect(result.errors[0].errorType).toBe("INVALID_NUMBER");
  });

  it("accepts common Yes/No/1/0 spellings for Capitalized, case-insensitively", () => {
    const row = baseRow();
    row["Asset Number"] = "FA-000903";
    row["Capitalized"] = "yes";
    const result = parseAndValidateRows([row], new Set());
    expect(result.validRows[0].capitalized).toBe(true);
  });

  it("keeps only the last occurrence when an Asset Number repeats within the file", () => {
    const first = baseRow();
    first["Asset Number"] = "FA-000904";
    first["Description 1"] = "Old description";
    const second = baseRow();
    second["Asset Number"] = "FA-000904";
    second["Description 1"] = "Corrected description";
    const result = parseAndValidateRows([first, second], new Set());
    expect(result.validRows).toHaveLength(1);
    expect(result.validRows[0].description1).toBe("Corrected description");
    expect(result.duplicateInFileCount).toBe(1);
  });

  it("classifies rows against already-existing Asset Numbers as updates, not new records", () => {
    const row = baseRow();
    row["Asset Number"] = "FA-000123";
    const result = parseAndValidateRows([row], new Set(["FA-000123"]));
    expect(result.newCount).toBe(0);
    expect(result.existingCount).toBe(1);
  });
});

describe("parseWorkbook — CSV path handles quoted commas", () => {
  it("splits a quoted field containing a comma correctly", async () => {
    const csv = 'Asset Number,Description 1\nFA-1,"Laptop, 15-inch"';
    const { headers, rows } = await parseWorkbook(Buffer.from(csv), "test.csv");
    expect(headers).toEqual(["Asset Number", "Description 1"]);
    expect(rows[0]["Description 1"]).toBe("Laptop, 15-inch");
  });
});
