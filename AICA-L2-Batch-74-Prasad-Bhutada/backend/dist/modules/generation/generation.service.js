"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.getMergedPlaceholders = getMergedPlaceholders;
exports.autoFillFromClient = autoFillFromClient;
exports.validateGenerationInputs = validateGenerationInputs;
exports.generateDocuments = generateDocuments;
exports.zipOutputs = zipOutputs;
const fs_1 = __importDefault(require("fs"));
const path_1 = __importDefault(require("path"));
const adm_zip_1 = __importDefault(require("adm-zip"));
const prisma_1 = require("../../db/prisma");
const logger_1 = require("../../utils/logger");
const settings_service_1 = require("../settings/settings.service");
const docxEngine_1 = require("./docxEngine");
const pdfEngine_1 = require("./pdfEngine");
const validators_1 = require("./validators");
/** Module 5: merge placeholders across a selection of templates, deduped, each tagged with which templates use it. */
async function getMergedPlaceholders(templateIds) {
    if (!templateIds.length)
        throw new logger_1.AppError('Please select at least one template.', 400);
    const templates = await prisma_1.prisma.template.findMany({
        where: { id: { in: templateIds }, status: 'Active' },
        include: { placeholders: { include: { placeholder: true } } },
    });
    if (templates.length !== templateIds.length) {
        throw new logger_1.AppError('One or more selected templates could not be found.', 404);
    }
    const merged = new Map();
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
            merged.get(key).usedIn.push(t.name);
        }
    }
    // Also attach client-master mapping so the UI can offer "Import from Client Master".
    const placeholderIds = Array.from(merged.values()).map((p) => p.placeholderId);
    const mappings = await prisma_1.prisma.placeholderMapping.findMany({
        where: { placeholderId: { in: placeholderIds } },
    });
    const mapByPlaceholder = new Map(mappings.map((m) => [m.placeholderId, m.clientFieldKey]));
    return Array.from(merged.values()).map((p) => ({
        ...p,
        mappedClientField: mapByPlaceholder.get(p.placeholderId) || null,
    }));
}
/** Auto-fill placeholder values from a Client Master record, following the configured mappings. */
async function autoFillFromClient(clientId, templateIds) {
    const client = await prisma_1.prisma.client.findUnique({ where: { id: clientId }, include: { customValues: { include: { field: true } } } });
    if (!client)
        throw new logger_1.AppError('Client not found.', 404);
    const merged = await getMergedPlaceholders(templateIds);
    const systemFieldMap = {
        name: client.name,
        addressLine1: client.addressLine1,
        addressLine2: client.addressLine2,
        clientType: client.clientType,
        mobile: client.mobile,
        email: client.email,
    };
    const customFieldMap = new Map(client.customValues.map((v) => [v.field.fieldKey, v.value]));
    const values = {};
    for (const p of merged) {
        if (!p.mappedClientField)
            continue;
        const key = p.mappedClientField;
        const val = systemFieldMap[key] ?? customFieldMap.get(key);
        if (val)
            values[p.name] = val;
    }
    return values;
}
function sanitizeForFilename(s) {
    return s.replace(/[\\/:*?"<>|]/g, '').trim();
}
async function validateGenerationInputs(templateIds, values) {
    const merged = await getMergedPlaceholders(templateIds);
    const errors = [];
    for (const p of merged) {
        if (p.isImage)
            continue; // image presence checked separately (file upload)
        const result = (0, validators_1.validatePlaceholderValue)(p.validationType, values[p.name] ?? '');
        if (!result.valid)
            errors.push({ placeholder: p.name, message: result.message || 'Invalid value.' });
    }
    return errors;
}
/**
 * Generates one .docx (and optionally .pdf) per selected template, applies the
 * "<Document Name> - <Client Name>.docx" naming convention, zips multi-file
 * output, and records Generation History (Module 10).
 */
async function generateDocuments(req) {
    const errors = await validateGenerationInputs(req.templateIds, req.values);
    if (errors.length) {
        throw new logger_1.AppError(`Please fix the following before generating: ${errors.map((e) => `${e.placeholder} (${e.message})`).join('; ')}`, 400);
    }
    const templates = await prisma_1.prisma.template.findMany({
        where: { id: { in: req.templateIds }, status: 'Active' },
    });
    const generatedRoot = await (0, settings_service_1.getSetting)(settings_service_1.SETTING_KEYS.GENERATED_FOLDER);
    if (!generatedRoot)
        throw new logger_1.AppError('Generated documents folder is not configured.', 500);
    const templateFolder = await (0, settings_service_1.getSetting)(settings_service_1.SETTING_KEYS.TEMPLATE_FOLDER);
    if (!templateFolder)
        throw new logger_1.AppError('Template folder is not configured.', 500);
    const clientFolderName = sanitizeForFilename(req.clientName);
    const batchDir = path_1.default.join(generatedRoot, clientFolderName, new Date().toISOString().slice(0, 10));
    fs_1.default.mkdirSync(batchDir, { recursive: true });
    const merged = await getMergedPlaceholders(req.templateIds);
    const imagePlaceholderNames = new Set(merged.filter((p) => p.isImage).map((p) => p.name));
    const outputs = [];
    let anyPdfFailed = false;
    for (const template of templates) {
        const baseName = `${sanitizeForFilename(template.name)} - ${clientFolderName}`;
        const docxPath = path_1.default.join(batchDir, `${baseName}.docx`);
        (0, docxEngine_1.generateDocx)({
            templateFilePath: path_1.default.join(templateFolder, template.fileLocation),
            values: { ...req.values, ...req.imagePaths },
            imagePlaceholderNames,
            outputFilePath: docxPath,
        });
        let pdfPath;
        let pdfError;
        if (req.outputFormats.includes('pdf')) {
            // PDF conversion is a "nice to have" layered on top of the Word document, not a
            // precondition for it. If LibreOffice isn't installed/configured, we still want
            // the already-generated .docx to reach the user rather than throwing the whole
            // batch away - staff can still download Word, and we surface a single clear
            // warning about PDF rather than silently losing every document in the request.
            try {
                pdfPath = await (0, pdfEngine_1.convertDocxToPdf)(docxPath, batchDir);
            }
            catch (e) {
                anyPdfFailed = true;
                pdfError = e?.userMessage || e?.message || 'PDF conversion failed.';
                logger_1.logger.warn(`PDF conversion failed for "${baseName}": ${pdfError}`);
            }
        }
        outputs.push({ templateId: template.id, templateName: template.name, docxPath, pdfPath, fileName: baseName, pdfError });
    }
    const history = await prisma_1.prisma.generationHistory.create({
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
    logger_1.logger.info(`Generated ${outputs.length} document(s) for client "${req.clientName}" (history ${history.id})`);
    return { historyId: history.id, outputs, batchDir, pdfUnavailable: anyPdfFailed };
}
function zipOutputs(files, zipFileName, destDir) {
    const zip = new adm_zip_1.default();
    for (const f of files) {
        if (fs_1.default.existsSync(f))
            zip.addLocalFile(f);
    }
    const zipPath = path_1.default.join(destDir, zipFileName);
    zip.writeZip(zipPath);
    return zipPath;
}
//# sourceMappingURL=generation.service.js.map