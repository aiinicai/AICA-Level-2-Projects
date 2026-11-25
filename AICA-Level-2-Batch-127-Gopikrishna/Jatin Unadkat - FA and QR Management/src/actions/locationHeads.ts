"use server";

import { revalidatePath } from "next/cache";
import { prisma } from "@/lib/prisma";
import { requireRole } from "@/lib/rbac";
import { logAudit } from "@/lib/audit";

export async function assignLocationHead(formData: FormData) {
  const session = await requireRole("ADMIN");
  const userId = String(formData.get("userId"));
  const locationId = String(formData.get("locationId"));
  if (!userId || !locationId) throw new Error("Select both a user and a location.");

  const existing = await prisma.locationHeadAssignment.findUnique({
    where: { userId_locationId: { userId, locationId } },
  });
  if (existing) throw new Error("This user is already assigned to this location.");

  const assignment = await prisma.locationHeadAssignment.create({
    data: { userId, locationId, assignedById: session.user.id },
  });

  await logAudit({
    userId: session.user.id,
    action: "ASSIGN_LOCATION_HEAD",
    entityType: "LocationHeadAssignment",
    entityId: assignment.id,
    newValue: { userId, locationId },
  });

  revalidatePath("/location-heads");
}

export async function removeLocationHeadAssignment(id: string) {
  const session = await requireRole("ADMIN");
  await prisma.locationHeadAssignment.delete({ where: { id } });

  await logAudit({
    userId: session.user.id,
    action: "REMOVE_LOCATION_HEAD",
    entityType: "LocationHeadAssignment",
    entityId: id,
  });

  revalidatePath("/location-heads");
}
