import { requireRole } from "@/lib/rbac";
import { prisma } from "@/lib/prisma";
import { getLocationHeadScopeRoots, locationScopeWhereClause } from "@/lib/locationScope";
import { getLocationOptions } from "@/lib/locations";
import BulkQrClient from "./BulkQrClient";
import type { Prisma } from "@prisma/client";

export default async function BulkQrPage({
  searchParams,
}: {
  searchParams: Promise<{ assetClass?: string; locationId?: string; noQrOnly?: string }>;
}) {
  const session = await requireRole("ADMIN", "LOCATION_HEAD");
  const { assetClass, locationId, noQrOnly } = await searchParams;

  const where: Prisma.AssetWhereInput = { isActive: true };
  if (session.user.role === "LOCATION_HEAD") {
    where.currentLocation = { is: locationScopeWhereClause(await getLocationHeadScopeRoots(session.user.id)) };
  }
  if (assetClass) where.sapAssetData = { is: { assetClassCode: assetClass } };
  if (locationId) where.currentLocationId = locationId;

  const [assets, assetClasses, locations] = await Promise.all([
    prisma.asset.findMany({
      where,
      include: { qrCodes: { where: { isActive: true } } },
      orderBy: { assetNumber: "asc" },
      take: 500,
    }),
    prisma.sapAssetData.findMany({
      where: { assetClassCode: { not: null } },
      select: { assetClassCode: true, assetClassDescription: true },
      distinct: ["assetClassCode"],
    }),
    getLocationOptions(),
  ]);

  const rows = assets
    .filter((a) => (noQrOnly === "true" ? a.qrCodes.length === 0 : true))
    .map((a) => ({ id: a.id, assetNumber: a.assetNumber, description: a.description, hasQr: a.qrCodes.length > 0 }));

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold">Bulk QR Generation</h1>
        <p className="text-sm text-muted mt-1">Filter, select, and generate a single printable label sheet for many assets at once.</p>
      </div>

      <form className="card p-4 flex flex-wrap gap-3 items-end">
        <div className="min-w-[180px]">
          <label className="label" htmlFor="assetClass">SAP Asset Class</label>
          <select id="assetClass" name="assetClass" defaultValue={assetClass ?? ""} className="input">
            <option value="">All</option>
            {assetClasses.map((c) => c.assetClassCode && (
              <option key={c.assetClassCode} value={c.assetClassCode}>{c.assetClassCode} — {c.assetClassDescription}</option>
            ))}
          </select>
        </div>
        <div className="min-w-[200px]">
          <label className="label" htmlFor="locationId">Location</label>
          <select id="locationId" name="locationId" defaultValue={locationId ?? ""} className="input">
            <option value="">All</option>
            {locations.map((l) => <option key={l.id} value={l.id}>{l.label}</option>)}
          </select>
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" name="noQrOnly" value="true" defaultChecked={noQrOnly === "true"} />
          Assets without a QR yet
        </label>
        <button type="submit" className="btn-secondary">Filter</button>
      </form>

      <BulkQrClient assets={rows} />
    </div>
  );
}
