"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.errorHandler = errorHandler;
exports.notFoundHandler = notFoundHandler;
const logger_1 = require("../utils/logger");
function errorHandler(err, req, res, _next) {
    if (err instanceof logger_1.AppError) {
        logger_1.logger.warn(`AppError on ${req.method} ${req.path}: ${err.message}`);
        return res.status(err.statusCode).json({ success: false, message: err.userMessage });
    }
    const error = err;
    logger_1.logger.error(`Unhandled error on ${req.method} ${req.path}: ${error.stack || error.message}`);
    return res.status(500).json({
        success: false,
        message: 'Something went wrong on our end. The issue has been logged - please try again or contact IT support.',
    });
}
function notFoundHandler(req, res) {
    res.status(404).json({ success: false, message: 'The requested resource was not found.' });
}
//# sourceMappingURL=errorHandler.js.map