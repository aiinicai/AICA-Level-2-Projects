import { requireSession } from "@/lib/rbac";
import ScanClient from "./ScanClient";

export default async function ScanPage() {
  await requireSession();
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold">Scan QR</h1>
        <p className="text-sm text-muted mt-1">Scan an asset&apos;s label to look it up.</p>
      </div>
      <ScanClient />
    </div>
  );
}
