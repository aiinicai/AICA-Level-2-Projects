import Link from "next/link";
import { requireSession } from "@/lib/rbac";
import { getLocationHeadScopeRoots, locationScopeWhereClause } from "@/lib/locationScope";
import { prisma } from "@/lib/prisma";
import type { Prisma, VerificationStatus } from "@prisma/client";

const STATUS_STYLE: Record<string, string> = {
  NOT_VERIFIED: "bg-steel-soft text-steel",
  VERIFIED: "bg-good-soft text-good",
  NOT_FOUND: "bg-bad-soft text-bad",
  LOCATION_MISMATCH: "bg-warn-soft text-warn",
  DAMAGED: "bg-bad-soft text-bad",
  RELOCATED: "bg-warn-soft text-warn",
  UNDER_INVESTIGATION: "bg-warn-soft text-warn",
};

export default async function AssetsPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; status?: string }>;
}) {
  const session = await requireSession();
  const { q, status } = await searchParams;

  const where: Prisma.AssetWhereInput = { isActive: true };
  if (q) {
    where.OR = [
      { assetNumber: { contains: q } },
      { description: { contains: q } },
      { serialNumber: { contains: q } },
    ];
  }
  if (status) where.verificationStatus = status as VerificationStatus;
  if (session.user.role === "LOCATION_HEAD") {
    const roots = await getLocationHeadScopeRoots(session.user.id);
    where.currentLocation = { is: locationScopeWhereClause(roots) };
  }

  const assets = await prisma.asset.findMany({
    where,
    include: { category: true, department: true, currentLocation: true, sapAssetData: true },
    orderBy: { assetNumber: "asc" },
    take: 200,
  });

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-semibold">Assets</h1>
          <p className="text-sm text-muted mt-1">{assets.length} shown</p>
        </div>
        {session.user.role === "ADMIN" && (
          <div className="flex gap-2">
            <Link href="/sap-import" className="btn-secondary">SAP import</Link>
            <Link href="/assets/new" className="btn-primary">Add unregistered asset</Link>
          </div>
        )}
      </div>

      <form className="card p-4 flex flex-wrap gap-3 items-end">
        <div className="flex-1 min-w-[200px]">
          <label className="label" htmlFor="q">Search</label>
          <input id="q" name="q" defaultValue={q} className="input" placeholder="Asset number, description, serial…" />
        </div>
        <div className="min-w-[200px]">
          <label className="label" htmlFor="status">Verification status</label>
          <select id="status" name="status" defaultValue={status ?? ""} className="input">
            <option value="">All</option>
            <option value="NOT_VERIFIED">Not Verified</option>
            <option value="VERIFIED">Verified</option>
            <option value="NOT_FOUND">Not Found</option>
            <option value="LOCATION_MISMATCH">Location Mismatch</option>
            <option value="DAMAGED">Damaged</option>
            <option value="RELOCATED">Relocated</option>
            <option value="UNDER_INVESTIGATION">Under Investigation</option>
          </select>
        </div>
        <button type="submit" className="btn-secondary">Filter</button>
      </form>

      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-muted border-b border-line">
              <th className="py-2 px-4">Asset #</th>
              <th className="py-2 px-4">Description</th>
              <th className="py-2 px-4">SAP Asset Class</th>
              <th className="py-2 px-4">Department</th>
              <th className="py-2 px-4">Location</th>
              <th className="py-2 px-4">Status</th>
            </tr>
          </thead>
          <tbody>
            {assets.map((a) => (
              <tr key={a.id} className="border-b border-line last:border-0 hover:bg-black/[0.02]">
                <td className="py-2 px-4">
                  <Link href={`/assets/${a.id}`} className="font-mono text-steel hover:underline">{a.assetNumber}</Link>
                </td>
                <td className="py-2 px-4">{a.description}</td>
                <td className="py-2 px-4 text-muted">{a.sapAssetData?.assetClassDescription ?? (a.sourceType === "SAP_IMPORTED" ? "—" : "Not in SAP")}</td>
                <td className="py-2 px-4 text-muted">{a.department?.name ?? "—"}</td>
                <td className="py-2 px-4 text-muted">{a.currentLocation?.fullPath ?? "—"}</td>
                <td className="py-2 px-4">
                  <span className={`pill ${STATUS_STYLE[a.verificationStatus] ?? ""}`}>
                    {a.verificationStatus.replaceAll("_", " ")}
                  </span>
                </td>
              </tr>
            ))}
            {assets.length === 0 && (
              <tr><td colSpan={6} className="py-8 text-center text-muted">No assets match this search.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
