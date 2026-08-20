import fs from 'fs';
import path from 'path';
import AdmZip from 'adm-zip';
import { prisma } from '../../db/prisma';
import { AppError, logger } from '../../utils/logger';
import { getSetting, SETTING_KEYS } from '../settings/settings.service';
import { generateDocx } from './docxEngine';
import { convertDocxToPdf } from './pdfEngine';
import { validatePlaceholderValue } from './validators';

/** Module 5: merge placeholders across a selection of templates, deduped, each tagged with which templates use it. */
export async function getMergedPlaceholders(templateIds: string[]) {
  if (!templateIds.length) throw new AppError('Please select at least one template.', 400);

  const templates = await prisma.template.findMany({
    where: { id: { in: templateIds }, status: 'Active' },
    include: { placeholders: { include: { placeholder: true } } },
  });
  if (templates.length !== templateIds.length) {
    throw new AppError('One or more selected templates could not be found.', 404);
  }

  const merged = new Map<
    string,
    { placeholderId: string; name: string; validationType: string; isImage: boolean; usedIn: string[] }
  >();

  for (const t of templates) {
    for (const tp of t.placeholders) {
      const key = tp.placeholder.name;
      if (!merged.has(key)) {
        merged.set(key, {
          placeholderId: tp.placeholder.id,
          name: tp.placeholder.name,
          validationType: tp.placeholder.validationType,
          isImage: tp.placeholder.isImage,
          usedIn: [],
        });
      }
      merged.get(key)!.usedIn.push(t.name);
    }
  }

  // Also attach client-master mapping so the UI can offer "Import from Client Master".
  const placeholderIds = Array.from(merged.values()).map((p) => p.placeholderId);
  const mappings = await prisma.placeholderMapping.findMany({
    where: { placeholderId: { in: placeholderIds } },
  });
  const mapByPlaceholder = new Map(mappings.map((m: any) => [m.placeholderId, m.clientFieldKey]));

  return Array.from(merged.values()).map((p) => ({
    ...p,
    mappedClientField: mapByPlaceholder.get(p.placeholderId) || null,
  }));
}

/** Auto-fill placeholder values from a Client Master record, following the configured mappings. */
export async function autoFillFromClient(clientId: string, templateIds: string[]) {
  const client = await prisma.client.findUnique({ where: { id: clientId }, include: { customValues: { include: { field: true } } } });
  if (!client) throw new AppError('Client not found.', 404);

  const merged = await getMergedPlaceholders(templateIds);
  const systemFieldMap: Record<string, string | null | undefined> = {
    name: client.name,
    addressLine1: client.addressLine1,
    addressLine2: client.addressLine2,
    clientType: client.clientType,
    mobile: client.mobile,
    email: client.email,
  };
  const customFieldMap = new Map(client.customValues.map((v: any) => [v.field.fieldKey, v.value]));

  const values: Record<string, string> = {};
  for (const p of merged as Array<{ name: string; mappedClientField: string | null }>) {
    if (!p.mappedClientField) continue;
    const key: string = p.mappedClientField;
    const val = systemFieldMap[key] ?? (customFieldMap.get(key) as string | undefined);
    if (val) values[p.name] = val;
  }
  return values;
}

export interface GenerateRequest {
  clientId?: string;
  clientName: string;
  templateIds: string[];
  values: Record<string, string>; // text placeholder name -> value
  imagePaths: Record<string, string>; // image placeholder name -> uploaded temp file path
  outputFormats: ('docx' | 'pdf')[];
}

function sanitizeForFilename(s: string): string {
  return s.replace(/[\\/:*?"<>|]/g, '').trim();
}

export async function validateGenerationInputs(templateIds: string[], values: Record<string, string>) {
  const merged = await getMergedPlaceholders(templateIds);
  const errors: { placeholder: string; message: string }[] = [];
  for (const p of merged) {
    if (p.isImage) continue; // image presence checked separately (file upload)
    const result = validatePlaceholderValue(p.validationType, values[p.name] ?? '');
    if (!result.valid) errors.push({ placeholder: p.name, message: result.message || 'Invalid value.' });
  }
  return errors;
}

/**
 * Generates one .docx (and optionally .pdf) per selected template, applies the
 * "<Document Name> - <Client Name>.docx" naming convention, zips multi-file
 * output, and records Generation History (Module 10).
 */
export async function generateDocuments(req: GenerateRequest) {
  const errors = await validateGenerationInputs(req.templateIds, req.values);
  if (errors.length) {
    throw new AppError(
      `Please fix the following before generating: ${errors.map((e) => `${e.placeholder} (${e.message})`).join('; ')}`,
      400,
    );
  }

  const templates = await prisma.template.findMany({
    where: { id: { in: req.templateIds }, status: 'Active' },
  });

  const generatedRoot = await getSetting(SETTING_KEYS.GENERATED_FOLDER);
  if (!generatedRoot) throw new AppError('Generated documents folder is not configured.', 500);

  const templateFolder = await getSetting(SETTING_KEYS.TEMPLATE_FOLDER);
  if (!templateFolder) throw new AppError('Template folder is not configured.', 500);

  const clientFolderName = sanitizeForFilename(req.clientName);
  const batchDir = path.join(generatedRoot, clientFolderName, new Date().toISOString().slice(0, 10));
  fs.mkdirSync(batchDir, { recursive: true });

  const merged = await getMergedPlaceholders(req.templateIds);
  const imagePlaceholderNames = new Set(merged.filter((p) => p.isImage).map((p) => p.name));

  const outputs: {
    templateId: string;
    templateName: string;
    docxPath?: string;
    pdfPath?: string;
    fileName: string;
    pdfError?: string;
  }[] = [];
  let anyPdfFailed = false;

  for (const template of templates) {
    const baseName = `${sanitizeForFilename(template.name)} - ${clientFolderName}`;
    const docxPath = path.join(batchDir, `${baseName}.docx`);

    generateDocx({
      templateFilePath: path.join(templateFolder, template.fileLocation),
      values: { ...req.values, ...req.imagePaths },
      imagePlaceholderNames,
      outputFilePath: docxPath,
    });

    let pdfPath: string | undefined;
    let pdfError: string | undefined;
    if (req.outputFormats.includes('pdf')) {
      // PDF conversion is a "nice to have" layered on top of the Word document, not a
      // precondition for it. If LibreOffice isn't installed/configured, we still want
      // the already-generated .docx to reach the user rather than throwing the whole
      // batch away - staff can still download Word, and we surface a single clear
      // warning about PDF rather than silently losing every document in the request.
      try {
        pdfPath = await convertDocxToPdf(docxPath, batchDir);
      } catch (e: any) {
        anyPdfFailed = true;
        pdfError = e?.userMessage || e?.message || 'PDF conversion failed.';
        logger.warn(`PDF conversion failed for "${baseName}": ${pdfError}`);
      }
    }

    outputs.push({ templateId: template.id, templateName: template.name, docxPath, pdfPath, fileName: baseName, pdfError });
  }

  const history = await prisma.generationHistory.create({
    data: {
      clientId: req.clientId,
      clientNameSnapshot: req.clientName,
      placeholderValuesJson: JSON.stringify(req.values),
      outputFolder: batchDir,
      templates: {
        create: outputs.map((o) => ({
          templateId: o.templateId,
          generatedFileName: `${o.fileName}.docx`,
        })),
      },
    },
  });

  logger.info(`Generated ${outputs.length} document(s) for client "${req.clientName}" (history ${history.id})`);
  return { historyId: history.id, outputs, batchDir, pdfUnavailable: anyPdfFailed };
}

export function zipOutputs(files: string[], zipFileName: string, destDir: string): string {
  const zip = new AdmZip();
  for (const f of files) {
    if (fs.existsSync(f)) zip.addLocalFile(f);
  }
  const zipPath = path.join(destDir, zipFileName);
  zip.writeZip(zipPath);
  return zipPath;
}
