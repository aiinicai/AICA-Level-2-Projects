import { requireRole } from "@/lib/rbac";
import { getFormOptions } from "@/lib/options";
import { createAsset } from "@/actions/assets";
import AssetForm from "@/components/AssetForm";

export default async function NewAssetPage() {
  await requireRole("ADMIN");
  const options = await getFormOptions();

  return (
    <div className="space-y-5 max-w-3xl">
      <div>
        <h1 className="text-xl font-semibold">Add asset</h1>
        <p className="text-sm text-muted mt-1">
          For assets physically found but not yet in SAP (design dossier, ADD17 #9) — normal assets arrive via
          <a href="/sap-import" className="text-steel hover:underline"> SAP Import</a> instead. This creates an
          &ldquo;Unrecorded in SAP&rdquo; exception for reconciliation.
        </p>
      </div>
      <AssetForm action={createAsset} {...options} submitLabel="Create asset" />
    </div>
  );
}
