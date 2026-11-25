import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { prisma } from "@/lib/prisma";
import type { RoleName } from "@prisma/client";
import type { Session } from "next-auth";

// ⚠️ TEMPORARY, TESTING-ONLY BYPASS (paired with src/proxy.ts). When on,
// every request is treated as the Admin demo user — no login, no RBAC
// distinction between roles. Looks the Admin user up fresh each call so it
// survives a db:reset without hitting a stale-ID foreign-key error.
// Set DISABLE_AUTH_FOR_TESTING=false (or delete the var) in .env to restore
// real login before this app holds anything real or goes anywhere
// non-ephemeral — with this on, anyone with the URL has full Admin access.
const AUTH_DISABLED = process.env.DISABLE_AUTH_FOR_TESTING === "true";

async function getBypassSession(): Promise<Session> {
  // Looked up fresh every call (not cached) so this survives a db:reset
  // instead of handing out a stale user ID that no longer exists.
  const admin = await prisma.user.findFirst({
    where: { role: { name: "ADMIN" }, isActive: true },
    include: { role: true },
  });
  if (!admin) throw new Error("DISABLE_AUTH_FOR_TESTING is on but no Admin user exists — run npm run db:seed.");
  return {
    user: { id: admin.id, name: admin.fullName, email: admin.email, role: admin.role.name },
    expires: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
  };
}

/**
 * Every mutation and every gated page calls one of these — the client
 * hiding a button is UX only, this is the real authorization boundary
 * (design dossier, Section G).
 */
export async function requireSession() {
  if (AUTH_DISABLED) return getBypassSession();
  const session = await auth();
  if (!session?.user) redirect("/login");
  return session;
}

export async function requireRole(...roles: RoleName[]) {
  const session = await requireSession();
  if (!AUTH_DISABLED && !roles.includes(session.user.role)) {
    redirect("/forbidden");
  }
  return session;
}

/**
 * Route Handlers can't use next/navigation's redirect() — it only unwinds
 * correctly inside Server Components/Actions. Use this in route.ts files
 * instead and return the 401/403 it gives back.
 */
export async function requireRoleApi(...roles: RoleName[]) {
  if (AUTH_DISABLED) return { ok: true as const, session: await getBypassSession() };
  const session = await auth();
  if (!session?.user) return { ok: false as const, status: 401 as const };
  if (!roles.includes(session.user.role)) return { ok: false as const, status: 403 as const };
  return { ok: true as const, session };
}

export function can(role: RoleName, action: string): boolean {
  const matrix: Record<string, RoleName[]> = {
    "asset:write": ["ADMIN"],
    "asset:import": ["ADMIN"],
    "qr:generate": ["ADMIN"],
    "location:write": ["ADMIN"],
    "campaign:write": ["ADMIN"],
    "exception:resolve": ["ADMIN"],
    "user:manage": ["ADMIN"],
    "audit:read": ["ADMIN"],
    "verification:submit": ["ADMIN", "VERIFIER"],
  };
  const allowed = matrix[action];
  return allowed ? allowed.includes(role) : true;
}
