"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.importTemplate = importTemplate;
exports.syncPlaceholders = syncPlaceholders;
exports.getTemplateById = getTemplateById;
exports.listTemplates = listTemplates;
exports.renameTemplate = renameTemplate;
exports.replaceTemplateFile = replaceTemplateFile;
exports.checkTemplateDependencies = checkTemplateDependencies;
exports.softDeleteTemplate = softDeleteTemplate;
exports.restoreTemplate = restoreTemplate;
exports.listRecycleBin = listRecycleBin;
exports.renderPreviewHtml = renderPreviewHtml;
exports.getTemplateAbsolutePath = getTemplateAbsolutePath;
const fs_1 = __importDefault(require("fs"));
const path_1 = __importDefault(require("path"));
const mammoth_1 = __importDefault(require("mammoth"));
const prisma_1 = require("../../db/prisma");
const logger_1 = require("../../utils/logger");
const settings_service_1 = require("../settings/settings.service");
const placeholderParser_1 = require("./placeholderParser");
async function templateFolder() {
    const dir = await (0, settings_service_1.getSetting)(settings_service_1.SETTING_KEYS.TEMPLATE_FOLDER);
    if (!dir)
        throw new logger_1.AppError('Template storage folder is not configured. Please check Settings.', 500);
    return dir;
}
/** Persists an uploaded .doc/.docx file to the template folder + creates DB metadata + indexes placeholders. */
async function importTemplate(params) {
    const ext = path_1.default.extname(params.originalName).toLowerCase();
    if (!['.doc', '.docx'].includes(ext)) {
        throw new logger_1.AppError('Only .doc and .docx files can be imported as templates.', 400);
    }
    if (ext === '.doc') {
        throw new logger_1.AppError('Legacy .doc files must be converted to .docx before import (Word: File > Save As > .docx). Placeholder detection and generation require the .docx XML format.', 400);
    }
    const folder = await templateFolder();
    const template = await prisma_1.prisma.template.create({
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
    const destPath = path_1.default.join(folder, storedFileName);
    fs_1.default.copyFileSync(params.tempFilePath, destPath);
    const stat = fs_1.default.statSync(destPath);
    await prisma_1.prisma.template.update({
        where: { id: template.id },
        data: { fileLocation: storedFileName, fileSizeBytes: stat.size },
    });
    await indexKeywords(template.id, params.keywords);
    await syncPlaceholders(template.id, destPath);
    logger_1.logger.info(`Template imported: ${params.name} (${template.id})`);
    return getTemplateById(template.id);
}
async function indexKeywords(templateId, keywords) {
    await prisma_1.prisma.templateKeyword.deleteMany({ where: { templateId } });
    const clean = keywords.map((k) => k.trim()).filter(Boolean);
    if (clean.length) {
        await prisma_1.prisma.templateKeyword.createMany({
            data: clean.map((keyword) => ({ templateId, keyword })),
        });
    }
    await prisma_1.prisma.template.update({ where: { id: templateId }, data: { keywords: clean.join(', ') } });
}
/** Detects placeholders in the stored file and syncs the Placeholder/TemplatePlaceholder tables (Module 2/3). */
async function syncPlaceholders(templateId, absoluteFilePath) {
    const detected = (0, placeholderParser_1.detectPlaceholders)(absoluteFilePath);
    await prisma_1.prisma.templatePlaceholder.deleteMany({ where: { templateId } });
    for (const d of detected) {
        const placeholder = await prisma_1.prisma.placeholder.upsert({
            where: { name: d.name },
            update: { isImage: d.isImage },
            create: { name: d.name, isImage: d.isImage, validationType: d.isImage ? 'Image' : 'Text' },
        });
        await prisma_1.prisma.templatePlaceholder.create({
            data: { templateId, placeholderId: placeholder.id },
        });
    }
}
async function getTemplateById(id) {
    const t = await prisma_1.prisma.template.findUnique({
        where: { id },
        include: { category: true, placeholders: { include: { placeholder: true } } },
    });
    if (!t || t.status === 'Deleted')
        throw new logger_1.AppError('Template not found.', 404);
    return t;
}
async function listTemplates(filters) {
    const status = filters.status || 'Active';
    return prisma_1.prisma.template.findMany({
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
async function renameTemplate(id, newName) {
    await getTemplateById(id);
    return prisma_1.prisma.template.update({ where: { id }, data: { name: newName } });
}
/** Replaces the underlying file for an existing template entry (re-detects placeholders, bumps version). */
async function replaceTemplateFile(id, tempFilePath, originalName) {
    const template = await getTemplateById(id);
    const folder = await templateFolder();
    const destPath = path_1.default.join(folder, template.fileLocation);
    fs_1.default.copyFileSync(tempFilePath, destPath);
    const stat = fs_1.default.statSync(destPath);
    await syncPlaceholders(id, destPath);
    return prisma_1.prisma.template.update({
        where: { id },
        data: { version: template.version + 1, fileSizeBytes: stat.size, originalName },
    });
}
/** Before deleting: check if the template appears in generation history (a soft "dependency"). */
async function checkTemplateDependencies(id) {
    const usageCount = await prisma_1.prisma.generationHistoryTemplate.count({ where: { templateId: id } });
    return {
        hasDependencies: usageCount > 0,
        usageCount,
        message: usageCount > 0
            ? `This template has been used to generate ${usageCount} document(s) previously. Deleting it will move it to the Recycle Bin (documents already generated are not affected), but it will no longer be selectable for new generation.`
            : null,
    };
}
async function softDeleteTemplate(id) {
    await getTemplateById(id);
    await prisma_1.prisma.template.update({ where: { id }, data: { status: 'Deleted', deletedAt: new Date() } });
    await prisma_1.prisma.auditLog.create({
        data: { action: 'TEMPLATE_DELETE', entityType: 'Template', entityId: id },
    });
}
async function restoreTemplate(id) {
    const t = await prisma_1.prisma.template.findUnique({ where: { id } });
    if (!t)
        throw new logger_1.AppError('Template not found.', 404);
    await prisma_1.prisma.template.update({ where: { id }, data: { status: 'Active', deletedAt: null } });
    await prisma_1.prisma.auditLog.create({
        data: { action: 'TEMPLATE_RESTORE', entityType: 'Template', entityId: id },
    });
}
async function listRecycleBin() {
    return prisma_1.prisma.template.findMany({ where: { status: 'Deleted' }, include: { category: true } });
}
/** Renders an HTML preview that closely resembles Word's own rendering, for the centre panel. */
async function renderPreviewHtml(id) {
    const template = await getTemplateById(id);
    const folder = await templateFolder();
    const filePath = path_1.default.join(folder, template.fileLocation);
    const result = await mammoth_1.default.convertToHtml({ path: filePath }, {
        styleMap: [
            "p[style-name='Title'] => h1.doc-title",
            "p[style-name='Heading 1'] => h1",
            "p[style-name='Heading 2'] => h2",
        ],
    });
    if (result.messages.length) {
        logger_1.logger.debug(`Preview conversion notes for ${id}: ${JSON.stringify(result.messages)}`);
    }
    return result.value;
}
async function getTemplateAbsolutePath(id) {
    const template = await getTemplateById(id);
    const folder = await templateFolder();
    return path_1.default.join(folder, template.fileLocation);
}
//# sourceMappingURL=templates.service.js.map