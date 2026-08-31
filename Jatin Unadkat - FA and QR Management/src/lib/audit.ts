import { prisma } from "@/lib/prisma";

export async function logAudit(params: {
  userId?: string | null;
  action: string;
  entityType: string;
  entityId: string;
  oldValue?: unknown;
  newValue?: unknown;
  source?: string;
}) {
  await prisma.auditLog.create({
    data: {
      userId: params.userId ?? null,
      action: params.action,
      entityType: params.entityType,
      entityId: params.entityId,
      oldValueJson: params.oldValue !== undefined ? JSON.stringify(params.oldValue) : null,
      newValueJson: params.newValue !== undefined ? JSON.stringify(params.newValue) : null,
      source: params.source ?? "WEB",
    },
  });
}
