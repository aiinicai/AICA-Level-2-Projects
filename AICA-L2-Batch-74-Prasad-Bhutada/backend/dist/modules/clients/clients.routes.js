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
const svc = __importStar(require("./clients.service"));
const upload = (0, multer_1.default)({ dest: os_1.default.tmpdir() });
const router = (0, express_1.Router)();
router.get('/', async (req, res, next) => {
    try {
        res.json({ success: true, data: await svc.listClients(req.query.search) });
    }
    catch (e) {
        next(e);
    }
});
router.get('/fields', async (_req, res, next) => {
    try {
        res.json({ success: true, data: await svc.listClientFields() });
    }
    catch (e) {
        next(e);
    }
});
router.post('/fields', async (req, res, next) => {
    try {
        res.status(201).json({ success: true, data: await svc.addClientField(req.body) });
    }
    catch (e) {
        next(e);
    }
});
router.get('/export', async (_req, res, next) => {
    try {
        const buffer = await svc.exportToExcel();
        res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
        res.setHeader('Content-Disposition', 'attachment; filename="Clients.xlsx"');
        res.send(buffer);
    }
    catch (e) {
        next(e);
    }
});
router.post('/import', upload.single('file'), async (req, res, next) => {
    try {
        const file = req.file;
        res.json({ success: true, data: await svc.bulkImportFromExcel(file.path) });
    }
    catch (e) {
        next(e);
    }
});
router.get('/:id', async (req, res, next) => {
    try {
        res.json({ success: true, data: await svc.getClient(req.params.id) });
    }
    catch (e) {
        next(e);
    }
});
router.post('/', async (req, res, next) => {
    try {
        res.status(201).json({ success: true, data: await svc.createClient(req.body) });
    }
    catch (e) {
        next(e);
    }
});
router.put('/:id', async (req, res, next) => {
    try {
        res.json({ success: true, data: await svc.updateClient(req.params.id, req.body) });
    }
    catch (e) {
        next(e);
    }
});
router.delete('/:id', async (req, res, next) => {
    try {
        await svc.deleteClient(req.params.id);
        res.json({ success: true, message: 'Client deleted.' });
    }
    catch (e) {
        next(e);
    }
});
exports.default = router;
//# sourceMappingURL=clients.routes.js.map