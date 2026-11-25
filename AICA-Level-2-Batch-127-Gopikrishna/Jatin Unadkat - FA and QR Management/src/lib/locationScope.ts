import { redirect } from "next/navigation";
import { prisma } from "@/lib/prisma";
import type { Session } from "next-auth";

/**
 * A Location Head's scope is every location whose fullPath starts with one
 * of their assigned locations' fullPath (design dossier, ADD07 §03). Reuses
 * the materialized fullPath column — no recursive query needed.
 */
export async function getLocationHeadScopeRoots(userId: string): Promise<string[]> {
  const assignments = await prisma.locationHeadAssignment.findMany({
    where: { userId },
    include: { location: true },
  });
  return assignments.map((a) => a.location.fullPath);
}

export function isInScope(fullPath: string, roots: string[]): boolean {
  return roots.some((root) => fullPath === root || fullPath.startsWith(`${root} / `));
}

/**
 * Prisma `contains`-based OR filter for a Location Head's scope, suitable
 * for a `where: { currentLocation: { is: locationScopeWhere(roots) } }`
 * clause. Returns undefined (no filter) for non-scoped roles.
 */
export function locationScopeWhereClause(roots: string[]) {
  if (roots.length === 0) return { fullPath: "__no_scope__" };
  return { OR: roots.map((root) => ({ fullPath: { startsWith: root } })) };
}

export async function requireLocationScope(session: Session, fullPath: string | null | undefined) {
  if (session.user.role !== "LOCATION_HEAD") return;
  if (!fullPath) redirect("/forbidden");
  const roots = await getLocationHeadScopeRoots(session.user.id);
  if (!isInScope(fullPath, roots)) redirect("/forbidden");
}
