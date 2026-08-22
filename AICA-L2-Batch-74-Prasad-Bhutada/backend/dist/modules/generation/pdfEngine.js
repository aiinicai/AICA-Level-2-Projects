"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.convertDocxToPdf = convertDocxToPdf;
const child_process_1 = require("child_process");
const path_1 = __importDefault(require("path"));
const fs_1 = __importDefault(require("fs"));
const os_1 = __importDefault(require("os"));
const crypto_1 = __importDefault(require("crypto"));
const logger_1 = require("../../utils/logger");
const settings_service_1 = require("../settings/settings.service");
const config_1 = require("../../config");
/**
 * Converts a generated .docx to .pdf.
 *
 * Engine choice: LibreOffice headless (`soffice --headless --convert-to pdf`).
 * This is deliberately NOT a pure-JS docx->pdf library. Pure-JS converters
 * cannot reliably reproduce Word table layout, headers/footers, pagination
 * and font substitution - which the spec explicitly requires to be
 * "identical". LibreOffice's own layout engine renders the OOXML the same
 * way a desktop install of LibreOffice/Word would, which is the closest
 * practical fidelity achievable without a licensed Word Interop/Aspose
 * dependency. The engine is abstracted behind this module (and the
 * `pdfEngine` Setting) specifically so a different engine (e.g. a licensed
 * Aspose.Words or MS Office interop engine) can be swapped in later without
 * touching any calling code - satisfying the "PDF Engine" setting requirement.
 */
async function convertDocxToPdf(docxPath, outputDir) {
    const engine = (await (0, settings_service_1.getSetting)(settings_service_1.SETTING_KEYS.PDF_ENGINE)) || 'libreoffice';
    if (engine !== 'libreoffice') {
        throw new logger_1.AppError(`PDF engine "${engine}" is not yet implemented on this server.`, 500);
    }
    fs_1.default.mkdirSync(outputDir, { recursive: true });
    // Use a fresh, isolated LibreOffice user profile per conversion, instead of each
    // invocation's default profile. This fixes two real problems seen in practice:
    //   1. On Windows, LibreOffice normally installs a "Quickstarter" that runs
    //      quietly in the system tray after login and holds a lock on the default
    //      profile - any headless `soffice --convert-to` call against that same
    //      profile then hangs or fails silently, even though `soffice --version`
    //      from a terminal works fine (that check doesn't touch the profile lock).
    //   2. Multiple staff generating PDFs at the same time on a shared office LAN
    //      server would otherwise contend for that same single default profile.
    // A disposable profile directory sidesteps both. The one-time cost is a few
    // extra seconds for LibreOffice to bootstrap a new profile on each call.
    const profileDir = path_1.default.join(os_1.default.tmpdir(), `cadocs-lo-profile-${crypto_1.default.randomUUID()}`);
    const profileUrl = 'file:///' + profileDir.replace(/\\/g, '/');
    try {
        await new Promise((resolve, reject) => {
            (0, child_process_1.execFile)(config_1.config.sofficePath, [
                '--headless',
                '--norestore',
                `-env:UserInstallation=${profileUrl}`,
                '--convert-to',
                'pdf',
                '--outdir',
                outputDir,
                docxPath,
            ], { timeout: 120000 }, (error, stdout, stderr) => {
                if (error) {
                    const detail = (stderr || stdout || error.message || '').trim().slice(0, 300);
                    logger_1.logger.error(`LibreOffice PDF conversion failed (path: ${config_1.config.sofficePath}): ${detail}`);
                    const reason = detail ? ` (details: ${detail})` : '';
                    reject(new logger_1.AppError(`Could not generate PDF${reason}. Verify the LibreOffice path in Settings points directly at soffice.exe, and that no LibreOffice window/Quickstarter icon is required to be closed first.`, 500));
                    return;
                }
                resolve();
            });
        });
    }
    finally {
        fs_1.default.rm(profileDir, { recursive: true, force: true }, () => {
            /* best-effort cleanup of the temporary profile; a leftover temp folder is harmless */
        });
    }
    const base = path_1.default.basename(docxPath, path_1.default.extname(docxPath));
    const pdfPath = path_1.default.join(outputDir, `${base}.pdf`);
    if (!fs_1.default.existsSync(pdfPath)) {
        throw new logger_1.AppError('PDF conversion completed but the output file was not found.', 500);
    }
    return pdfPath;
}
//# sourceMappingURL=pdfEngine.js.map