import { notFound } from "next/navigation";
import Link from "next/link";
import { requireRole } from "@/lib/rbac";
import { prisma } from "@/lib/prisma";
import { format } from "date-fns";
import { setCampaignStatus } from "@/actions/campaigns";

export default async function CampaignDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const session = await requireRole("ADMIN", "LOCATION_HEAD");
  const isAdmin = session.user.role === "ADMIN";
  const { id } = await params;

  const campaign = await prisma.verificationCampaign.findUnique({ where: { id } });
  if (!campaign) notFound();

  const scope = JSON.parse(campaign.scopeJson || "{}") as { departments?: string[] };
  const assetWhere = scope.departments?.length ? { departmentId: { in: scope.departments }, isActive: true } : { isActive: true };

  const [totalInScope, records] = await Promise.all([
    prisma.asset.count({ where: assetWhere }),
    prisma.verificationRecord.findMany({
      where: { campaignId: id },
      include: { asset: true, verifier: true },
      orderBy: { verifiedAt: "desc" },
    }),
  ]);

  const verifiedAssetIds = new Set(records.map((r) => r.assetId));
  const completion = totalInScope > 0 ? Math.round((verifiedAssetIds.size / totalInScope) * 100) : 0;

  const close = async () => { "use server"; await setCampaignStatus(id, "CLOSED"); };
  const reopen = async () => { "use server"; await setCampaignStatus(id, "ACTIVE"); };

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-semibold">{campaign.name}</h1>
          <p className="text-sm text-muted mt-1">{format(campaign.startDate, "dd MMM yyyy")} – {format(campaign.endDate, "dd MMM yyyy")}</p>
        </div>
        {isAdmin && (
          <form action={campaign.status === "CLOSED" ? reopen : close}>
            <button type="submit" className="btn-secondary">{campaign.status === "CLOSED" ? "Reopen" : "Close campaign"}</button>
          </form>
        )}
      </div>

      <div className="card p-5">
        <div className="flex items-center justify-between mb-2">
          <p className="text-sm font-medium">Completion</p>
          <p className="text-sm font-mono">{verifiedAssetIds.size} / {totalInScope} ({completion}%)</p>
        </div>
        <div className="h-2 rounded-full bg-line overflow-hidden">
          <div className="h-full bg-accent" style={{ width: `${completion}%` }} />
        </div>
      </div>

      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-muted border-b border-line">
              <th className="py-2 px-4">Asset</th>
              <th className="py-2 px-4">Result</th>
              <th className="py-2 px-4">Verifier</th>
              <th className="py-2 px-4">When</th>
            </tr>
          </thead>
          <tbody>
            {records.map((r) => (
              <tr key={r.id} className="border-b border-line last:border-0">
                <td className="py-2 px-4"><Link href={`/assets/${r.assetId}`} className="font-mono text-steel hover:underline">{r.asset.assetNumber}</Link></td>
                <td className="py-2 px-4">{r.result.replaceAll("_", " ")}</td>
                <td className="py-2 px-4 text-muted">{r.verifier.fullName}</td>
                <td className="py-2 px-4 text-muted">{format(r.verifiedAt, "dd MMM yyyy, HH:mm")}</td>
              </tr>
            ))}
            {records.length === 0 && <tr><td colSpan={4} className="py-8 text-center text-muted">No verifications logged yet.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
