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
Object.defineProperty(exports, "__esModule", { value: true });
exports.list = list;
exports.getOne = getOne;
exports.preview = preview;
exports.importTemplates = importTemplates;
exports.replaceFile = replaceFile;
exports.rename = rename;
exports.download = download;
exports.dependencyCheck = dependencyCheck;
exports.softDelete = softDelete;
exports.restore = restore;
exports.recycleBin = recycleBin;
const svc = __importStar(require("./templates.service"));
const logger_1 = require("../../utils/logger");
async function list(req, res, next) {
    try {
        const { search, categoryId, status } = req.query;
        const templates = await svc.listTemplates({ search, categoryId, status });
        res.json({ success: true, data: templates });
    }
    catch (e) {
        next(e);
    }
}
async function getOne(req, res, next) {
    try {
        res.json({ success: true, data: await svc.getTemplateById(req.params.id) });
    }
    catch (e) {
        next(e);
    }
}
async function preview(req, res, next) {
    try {
        const html = await svc.renderPreviewHtml(req.params.id);
        res.json({ success: true, data: { html } });
    }
    catch (e) {
        next(e);
    }
}
/** Import supports single or multiple files: each file becomes its own template row, sharing category/keywords. */
async function importTemplates(req, res, next) {
    try {
        const files = req.files;
        if (!files || files.length === 0)
            throw new logger_1.AppError('Please select at least one .docx file to import.', 400);
        const { categoryId, keywords, description } = req.body;
        if (!categoryId)
            throw new logger_1.AppError('Please choose a category.', 400);
        const keywordList = keywords ? String(keywords).split(',') : [];
        const results = [];
        for (const file of files) {
            const name = req.body.name || file.originalname.replace(/\.[^/.]+$/, '');
            const created = await svc.importTemplate({
                tempFilePath: file.path,
                originalName: file.originalname,
                name,
                categoryId,
                keywords: keywordList,
                description,
            });
            results.push(created);
        }
        res.status(201).json({ success: true, data: results });
    }
    catch (e) {
        next(e);
    }
}
async function replaceFile(req, res, next) {
    try {
        const file = req.file;
        if (!file)
            throw new logger_1.AppError('Please select a replacement .docx file.', 400);
        const updated = await svc.replaceTemplateFile(req.params.id, file.path, file.originalname);
        res.json({ success: true, data: updated });
    }
    catch (e) {
        next(e);
    }
}
async function rename(req, res, next) {
    try {
        const { name } = req.body;
        if (!name)
            throw new logger_1.AppError('New name is required.', 400);
        res.json({ success: true, data: await svc.renameTemplate(req.params.id, name) });
    }
    catch (e) {
        next(e);
    }
}
async function download(req, res, next) {
    try {
        const template = await svc.getTemplateById(req.params.id);
        const filePath = await svc.getTemplateAbsolutePath(req.params.id);
        res.download(filePath, `${template.name}.docx`);
    }
    catch (e) {
        next(e);
    }
}
async function dependencyCheck(req, res, next) {
    try {
        res.json({ success: true, data: await svc.checkTemplateDependencies(req.params.id) });
    }
    catch (e) {
        next(e);
    }
}
async function softDelete(req, res, next) {
    try {
        await svc.softDeleteTemplate(req.params.id);
        res.json({ success: true, message: 'Template moved to Recycle Bin.' });
    }
    catch (e) {
        next(e);
    }
}
async function restore(req, res, next) {
    try {
        await svc.restoreTemplate(req.params.id);
        res.json({ success: true, message: 'Template restored.' });
    }
    catch (e) {
        next(e);
    }
}
async function recycleBin(_req, res, next) {
    try {
        res.json({ success: true, data: await svc.listRecycleBin() });
    }
    catch (e) {
        next(e);
    }
}
//# sourceMappingURL=templates.controller.js.map