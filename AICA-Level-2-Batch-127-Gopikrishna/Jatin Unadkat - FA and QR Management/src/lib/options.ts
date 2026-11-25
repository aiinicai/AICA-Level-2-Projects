import { prisma } from "@/lib/prisma";
import { getLocationOptions } from "@/lib/locations";

export async function getFormOptions() {
  const [categories, departments, vendors, locations] = await Promise.all([
    prisma.assetCategory.findMany({ where: { isActive: true }, orderBy: { name: "asc" } }),
    prisma.department.findMany({ where: { isActive: true }, orderBy: { name: "asc" } }),
    prisma.vendor.findMany({ where: { isActive: true }, orderBy: { name: "asc" } }),
    getLocationOptions(),
  ]);
  return {
    categories: categories.map((c) => ({ id: c.id, label: c.name })),
    departments: departments.map((d) => ({ id: d.id, label: d.name })),
    vendors: vendors.map((v) => ({ id: v.id, label: v.name })),
    locations,
  };
}
