import { notFound } from "next/navigation";
import { requireRole } from "@/lib/rbac";
import { prisma } from "@/lib/prisma";
import { getFormOptions } from "@/lib/options";
import { updateAsset } from "@/actions/assets";
import AssetForm from "@/components/AssetForm";

export default async function EditAssetPage({ params }: { params: Promise<{ id: string }> }) {
  await requireRole("ADMIN");
  const { id } = await params;
  const [asset, options] = await Promise.all([
    prisma.asset.findUnique({ where: { id } }),
    getFormOptions(),
  ]);
  if (!asset) notFound();

  const action = async (formData: FormData) => {
    "use server";
    await updateAsset(id, formData);
  };

  return (
    <div className="space-y-5 max-w-3xl">
      <div>
        <h1 className="text-xl font-semibold">Edit {asset.assetNumber}</h1>
        <p className="text-sm text-muted mt-1">Changes to the master record are audit-logged.</p>
      </div>
      <AssetForm
        action={action}
        {...options}
        defaultValues={asset}
        isSapLinked={asset.sourceType === "SAP_IMPORTED"}
        submitLabel="Save changes"
      />
    </div>
  );
}
