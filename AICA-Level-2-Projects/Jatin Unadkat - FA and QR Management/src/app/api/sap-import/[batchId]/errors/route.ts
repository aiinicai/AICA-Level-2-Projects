import { NextResponse } from "next/server";
import { requireRoleApi } from "@/lib/rbac";
import { prisma } from "@/lib/prisma";
import { toCsv } from "@/lib/csv";

export async function GET(_request: Request, { params }: { params: Promise<{ batchId: string }> }) {
  const auth = await requireRoleApi("ADMIN");
  if (!auth.ok) return NextResponse.json({ error: "Unauthorized" }, { status: auth.status });
  const { batchId } = await params;

  const errors = await prisma.sapImportError.findMany({ where: { batchId }, orderBy: { rowNumber: "asc" } });
  const csv = toCsv(
    ["Row", "Asset Number", "Error Type", "Detail"],
    errors.map((e) => [e.rowNumber, e.assetNumber, e.errorType, e.errorDetail])
  );

  return new NextResponse(csv, {
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Content-Disposition": `attachment; filename="sap-import-${batchId}-errors.csv"`,
    },
  });
}
