"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.AppError = exports.logger = void 0;
const winston_1 = __importDefault(require("winston"));
const winston_daily_rotate_file_1 = __importDefault(require("winston-daily-rotate-file"));
const path_1 = __importDefault(require("path"));
const logDir = path_1.default.resolve('./logs');
exports.logger = winston_1.default.createLogger({
    level: process.env.NODE_ENV === 'production' ? 'info' : 'debug',
    format: winston_1.default.format.combine(winston_1.default.format.timestamp(), winston_1.default.format.errors({ stack: true }), winston_1.default.format.json()),
    transports: [
        new winston_daily_rotate_file_1.default({
            dirname: logDir,
            filename: 'cadocs-%DATE%.log',
            datePattern: 'YYYY-MM-DD',
            maxFiles: '30d',
            maxSize: '20m',
        }),
        new winston_1.default.transports.Console({
            format: winston_1.default.format.combine(winston_1.default.format.colorize(), winston_1.default.format.simple()),
        }),
    ],
});
/** Custom error carrying a safe, user-facing message separate from internal detail. */
class AppError extends Error {
    constructor(userMessage, statusCode = 400, internalMessage) {
        super(internalMessage || userMessage);
        this.userMessage = userMessage;
        this.statusCode = statusCode;
    }
}
exports.AppError = AppError;
//# sourceMappingURL=logger.js.map