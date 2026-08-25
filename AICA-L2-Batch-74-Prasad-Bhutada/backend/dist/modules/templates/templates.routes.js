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
const ctrl = __importStar(require("./templates.controller"));
const auth_1 = require("../../middleware/auth");
const upload = (0, multer_1.default)({ dest: os_1.default.tmpdir(), limits: { fileSize: 25 * 1024 * 1024 } });
const router = (0, express_1.Router)();
// Read-only browsing (list/preview/download) intentionally does NOT require the
// template-admin password, since staff need to browse+preview templates while
// generating documents (Module 5/6). Only structural changes are gated.
router.get('/', ctrl.list);
router.get('/:id', ctrl.getOne);
router.get('/:id/preview', ctrl.preview);
router.get('/:id/download', ctrl.download);
router.use(auth_1.requireTemplateAdmin);
router.post('/import', upload.array('files', 20), ctrl.importTemplates);
router.post('/:id/replace', upload.single('file'), ctrl.replaceFile);
router.patch('/:id/rename', ctrl.rename);
router.get('/:id/dependencies', ctrl.dependencyCheck);
router.delete('/:id', ctrl.softDelete);
router.post('/:id/restore', ctrl.restore);
router.get('/recycle-bin/list', ctrl.recycleBin);
exports.default = router;
//# sourceMappingURL=templates.routes.js.map