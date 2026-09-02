import { NextResponse } from "next/server";
import { requireRoleApi } from "@/lib/rbac";
import { prisma } from "@/lib/prisma";
import { toCsv } from "@/lib/csv";
import { getLocationHeadScopeRoots, locationScopeWhereClause } from "@/lib/locationScope";
import type { Prisma } from "@prisma/client";

type ReportType =
  | "asset-master"
  | "verification"
  | "location-mismatch"
  | "missing"
  | "damaged"
  | "pending"
  | "movement-history"
  | "audit-trail"
  | "qr-register";

async function buildReport(type: ReportType, assetScope: Prisma.AssetWhereInput) {
  switch (type) {
    case "asset-master": {
      const assets = await prisma.asset.findMany({
        where: assetScope,
        include: { category: true, department: true, currentLocation: true, vendor: true, sapAssetData: true },
        orderBy: { assetNumber: "asc" },
      });
      return {
        headers: ["Asset Number", "Description", "Category", "Department", "Location", "Vendor", "Status", "Verification Status", "Net Book Value (SAP)"],
        rows: assets.map((a) => [a.assetNumber, a.description, a.category?.name, a.department?.name, a.currentLocation?.fullPath, a.vendor?.name, a.assetStatus, a.verificationStatus, a.sapAssetData?.netBookValue]),
      };
    }
    case "verification": {
      const records = await prisma.verificationRecord.findMany({
        where: { asset: assetScope },
        include: { asset: true, verifier: true, verifiedLocation: true, campaign: true },
        orderBy: { verifiedAt: "desc" },
      });
      return {
        headers: ["Asset Number", "Result", "Condition", "Verified Location", "Verifier", "Campaign", "Verified At"],
        rows: records.map((r) => [r.asset.assetNumber, r.result, r.condition, r.verifiedLocation?.fullPath, r.verifier.fullName, r.campaign?.name, r.verifiedAt.toISOString()]),
      };
    }
    case "location-mismatch": {
      const assets = await prisma.asset.findMany({
        where: { ...assetScope, verificationStatus: "LOCATION_MISMATCH" },
        include: { currentLocation: true },
      });
      return {
        headers: ["Asset Number", "Description", "Book/Current Location"],
        rows: assets.map((a) => [a.assetNumber, a.description, a.currentLocation?.fullPath]),
      };
    }
    case "missing": {
      const assets = await prisma.asset.findMany({ where: { ...assetScope, verificationStatus: "NOT_FOUND" } });
      return {
        headers: ["Asset Number", "Description", "Serial Number"],
        rows: assets.map((a) => [a.assetNumber, a.description, a.serialNumber]),
      };
    }
    case "damaged": {
      const assets = await prisma.asset.findMany({ where: { ...assetScope, verificationStatus: "DAMAGED" } });
      return {
        headers: ["Asset Number", "Description", "Physical Condition", "Remarks"],
        rows: assets.map((a) => [a.assetNumber, a.description, a.physicalCondition, a.remarks]),
      };
    }
    case "pending": {
      const assets = await prisma.asset.findMany({
        where: { ...assetScope, verificationStatus: "NOT_VERIFIED", isActive: true },
        include: { department: true },
      });
      return {
        headers: ["Asset Number", "Description", "Department"],
        rows: assets.map((a) => [a.assetNumber, a.description, a.department?.name]),
      };
    }
    case "movement-history": {
      const history = await prisma.assetLocationHistory.findMany({
        where: { asset: assetScope },
        include: { asset: true, fromLocation: true, toLocation: true, changedBy: true },
        orderBy: { changedAt: "desc" },
      });
      return {
        headers: ["Asset Number", "From", "To", "Changed By", "Source", "Changed At"],
        rows: history.map((h) => [h.asset.assetNumber, h.fromLocation?.fullPath, h.toLocation.fullPath, h.changedBy?.fullName, h.source, h.changedAt.toISOString()]),
      };
    }
    case "audit-trail": {
      const logs = await prisma.auditLog.findMany({ include: { user: true }, orderBy: { occurredAt: "desc" }, take: 1000 });
      return {
        headers: ["When", "User", "Action", "Entity Type", "Entity Id", "Old Value", "New Value"],
        rows: logs.map((l) => [l.occurredAt.toISOString(), l.user?.fullName, l.action, l.entityType, l.entityId, l.oldValueJson, l.newValueJson]),
      };
    }
    case "qr-register": {
      const codes = await prisma.qrCode.findMany({
        where: { asset: assetScope },
        include: { asset: true },
        orderBy: { generatedAt: "desc" },
      });
      return {
        headers: ["Asset Number", "Token", "Size", "Active", "Reprint Count", "Generated At"],
        rows: codes.map((q) => [q.asset.assetNumber, q.token, q.sizePreset, q.isActive, q.reprintCount, q.generatedAt.toISOString()]),
      };
    }
  }
}

export async function GET(_request: Request, { params }: { params: Promise<{ type: string }> }) {
  const auth = await requireRoleApi("ADMIN", "LOCATION_HEAD");
  if (!auth.ok) return NextResponse.json({ error: "Unauthorized" }, { status: auth.status });
  const { type } = await params;

  if (type === "audit-trail" && auth.session.user.role !== "ADMIN") {
    return NextResponse.json({ error: "Audit trail export is Admin-only." }, { status: 403 });
  }

  const assetScope: Prisma.AssetWhereInput =
    auth.session.user.role === "LOCATION_HEAD"
      ? { currentLocation: { is: locationScopeWhereClause(await getLocationHeadScopeRoots(auth.session.user.id)) } }
      : {};

  const report = await buildReport(type as ReportType, assetScope);
  if (!report) return NextResponse.json({ error: "Unknown report type" }, { status: 404 });

  const csv = toCsv(report.headers, report.rows);
  return new NextResponse(csv, {
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Content-Disposition": `attachment; filename="${type}.csv"`,
    },
  });
}
