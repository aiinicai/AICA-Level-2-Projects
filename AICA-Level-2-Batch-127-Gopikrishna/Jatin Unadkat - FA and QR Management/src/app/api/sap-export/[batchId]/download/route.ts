import { NextResponse } from "next/server";
import { requireRoleApi } from "@/lib/rbac";
import { prisma } from "@/lib/prisma";
import { readVarFile } from "@/lib/fileStorage";

export async function GET(_request: Request, { params }: { params: Promise<{ batchId: string }> }) {
  const auth = await requireRoleApi("ADMIN");
  if (!auth.ok) return NextResponse.json({ error: "Unauthorized" }, { status: auth.status });
  const { batchId } = await params;

  const batch = await prisma.sapExportBatch.findUnique({ where: { id: batchId } });
  if (!batch) return NextResponse.json({ error: "Not found" }, { status: 404 });

  const buffer = await readVarFile(batch.filePath);
  return new NextResponse(new Uint8Array(buffer), {
    headers: {
      "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      "Content-Disposition": `attachment; filename="${batch.fileName}"`,
    },
  });
}
