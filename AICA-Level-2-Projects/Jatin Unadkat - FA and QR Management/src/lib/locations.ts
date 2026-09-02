import { prisma } from "@/lib/prisma";

export async function computeFullPath(parentLocationId: string | null, name: string): Promise<string> {
  if (!parentLocationId) return name;
  const parent = await prisma.location.findUnique({ where: { id: parentLocationId } });
  if (!parent) return name;
  return `${parent.fullPath} / ${name}`;
}

export type LocationNode = {
  id: string;
  name: string;
  levelNumber: number;
  fullPath: string;
  isActive: boolean;
  children: LocationNode[];
};

export async function getLocationTree(): Promise<LocationNode[]> {
  const all = await prisma.location.findMany({ orderBy: [{ levelNumber: "asc" }, { name: "asc" }] });
  const byId = new Map<string, LocationNode>();
  all.forEach((l) => byId.set(l.id, { ...l, children: [] }));
  const roots: LocationNode[] = [];
  all.forEach((l) => {
    const node = byId.get(l.id)!;
    if (l.parentLocationId && byId.has(l.parentLocationId)) {
      byId.get(l.parentLocationId)!.children.push(node);
    } else {
      roots.push(node);
    }
  });
  return roots;
}

export async function getLocationOptions() {
  const all = await prisma.location.findMany({
    where: { isActive: true },
    orderBy: { fullPath: "asc" },
  });
  return all.map((l) => ({ id: l.id, label: l.fullPath }));
}
