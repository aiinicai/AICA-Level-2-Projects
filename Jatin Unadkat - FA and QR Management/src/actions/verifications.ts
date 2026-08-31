"use server";

import { z } from "zod";
import { revalidatePath } from "next/cache";
import { prisma } from "@/lib/prisma";
import { requireRole } from "@/lib/rbac";
import { logAudit } from "@/lib/audit";
import { processAndStorePhoto, validateUpload } from "@/lib/images";
import type { VerificationResult, VerificationStatus } from "@prisma/client";

const schema = z.object({
  result: z.enum(["VERIFIED", "NOT_FOUND", "DAMAGED", "RELOCATED"]),
  verifiedLocationId: z.string().min(1, "Select the location where you found (or expected) the asset."),
  condition: z.string().optional(),
  observedSerialNumber: z.string().optional(),
  remarks: z.string().optional(),
  campaignId: z.string().optional(),
  gpsLat: z.string().optional(),
  gpsLng: z.string().optional(),
});

const RESULT_TO_STATUS: Record<VerificationResult, VerificationStatus> = {
  VERIFIED: "VERIFIED",
  NOT_FOUND: "NOT_FOUND",
  DAMAGED: "DAMAGED",
  RELOCATED: "RELOCATED",
};

const RESULT_TO_EXCEPTION = {
  NOT_FOUND: "NOT_FOUND",
  DAMAGED: "DAMAGED",
} as const;

export async function submitVerification(assetId: string, formData: FormData) {
  const session = await requireRole("ADMIN", "VERIFIER", "LOCATION_HEAD");

  const parsed = schema.safeParse({
    result: formData.get("result"),
    verifiedLocationId: formData.get("verifiedLocationId"),
    condition: formData.get("condition") || undefined,
    observedSerialNumber: formData.get("observedSerialNumber") || undefined,
    remarks: formData.get("remarks") || undefined,
    campaignId: formData.get("campaignId") || undefined,
    gpsLat: formData.get("gpsLat") || undefined,
    gpsLng: formData.get("gpsLng") || undefined,
  });
  if (!parsed.success) throw new Error(parsed.error.issues[0].message);
  const data = parsed.data;

  const asset = await prisma.asset.findUnique({ where: { id: assetId } });
  if (!asset) throw new Error("Asset not found.");

  const locationChanged = asset.currentLocationId !== data.verifiedLocationId;
  const finalStatus: VerificationStatus =
    data.result === "VERIFIED" && locationChanged ? "LOCATION_MISMATCH" : RESULT_TO_STATUS[data.result];

  const verification = await prisma.verificationRecord.create({
    data: {
      assetId,
      campaignId: data.campaignId || null,
      verifierId: session.user.id,
      result: data.result,
      condition: data.condition || null,
      observedSerialNumber: data.observedSerialNumber || null,
      verifiedLocationId: data.verifiedLocationId,
      remarks: data.remarks,
      gpsLat: data.gpsLat ? Number(data.gpsLat) : null,
      gpsLng: data.gpsLng ? Number(data.gpsLng) : null,
    },
  });

  if (locationChanged) {
    await prisma.assetLocationHistory.create({
      data: {
        assetId,
        fromLocationId: asset.currentLocationId,
        toLocationId: data.verifiedLocationId,
        changedById: session.user.id,
        source: "VERIFICATION",
      },
    });
  }

  await prisma.asset.update({
    where: { id: assetId },
    data: {
      currentLocationId: data.verifiedLocationId,
      verificationStatus: finalStatus,
      physicalCondition: data.condition || undefined,
      lastVerifiedAt: verification.verifiedAt,
      lastVerifiedById: session.user.id,
    },
  });

  const photo = formData.get("photo") as File | null;
  if (photo && photo.size > 0) {
    validateUpload(photo);
    const buffer = Buffer.from(await photo.arrayBuffer());
    const { storageKey, thumbnailKey } = await processAndStorePhoto(buffer, assetId);
    await prisma.assetPhotograph.create({
      data: {
        assetId,
        verificationId: verification.id,
        storageKey,
        thumbnailKey,
        photoType: "VERIFICATION",
        uploadedById: session.user.id,
      },
    });
  }

  const exceptionType = RESULT_TO_EXCEPTION[data.result as keyof typeof RESULT_TO_EXCEPTION];
  if (exceptionType || (data.result === "VERIFIED" && locationChanged)) {
    await prisma.exception.create({
      data: {
        assetId,
        verificationId: verification.id,
        type: exceptionType ?? "FOUND_ELSEWHERE",
        status: "OPEN",
      },
    });
  }

  await logAudit({
    userId: session.user.id,
    action: "SUBMIT_VERIFICATION",
    entityType: "VerificationRecord",
    entityId: verification.id,
    newValue: { result: data.result, verifiedLocationId: data.verifiedLocationId },
  });

  revalidatePath(`/assets/${assetId}`);
  revalidatePath("/exceptions");
  revalidatePath("/dashboard");
  revalidatePath("/mismatches");

  return { ok: true as const, result: data.result, status: finalStatus };
}
