import { requireRole } from "@/lib/rbac";
import { prisma } from "@/lib/prisma";
import { getLocationHeadScopeRoots, locationScopeWhereClause } from "@/lib/locationScope";
import SapExportClient from "./SapExportClient";
import type { Prisma } from "@prisma/client";

export default async function SapExportPage() {
  const session = await requireRole("ADMIN", "LOCATION_HEAD");

  const where: Prisma.AssetWhereInput = { isActive: true, verificationStatus: { not: "NOT_VERIFIED" } };
  if (session.user.role === "LOCATION_HEAD") {
    where.currentLocation = { is: locationScopeWhereClause(await getLocationHeadScopeRoots(session.user.id)) };
  }

  const assets = await prisma.asset.findMany({
    where,
    orderBy: { assetNumber: "asc" },
    take: 500,
  });

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold">Export for SAP Upload</h1>
        <p className="text-sm text-muted mt-1">
          Select verified records, validate, and generate an Excel file for the SAP team to upload manually. This
          never writes to SAP directly.
        </p>
      </div>
      <SapExportClient
        assets={assets.map((a) => ({ id: a.id, assetNumber: a.assetNumber, description: a.description, verificationStatus: a.verificationStatus }))}
        role={session.user.role}
      />
    </div>
  );
}
