"use server";

import { z } from "zod";
import bcrypt from "bcryptjs";
import { revalidatePath } from "next/cache";
import { prisma } from "@/lib/prisma";
import { requireRole } from "@/lib/rbac";
import { logAudit } from "@/lib/audit";

const schema = z.object({
  fullName: z.string().min(1, "Name is required"),
  email: z.email("Enter a valid email"),
  password: z.string().min(8, "Password must be at least 8 characters"),
  roleName: z.enum(["ADMIN", "LOCATION_HEAD", "READ_ONLY", "VERIFIER"]),
});

export async function createUser(formData: FormData) {
  const session = await requireRole("ADMIN");
  const parsed = schema.safeParse({
    fullName: formData.get("fullName"),
    email: formData.get("email"),
    password: formData.get("password"),
    roleName: formData.get("roleName"),
  });
  if (!parsed.success) throw new Error(parsed.error.issues[0].message);
  const { fullName, email, password, roleName } = parsed.data;

  const existing = await prisma.user.findUnique({ where: { email: email.toLowerCase() } });
  if (existing) throw new Error("A user with this email already exists.");

  const role = await prisma.role.findUnique({ where: { name: roleName } });
  if (!role) throw new Error("Role not found.");

  const passwordHash = await bcrypt.hash(password, 10);
  const user = await prisma.user.create({
    data: { fullName, email: email.toLowerCase(), passwordHash, roleId: role.id },
  });

  await logAudit({
    userId: session.user.id,
    action: "CREATE",
    entityType: "User",
    entityId: user.id,
    newValue: { fullName, email, roleName },
  });

  revalidatePath("/users");
}

export async function setUserActive(userId: string, isActive: boolean) {
  const session = await requireRole("ADMIN");
  if (userId === session.user.id && !isActive) throw new Error("You cannot deactivate your own account.");

  const user = await prisma.user.update({ where: { id: userId }, data: { isActive } });

  await logAudit({
    userId: session.user.id,
    action: isActive ? "REACTIVATE" : "DEACTIVATE",
    entityType: "User",
    entityId: user.id,
    newValue: { isActive },
  });

  revalidatePath("/users");
}
