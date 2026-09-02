"use server";

import { revalidatePath } from "next/cache";
import { prisma } from "@/lib/prisma";
import { requireRole } from "@/lib/rbac";
import { logAudit } from "@/lib/audit";
import {
  parseWorkbook,
  validateColumns,
  parseAndValidateRows,
  type ParsedSapRow,
  type SapImportRowError,
} from "@/lib/sapImport";

export type SapImportParseResult =
  | { success: false; error: string; missingColumns?: string[] }
  | {
      success: true;
      fileName: string;
      unexpectedColumns: string[];
      preview: {
        totalRows: number;
        newCount: number;
        existingCount: number;
        blankValueCounts: Record<string, number>;
        invalidRowCount: number;
        duplicateInFileCount: number;
      };
      validRows: ParsedSapRow[];
      errors: SapImportRowError[];
    };

export async function parseSapImportFile(formData: FormData): Promise<SapImportParseResult> {
  await requireRole("ADMIN");
  const file = formData.get("file") as File | null;
  if (!file || file.size === 0) return { success: false, error: "Choose a file to import." };

  const buffer = Buffer.from(await file.arrayBuffer());
  const { headers, rows } = await parseWorkbook(buffer, file.name);
  if (headers.length === 0) return { success: false, error: "The file appears to be empty or unreadable." };

  const { missing, unexpected } = validateColumns(headers);
  if (missing.length > 0) {
    return {
      success: false,
      error: `The file is missing ${missing.length} expected column(s). Every column in the SAP template must be present, even if individual values are blank.`,
      missingColumns: missing,
    };
  }

  const existingAssetNumbers = new Set(
    (await prisma.asset.findMany({ select: { assetNumber: true } })).map((a) => a.assetNumber)
  );

  const result = parseAndValidateRows(rows, existingAssetNumbers);

  return {
    success: true,
    fileName: file.name,
    unexpectedColumns: unexpected,
    preview: {
      totalRows: result.totalRows,
      newCount: result.newCount,
      existingCount: result.existingCount,
      blankValueCounts: result.blankValueCounts,
      invalidRowCount: result.invalidRowCount,
      duplicateInFileCount: result.duplicateInFileCount,
    },
    validRows: result.validRows,
    errors: result.errors,
  };
}

function customFieldsData(custom: (string | null)[]) {
  const data: Record<string, string | null> = {};
  custom.forEach((v, i) => {
    data[`custom${String(i + 1).padStart(2, "0")}`] = v;
  });
  return data;
}

function combineDescription(d1: string | null, d2: string | null): string {
  if (d1 && d2) return `${d1} — ${d2}`;
  return d1 || d2 || "(no description from SAP)";
}

const CHUNK_SIZE = 200;

export async function confirmSapImport(
  fileName: string,
  validRows: ParsedSapRow[],
  errors: SapImportRowError[]
) {
  const session = await requireRole("ADMIN");

  let newRecords = 0;
  let updatedRecords = 0;
  let unchangedRecords = 0;

  // Create the batch first so SapAssetData rows can reference it.
  const batch = await prisma.sapImportBatch.create({
    data: {
      fileName,
      importedById: session.user.id,
      totalRows: validRows.length + errors.filter((e) => e.errorType !== "DUPLICATE_IN_FILE").length,
      newRecords: 0,
      updatedRecords: 0,
      unchangedRecords: 0,
      errorRecords: errors.filter((e) => e.errorType !== "DUPLICATE_IN_FILE").length,
      status: errors.length > 0 ? "COMPLETED_WITH_ERRORS" : "COMPLETED",
    },
  });

  for (let i = 0; i < validRows.length; i += CHUNK_SIZE) {
    const chunk = validRows.slice(i, i + CHUNK_SIZE);
    for (const row of chunk) {
      const existing = await prisma.asset.findUnique({
        where: { assetNumber: row.assetNumber },
        include: { sapAssetData: true },
      });

      const description = combineDescription(row.description1, row.description2);
      const custom = customFieldsData(row.custom);

      if (!existing) {
        const asset = await prisma.asset.create({
          data: {
            assetNumber: row.assetNumber,
            description,
            serialNumber: row.serialNumber,
            sourceType: "SAP_IMPORTED",
            sapAssetData: {
              create: {
                description1: row.description1,
                description2: row.description2,
                assetClassCode: row.assetClassCode,
                assetClassDescription: row.assetClassDescription,
                serialNumber: row.serialNumber,
                inventoryNumber: row.inventoryNumber,
                capitalized: row.capitalized,
                netBookValue: row.netBookValue,
                grossBookValue: row.grossBookValue,
                lastImportBatchId: batch.id,
                ...custom,
              },
            },
          },
        });
        await logAudit({
          userId: session.user.id,
          action: "SAP_IMPORT_CREATE",
          entityType: "Asset",
          entityId: asset.id,
          newValue: row,
          source: "SAP_IMPORT",
        });
        newRecords += 1;
        continue;
      }

      const before = existing.sapAssetData;
      const changed =
        !before ||
        before.description1 !== row.description1 ||
        before.description2 !== row.description2 ||
        before.assetClassCode !== row.assetClassCode ||
        before.assetClassDescription !== row.assetClassDescription ||
        before.serialNumber !== row.serialNumber ||
        before.inventoryNumber !== row.inventoryNumber ||
        before.capitalized !== row.capitalized ||
        before.netBookValue !== row.netBookValue ||
        before.grossBookValue !== row.grossBookValue ||
        CUSTOM_KEYS.some((k) => (before as unknown as Record<string, unknown>)[k] !== custom[k]);

      await prisma.asset.update({
        where: { id: existing.id },
        data: {
          description,
          serialNumber: row.serialNumber,
          sourceType: "SAP_IMPORTED",
          sapAssetData: {
            upsert: {
              create: {
                description1: row.description1,
                description2: row.description2,
                assetClassCode: row.assetClassCode,
                assetClassDescription: row.assetClassDescription,
                serialNumber: row.serialNumber,
                inventoryNumber: row.inventoryNumber,
                capitalized: row.capitalized,
                netBookValue: row.netBookValue,
                grossBookValue: row.grossBookValue,
                lastImportBatchId: batch.id,
                ...custom,
              },
              update: {
                description1: row.description1,
                description2: row.description2,
                assetClassCode: row.assetClassCode,
                assetClassDescription: row.assetClassDescription,
                serialNumber: row.serialNumber,
                inventoryNumber: row.inventoryNumber,
                capitalized: row.capitalized,
                netBookValue: row.netBookValue,
                grossBookValue: row.grossBookValue,
                lastImportBatchId: batch.id,
                ...custom,
              },
            },
          },
        },
      });

      if (changed) {
        updatedRecords += 1;
        await logAudit({
          userId: session.user.id,
          action: "SAP_IMPORT_UPDATE",
          entityType: "Asset",
          entityId: existing.id,
          oldValue: before,
          newValue: row,
          source: "SAP_IMPORT",
        });
      } else {
        unchangedRecords += 1;
      }
    }
  }

  if (errors.length > 0) {
    await prisma.sapImportError.createMany({
      data: errors.map((e) => ({
        batchId: batch.id,
        rowNumber: e.rowNumber,
        assetNumber: e.assetNumber,
        errorType: e.errorType,
        errorDetail: e.errorDetail,
        rawRowJson: e.rawRowJson,
      })),
    });
  }

  await prisma.sapImportBatch.update({
    where: { id: batch.id },
    data: { newRecords, updatedRecords, unchangedRecords },
  });

  await logAudit({
    userId: session.user.id,
    action: "SAP_IMPORT_BATCH",
    entityType: "SapImportBatch",
    entityId: batch.id,
    newValue: { fileName, newRecords, updatedRecords, unchangedRecords, errorRecords: errors.length },
    source: "SAP_IMPORT",
  });

  revalidatePath("/assets");
  revalidatePath("/sap-import-history");
  revalidatePath("/mismatches");
  revalidatePath("/dashboard");

  return { batchId: batch.id, newRecords, updatedRecords, unchangedRecords, errorRecords: errors.length };
}

const CUSTOM_KEYS = Array.from({ length: 15 }, (_, i) => `custom${String(i + 1).padStart(2, "0")}`);
