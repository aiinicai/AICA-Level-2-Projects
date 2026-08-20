"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.requireTemplateAdmin = requireTemplateAdmin;
exports.issueTemplateAdminToken = issueTemplateAdminToken;
const jsonwebtoken_1 = __importDefault(require("jsonwebtoken"));
const config_1 = require("../config");
const logger_1 = require("../utils/logger");
/**
 * Guards Template Management ("Manage Formats") endpoints only.
 * Everyday document-generation/client-management usage requires NO login,
 * per functional requirement: "No authentication required for daily users."
 */
function requireTemplateAdmin(req, res, next) {
    const header = req.headers.authorization;
    if (!header || !header.startsWith('Bearer ')) {
        return next(new logger_1.AppError('Template management access required. Please unlock with the password.', 401));
    }
    const token = header.substring('Bearer '.length);
    try {
        const payload = jsonwebtoken_1.default.verify(token, config_1.config.jwtSecret);
        if (payload.scope !== 'template-admin') {
            throw new Error('wrong scope');
        }
        req.isTemplateAdmin = true;
        next();
    }
    catch {
        next(new logger_1.AppError('Your session has expired. Please unlock Template Management again.', 401));
    }
}
function issueTemplateAdminToken() {
    return jsonwebtoken_1.default.sign({ scope: 'template-admin' }, config_1.config.jwtSecret, { expiresIn: '4h' });
}
//# sourceMappingURL=auth.js.map