import { NextResponse } from "next/server";
import { requireRoleApi } from "@/lib/rbac";
import { prisma } from "@/lib/prisma";
import { readVarFile } from "@/lib/fileStorage";

export async function GET(_request: Request, { params }: { params: Promise<{ jobId: string }> }) {
  const auth = await requireRoleApi("ADMIN", "LOCATION_HEAD");
  if (!auth.ok) return NextResponse.json({ error: "Unauthorized" }, { status: auth.status });
  const { jobId } = await params;

  const job = await prisma.bulkQrJob.findUnique({ where: { id: jobId } });
  if (!job || !job.resultFilePath) return NextResponse.json({ error: "Not found" }, { status: 404 });

  const buffer = await readVarFile(job.resultFilePath);
  return new NextResponse(new Uint8Array(buffer), {
    headers: {
      "Content-Type": "application/pdf",
      "Content-Disposition": `attachment; filename="bulk-qr-labels.pdf"`,
    },
  });
}
