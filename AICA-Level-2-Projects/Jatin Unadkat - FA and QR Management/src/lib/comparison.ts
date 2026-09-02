import type { Asset, SapAssetData, VerificationRecord, Location } from "@prisma/client";

export type MismatchFlag = {
  key: "location" | "serial" | "condition";
  label: string;
  severity: "bad" | "warn";
  sapValue: string;
  physicalValue: string;
};

type AssetForComparison = Asset & {
  sapAssetData: SapAssetData | null;
  currentLocation: Location | null;
  verificationRecords: (VerificationRecord & { verifiedLocation: Location | null })[];
};

/**
 * SAP-vs-physical mismatch detection (design dossier, ADD13 §02). Compares
 * the read-only SAP record against what a verifier actually observed —
 * never against fields the portal itself just synced from the same source,
 * which would trivially always agree. Never auto-resolves either side.
 */
export function getMismatchFlags(asset: AssetForComparison): MismatchFlag[] {
  const flags: MismatchFlag[] = [];
  const latest = asset.verificationRecords[0];

  // asset.currentLocation is set FROM the latest verification the moment it's
  // submitted, so comparing them to each other would always agree. The
  // meaningful signal is the status a mismatch verification already set.
  if (asset.verificationStatus === "LOCATION_MISMATCH" && latest?.verifiedLocation) {
    flags.push({
      key: "location",
      label: "Location Mismatch",
      severity: "bad",
      sapValue: "Previously booked location (see movement history)",
      physicalValue: latest.verifiedLocation.fullPath,
    });
  }

  const sapSerial = asset.sapAssetData?.serialNumber;
  const observedSerial = latest?.observedSerialNumber;
  if (sapSerial && observedSerial && sapSerial !== observedSerial) {
    flags.push({
      key: "serial",
      label: "Serial Number Mismatch",
      severity: "bad",
      sapValue: sapSerial,
      physicalValue: observedSerial,
    });
  }

  if (latest?.condition && latest.condition !== "Good") {
    flags.push({
      key: "condition",
      label: "Condition Issue",
      severity: "warn",
      sapValue: "—",
      physicalValue: latest.condition,
    });
  }

  return flags;
}
