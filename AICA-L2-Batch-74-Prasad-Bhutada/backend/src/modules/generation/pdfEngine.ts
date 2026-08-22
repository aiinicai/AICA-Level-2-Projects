import { execFile } from 'child_process';
import path from 'path';
import fs from 'fs';
import os from 'os';
import crypto from 'crypto';
import { AppError, logger } from '../../utils/logger';
import { getSetting, SETTING_KEYS } from '../settings/settings.service';
import { config } from '../../config';

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
export async function convertDocxToPdf(docxPath: string, outputDir: string): Promise<string> {
  const engine = (await getSetting(SETTING_KEYS.PDF_ENGINE)) || 'libreoffice';
  if (engine !== 'libreoffice') {
    throw new AppError(`PDF engine "${engine}" is not yet implemented on this server.`, 500);
  }

  fs.mkdirSync(outputDir, { recursive: true });

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
  const profileDir = path.join(os.tmpdir(), `cadocs-lo-profile-${crypto.randomUUID()}`);
  const profileUrl = 'file:///' + profileDir.replace(/\\/g, '/');

  try {
    await new Promise<void>((resolve, reject) => {
      execFile(
        config.sofficePath,
        [
          '--headless',
          '--norestore',
          `-env:UserInstallation=${profileUrl}`,
          '--convert-to',
          'pdf',
          '--outdir',
          outputDir,
          docxPath,
        ],
        { timeout: 120_000 },
        (error, stdout, stderr) => {
          if (error) {
            const detail = (stderr || stdout || error.message || '').trim().slice(0, 300);
            logger.error(`LibreOffice PDF conversion failed (path: ${config.sofficePath}): ${detail}`);
            const reason = detail ? ` (details: ${detail})` : '';
            reject(
              new AppError(
                `Could not generate PDF${reason}. Verify the LibreOffice path in Settings points directly at soffice.exe, and that no LibreOffice window/Quickstarter icon is required to be closed first.`,
                500,
              ),
            );
            return;
          }
          resolve();
        },
      );
    });
  } finally {
    fs.rm(profileDir, { recursive: true, force: true }, () => {
      /* best-effort cleanup of the temporary profile; a leftover temp folder is harmless */
    });
  }

  const base = path.basename(docxPath, path.extname(docxPath));
  const pdfPath = path.join(outputDir, `${base}.pdf`);
  if (!fs.existsSync(pdfPath)) {
    throw new AppError('PDF conversion completed but the output file was not found.', 500);
  }
  return pdfPath;
}
