import Link from "next/link";
import { requireRole } from "@/lib/rbac";
import { prisma } from "@/lib/prisma";
import { getLocationHeadScopeRoots, locationScopeWhereClause } from "@/lib/locationScope";
import { getMismatchFlags } from "@/lib/comparison";

export default async function MismatchesPage() {
  const session = await requireRole("ADMIN", "LOCATION_HEAD");

  const where =
    session.user.role === "LOCATION_HEAD"
      ? { currentLocation: { is: locationScopeWhereClause(await getLocationHeadScopeRoots(session.user.id)) } }
      : {};

  const assets = await prisma.asset.findMany({
    where: { ...where, isActive: true },
    include: {
      sapAssetData: true,
      currentLocation: true,
      verificationRecords: {
        orderBy: { verifiedAt: "desc" },
        take: 1,
        include: { verifier: true, verifiedLocation: true },
      },
    },
  });

  const flagged = assets
    .map((a) => ({ asset: a, flags: getMismatchFlags(a) }))
    .filter((r) => r.flags.length > 0);

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold">Mismatch / Exception Dashboard</h1>
        <p className="text-sm text-muted mt-1">SAP-vs-physical discrepancies, surfaced automatically — never auto-resolved either direction.</p>
      </div>

      <div className="card divide-y divide-line">
        {flagged.map(({ asset, flags }) => (
          <div key={asset.id} className="p-4 space-y-2">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <Link href={`/assets/${asset.id}`} className="font-mono text-sm text-steel hover:underline">{asset.assetNumber}</Link>
              <span className="text-sm text-muted">{asset.description}</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {flags.map((f) => (
                <span key={f.key} className={`pill ${f.severity === "bad" ? "bg-bad-soft text-bad" : "bg-warn-soft text-warn"}`}>
                  {f.severity === "bad" ? "🔴" : "🟠"} {f.label}
                </span>
              ))}
            </div>
          </div>
        ))}
        {flagged.length === 0 && <p className="p-8 text-center text-muted text-sm">No mismatches — SAP and physical verification agree everywhere in scope.</p>}
      </div>
    </div>
  );
}
