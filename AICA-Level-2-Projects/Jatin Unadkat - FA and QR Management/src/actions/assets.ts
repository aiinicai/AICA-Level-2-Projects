"use server";

import { z } from "zod";
import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { prisma } from "@/lib/prisma";
import { requireRole } from "@/lib/rbac";
import { logAudit } from "@/lib/audit";

const optionalStr = z.string().trim().optional().transform((v) => (v ? v : undefined));

// Portal-owned fields only — SAP-sourced financial/identity data lives in
// SapAssetData and is never written here (design dossier, ADD06/ADD16).
const assetSchema = z.object({
  assetNumber: z.string().trim().min(1, "Asset number is required"),
  description: z.string().trim().min(1, "Description is required"),
  assetType: optionalStr,
  serialNumber: optionalStr,
  manufacturer: optionalStr,
  modelNumber: optionalStr,
  categoryId: optionalStr,
  departmentId: optionalStr,
  vendorId: optionalStr,
  currentLocationId: optionalStr,
  remarks: optionalStr,
});

// Fields that become locked once an asset is SAP-linked — any attempt to
// change them through the portal is rejected, even from Admin.
const SAP_LOCKED_FIELDS = ["assetNumber", "description", "serialNumber", "assetType", "manufacturer", "modelNumber"] as const;

function readAssetForm(formData: FormData) {
  const raw = Object.fromEntries(formData.entries());
  return assetSchema.parse(raw);
}

export async function createAsset(formData: FormData) {
  const session = await requireRole("ADMIN");
  const data = readAssetForm(formData);

  const existing = await prisma.asset.findUnique({ where: { assetNumber: data.assetNumber } });
  if (existing) throw new Error(`Asset number ${data.assetNumber} already exists.`);

  // Manual creation is only for assets found in the field but not yet in
  // SAP (design dossier, ADD03/ADD17 #9) — never for SAP-owned data.
  const asset = await prisma.asset.create({ data: { ...data, sourceType: "PORTAL_UNREGISTERED" } });

  await prisma.exception.create({
    data: { assetId: asset.id, type: "UNRECORDED_ASSET", status: "OPEN" },
  });

  await logAudit({
    userId: session.user.id,
    action: "CREATE",
    entityType: "Asset",
    entityId: asset.id,
    newValue: data,
  });

  revalidatePath("/assets");
  redirect(`/assets/${asset.id}`);
}

export async function updateAsset(assetId: string, formData: FormData) {
  const session = await requireRole("ADMIN");
  const data = readAssetForm(formData);

  const before = await prisma.asset.findUnique({ where: { id: assetId } });
  if (!before) throw new Error("Asset not found.");

  if (before.sourceType === "SAP_IMPORTED") {
    for (const field of SAP_LOCKED_FIELDS) {
      const oldValue = before[field] ?? null;
      const newValue = data[field] ?? null;
      if (oldValue !== newValue) {
        throw new Error(
          `${field} is sourced from SAP and cannot be edited in the portal. Correct it in SAP and re-import.`
        );
      }
    }
  }

  if (before.currentLocationId !== data.currentLocationId) {
    await prisma.assetLocationHistory.create({
      data: {
        assetId,
        fromLocationId: before.currentLocationId,
        toLocationId: data.currentLocationId ?? before.currentLocationId!,
        changedById: session.user.id,
        source: "MASTER_EDIT",
      },
    });
  }

  const asset = await prisma.asset.update({ where: { id: assetId }, data });

  await logAudit({
    userId: session.user.id,
    action: "UPDATE",
    entityType: "Asset",
    entityId: asset.id,
    oldValue: before,
    newValue: data,
  });

  revalidatePath("/assets");
  revalidatePath(`/assets/${assetId}`);
  redirect(`/assets/${assetId}`);
}

export async function setAssetActive(assetId: string, isActive: boolean) {
  const session = await requireRole("ADMIN");
  const before = await prisma.asset.findUnique({ where: { id: assetId } });
  const asset = await prisma.asset.update({ where: { id: assetId }, data: { isActive } });

  await logAudit({
    userId: session.user.id,
    action: isActive ? "REACTIVATE" : "ARCHIVE",
    entityType: "Asset",
    entityId: asset.id,
    oldValue: { isActive: before?.isActive },
    newValue: { isActive },
  });

  revalidatePath("/assets");
  revalidatePath(`/assets/${assetId}`);
}
