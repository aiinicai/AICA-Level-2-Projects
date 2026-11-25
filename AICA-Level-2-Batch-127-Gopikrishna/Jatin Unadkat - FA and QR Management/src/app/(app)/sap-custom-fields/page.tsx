import { requireRole } from "@/lib/rbac";
import { prisma } from "@/lib/prisma";
import { CUSTOM_SLOT_COUNT } from "@/lib/sapImport";
import { updateCustomFieldLabel } from "@/actions/sapCustomFields";

export default async function SapCustomFieldsPage() {
  await requireRole("ADMIN");
  const configs = await prisma.sapCustomFieldConfig.findMany();
  const bySlot = new Map(configs.map((c) => [c.slotNumber, c]));

  const slots = Array.from({ length: CUSTOM_SLOT_COUNT }, (_, i) => i + 1);

  return (
    <div className="space-y-5 max-w-2xl">
      <div>
        <h1 className="text-xl font-semibold">SAP Custom Field Configuration</h1>
        <p className="text-sm text-muted mt-1">
          The 15 custom-column slots are fixed by the import template — rename their display heading here (e.g.
          &ldquo;Custom Field 01&rdquo; → &ldquo;Cost Center&rdquo;). Applies everywhere the field is shown.
        </p>
      </div>

      <div className="card divide-y divide-line">
        {slots.map((slot) => {
          const config = bySlot.get(slot);
          const defaultLabel = `Custom Field ${String(slot).padStart(2, "0")}`;
          return (
            <form
              key={slot}
              action={async (formData: FormData) => {
                "use server";
                await updateCustomFieldLabel(slot, formData);
              }}
              className="p-3 flex items-center gap-3"
            >
              <span className="font-mono text-xs text-muted w-28">{defaultLabel}</span>
              <input
                name="displayLabel"
                defaultValue={config?.displayLabel ?? ""}
                placeholder={defaultLabel}
                className="input flex-1"
              />
              <button type="submit" className="btn-secondary text-xs px-3 py-1.5">Save</button>
            </form>
          );
        })}
      </div>
    </div>
  );
}
