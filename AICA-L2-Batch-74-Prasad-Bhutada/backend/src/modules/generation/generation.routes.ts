import { Router, Request, Response, NextFunction } from 'express';
import multer from 'multer';
import os from 'os';
import path from 'path';
import fs from 'fs';
import mammoth from 'mammoth';
import * as svc from './generation.service';
import { AppError } from '../../utils/logger';
import { getSetting, SETTING_KEYS } from '../settings/settings.service';

// Signature/Logo/Photograph placeholders only ever need common photo/scan formats.
// Restricting accepted types here also closes off a known unpatched DoS in the
// `image-size` library (infinite loop parsing malformed ICNS/JXL/HEIF files) by
// never letting those file types reach it in the first place - see docs/ARCHITECTURE.md.
const ALLOWED_IMAGE_TYPES = new Set(['image/png', 'image/jpeg', 'image/gif']);

const upload = multer({
  dest: os.tmpdir(),
  limits: { fileSize: 10 * 1024 * 1024 },
  fileFilter: (_req, file, cb) => {
    if (ALLOWED_IMAGE_TYPES.has(file.mimetype)) return cb(null, true);
    cb(new AppError('Please upload a PNG, JPG, or GIF image.', 400));
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
async function resolveSafeGeneratedPath(dir: string, file?: string): Promise<string> {
  const generatedRoot = await getSetting(SETTING_KEYS.GENERATED_FOLDER);
  if (!generatedRoot) throw new AppError('Generated documents folder is not configured.', 500);

  const resolvedRoot = path.resolve(generatedRoot);
  const resolvedDir = path.resolve(dir);
  const relativeToRoot = path.relative(resolvedRoot, resolvedDir);
  if (relativeToRoot.startsWith('..') || path.isAbsolute(relativeToRoot)) {
    throw new AppError('Invalid file location.', 400);
  }

  if (file) {
    if (file.includes('..') || file.includes('/') || file.includes('\\')) {
      throw new AppError('Invalid file name.', 400);
    }
    return path.join(resolvedDir, file);
  }
  return resolvedDir;
}

const router = Router();

router.post('/merge-placeholders', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const { templateIds } = req.body as { templateIds: string[] };
    res.json({ success: true, data: await svc.getMergedPlaceholders(templateIds) });
  } catch (e) {
    next(e);
  }
});

router.post('/autofill', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const { clientId, templateIds } = req.body as { clientId: string; templateIds: string[] };
    res.json({ success: true, data: await svc.autoFillFromClient(clientId, templateIds) });
  } catch (e) {
    next(e);
  }
});

router.post('/validate', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const { templateIds, values } = req.body as { templateIds: string[]; values: Record<string, string> };
    res.json({ success: true, data: await svc.validateGenerationInputs(templateIds, values) });
  } catch (e) {
    next(e);
  }
});

/**
 * Multipart form: fields = clientId?, clientName, templateIds (JSON string array),
 * values (JSON string map), outputFormats (JSON string array), plus any number of
 * image files whose fieldname equals the image placeholder name (e.g. "Signature").
 */
router.post('/generate', upload.any(), async (req: Request, res: Response, next: NextFunction) => {
  try {
    const body = req.body as Record<string, string>;
    const templateIds: string[] = JSON.parse(body.templateIds || '[]');
    const values: Record<string, string> = JSON.parse(body.values || '{}');
    const outputFormats: ('docx' | 'pdf')[] = JSON.parse(body.outputFormats || '["docx"]');

    if (!body.clientName) throw new AppError('Client name is required.', 400);
    if (!templateIds.length) throw new AppError('Please select at least one template.', 400);

    const files = (req.files as Express.Multer.File[]) || [];
    const imagePaths: Record<string, string> = {};
    for (const f of files) imagePaths[f.fieldname] = f.path;

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
          docxFileName: o.docxPath ? path.basename(o.docxPath) : null,
          pdfFileName: o.pdfPath ? path.basename(o.pdfPath) : null,
          pdfError: o.pdfError || null,
        })),
        batchDir: result.batchDir,
        pdfUnavailable: result.pdfUnavailable,
      },
    });
  } catch (e) {
    next(e);
  }
});

/** Downloads a single generated file, or all of them as a ZIP when `all=true`. */
router.get('/download', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const { dir, file, all, zipName } = req.query as Record<string, string>;
    if (!dir) throw new AppError('Missing directory reference.', 400);

    if (all === 'true') {
      const safeDir = await resolveSafeGeneratedPath(dir);
      const files: string[] = fs
        .readdirSync(safeDir)
        .filter((f: string) => !f.endsWith('.zip'))
        .map((f: string) => path.join(safeDir, f));
      const zipPath = svc.zipOutputs(files, (zipName || 'Documents.zip').replace(/[^\w.\- ]/g, ''), safeDir);
      return res.download(zipPath);
    }

    if (!file) throw new AppError('Missing file reference.', 400);
    const safePath = await resolveSafeGeneratedPath(dir, file);
    res.download(safePath);
  } catch (e) {
    next(e);
  }
});

/**
 * Word-like HTML preview of a generated document (Module 6, centre panel) -
 * mirrors templates.service.renderPreviewHtml but for a freshly generated file
 * rather than a master template.
 */
router.get('/preview', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const { dir, file } = req.query as Record<string, string>;
    if (!dir || !file) throw new AppError('Missing file reference.', 400);
    const safePath = await resolveSafeGeneratedPath(dir, file);
    if (!fs.existsSync(safePath)) throw new AppError('File not found.', 404);

    const result = await mammoth.convertToHtml({ path: safePath });
    res.json({ success: true, data: { html: result.value } });
  } catch (e) {
    next(e);
  }
});

export default router;
