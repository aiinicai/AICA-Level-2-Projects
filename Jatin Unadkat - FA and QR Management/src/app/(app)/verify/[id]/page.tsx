import { notFound } from "next/navigation";
import { requireRole } from "@/lib/rbac";
import { prisma } from "@/lib/prisma";
import { getLocationOptions } from "@/lib/locations";
import VerifyForm from "./VerifyForm";

export default async function VerifyAssetPage({ params }: { params: Promise<{ id: string }> }) {
  await requireRole("ADMIN", "VERIFIER", "LOCATION_HEAD");
  const { id } = await params;

  const [asset, locations, activeCampaign] = await Promise.all([
    prisma.asset.findUnique({ where: { id }, include: { currentLocation: true } }),
    getLocationOptions(),
    prisma.verificationCampaign.findFirst({ where: { status: "ACTIVE" }, orderBy: { startDate: "desc" } }),
  ]);
  if (!asset) notFound();

  const gpsEnabled = process.env.ORG_GPS_CAPTURE_ENABLED === "true";

  return (
    <div className="max-w-lg mx-auto space-y-5">
      <div>
        <p className="font-mono text-xs text-muted">{asset.assetNumber}</p>
        <h1 className="text-xl font-semibold">{asset.description}</h1>
        <p className="text-sm text-muted mt-1">Book location: {asset.currentLocation?.fullPath ?? "—"}</p>
        {activeCampaign && <p className="pill bg-steel-soft text-steel mt-2 inline-block">{activeCampaign.name}</p>}
      </div>
      <VerifyForm
        assetId={asset.id}
        locations={locations}
        currentLocationId={asset.currentLocationId ?? undefined}
        campaignId={activeCampaign?.id}
        gpsEnabled={gpsEnabled}
      />
    </div>
  );
}
