import ExcelJS from "exceljs";
import { format } from "date-fns";
import type { Asset, Location, User, SapExportTemplateField } from "@prisma/client";

export const PORTAL_SOURCE_FIELDS = [
  { key: "assetNumber", label: "Asset Number" },
  { key: "physicalLocation", label: "Physical Location (full path)" },
  { key: "verificationStatus", label: "Verification Status" },
  { key: "physicalCondition", label: "Physical Condition" },
  { key: "lastVerifiedAt", label: "Last Verified Date" },
  { key: "lastVerifiedBy", label: "Verified By" },
  { key: "remarks", label: "Remarks" },
] as const;

export type ExportableAsset = Asset & {
  currentLocation: Location | null;
  lastVerifiedBy: User | null;
};

export function resolvePortalField(asset: ExportableAsset, key: string, dateFormat?: string): string {
  switch (key) {
    case "assetNumber":
      return asset.assetNumber;
    case "physicalLocation":
      return asset.currentLocation?.fullPath ?? "";
    case "verificationStatus":
      return asset.verificationStatus.replaceAll("_", " ");
    case "physicalCondition":
      return asset.physicalCondition ?? "";
    case "lastVerifiedAt":
      return asset.lastVerifiedAt ? format(asset.lastVerifiedAt, dateFormat || "dd.MM.yyyy") : "";
    case "lastVerifiedBy":
      return asset.lastVerifiedBy?.fullName ?? "";
    case "remarks":
      return asset.remarks ?? "";
    default:
      return "";
  }
}

export async function buildExportWorkbook(
  assets: ExportableAsset[],
  fields: SapExportTemplateField[]
): Promise<Uint8Array> {
  const workbook = new ExcelJS.Workbook();
  const sheet = workbook.addWorksheet("SAP Upload");

  const ordered = [...fields].sort((a, b) => a.columnOrder - b.columnOrder);
  sheet.columns = ordered.map((f) => ({ header: f.sapFieldName, key: f.id, width: 22 }));

  for (const asset of assets) {
    const row: Record<string, string> = {};
    ordered.forEach((f) => {
      row[f.id] = resolvePortalField(asset, f.portalSourceField, f.format ?? undefined);
    });
    sheet.addRow(row);
  }

  sheet.getRow(1).font = { bold: true };
  return workbook.xlsx.writeBuffer() as unknown as Promise<Uint8Array>;
}
