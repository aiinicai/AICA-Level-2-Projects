type Option = { id: string; label: string };

function LockedField({ label, name, value }: { label: string; name: string; value?: string | null }) {
  return (
    <div>
      <label className="label" htmlFor={name}>{label} <span className="pill locked ml-1">🔒 SAP</span></label>
      <input type="hidden" name={name} value={value ?? ""} />
      <p className="input bg-black/[0.03] text-muted cursor-not-allowed">{value || "—"}</p>
    </div>
  );
}

export default function AssetForm({
  action,
  categories,
  departments,
  vendors,
  locations,
  defaultValues,
  isSapLinked,
  submitLabel,
}: {
  action: (formData: FormData) => void | Promise<void>;
  categories: Option[];
  departments: Option[];
  vendors: Option[];
  locations: Option[];
  defaultValues?: Record<string, unknown>;
  isSapLinked?: boolean;
  submitLabel: string;
}) {
  const dv = defaultValues ?? {};
  return (
    <form action={action} className="space-y-6">
      {isSapLinked && (
        <div className="callout">
          <span className="label">SAP-linked asset</span>
          <p>Identity fields below are sourced from SAP and locked. Correct them in SAP and re-import — only classification, location, and remarks are editable here.</p>
        </div>
      )}

      <section className="card p-5">
        <h2 className="text-sm font-semibold mb-4">Identity</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {isSapLinked ? (
            <LockedField label="Asset number" name="assetNumber" value={dv.assetNumber as string} />
          ) : (
            <div>
              <label className="label" htmlFor="assetNumber">Asset number</label>
              <input id="assetNumber" name="assetNumber" required defaultValue={dv.assetNumber as string} className="input font-mono" placeholder="FA-000123" />
            </div>
          )}
          {isSapLinked ? (
            <LockedField label="Asset type" name="assetType" value={dv.assetType as string} />
          ) : (
            <div>
              <label className="label" htmlFor="assetType">Asset type</label>
              <input id="assetType" name="assetType" defaultValue={dv.assetType as string} className="input" placeholder="Laptop, Furniture, Server…" />
            </div>
          )}

          {isSapLinked ? (
            <div className="md:col-span-2"><LockedField label="Description" name="description" value={dv.description as string} /></div>
          ) : (
            <div className="md:col-span-2">
              <label className="label" htmlFor="description">Description</label>
              <input id="description" name="description" required defaultValue={dv.description as string} className="input" placeholder="Found in Room 210, looks like a workstation PC" />
            </div>
          )}

          {isSapLinked ? (
            <LockedField label="Serial number" name="serialNumber" value={dv.serialNumber as string} />
          ) : (
            <div>
              <label className="label" htmlFor="serialNumber">Serial number</label>
              <input id="serialNumber" name="serialNumber" defaultValue={dv.serialNumber as string} className="input font-mono" />
            </div>
          )}

          {isSapLinked ? (
            <LockedField label="Manufacturer" name="manufacturer" value={dv.manufacturer as string} />
          ) : (
            <div>
              <label className="label" htmlFor="manufacturer">Manufacturer</label>
              <input id="manufacturer" name="manufacturer" defaultValue={dv.manufacturer as string} className="input" />
            </div>
          )}

          {isSapLinked ? (
            <LockedField label="Model number" name="modelNumber" value={dv.modelNumber as string} />
          ) : (
            <div>
              <label className="label" htmlFor="modelNumber">Model number</label>
              <input id="modelNumber" name="modelNumber" defaultValue={dv.modelNumber as string} className="input" />
            </div>
          )}
        </div>
      </section>

      <section className="card p-5">
        <h2 className="text-sm font-semibold mb-4">Classification, ownership &amp; location</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="label" htmlFor="categoryId">Category</label>
            <select id="categoryId" name="categoryId" defaultValue={(dv.categoryId as string) ?? ""} className="input">
              <option value="">—</option>
              {categories.map((c) => <option key={c.id} value={c.id}>{c.label}</option>)}
            </select>
          </div>
          <div>
            <label className="label" htmlFor="departmentId">Department</label>
            <select id="departmentId" name="departmentId" defaultValue={(dv.departmentId as string) ?? ""} className="input">
              <option value="">—</option>
              {departments.map((d) => <option key={d.id} value={d.id}>{d.label}</option>)}
            </select>
          </div>
          <div>
            <label className="label" htmlFor="vendorId">Vendor / Supplier</label>
            <select id="vendorId" name="vendorId" defaultValue={(dv.vendorId as string) ?? ""} className="input">
              <option value="">—</option>
              {vendors.map((v) => <option key={v.id} value={v.id}>{v.label}</option>)}
            </select>
          </div>
          <div>
            <label className="label" htmlFor="currentLocationId">Location</label>
            <select id="currentLocationId" name="currentLocationId" defaultValue={(dv.currentLocationId as string) ?? ""} className="input">
              <option value="">—</option>
              {locations.map((l) => <option key={l.id} value={l.id}>{l.label}</option>)}
            </select>
          </div>
        </div>
      </section>

      <section className="card p-5">
        <h2 className="text-sm font-semibold mb-4">Remarks</h2>
        <textarea name="remarks" defaultValue={dv.remarks as string} className="input" rows={3} placeholder="Optional notes" />
      </section>

      <div className="flex justify-end">
        <button type="submit" className="btn-primary">{submitLabel}</button>
      </div>
    </form>
  );
}
