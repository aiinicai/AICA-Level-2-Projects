import { describe, it, expect } from "vitest";
import { getMismatchFlags } from "./comparison";

function baseAsset(overrides: Record<string, unknown> = {}) {
  return {
    verificationStatus: "VERIFIED",
    sapAssetData: { serialNumber: "SAP-SERIAL-1" },
    currentLocation: { id: "loc-1", fullPath: "Mumbai / HO" },
    verificationRecords: [],
    ...overrides,
  } as unknown as Parameters<typeof getMismatchFlags>[0];
}

describe("getMismatchFlags", () => {
  it("returns no flags for a clean verification", () => {
    const asset = baseAsset({
      verificationRecords: [{ verifiedLocation: { id: "loc-1", fullPath: "Mumbai / HO" }, condition: "Good", observedSerialNumber: null }],
    });
    expect(getMismatchFlags(asset)).toHaveLength(0);
  });

  it("flags a location mismatch only when the asset's status says so — not by comparing already-synced fields", () => {
    // currentLocation and the latest verification's location are the SAME here
    // (the portal syncs them together on submit), so a naive field comparison
    // would never fire. The status flag is the real signal.
    const inSync = baseAsset({
      verificationStatus: "VERIFIED",
      verificationRecords: [{ verifiedLocation: { id: "loc-1", fullPath: "Mumbai / HO" } }],
    });
    expect(getMismatchFlags(inSync).find((f) => f.key === "location")).toBeUndefined();

    const flaggedByStatus = baseAsset({
      verificationStatus: "LOCATION_MISMATCH",
      verificationRecords: [{ verifiedLocation: { id: "loc-2", fullPath: "Mumbai / Warehouse" } }],
    });
    expect(getMismatchFlags(flaggedByStatus).find((f) => f.key === "location")).toBeTruthy();
  });

  it("flags a serial mismatch only when the verifier recorded a different observed serial", () => {
    const noObservation = baseAsset({
      verificationRecords: [{ verifiedLocation: null, observedSerialNumber: null }],
    });
    expect(getMismatchFlags(noObservation).find((f) => f.key === "serial")).toBeUndefined();

    const mismatched = baseAsset({
      sapAssetData: { serialNumber: "SAP-SERIAL-1" },
      verificationRecords: [{ verifiedLocation: null, observedSerialNumber: "DIFFERENT-SERIAL" }],
    });
    const flag = getMismatchFlags(mismatched).find((f) => f.key === "serial");
    expect(flag).toBeTruthy();
    expect(flag?.sapValue).toBe("SAP-SERIAL-1");
    expect(flag?.physicalValue).toBe("DIFFERENT-SERIAL");
  });

  it("flags a condition issue for anything other than Good", () => {
    const damaged = baseAsset({ verificationRecords: [{ verifiedLocation: null, condition: "Damaged" }] });
    expect(getMismatchFlags(damaged).find((f) => f.key === "condition")?.severity).toBe("warn");

    const good = baseAsset({ verificationRecords: [{ verifiedLocation: null, condition: "Good" }] });
    expect(getMismatchFlags(good).find((f) => f.key === "condition")).toBeUndefined();
  });

  it("returns no flags for an asset that has never been verified", () => {
    expect(getMismatchFlags(baseAsset({ verificationRecords: [] }))).toHaveLength(0);
  });
});
