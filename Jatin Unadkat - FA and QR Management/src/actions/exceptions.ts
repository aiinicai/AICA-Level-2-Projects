"use server";

import { revalidatePath } from "next/cache";
import { prisma } from "@/lib/prisma";
import { requireRole } from "@/lib/rbac";
import { getLocationHeadScopeRoots, isInScope } from "@/lib/locationScope";
import { logAudit } from "@/lib/audit";
import type { Session } from "next-auth";

async function assertExceptionInScope(session: Session, exceptionId: string) {
  if (session.user.role !== "LOCATION_HEAD") return;
  const exception = await prisma.exception.findUnique({
    where: { id: exceptionId },
    include: { asset: { include: { currentLocation: true } } },
  });
  const fullPath = exception?.asset.currentLocation?.fullPath;
  const roots = await getLocationHeadScopeRoots(session.user.id);
  if (!fullPath || !isInScope(fullPath, roots)) {
    throw new Error("This exception is outside your assigned location scope.");
  }
}

export async function assignException(exceptionId: string, assignedToId: string) {
  const session = await requireRole("ADMIN", "LOCATION_HEAD");
  await assertExceptionInScope(session, exceptionId);

  const exception = await prisma.exception.update({
    where: { id: exceptionId },
    data: { assignedToId, status: "ASSIGNED" },
  });

  await logAudit({
    userId: session.user.id,
    action: "ASSIGN",
    entityType: "Exception",
    entityId: exception.id,
    newValue: { assignedToId },
  });

  revalidatePath("/exceptions");
}

export async function resolveException(exceptionId: string, formData: FormData) {
  const session = await requireRole("ADMIN", "LOCATION_HEAD");
  await assertExceptionInScope(session, exceptionId);
  const notes = String(formData.get("resolutionNotes") ?? "");

  const exception = await prisma.exception.update({
    where: { id: exceptionId },
    data: {
      status: "RESOLVED",
      resolutionNotes: notes || null,
      resolvedById: session.user.id,
      resolvedAt: new Date(),
    },
  });

  await logAudit({
    userId: session.user.id,
    action: "RESOLVE",
    entityType: "Exception",
    entityId: exception.id,
    newValue: { resolutionNotes: notes },
  });

  revalidatePath("/exceptions");
}

/** A Location Head's single approve/reject gate before Admin resolution (ADD07 §04). */
export async function reviewException(exceptionId: string, decision: "APPROVED" | "REJECTED") {
  const session = await requireRole("ADMIN", "LOCATION_HEAD");
  await assertExceptionInScope(session, exceptionId);

  const exception = await prisma.exception.update({
    where: { id: exceptionId },
    data: { reviewedById: session.user.id, reviewDecision: decision, reviewedAt: new Date() },
  });

  await logAudit({
    userId: session.user.id,
    action: "REVIEW",
    entityType: "Exception",
    entityId: exception.id,
    newValue: { reviewDecision: decision },
  });

  revalidatePath("/exceptions");
}
