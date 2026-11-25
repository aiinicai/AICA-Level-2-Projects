import { notFound } from "next/navigation";
import { requireRole } from "@/lib/rbac";
import { requireLocationScope } from "@/lib/locationScope";
import { prisma } from "@/lib/prisma";
import { renderQrDataUrl, QR_SIZE_PRESETS } from "@/lib/qr";
import { generateQrCode, reprintQrCode } from "@/actions/qr";
import PrintButton from "@/components/PrintButton";

export default async function AssetQrPage({ params }: { params: Promise<{ id: string }> }) {
  const session = await requireRole("ADMIN", "LOCATION_HEAD");
  const { id } = await params;

  const asset = await prisma.asset.findUnique({
    where: { id },
    include: { qrCodes: { where: { isActive: true }, orderBy: { generatedAt: "desc" }, take: 1 }, currentLocation: true },
  });
  if (!asset) notFound();
  await requireLocationScope(session, asset.currentLocation?.fullPath);

  const active = asset.qrCodes[0];
  const dataUrl = active ? await renderQrDataUrl(active.token, 400) : null;
  const sizeMm = active ? QR_SIZE_PRESETS[active.sizePreset as keyof typeof QR_SIZE_PRESETS]?.mm ?? 40 : 40;

  const generate = async (formData: FormData) => {
    "use server";
    await generateQrCode(id, String(formData.get("sizePreset")));
  };
  const reprint = async () => {
    "use server";
    if (active) await reprintQrCode(active.id);
  };

  return (
    <div className="max-w-2xl space-y-6">
      <div className="print:hidden">
        <h1 className="text-xl font-semibold">QR code — {asset.assetNumber}</h1>
        <p className="text-sm text-muted mt-1">Generate, resize, and print a label for this asset.</p>
      </div>

      <div className="card p-5 print:hidden">
        <h2 className="text-sm font-semibold mb-3">{active ? "Reissue label" : "Generate label"}</h2>
        <form action={generate} className="flex flex-wrap gap-3 items-end">
          <div>
            <label className="label" htmlFor="sizePreset">Size</label>
            <select id="sizePreset" name="sizePreset" defaultValue={active?.sizePreset ?? "MEDIUM"} className="input">
              {Object.entries(QR_SIZE_PRESETS).map(([key, v]) => (
                <option key={key} value={key}>{v.label} ({v.mm}×{v.mm} mm)</option>
              ))}
            </select>
          </div>
          <button type="submit" className="btn-primary">{active ? "Generate new code" : "Generate"}</button>
        </form>
        {active && (
          <form action={reprint} className="mt-3">
            <button type="submit" className="text-xs text-steel hover:underline">
              Reprint same code (reprints so far: {active.reprintCount})
            </button>
          </form>
        )}
      </div>

      {active && dataUrl && (
        <div className="card p-8 flex flex-col items-center gap-4">
          <div
            className="border border-line rounded-md flex flex-col items-center justify-center p-3 gap-2 bg-white"
            style={{ width: `${Math.max(sizeMm * 3, 120)}px` }}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={dataUrl} alt={`QR code for ${asset.assetNumber}`} className="w-full h-auto" />
            <p className="font-mono text-xs text-center break-all">{asset.assetNumber}</p>
            <p className="text-[10px] text-center text-muted">{asset.description}</p>
          </div>
          <PrintButton />
        </div>
      )}
    </div>
  );
}
