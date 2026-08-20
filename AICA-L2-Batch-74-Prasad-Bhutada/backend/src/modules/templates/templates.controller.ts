import { Request, Response, NextFunction } from 'express';
import * as svc from './templates.service';
import { AppError } from '../../utils/logger';

export async function list(req: Request, res: Response, next: NextFunction) {
  try {
    const { search, categoryId, status } = req.query as Record<string, string>;
    const templates = await svc.listTemplates({ search, categoryId, status });
    res.json({ success: true, data: templates });
  } catch (e) {
    next(e);
  }
}

export async function getOne(req: Request, res: Response, next: NextFunction) {
  try {
    res.json({ success: true, data: await svc.getTemplateById(req.params.id) });
  } catch (e) {
    next(e);
  }
}

export async function preview(req: Request, res: Response, next: NextFunction) {
  try {
    const html = await svc.renderPreviewHtml(req.params.id);
    res.json({ success: true, data: { html } });
  } catch (e) {
    next(e);
  }
}

/** Import supports single or multiple files: each file becomes its own template row, sharing category/keywords. */
export async function importTemplates(req: Request, res: Response, next: NextFunction) {
  try {
    const files = req.files as Express.Multer.File[];
    if (!files || files.length === 0) throw new AppError('Please select at least one .docx file to import.', 400);
    const { categoryId, keywords, description } = req.body;
    if (!categoryId) throw new AppError('Please choose a category.', 400);

    const keywordList: string[] = keywords ? String(keywords).split(',') : [];
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
  } catch (e) {
    next(e);
  }
}

export async function replaceFile(req: Request, res: Response, next: NextFunction) {
  try {
    const file = req.file as Express.Multer.File;
    if (!file) throw new AppError('Please select a replacement .docx file.', 400);
    const updated = await svc.replaceTemplateFile(req.params.id, file.path, file.originalname);
    res.json({ success: true, data: updated });
  } catch (e) {
    next(e);
  }
}

export async function rename(req: Request, res: Response, next: NextFunction) {
  try {
    const { name } = req.body;
    if (!name) throw new AppError('New name is required.', 400);
    res.json({ success: true, data: await svc.renameTemplate(req.params.id, name) });
  } catch (e) {
    next(e);
  }
}

export async function download(req: Request, res: Response, next: NextFunction) {
  try {
    const template = await svc.getTemplateById(req.params.id);
    const filePath = await svc.getTemplateAbsolutePath(req.params.id);
    res.download(filePath, `${template.name}.docx`);
  } catch (e) {
    next(e);
  }
}

export async function dependencyCheck(req: Request, res: Response, next: NextFunction) {
  try {
    res.json({ success: true, data: await svc.checkTemplateDependencies(req.params.id) });
  } catch (e) {
    next(e);
  }
}

export async function softDelete(req: Request, res: Response, next: NextFunction) {
  try {
    await svc.softDeleteTemplate(req.params.id);
    res.json({ success: true, message: 'Template moved to Recycle Bin.' });
  } catch (e) {
    next(e);
  }
}

export async function restore(req: Request, res: Response, next: NextFunction) {
  try {
    await svc.restoreTemplate(req.params.id);
    res.json({ success: true, message: 'Template restored.' });
  } catch (e) {
    next(e);
  }
}

export async function recycleBin(_req: Request, res: Response, next: NextFunction) {
  try {
    res.json({ success: true, data: await svc.listRecycleBin() });
  } catch (e) {
    next(e);
  }
}
