import { requireRole } from "@/lib/rbac";
import SapImportWizard from "./SapImportWizard";
import { STANDARD_COLUMNS, CUSTOM_SLOT_COUNT } from "@/lib/sapImport";

export default async function SapImportPage() {
  await requireRole("ADMIN");
  return (
    <div className="space-y-5 max-w-3xl">
      <div>
        <h1 className="text-xl font-semibold">SAP Data Import</h1>
        <p className="text-sm text-muted mt-1">
          Upload the organization&apos;s SAP Fixed Asset Register export. Every column below must be present in the
          file — <strong>{STANDARD_COLUMNS.join(", ")}</strong>, plus {CUSTOM_SLOT_COUNT} custom columns — but no
          individual value is required. Imported data is read-only in the portal once it lands.
        </p>
      </div>
      <SapImportWizard />
    </div>
  );
}
