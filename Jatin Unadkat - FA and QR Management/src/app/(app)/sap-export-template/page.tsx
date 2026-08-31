import { requireRole } from "@/lib/rbac";
import { prisma } from "@/lib/prisma";
import { addExportTemplateField, removeExportTemplateField } from "@/actions/sapExport";
import { PORTAL_SOURCE_FIELDS } from "@/lib/sapExport";

export default async function SapExportTemplatePage() {
  await requireRole("ADMIN");
  const fields = await prisma.sapExportTemplateField.findMany({ orderBy: { columnOrder: "asc" } });

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-xl font-semibold">SAP Export Template</h1>
        <p className="text-sm text-muted mt-1">
          Map portal fields to your SAP upload column names. The exact SAP field names, order, and format are{" "}
          <strong>Organization/SAP Configuration Dependent</strong> — configure them here to match your process.
        </p>
      </div>

      <div className="card p-5">
        <h2 className="text-sm font-semibold mb-3">Add a column</h2>
        <form action={addExportTemplateField} className="grid grid-cols-1 md:grid-cols-5 gap-3 items-end">
          <div>
            <label className="label" htmlFor="sapFieldName">SAP field name</label>
            <input id="sapFieldName" name="sapFieldName" required className="input font-mono" placeholder="e.g. STORT" />
          </div>
          <div>
            <label className="label" htmlFor="portalSourceField">Portal source</label>
            <select id="portalSourceField" name="portalSourceField" required className="input">
              {PORTAL_SOURCE_FIELDS.map((f) => <option key={f.key} value={f.key}>{f.label}</option>)}
            </select>
          </div>
          <div>
            <label className="label" htmlFor="columnOrder">Order</label>
            <input id="columnOrder" name="columnOrder" type="number" required defaultValue={fields.length + 1} className="input" />
          </div>
          <div>
            <label className="label" htmlFor="format">Format</label>
            <input id="format" name="format" className="input" placeholder="dd.MM.yyyy" />
          </div>
          <div className="flex items-center gap-2 pb-2">
            <label className="flex items-center gap-1.5 text-sm"><input type="checkbox" name="isRequired" /> Required</label>
          </div>
          <div className="md:col-span-5">
            <button type="submit" className="btn-primary">Add column</button>
          </div>
        </form>
      </div>

      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-muted border-b border-line">
              <th className="py-2 px-4">#</th>
              <th className="py-2 px-4">SAP Field</th>
              <th className="py-2 px-4">Portal Source</th>
              <th className="py-2 px-4">Format</th>
              <th className="py-2 px-4">Required</th>
              <th className="py-2 px-4"></th>
            </tr>
          </thead>
          <tbody>
            {fields.map((f) => (
              <tr key={f.id} className="border-b border-line last:border-0">
                <td className="py-2 px-4 font-mono text-xs">{f.columnOrder}</td>
                <td className="py-2 px-4 font-mono">{f.sapFieldName}</td>
                <td className="py-2 px-4 text-muted">{PORTAL_SOURCE_FIELDS.find((p) => p.key === f.portalSourceField)?.label ?? f.portalSourceField}</td>
                <td className="py-2 px-4 text-muted font-mono text-xs">{f.format ?? "—"}</td>
                <td className="py-2 px-4">{f.isRequired ? <span className="pill bg-warn-soft text-warn">Required</span> : "—"}</td>
                <td className="py-2 px-4">
                  <form action={async () => { "use server"; await removeExportTemplateField(f.id); }}>
                    <button type="submit" className="text-xs text-bad hover:underline">Remove</button>
                  </form>
                </td>
              </tr>
            ))}
            {fields.length === 0 && <tr><td colSpan={6} className="py-8 text-center text-muted">No template configured — add a column above.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
