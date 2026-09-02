"use server";

import { z } from "zod";
import { revalidatePath } from "next/cache";
import { prisma } from "@/lib/prisma";
import { requireRole } from "@/lib/rbac";
import { getLocationHeadScopeRoots, isInScope } from "@/lib/locationScope";
import { logAudit } from "@/lib/audit";

const createSchema = z.object({
  name: z.string().min(1, "Name is required").max(120),
  parentLocationId: z.string().optional(),
});

async function assertLocationInScope(role: string, userId: string, fullPath: string) {
  if (role !== "LOCATION_HEAD") return;
  const roots = await getLocationHeadScopeRoots(userId);
  if (!isInScope(fullPath, roots)) throw new Error("This location is outside your assigned scope.");
}

export async function createLocation(formData: FormData) {
  const session = await requireRole("ADMIN", "LOCATION_HEAD");
  const parsed = createSchema.safeParse({
    name: formData.get("name"),
    parentLocationId: formData.get("parentLocationId") || undefined,
  });
  if (!parsed.success) throw new Error(parsed.error.issues[0].message);
  const { name, parentLocationId } = parsed.data;

  // A Location Head may only add sub-locations under their own scope — a
  // blank parent (a new top-level Main Location) is Admin-only.
  if (session.user.role === "LOCATION_HEAD" && !parentLocationId) {
    throw new Error("Only Admin can create a new top-level location. Add a sub-location under your assigned location instead.");
  }

  let levelNumber = 1;
  let parentFullPath: string | null = null;
  if (parentLocationId) {
    const parent = await prisma.location.findUnique({ where: { id: parentLocationId } });
    if (!parent) throw new Error("Parent location not found.");
    levelNumber = parent.levelNumber + 1;
    parentFullPath = parent.fullPath;
    await assertLocationInScope(session.user.role, session.user.id, parent.fullPath);
  }

  const fullPath = parentFullPath ? `${parentFullPath} / ${name}` : name;

  const location = await prisma.location.create({
    data: { name, parentLocationId: parentLocationId ?? null, levelNumber, fullPath },
  });

  await logAudit({
    userId: session.user.id,
    action: "CREATE",
    entityType: "Location",
    entityId: location.id,
    newValue: { name, fullPath },
  });

  revalidatePath("/locations");
}

export async function setLocationActive(locationId: string, isActive: boolean) {
  const session = await requireRole("ADMIN", "LOCATION_HEAD");

  const before = await prisma.location.findUnique({ where: { id: locationId } });
  if (!before) throw new Error("Location not found.");
  await assertLocationInScope(session.user.role, session.user.id, before.fullPath);

  if (!isActive) {
    const inUse = await prisma.asset.count({ where: { currentLocationId: locationId, isActive: true } });
    if (inUse > 0) {
      throw new Error(`Cannot deactivate — ${inUse} active asset(s) are still assigned to this location.`);
    }
  }

  const location = await prisma.location.update({ where: { id: locationId }, data: { isActive } });

  await logAudit({
    userId: session.user.id,
    action: isActive ? "REACTIVATE" : "DEACTIVATE",
    entityType: "Location",
    entityId: location.id,
    oldValue: { isActive: before.isActive },
    newValue: { isActive },
  });

  revalidatePath("/locations");
}
