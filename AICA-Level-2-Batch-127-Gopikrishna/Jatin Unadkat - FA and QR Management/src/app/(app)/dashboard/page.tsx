import Link from "next/link";
import { requireSession } from "@/lib/rbac";
import { prisma } from "@/lib/prisma";
import { format } from "date-fns";
import { getLocationHeadScopeRoots, locationScopeWhereClause } from "@/lib/locationScope";
import type { Prisma } from "@prisma/client";

function Kpi({ label, value, tone }: { label: string; value: number | string; tone?: string }) {
  return (
    <div className="card p-4">
      <p className={`font-mono text-xl font-semibold ${tone ?? "text-accent"}`}>{value}</p>
      <p className="text-xs text-muted mt-1">{label}</p>
    </div>
  );
}

async function ScopedDashboard({ scopeRoots }: { scopeRoots?: string[] }) {
  const locationFilter: Prisma.AssetWhereInput = scopeRoots
    ? { currentLocation: { is: locationScopeWhereClause(scopeRoots) } }
    : {};

  const [total, verified, pending, notFound, mismatch, damaged, relocated, campaigns, exceptions] = await Promise.all([
    prisma.asset.count({ where: { isActive: true, ...locationFilter } }),
    prisma.asset.count({ where: { verificationStatus: "VERIFIED", ...locationFilter } }),
    prisma.asset.count({ where: { verificationStatus: "NOT_VERIFIED", isActive: true, ...locationFilter } }),
    prisma.asset.count({ where: { verificationStatus: "NOT_FOUND", ...locationFilter } }),
    prisma.asset.count({ where: { verificationStatus: "LOCATION_MISMATCH", ...locationFilter } }),
    prisma.asset.count({ where: { verificationStatus: "DAMAGED", ...locationFilter } }),
    prisma.asset.count({ where: { verificationStatus: "RELOCATED", ...locationFilter } }),
    prisma.verificationCampaign.findMany({ where: { status: "ACTIVE" } }),
    prisma.exception.findMany({
      where: { status: { not: "RESOLVED" }, asset: locationFilter },
      include: { asset: true },
      take: 5,
      orderBy: { createdAt: "desc" },
    }),
  ]);
  const completion = total > 0 ? Math.round((verified / total) * 100) : 0;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Kpi label="Total assets" value={total} />
        <Kpi label="Verified" value={verified} tone="text-good" />
        <Kpi label="Pending verification" value={pending} tone="text-steel" />
        <Kpi label="Completion" value={`${completion}%`} />
        <Kpi label="Not found" value={notFound} tone="text-bad" />
        <Kpi label="Location mismatch" value={mismatch} tone="text-warn" />
        <Kpi label="Damaged" value={damaged} tone="text-bad" />
        <Kpi label="Relocated" value={relocated} tone="text-warn" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="card p-5">
          <h2 className="text-sm font-semibold mb-3">Active campaigns</h2>
          {campaigns.length === 0 && <p className="text-sm text-muted">None running. <Link href="/campaigns" className="text-steel hover:underline">Start one →</Link></p>}
          <div className="space-y-2">
            {campaigns.map((c) => (
              <Link key={c.id} href={`/campaigns/${c.id}`} className="block text-sm text-steel hover:underline">{c.name}</Link>
            ))}
          </div>
        </div>
        <div className="card p-5">
          <h2 className="text-sm font-semibold mb-3">Recent exceptions</h2>
          {exceptions.length === 0 && <p className="text-sm text-muted">No open exceptions.</p>}
          <div className="space-y-2">
            {exceptions.map((e) => (
              <div key={e.id} className="flex items-center justify-between text-sm">
                <Link href={`/assets/${e.assetId}`} className="font-mono text-steel hover:underline">{e.asset.assetNumber}</Link>
                <span className="text-muted">{e.type.replaceAll("_", " ")}</span>
              </div>
            ))}
          </div>
          <Link href="/exceptions" className="text-xs text-steel hover:underline mt-3 inline-block">Open exception queue →</Link>
        </div>
      </div>
      <Link href="/mismatches" className="text-xs text-steel hover:underline">View the mismatch dashboard →</Link>
    </div>
  );
}

async function VerifierDashboard({ userId }: { userId: string }) {
  const [campaign, myRecent] = await Promise.all([
    prisma.verificationCampaign.findFirst({ where: { status: "ACTIVE" }, orderBy: { startDate: "desc" } }),
    prisma.verificationRecord.findMany({ where: { verifierId: userId }, include: { asset: true }, orderBy: { verifiedAt: "desc" }, take: 8 }),
  ]);

  return (
    <div className="space-y-6">
      {campaign && (
        <div className="card p-5">
          <p className="pill bg-steel-soft text-steel">{campaign.name}</p>
          <p className="text-sm text-muted mt-2">{format(campaign.startDate, "dd MMM")} – {format(campaign.endDate, "dd MMM yyyy")}</p>
        </div>
      )}
      <Link href="/scan" className="btn-primary w-full text-center py-4 text-base block">Scan a QR to verify an asset</Link>
      <div className="card p-5">
        <h2 className="text-sm font-semibold mb-3">Your recent verifications</h2>
        {myRecent.length === 0 && <p className="text-sm text-muted">Nothing submitted yet — go scan something.</p>}
        <div className="space-y-2">
          {myRecent.map((v) => (
            <div key={v.id} className="flex items-center justify-between text-sm">
              <Link href={`/assets/${v.assetId}`} className="font-mono text-steel hover:underline">{v.asset.assetNumber}</Link>
              <span className="text-muted">{v.result.replaceAll("_", " ")} · {format(v.verifiedAt, "dd MMM")}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function ReadOnlyDashboard() {
  return (
    <div className="space-y-4">
      <Link href="/scan" className="btn-primary w-full text-center py-4 text-base block">Scan a QR to look up an asset</Link>
      <Link href="/assets" className="btn-secondary w-full text-center py-4 text-base block">Search the asset register</Link>
    </div>
  );
}

export default async function DashboardPage() {
  const session = await requireSession();
  const scopeRoots =
    session.user.role === "LOCATION_HEAD" ? await getLocationHeadScopeRoots(session.user.id) : undefined;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold">Welcome, {session.user.name}</h1>
        <p className="text-sm text-muted mt-1">
          {session.user.role === "ADMIN" && "Register health and verification progress."}
          {session.user.role === "LOCATION_HEAD" && `Verification progress for your assigned location${scopeRoots && scopeRoots.length > 1 ? "s" : ""}: ${scopeRoots?.join(", ")}.`}
          {session.user.role === "VERIFIER" && "Your field verification workspace."}
          {session.user.role === "READ_ONLY" && "Look up assets and their verification status."}
        </p>
      </div>
      {session.user.role === "ADMIN" && <ScopedDashboard />}
      {session.user.role === "LOCATION_HEAD" && <ScopedDashboard scopeRoots={scopeRoots} />}
      {session.user.role === "VERIFIER" && <VerifierDashboard userId={session.user.id} />}
      {session.user.role === "READ_ONLY" && <ReadOnlyDashboard />}
    </div>
  );
}
