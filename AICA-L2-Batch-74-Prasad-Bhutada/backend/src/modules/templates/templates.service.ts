import fs from 'fs';
import path from 'path';
import mammoth from 'mammoth';
import { prisma } from '../../db/prisma';
import { AppError, logger } from '../../utils/logger';
import { getSetting, SETTING_KEYS } from '../settings/settings.service';
import { detectPlaceholders } from './placeholderParser';

async function templateFolder(): Promise<string> {
  const dir = await getSetting(SETTING_KEYS.TEMPLATE_FOLDER);
  if (!dir) throw new AppError('Template storage folder is not configured. Please check Settings.', 500);
  return dir;
}

/** Persists an uploaded .doc/.docx file to the template folder + creates DB metadata + indexes placeholders. */
export async function importTemplate(params: {
  tempFilePath: string;
  originalName: string;
  name: string;
  categoryId: string;
  keywords: string[];
  description?: string;
}) {
  const ext = path.extname(params.originalName).toLowerCase();
  if (!['.doc', '.docx'].includes(ext)) {
    throw new AppError('Only .doc and .docx files can be imported as templates.', 400);
  }
  if (ext === '.doc') {
    throw new AppError(
      'Legacy .doc files must be converted to .docx before import (Word: File > Save As > .docx). Placeholder detection and generation require the .docx XML format.',
      400,
    );
  }

  const folder = await templateFolder();
  const template = await prisma.template.create({
    data: {
      name: params.name,
      categoryId: params.categoryId,
      description: params.description,
      originalName: params.originalName,
      fileLocation: '', // set below once we know the id-based filename
      status: 'Active',
    },
  });

  const storedFileName = `${template.id}.docx`;
  const destPath = path.join(folder, storedFileName);
  fs.copyFileSync(params.tempFilePath, destPath);
  const stat = fs.statSync(destPath);

  await prisma.template.update({
    where: { id: template.id },
    data: { fileLocation: storedFileName, fileSizeBytes: stat.size },
  });

  await indexKeywords(template.id, params.keywords);
  await syncPlaceholders(template.id, destPath);

  logger.info(`Template imported: ${params.name} (${template.id})`);
  return getTemplateById(template.id);
}

async function indexKeywords(templateId: string, keywords: string[]) {
  await prisma.templateKeyword.deleteMany({ where: { templateId } });
  const clean = keywords.map((k) => k.trim()).filter(Boolean);
  if (clean.length) {
    await prisma.templateKeyword.createMany({
      data: clean.map((keyword) => ({ templateId, keyword })),
    });
  }
  await prisma.template.update({ where: { id: templateId }, data: { keywords: clean.join(', ') } });
}

/** Detects placeholders in the stored file and syncs the Placeholder/TemplatePlaceholder tables (Module 2/3). */
export async function syncPlaceholders(templateId: string, absoluteFilePath: string) {
  const detected = detectPlaceholders(absoluteFilePath);

  await prisma.templatePlaceholder.deleteMany({ where: { templateId } });

  for (const d of detected) {
    const placeholder = await prisma.placeholder.upsert({
      where: { name: d.name },
      update: { isImage: d.isImage },
      create: { name: d.name, isImage: d.isImage, validationType: d.isImage ? 'Image' : 'Text' },
    });
    await prisma.templatePlaceholder.create({
      data: { templateId, placeholderId: placeholder.id },
    });
  }
}

export async function getTemplateById(id: string) {
  const t = await prisma.template.findUnique({
    where: { id },
    include: { category: true, placeholders: { include: { placeholder: true } } },
  });
  if (!t || t.status === 'Deleted') throw new AppError('Template not found.', 404);
  return t;
}

export async function listTemplates(filters: { search?: string; categoryId?: string; status?: string }) {
  const status = filters.status || 'Active';
  return prisma.template.findMany({
    where: {
      status,
      ...(filters.categoryId ? { categoryId: filters.categoryId } : {}),
      ...(filters.search
        ? {
            OR: [
              { name: { contains: filters.search } },
              { keywords: { contains: filters.search } },
              { keywordEntries: { some: { keyword: { contains: filters.search } } } },
            ],
          }
        : {}),
    },
    include: { category: true },
    orderBy: { name: 'asc' },
  });
}

export async function renameTemplate(id: string, newName: string) {
  await getTemplateById(id);
  return prisma.template.update({ where: { id }, data: { name: newName } });
}

/** Replaces the underlying file for an existing template entry (re-detects placeholders, bumps version). */
export async function replaceTemplateFile(id: string, tempFilePath: string, originalName: string) {
  const template = await getTemplateById(id);
  const folder = await templateFolder();
  const destPath = path.join(folder, template.fileLocation);
  fs.copyFileSync(tempFilePath, destPath);
  const stat = fs.statSync(destPath);

  await syncPlaceholders(id, destPath);

  return prisma.template.update({
    where: { id },
    data: { version: template.version + 1, fileSizeBytes: stat.size, originalName },
  });
}

/** Before deleting: check if the template appears in generation history (a soft "dependency"). */
export async function checkTemplateDependencies(id: string) {
  const usageCount = await prisma.generationHistoryTemplate.count({ where: { templateId: id } });
  return {
    hasDependencies: usageCount > 0,
    usageCount,
    message:
      usageCount > 0
        ? `This template has been used to generate ${usageCount} document(s) previously. Deleting it will move it to the Recycle Bin (documents already generated are not affected), but it will no longer be selectable for new generation.`
        : null,
  };
}

export async function softDeleteTemplate(id: string) {
  await getTemplateById(id);
  await prisma.template.update({ where: { id }, data: { status: 'Deleted', deletedAt: new Date() } });
  await prisma.auditLog.create({
    data: { action: 'TEMPLATE_DELETE', entityType: 'Template', entityId: id },
  });
}

export async function restoreTemplate(id: string) {
  const t = await prisma.template.findUnique({ where: { id } });
  if (!t) throw new AppError('Template not found.', 404);
  await prisma.template.update({ where: { id }, data: { status: 'Active', deletedAt: null } });
  await prisma.auditLog.create({
    data: { action: 'TEMPLATE_RESTORE', entityType: 'Template', entityId: id },
  });
}

export async function listRecycleBin() {
  return prisma.template.findMany({ where: { status: 'Deleted' }, include: { category: true } });
}

/** Renders an HTML preview that closely resembles Word's own rendering, for the centre panel. */
export async function renderPreviewHtml(id: string): Promise<string> {
  const template = await getTemplateById(id);
  const folder = await templateFolder();
  const filePath = path.join(folder, template.fileLocation);
  const result = await mammoth.convertToHtml(
    { path: filePath },
    {
      styleMap: [
        "p[style-name='Title'] => h1.doc-title",
        "p[style-name='Heading 1'] => h1",
        "p[style-name='Heading 2'] => h2",
      ],
    },
  );
  if (result.messages.length) {
    logger.debug(`Preview conversion notes for ${id}: ${JSON.stringify(result.messages)}`);
  }
  return result.value;
}

export async function getTemplateAbsolutePath(id: string): Promise<string> {
  const template = await getTemplateById(id);
  const folder = await templateFolder();
  return path.join(folder, template.fileLocation);
}
