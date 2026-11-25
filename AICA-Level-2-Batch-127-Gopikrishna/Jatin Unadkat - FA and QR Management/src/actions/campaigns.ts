"use server";

import { z } from "zod";
import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { prisma } from "@/lib/prisma";
import { requireRole } from "@/lib/rbac";
import { logAudit } from "@/lib/audit";

const schema = z.object({
  name: z.string().min(1, "Name is required"),
  startDate: z.string().min(1),
  endDate: z.string().min(1),
  departmentIds: z.array(z.string()).optional(),
});

export async function createCampaign(formData: FormData) {
  const session = await requireRole("ADMIN");
  const parsed = schema.safeParse({
    name: formData.get("name"),
    startDate: formData.get("startDate"),
    endDate: formData.get("endDate"),
    departmentIds: formData.getAll("departmentIds") as string[],
  });
  if (!parsed.success) throw new Error(parsed.error.issues[0].message);
  const { name, startDate, endDate, departmentIds } = parsed.data;

  const campaign = await prisma.verificationCampaign.create({
    data: {
      name,
      startDate: new Date(startDate),
      endDate: new Date(endDate),
      status: "ACTIVE",
      scopeJson: JSON.stringify({ departments: departmentIds ?? [] }),
    },
  });

  await logAudit({
    userId: session.user.id,
    action: "CREATE",
    entityType: "VerificationCampaign",
    entityId: campaign.id,
    newValue: { name, startDate, endDate },
  });

  revalidatePath("/campaigns");
  redirect(`/campaigns/${campaign.id}`);
}

export async function setCampaignStatus(campaignId: string, status: "ACTIVE" | "CLOSED" | "DRAFT") {
  const session = await requireRole("ADMIN");
  const campaign = await prisma.verificationCampaign.update({ where: { id: campaignId }, data: { status } });

  await logAudit({
    userId: session.user.id,
    action: "UPDATE_STATUS",
    entityType: "VerificationCampaign",
    entityId: campaign.id,
    newValue: { status },
  });

  revalidatePath("/campaigns");
  revalidatePath(`/campaigns/${campaignId}`);
}
