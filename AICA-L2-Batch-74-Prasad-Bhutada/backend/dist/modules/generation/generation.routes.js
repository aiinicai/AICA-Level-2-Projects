"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = require("express");
const multer_1 = __importDefault(require("multer"));
const os_1 = __importDefault(require("os"));
const path_1 = __importDefault(require("path"));
const fs_1 = __importDefault(require("fs"));
const mammoth_1 = __importDefault(require("mammoth"));
const svc = __importStar(require("./generation.service"));
const logger_1 = require("../../utils/logger");
const settings_service_1 = require("../settings/settings.service");
// Signature/Logo/Photograph placeholders only ever need common photo/scan formats.
// Restricting accepted types here also closes off a known unpatched DoS in the
// `image-size` library (infinite loop parsing malformed ICNS/JXL/HEIF files) by
// never letting those file types reach it in the first place - see docs/ARCHITECTURE.md.
const ALLOWED_IMAGE_TYPES = new Set(['image/png', 'image/jpeg', 'image/gif']);
const upload = (0, multer_1.default)({
    dest: os_1.default.tmpdir(),
    limits: { fileSize: 10 * 1024 * 1024 },
    fileFilter: (_req, file, cb) => {
        if (ALLOWED_IMAGE_TYPES.has(file.mimetype))
            return cb(null, true);
        cb(new logger_1.AppError('Please upload a PNG, JPG, or GIF image.', 400));
    },
});
/**
 * Resolves a (dir, file) pair from client-supplied query params into a real path,
 * while guaranteeing the result can never escape the configured Generated
 * Documents folder. `dir`/`file` come from the browser on every download AND
 * preview request on this un-authenticated route (staff need these without the
 * admin password), so this boundary check matters - without it, a crafted
 * `dir=..\..\..\Windows` or a `file` containing `..\` could read arbitrary
 * files on the server. Every route below MUST go through this, not use the
 * query params directly.
 */
async function resolveSafeGeneratedPath(dir, file) {
    const generatedRoot = await (0, settings_service_1.getSetting)(settings_service_1.SETTING_KEYS.GENERATED_FOLDER);
    if (!generatedRoot)
        throw new logger_1.AppError('Generated documents folder is not configured.', 500);
    const resolvedRoot = path_1.default.resolve(generatedRoot);
    const resolvedDir = path_1.default.resolve(dir);
    const relativeToRoot = path_1.default.relative(resolvedRoot, resolvedDir);
    if (relativeToRoot.startsWith('..') || path_1.default.isAbsolute(relativeToRoot)) {
        throw new logger_1.AppError('Invalid file location.', 400);
    }
    if (file) {
        if (file.includes('..') || file.includes('/') || file.includes('\\')) {
            throw new logger_1.AppError('Invalid file name.', 400);
        }
        return path_1.default.join(resolvedDir, file);
    }
    return resolvedDir;
}
const router = (0, express_1.Router)();
router.post('/merge-placeholders', async (req, res, next) => {
    try {
        const { templateIds } = req.body;
        res.json({ success: true, data: await svc.getMergedPlaceholders(templateIds) });
    }
    catch (e) {
        next(e);
    }
});
router.post('/autofill', async (req, res, next) => {
    try {
        const { clientId, templateIds } = req.body;
        res.json({ success: true, data: await svc.autoFillFromClient(clientId, templateIds) });
    }
    catch (e) {
        next(e);
    }
});
router.post('/validate', async (req, res, next) => {
    try {
        const { templateIds, values } = req.body;
        res.json({ success: true, data: await svc.validateGenerationInputs(templateIds, values) });
    }
    catch (e) {
        next(e);
    }
});
/**
 * Multipart form: fields = clientId?, clientName, templateIds (JSON string array),
 * values (JSON string map), outputFormats (JSON string array), plus any number of
 * image files whose fieldname equals the image placeholder name (e.g. "Signature").
 */
router.post('/generate', upload.any(), async (req, res, next) => {
    try {
        const body = req.body;
        const templateIds = JSON.parse(body.templateIds || '[]');
        const values = JSON.parse(body.values || '{}');
        const outputFormats = JSON.parse(body.outputFormats || '["docx"]');
        if (!body.clientName)
            throw new logger_1.AppError('Client name is required.', 400);
        if (!templateIds.length)
            throw new logger_1.AppError('Please select at least one template.', 400);
        const files = req.files || [];
        const imagePaths = {};
        for (const f of files)
            imagePaths[f.fieldname] = f.path;
        const result = await svc.generateDocuments({
            clientId: body.clientId || undefined,
            clientName: body.clientName,
            templateIds,
            values,
            imagePaths,
            outputFormats,
        });
        res.status(201).json({
            success: true,
            data: {
                historyId: result.historyId,
                files: result.outputs.map((o) => ({
                    templateId: o.templateId,
                    templateName: o.templateName,
                    docxFileName: o.docxPath ? path_1.default.basename(o.docxPath) : null,
                    pdfFileName: o.pdfPath ? path_1.default.basename(o.pdfPath) : null,
                    pdfError: o.pdfError || null,
                })),
                batchDir: result.batchDir,
                pdfUnavailable: result.pdfUnavailable,
            },
        });
    }
    catch (e) {
        next(e);
    }
});
/** Downloads a single generated file, or all of them as a ZIP when `all=true`. */
router.get('/download', async (req, res, next) => {
    try {
        const { dir, file, all, zipName } = req.query;
        if (!dir)
            throw new logger_1.AppError('Missing directory reference.', 400);
        if (all === 'true') {
            const safeDir = await resolveSafeGeneratedPath(dir);
            const files = fs_1.default
                .readdirSync(safeDir)
                .filter((f) => !f.endsWith('.zip'))
                .map((f) => path_1.default.join(safeDir, f));
            const zipPath = svc.zipOutputs(files, (zipName || 'Documents.zip').replace(/[^\w.\- ]/g, ''), safeDir);
            return res.download(zipPath);
        }
        if (!file)
            throw new logger_1.AppError('Missing file reference.', 400);
        const safePath = await resolveSafeGeneratedPath(dir, file);
        res.download(safePath);
    }
    catch (e) {
        next(e);
    }
});
/**
 * Word-like HTML preview of a generated document (Module 6, centre panel) -
 * mirrors templates.service.renderPreviewHtml but for a freshly generated file
 * rather than a master template.
 */
router.get('/preview', async (req, res, next) => {
    try {
        const { dir, file } = req.query;
        if (!dir || !file)
            throw new logger_1.AppError('Missing file reference.', 400);
        const safePath = await resolveSafeGeneratedPath(dir, file);
        if (!fs_1.default.existsSync(safePath))
            throw new logger_1.AppError('File not found.', 404);
        const result = await mammoth_1.default.convertToHtml({ path: safePath });
        res.json({ success: true, data: { html: result.value } });
    }
    catch (e) {
        next(e);
    }
});
exports.default = router;
//# sourceMappingURL=generation.routes.js.map