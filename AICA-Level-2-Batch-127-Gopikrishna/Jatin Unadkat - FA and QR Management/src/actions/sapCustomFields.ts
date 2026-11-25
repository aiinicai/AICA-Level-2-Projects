"use server";

import { revalidatePath } from "next/cache";
import { prisma } from "@/lib/prisma";
import { requireRole } from "@/lib/rbac";
import { logAudit } from "@/lib/audit";

export async function updateCustomFieldLabel(slotNumber: number, formData: FormData) {
  const session = await requireRole("ADMIN");
  const displayLabel = String(formData.get("displayLabel") ?? "").trim() || null;

  const before = await prisma.sapCustomFieldConfig.findUnique({ where: { slotNumber } });

  const config = await prisma.sapCustomFieldConfig.upsert({
    where: { slotNumber },
    create: { slotNumber, displayLabel },
    update: { displayLabel },
  });

  await logAudit({
    userId: session.user.id,
    action: "RELABEL_CUSTOM_FIELD",
    entityType: "SapCustomFieldConfig",
    entityId: config.id,
    oldValue: { displayLabel: before?.displayLabel },
    newValue: { displayLabel },
  });

  revalidatePath("/sap-custom-fields");
  revalidatePath("/assets");
}
