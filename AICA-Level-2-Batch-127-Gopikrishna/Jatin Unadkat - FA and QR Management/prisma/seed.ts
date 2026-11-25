import { PrismaClient } from "@prisma/client";
import bcrypt from "bcryptjs";
import { generateQrToken } from "../src/lib/qr";

const prisma = new PrismaClient();

async function main() {
  console.log("Seeding AssetTrace demo data (SAP integration addendum)...");

  const [adminRole, locationHeadRole, readOnlyRole, verifierRole] = await Promise.all([
    prisma.role.upsert({ where: { name: "ADMIN" }, update: {}, create: { name: "ADMIN" } }),
    prisma.role.upsert({ where: { name: "LOCATION_HEAD" }, update: {}, create: { name: "LOCATION_HEAD" } }),
    prisma.role.upsert({ where: { name: "READ_ONLY" }, update: {}, create: { name: "READ_ONLY" } }),
    prisma.role.upsert({ where: { name: "VERIFIER" }, update: {}, create: { name: "VERIFIER" } }),
  ]);

  const passwordHash = await bcrypt.hash("Passw0rd!", 10);

  const admin = await prisma.user.upsert({
    where: { email: "admin@assettrace.demo" },
    update: {},
    create: { email: "admin@assettrace.demo", fullName: "Priya Shah (Admin)", passwordHash, roleId: adminRole.id },
  });
  const viewer = await prisma.user.upsert({
    where: { email: "viewer@assettrace.demo" },
    update: {},
    create: { email: "viewer@assettrace.demo", fullName: "Rahul Nair (Auditor)", passwordHash, roleId: readOnlyRole.id },
  });
  const verifier = await prisma.user.upsert({
    where: { email: "verifier@assettrace.demo" },
    update: {},
    create: { email: "verifier@assettrace.demo", fullName: "Sana Iyer (Field Staff)", passwordHash, roleId: verifierRole.id },
  });
  const locationHead = await prisma.user.upsert({
    where: { email: "locationhead@assettrace.demo" },
    update: {},
    create: { email: "locationhead@assettrace.demo", fullName: "John Mehta (Location Head)", passwordHash, roleId: locationHeadRole.id },
  });

  // ---- Location hierarchy: Site -> Building -> Department -> Room ----
  const mumbai = await prisma.location.create({ data: { name: "Mumbai", levelNumber: 1, fullPath: "Mumbai" } });
  const headOffice = await prisma.location.create({
    data: { name: "Head Office", levelNumber: 2, parentLocationId: mumbai.id, fullPath: "Mumbai / Head Office" },
  });
  const finance = await prisma.location.create({
    data: { name: "Finance", levelNumber: 3, parentLocationId: headOffice.id, fullPath: "Mumbai / Head Office / Finance" },
  });
  const room204 = await prisma.location.create({
    data: { name: "Room 204", levelNumber: 4, parentLocationId: finance.id, fullPath: "Mumbai / Head Office / Finance / Room 204" },
  });
  const room210 = await prisma.location.create({
    data: { name: "Room 210", levelNumber: 4, parentLocationId: finance.id, fullPath: "Mumbai / Head Office / Finance / Room 210" },
  });
  const it = await prisma.location.create({
    data: { name: "IT", levelNumber: 3, parentLocationId: headOffice.id, fullPath: "Mumbai / Head Office / IT" },
  });
  const serverRoom = await prisma.location.create({
    data: { name: "Server Room", levelNumber: 4, parentLocationId: it.id, fullPath: "Mumbai / Head Office / IT / Server Room" },
  });

  // John Mehta is the Location Head for all of Mumbai (design dossier, ADD12 worked example).
  await prisma.locationHeadAssignment.create({
    data: { userId: locationHead.id, locationId: mumbai.id, assignedById: admin.id },
  });

  const itCategory = await prisma.assetCategory.create({ data: { name: "IT Equipment" } });
  const laptopCategory = await prisma.assetCategory.create({
    data: { name: "Laptops", parentCategoryId: itCategory.id },
  });
  const furnitureCategory = await prisma.assetCategory.create({ data: { name: "Furniture" } });

  const financeDept = await prisma.department.create({ data: { name: "Finance", costCenterCode: "CC-100" } });
  const itDept = await prisma.department.create({ data: { name: "Information Technology", costCenterCode: "CC-200" } });

  const dell = await prisma.vendor.create({ data: { name: "Dell Technologies India" } });
  const godrej = await prisma.vendor.create({ data: { name: "Godrej Interio" } });

  // ---- SAP custom field headings (design dossier, brief's own example) ----
  await prisma.sapCustomFieldConfig.createMany({
    data: [
      { slotNumber: 1, displayLabel: "Cost Center" },
      { slotNumber: 2, displayLabel: "Profit Center" },
      { slotNumber: 3, displayLabel: "Business Area" },
      ...Array.from({ length: 12 }, (_, i) => ({ slotNumber: i + 4 })),
    ],
  });

  // ---- Simulated initial SAP import batch ----
  const initialBatch = await prisma.sapImportBatch.create({
    data: {
      fileName: "sap_far_export_initial.xlsx",
      importedById: admin.id,
      totalRows: 4,
      newRecords: 4,
      updatedRecords: 0,
      unchangedRecords: 0,
      errorRecords: 0,
      status: "COMPLETED",
    },
  });

  // ---- The FA-000123 walkthrough asset (SAP-linked) ----
  const laptop = await prisma.asset.create({
    data: {
      assetNumber: "FA-000123",
      description: "Laptop — Dell Latitude 5440",
      serialNumber: "ABC12345",
      sourceType: "SAP_IMPORTED",
      categoryId: laptopCategory.id,
      departmentId: financeDept.id,
      vendorId: dell.id,
      custodianUserId: admin.id,
      currentLocationId: room204.id,
      remarks: "Assigned to Finance controller's desk.",
      sapAssetData: {
        create: {
          description1: "Laptop",
          description2: "Dell Latitude 5440",
          assetClassCode: "3001",
          assetClassDescription: "Computer Equipment",
          serialNumber: "ABC12345",
          inventoryNumber: "INV-45210",
          capitalized: true,
          netBookValue: 79723,
          grossBookValue: 92000,
          custom01: "CC-4410",
          custom02: "PC-Finance",
          custom03: "Corporate",
          lastImportBatchId: initialBatch.id,
        },
      },
    },
  });

  const printer = await prisma.asset.create({
    data: {
      assetNumber: "FA-000124",
      description: "Printer — HP LaserJet Pro",
      sourceType: "SAP_IMPORTED",
      categoryId: itCategory.id,
      departmentId: itDept.id,
      vendorId: dell.id,
      currentLocationId: serverRoom.id,
      sapAssetData: {
        create: {
          description1: "Printer",
          description2: "HP LaserJet Pro",
          assetClassCode: "3010",
          assetClassDescription: "Office Equipment",
          serialNumber: null, // demonstrates a blank SAP field never blocking import
          inventoryNumber: "INV-45330",
          capitalized: true,
          netBookValue: 28900,
          grossBookValue: 34000,
          lastImportBatchId: initialBatch.id,
        },
      },
    },
  });

  const chair = await prisma.asset.create({
    data: {
      assetNumber: "FA-000125",
      description: "Furniture — Executive Office Chair",
      sourceType: "SAP_IMPORTED",
      categoryId: furnitureCategory.id,
      departmentId: financeDept.id,
      vendorId: godrej.id,
      currentLocationId: room204.id,
      sapAssetData: {
        create: {
          description1: "Furniture",
          description2: "Executive Office Chair",
          assetClassCode: "4001",
          assetClassDescription: "Furniture & Fixtures",
          serialNumber: null,
          inventoryNumber: null, // blank — also never blocks import
          capitalized: true,
          netBookValue: 9800,
          grossBookValue: 15500,
          lastImportBatchId: initialBatch.id,
        },
      },
    },
  });

  const server = await prisma.asset.create({
    data: {
      assetNumber: "FA-000126",
      description: "Server — Dell PowerEdge R750",
      serialNumber: "PE750-2201",
      sourceType: "SAP_IMPORTED",
      categoryId: itCategory.id,
      departmentId: itDept.id,
      vendorId: dell.id,
      currentLocationId: serverRoom.id,
      sapAssetData: {
        create: {
          description1: "Server",
          description2: "Dell PowerEdge R750",
          assetClassCode: "3001",
          assetClassDescription: "Computer Equipment",
          serialNumber: "PE750-2201",
          inventoryNumber: "INV-45400",
          capitalized: true,
          netBookValue: 512000,
          grossBookValue: 610000,
          custom01: "CC-4420",
          lastImportBatchId: initialBatch.id,
        },
      },
    },
  });

  // QR codes for every asset
  for (const asset of [laptop, printer, chair, server]) {
    await prisma.qrCode.create({
      data: {
        assetId: asset.id,
        token: generateQrToken(),
        sizePreset: "MEDIUM",
        generatedById: admin.id,
      },
    });
  }

  // ---- Verification campaign ----
  const campaign = await prisma.verificationCampaign.create({
    data: {
      name: "FY 2026-27 Annual Fixed Asset Verification",
      startDate: new Date("2026-08-01"),
      endDate: new Date("2026-09-30"),
      status: "ACTIVE",
      scopeJson: JSON.stringify({ departments: [financeDept.id, itDept.id] }),
    },
  });

  // A completed verification that surfaces the FA-000123 location-mismatch story
  const verifiedAt = new Date("2026-08-15T10:30:00Z");
  const verification = await prisma.verificationRecord.create({
    data: {
      assetId: laptop.id,
      campaignId: campaign.id,
      verifierId: verifier.id,
      result: "RELOCATED",
      condition: "Good",
      observedSerialNumber: "ABC12399", // deliberately differs from SAP's ABC12345 — demo mismatch
      verifiedLocationId: room210.id,
      remarks: "Found on the new hire's desk in Room 210, not Room 204.",
      verifiedAt,
    },
  });

  await prisma.assetLocationHistory.create({
    data: {
      assetId: laptop.id,
      fromLocationId: room204.id,
      toLocationId: room210.id,
      changedById: verifier.id,
      source: "VERIFICATION",
    },
  });

  await prisma.asset.update({
    where: { id: laptop.id },
    data: {
      currentLocationId: room210.id,
      verificationStatus: "LOCATION_MISMATCH",
      physicalCondition: "Good",
      lastVerifiedAt: verifiedAt,
      lastVerifiedById: verifier.id,
    },
  });

  await prisma.exception.create({
    data: {
      assetId: laptop.id,
      verificationId: verification.id,
      type: "FOUND_ELSEWHERE",
      status: "OPEN",
    },
  });

  // ---- Default SAP export template (design dossier, ADD10 §01) ----
  await prisma.sapExportTemplateField.createMany({
    data: [
      { sapFieldName: "ANLN1", portalSourceField: "assetNumber", columnOrder: 1, isRequired: true },
      { sapFieldName: "STORT", portalSourceField: "physicalLocation", columnOrder: 2 },
      { sapFieldName: "ZZSTATUS", portalSourceField: "verificationStatus", columnOrder: 3 },
      { sapFieldName: "ZZVERIFYDATE", portalSourceField: "lastVerifiedAt", columnOrder: 4, format: "dd.MM.yyyy" },
      { sapFieldName: "ZZVERIFIEDBY", portalSourceField: "lastVerifiedBy", columnOrder: 5 },
      { sapFieldName: "ZZREMARKS", portalSourceField: "remarks", columnOrder: 6 },
    ],
  });

  console.log("Seed complete.");
  console.log("Logins (password Passw0rd!):");
  console.log("  admin@assettrace.demo        — Admin");
  console.log("  locationhead@assettrace.demo — Location Head (Mumbai)");
  console.log("  verifier@assettrace.demo     — Verifier");
  console.log("  viewer@assettrace.demo       — Read-only");
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
