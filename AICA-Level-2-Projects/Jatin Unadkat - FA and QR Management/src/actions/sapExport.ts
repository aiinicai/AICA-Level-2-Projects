"use server";

import { revalidatePath } from "next/cache";
import { prisma } from "@/lib/prisma";
import { requireRole } from "@/lib/rbac";
import { getLocationHeadScopeRoots, isInScope } from "@/lib/locationScope";
import { logAudit } from "@/lib/audit";
import { buildExportWorkbook } from "@/lib/sapExport";
import { writeVarFile } from "@/lib/fileStorage";

export type SapExportValidation = {
  selectedCount: number;
  locationChangedCount: number;
  exceptionCount: number;
  excluded: { assetId: string; assetNumber: string; reason: string }[];
};

export async function validateSapExportSelection(assetIds: string[]): Promise<SapExportValidation> {
  await requireRole("ADMIN", "LOCATION_HEAD");

  const assets = await prisma.asset.findMany({
    where: { id: { in: assetIds } },
    include: {
      locationHistory: { where: { source: "VERIFICATION" } },
      exceptions: { where: { status: { not: "RESOLVED" } } },
    },
  });

  const excluded: SapExportValidation["excluded"] = [];
  for (const a of assets) {
    if (a.verificationStatus === "NOT_VERIFIED") {
      excluded.push({ assetId: a.id, assetNumber: a.assetNumber, reason: "Not yet verified" });
    }
  }

  return {
    selectedCount: assets.length,
    locationChangedCount: assets.filter((a) => a.locationHistory.length > 0).length,
    exceptionCount: assets.filter((a) => a.exceptions.length > 0).length,
    excluded,
  };
}

export async function generateSapExport(assetIds: string[]) {
  const session = await requireRole("ADMIN", "LOCATION_HEAD");

  if (session.user.role === "LOCATION_HEAD") {
    const roots = await getLocationHeadScopeRoots(session.user.id);
    const assets = await prisma.asset.findMany({ where: { id: { in: assetIds } }, include: { currentLocation: true } });
    const outOfScope = assets.find((a) => !a.currentLocation || !isInScope(a.currentLocation.fullPath, roots));
    if (outOfScope) throw new Error(`Asset ${outOfScope.assetNumber} is outside your assigned location scope.`);
  }

  const validation = await validateSapExportSelection(assetIds);
  const excludedIds = new Set(validation.excluded.map((e) => e.assetId));
  const includedIds = assetIds.filter((id) => !excludedIds.has(id));

  const [assets, fields] = await Promise.all([
    prisma.asset.findMany({
      where: { id: { in: includedIds } },
      include: { currentLocation: true, lastVerifiedBy: true },
    }),
    prisma.sapExportTemplateField.findMany({ orderBy: { columnOrder: "asc" } }),
  ]);

  if (fields.length === 0) throw new Error("No export template is configured. Set one up on the SAP Export Template page first.");

  const bytes = await buildExportWorkbook(assets, fields);
  const fileName = `sap-upload-${Date.now()}.xlsx`;
  const filePath = await writeVarFile("sap-exports", fileName, bytes);

  const batch = await prisma.sapExportBatch.create({
    data: { generatedById: session.user.id, fileName, filePath, status: "GENERATED" },
  });

  await prisma.sapExportRecord.createMany({
    data: [
      ...includedIds.map((assetId) => ({ batchId: batch.id, assetId, included: true })),
      ...validation.excluded.map((e) => ({ batchId: batch.id, assetId: e.assetId, included: false, exclusionReason: e.reason })),
    ],
  });

  await logAudit({
    userId: session.user.id,
    action: "SAP_EXPORT",
    entityType: "SapExportBatch",
    entityId: batch.id,
    newValue: { includedCount: includedIds.length, excludedCount: validation.excluded.length },
  });

  revalidatePath("/sap-export-history");
  return { batchId: batch.id, includedCount: includedIds.length, excludedCount: validation.excluded.length };
}

export async function addExportTemplateField(formData: FormData) {
  await requireRole("ADMIN");
  const sapFieldName = String(formData.get("sapFieldName") ?? "").trim();
  const portalSourceField = String(formData.get("portalSourceField") ?? "");
  const columnOrder = Number(formData.get("columnOrder") ?? 0);
  const format = String(formData.get("format") ?? "").trim() || null;
  const isRequired = formData.get("isRequired") === "on";
  if (!sapFieldName || !portalSourceField) throw new Error("SAP field name and portal source are required.");

  await prisma.sapExportTemplateField.create({
    data: { sapFieldName, portalSourceField, columnOrder, format, isRequired },
  });
  revalidatePath("/sap-export-template");
}

export async function removeExportTemplateField(id: string) {
  await requireRole("ADMIN");
  await prisma.sapExportTemplateField.delete({ where: { id } });
  revalidatePath("/sap-export-template");
}
