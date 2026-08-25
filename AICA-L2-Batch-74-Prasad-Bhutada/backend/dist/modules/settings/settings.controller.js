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
exports.unlock = unlock;
exports.getSettings = getSettings;
exports.updateSettings = updateSettings;
exports.changeTemplatePassword = changeTemplatePassword;
const svc = __importStar(require("./settings.service"));
const auth_1 = require("../../middleware/auth");
const logger_1 = require("../../utils/logger");
/** Unauthenticated on purpose - this IS the login step for Template Management. */
async function unlock(req, res, next) {
    try {
        const { password } = req.body;
        if (!password)
            throw new logger_1.AppError('Please enter the Template Management password.', 400);
        const ok = await svc.verifyTemplatePassword(password);
        if (!ok)
            throw new logger_1.AppError('Incorrect password.', 401);
        res.json({ success: true, data: { token: (0, auth_1.issueTemplateAdminToken)() } });
    }
    catch (e) {
        next(e);
    }
}
async function getSettings(_req, res, next) {
    try {
        res.json({ success: true, data: await svc.getAllSettings() });
    }
    catch (e) {
        next(e);
    }
}
async function updateSettings(req, res, next) {
    try {
        const updates = req.body;
        for (const [key, value] of Object.entries(updates)) {
            await svc.updateSetting(key, value);
        }
        res.json({ success: true, data: await svc.getAllSettings() });
    }
    catch (e) {
        next(e);
    }
}
async function changeTemplatePassword(req, res, next) {
    try {
        const { newPassword } = req.body;
        if (!newPassword || newPassword.length < 6) {
            throw new logger_1.AppError('New password must be at least 6 characters.', 400);
        }
        await svc.setTemplatePassword(newPassword);
        res.json({ success: true, message: 'Template Management password updated.' });
    }
    catch (e) {
        next(e);
    }
}
//# sourceMappingURL=settings.controller.js.map