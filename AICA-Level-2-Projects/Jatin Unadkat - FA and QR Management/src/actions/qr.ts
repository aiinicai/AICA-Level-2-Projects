"use server";

import { revalidatePath } from "next/cache";
import { prisma } from "@/lib/prisma";
import { requireRole } from "@/lib/rbac";
import { getLocationHeadScopeRoots, isInScope } from "@/lib/locationScope";
import { logAudit } from "@/lib/audit";
import { generateQrToken } from "@/lib/qr";
import { buildLabelSheetPdf } from "@/lib/qrPdf";
import { writeVarFile } from "@/lib/fileStorage";
import { QR_SIZE_PRESETS } from "@/lib/qr";
import type { Session } from "next-auth";

async function assertAssetInScope(session: Session, assetId: string) {
  if (session.user.role !== "LOCATION_HEAD") return;
  const asset = await prisma.asset.findUnique({ where: { id: assetId }, include: { currentLocation: true } });
  const roots = await getLocationHeadScopeRoots(session.user.id);
  if (!asset?.currentLocation || !isInScope(asset.currentLocation.fullPath, roots)) {
    throw new Error("This asset is outside your assigned location scope.");
  }
}

export async function generateQrCode(assetId: string, sizePreset: string) {
  const session = await requireRole("ADMIN", "LOCATION_HEAD");
  await assertAssetInScope(session, assetId);

  // Deactivate any existing active code for this asset before issuing a new one —
  // history stays intact because we never delete QrCode rows (design dossier, Section K).
  await prisma.qrCode.updateMany({ where: { assetId, isActive: true }, data: { isActive: false } });

  const qr = await prisma.qrCode.create({
    data: { assetId, token: generateQrToken(), sizePreset, generatedById: session.user.id },
  });

  await logAudit({
    userId: session.user.id,
    action: "GENERATE_QR",
    entityType: "QrCode",
    entityId: qr.id,
    newValue: { assetId, sizePreset },
  });

  revalidatePath(`/assets/${assetId}/qr`);
  revalidatePath(`/assets/${assetId}`);
}

export async function reprintQrCode(qrCodeId: string) {
  const session = await requireRole("ADMIN", "LOCATION_HEAD");
  const existing = await prisma.qrCode.findUnique({ where: { id: qrCodeId } });
  if (!existing) throw new Error("QR code not found.");
  await assertAssetInScope(session, existing.assetId);

  const qr = await prisma.qrCode.update({
    where: { id: qrCodeId },
    data: { reprintCount: { increment: 1 } },
  });

  await logAudit({
    userId: session.user.id,
    action: "REPRINT_QR",
    entityType: "QrCode",
    entityId: qr.id,
    newValue: { reprintCount: qr.reprintCount },
  });

  revalidatePath(`/assets/${qr.assetId}/qr`);
}

/**
 * Bulk QR generation, sized for course-project scale: runs synchronously
 * and the BulkQrJob row is created already COMPLETED. The shape (filters,
 * status, result path) matches what a real background job would need, so
 * swapping in async processing later needs no data-model change (ADD11).
 */
export async function generateBulkQr(assetIds: string[], sizePreset: string) {
  const session = await requireRole("ADMIN", "LOCATION_HEAD");
  if (assetIds.length === 0) throw new Error("Select at least one asset.");

  if (session.user.role === "LOCATION_HEAD") {
    const roots = await getLocationHeadScopeRoots(session.user.id);
    const assets = await prisma.asset.findMany({ where: { id: { in: assetIds } }, include: { currentLocation: true } });
    const outOfScope = assets.find((a) => !a.currentLocation || !isInScope(a.currentLocation.fullPath, roots));
    if (outOfScope) throw new Error(`Asset ${outOfScope.assetNumber} is outside your assigned location scope.`);
  }

  const sizeMm = QR_SIZE_PRESETS[sizePreset as keyof typeof QR_SIZE_PRESETS]?.mm ?? 40;

  const labels: { token: string; assetNumber: string; description: string }[] = [];
  for (const assetId of assetIds) {
    const existingActive = await prisma.qrCode.findFirst({ where: { assetId, isActive: true } });
    let token: string;
    if (existingActive) {
      token = existingActive.token;
    } else {
      const asset = await prisma.asset.findUnique({ where: { id: assetId } });
      if (!asset) continue;
      await prisma.qrCode.updateMany({ where: { assetId, isActive: true }, data: { isActive: false } });
      const created = await prisma.qrCode.create({
        data: { assetId, token: generateQrToken(), sizePreset, generatedById: session.user.id },
      });
      token = created.token;
    }
    const asset = await prisma.asset.findUnique({ where: { id: assetId } });
    if (asset) labels.push({ token, assetNumber: asset.assetNumber, description: asset.description });
  }

  const pdfBytes = await buildLabelSheetPdf(labels, sizeMm);
  const fileName = `bulk-qr-${Date.now()}.pdf`;
  const filePath = await writeVarFile("qr-bulk", fileName, pdfBytes);

  const job = await prisma.bulkQrJob.create({
    data: {
      requestedById: session.user.id,
      filterJson: JSON.stringify({ assetIds }),
      sizePreset,
      assetCount: labels.length,
      status: "COMPLETED",
      resultFilePath: filePath,
    },
  });

  await logAudit({
    userId: session.user.id,
    action: "GENERATE_BULK_QR",
    entityType: "BulkQrJob",
    entityId: job.id,
    newValue: { assetCount: labels.length, sizePreset },
  });

  return { jobId: job.id, assetCount: labels.length };
}
