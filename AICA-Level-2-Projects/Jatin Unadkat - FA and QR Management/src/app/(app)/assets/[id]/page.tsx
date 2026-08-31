import Link from "next/link";
import Image from "next/image";
import { notFound } from "next/navigation";
import { requireSession } from "@/lib/rbac";
import { requireLocationScope } from "@/lib/locationScope";
import { prisma } from "@/lib/prisma";
import { getMismatchFlags } from "@/lib/comparison";
import { format } from "date-fns";

const STATUS_STYLE: Record<string, string> = {
  NOT_VERIFIED: "bg-steel-soft text-steel",
  VERIFIED: "bg-good-soft text-good",
  NOT_FOUND: "bg-bad-soft text-bad",
  LOCATION_MISMATCH: "bg-warn-soft text-warn",
  DAMAGED: "bg-bad-soft text-bad",
  RELOCATED: "bg-warn-soft text-warn",
  UNDER_INVESTIGATION: "bg-warn-soft text-warn",
};

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <tr className="border-b border-line last:border-0">
      <td className="py-1.5 pr-4 text-xs uppercase tracking-wide text-muted whitespace-nowrap align-top">{label}</td>
      <td className="py-1.5 text-sm">{value ?? "—"}</td>
    </tr>
  );
}

export default async function AssetDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const session = await requireSession();
  const { id } = await params;

  const asset = await prisma.asset.findUnique({
    where: { id },
    include: {
      category: true,
      department: true,
      vendor: true,
      currentLocation: true,
      custodian: true,
      lastVerifiedBy: true,
      sapAssetData: { include: { lastImportBatch: true } },
      qrCodes: { where: { isActive: true }, orderBy: { generatedAt: "desc" }, take: 1 },
      verificationRecords: {
        orderBy: { verifiedAt: "desc" },
        include: { verifier: true, verifiedLocation: true },
        take: 10,
      },
      locationHistory: {
        orderBy: { changedAt: "desc" },
        include: { fromLocation: true, toLocation: true, changedBy: true },
        take: 10,
      },
      photographs: { orderBy: { takenAt: "desc" }, take: 12 },
      exceptions: { orderBy: { createdAt: "desc" }, include: { assignedTo: true } },
    },
  });
  if (!asset) notFound();

  await requireLocationScope(session, asset.currentLocation?.fullPath);

  const customFieldConfig = await prisma.sapCustomFieldConfig.findMany({ orderBy: { slotNumber: "asc" } });

  const isAdmin = session.user.role === "ADMIN";
  const isLocationHead = session.user.role === "LOCATION_HEAD";
  const isVerifier = session.user.role === "VERIFIER" || isAdmin || isLocationHead;
  const canManageQr = isAdmin || isLocationHead;

  const mismatches = getMismatchFlags(asset);

  const sap = asset.sapAssetData;
  const customEntries = customFieldConfig
    .map((c, i) => ({
      label: c.displayLabel || `Custom Field ${String(c.slotNumber).padStart(2, "0")}`,
      value: sap ? (sap as unknown as Record<string, string | null>)[`custom${String(c.slotNumber).padStart(2, "0")}`] : null,
      visible: c.isVisible,
      i,
    }))
    .filter((c) => c.visible && c.value);

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <p className="font-mono text-xs text-muted">{asset.assetNumber}</p>
          <h1 className="text-xl font-semibold">{asset.description}</h1>
          <div className="flex gap-2 mt-2 flex-wrap">
            <span className={`pill inline-block ${STATUS_STYLE[asset.verificationStatus] ?? ""}`}>
              {asset.verificationStatus.replaceAll("_", " ")}
            </span>
            <span className="pill bg-steel-soft text-steel">
              {asset.sourceType === "SAP_IMPORTED" ? "SAP-linked" : "Not in SAP"}
            </span>
          </div>
        </div>
        <div className="flex gap-2 flex-wrap">
          {isVerifier && <Link href={`/verify/${asset.id}`} className="btn-primary">Verify asset</Link>}
          {canManageQr && <Link href={`/assets/${asset.id}/qr`} className="btn-secondary">QR code</Link>}
          {isAdmin && <Link href={`/assets/${asset.id}/edit`} className="btn-secondary">Edit</Link>}
        </div>
      </div>

      {mismatches.length > 0 && (
        <div className="card p-4 border-bad space-y-2">
          <p className="text-sm text-bad font-medium">🔴 {mismatches.length} mismatch(es) between SAP and physical verification</p>
          {mismatches.map((m) => (
            <p key={m.key} className="text-sm text-muted">
              <strong className={m.severity === "bad" ? "text-bad" : "text-warn"}>{m.label}:</strong>{" "}
              {m.key === "location" && <>Physically found at <strong>{m.physicalValue}</strong>, different from where it was booked at the time.</>}
              {m.key === "serial" && <>SAP records <strong>{m.sapValue}</strong>, but the verifier observed <strong>{m.physicalValue}</strong>.</>}
              {m.key === "condition" && <>Physical condition observed as <strong>{m.physicalValue}</strong>.</>}
            </p>
          ))}
        </div>
      )}

      {/* SAP Fixed Asset Register Data — read-only, imported from SAP */}
      <section className="split-card">
        <div className="half sap">
          <h4>🔒 SAP Fixed Asset Register Data <span className="pill locked">Read Only — Imported from SAP</span></h4>
          {sap ? (
            <>
              <div className="tbl-wrap"><table>
                <tbody>
                  <Field label="Description 1 / 2" value={[sap.description1, sap.description2].filter(Boolean).join(" / ") || "—"} />
                  <Field label="Asset Class" value={[sap.assetClassCode, sap.assetClassDescription].filter(Boolean).join(" — ") || "—"} />
                  <Field label="Serial Number" value={sap.serialNumber} />
                  <Field label="Inventory Number" value={sap.inventoryNumber} />
                  <Field label="Capitalized" value={sap.capitalized === null ? "—" : sap.capitalized ? "Yes" : "No"} />
                  <Field label="Net Book Value" value={sap.netBookValue != null ? `₹${sap.netBookValue.toLocaleString()}` : "—"} />
                  <Field label="Gross Book Value" value={sap.grossBookValue != null ? `₹${sap.grossBookValue.toLocaleString()}` : "—"} />
                  {customEntries.map((c) => <Field key={c.i} label={c.label} value={c.value} />)}
                </tbody>
              </table></div>
              <p className="text-xs text-muted mt-3">
                Last synced from SAP: {sap.lastImportBatch ? format(sap.updatedAt, "dd MMM yyyy, HH:mm") : "—"}
                {sap.lastImportBatch && ` (batch ${sap.lastImportBatch.fileName})`}
              </p>
            </>
          ) : (
            <p className="text-sm text-muted">This asset has no linked SAP record — it was created directly in the portal (found in the field, not yet in SAP). See the exception queue to reconcile it.</p>
          )}
        </div>

        <div className="half verif">
          <h4>Physical Verification Data</h4>
          <div className="tbl-wrap"><table>
            <tbody>
              <Field label="Verification Status" value={<span className={`pill ${STATUS_STYLE[asset.verificationStatus] ?? ""}`}>{asset.verificationStatus.replaceAll("_", " ")}</span>} />
              <Field label="Physical Location" value={asset.currentLocation?.fullPath} />
              <Field label="Physical Condition" value={asset.physicalCondition} />
              <Field label="Category / Department" value={[asset.category?.name, asset.department?.name].filter(Boolean).join(" / ") || "—"} />
              <Field label="Custodian" value={asset.custodian?.fullName} />
              <Field label="Last Verified" value={asset.lastVerifiedAt ? `${format(asset.lastVerifiedAt, "dd MMM yyyy, HH:mm")} — ${asset.lastVerifiedBy?.fullName ?? ""}` : "Not yet verified"} />
              <Field label="Remarks" value={asset.remarks} />
            </tbody>
          </table></div>
        </div>
      </section>

      <section className="card p-5">
        <h2 className="text-sm font-semibold mb-4">Verification history</h2>
        {asset.verificationRecords.length === 0 && <p className="text-sm text-muted">No verifications recorded yet.</p>}
        <div className="space-y-3">
          {asset.verificationRecords.map((v) => (
            <div key={v.id} className="border-b border-line last:border-0 pb-3 last:pb-0">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <span className={`pill ${STATUS_STYLE[v.result] ?? "bg-steel-soft text-steel"}`}>{v.result.replaceAll("_", " ")}</span>
                <span className="text-xs text-muted">{format(v.verifiedAt, "dd MMM yyyy, HH:mm")} — {v.verifier.fullName}</span>
              </div>
              {v.verifiedLocation && <p className="text-sm mt-1">Found at: {v.verifiedLocation.fullPath}</p>}
              {v.condition && <p className="text-sm text-muted mt-1">Condition: {v.condition}</p>}
              {v.observedSerialNumber && <p className="text-sm text-muted mt-1">Observed serial: <span className="font-mono">{v.observedSerialNumber}</span></p>}
              {v.remarks && <p className="text-sm text-muted mt-1">&ldquo;{v.remarks}&rdquo;</p>}
            </div>
          ))}
        </div>
      </section>

      <section className="card p-5">
        <h2 className="text-sm font-semibold mb-4">Movement / location history</h2>
        {asset.locationHistory.length === 0 && <p className="text-sm text-muted">No location changes recorded.</p>}
        <div className="space-y-2">
          {asset.locationHistory.map((h) => (
            <div key={h.id} className="text-sm flex flex-wrap items-center gap-2">
              <span className="text-muted text-xs font-mono">{format(h.changedAt, "dd MMM yyyy")}</span>
              <span>{h.fromLocation?.fullPath ?? "—"} → {h.toLocation.fullPath}</span>
              <span className="pill bg-steel-soft text-steel text-[11px]">{h.source.replaceAll("_", " ")}</span>
            </div>
          ))}
        </div>
      </section>

      {asset.photographs.length > 0 && (
        <section className="card p-5">
          <h2 className="text-sm font-semibold mb-4">Photographs</h2>
          <div className="grid grid-cols-3 sm:grid-cols-4 gap-3">
            {asset.photographs.map((p) => (
              <a key={p.id} href={p.storageKey} target="_blank" rel="noreferrer" className="block rounded-md overflow-hidden border border-line">
                <Image src={p.thumbnailKey} alt="Asset photo" width={160} height={160} className="object-cover w-full h-24" unoptimized />
              </a>
            ))}
          </div>
        </section>
      )}

      {(isAdmin || isLocationHead) && asset.exceptions.length > 0 && (
        <section className="card p-5">
          <h2 className="text-sm font-semibold mb-4">Exceptions</h2>
          <div className="space-y-2">
            {asset.exceptions.map((e) => (
              <div key={e.id} className="text-sm flex items-center justify-between">
                <span>{e.type.replaceAll("_", " ")}</span>
                <span className={`pill ${e.status === "OPEN" ? "bg-warn-soft text-warn" : e.status === "RESOLVED" ? "bg-good-soft text-good" : "bg-steel-soft text-steel"}`}>{e.status}</span>
              </div>
            ))}
          </div>
          <Link href="/exceptions" className="text-xs text-steel hover:underline mt-3 inline-block">Manage in Exception Queue →</Link>
        </section>
      )}
    </div>
  );
}
