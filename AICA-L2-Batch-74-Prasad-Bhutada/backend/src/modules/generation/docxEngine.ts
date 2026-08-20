import fs from 'fs';
import path from 'path';
import PizZip from 'pizzip';
import Docxtemplater from 'docxtemplater';
// @ts-ignore - no bundled types
import ImageModule from 'docxtemplater-image-module-free';
import sizeOf from 'image-size';

export interface GenerationValues {
  [placeholderName: string]: string; // for image placeholders, value = absolute file path to the uploaded image
}

export interface GenerationOptions {
  templateFilePath: string;
  values: GenerationValues;
  imagePlaceholderNames: Set<string>;
  outputFilePath: string;
}

/**
 * Renders a single generated .docx from a template + placeholder values.
 *
 * Formatting preservation: Docxtemplater performs replacement at the XML
 * <w:r> (run) level - the run that contained "#Client Name#" keeps its own
 * <w:rPr> (font, size, bold, italic, underline, color, highlight) and the
 * paragraph/table cell keeps its own <w:pPr>/table properties untouched.
 * Only the *text content* of the run changes, so the replacement text
 * automatically inherits every formatting property of the placeholder run,
 * satisfying the spec's formatting-preservation requirement without any
 * custom style-copying code.
 *
 * The template file itself is never opened in write mode / never mutated -
 * we read it into an in-memory zip, render, and write a NEW file at
 * outputFilePath. The master template on disk is untouched (Module 8).
 */
export function generateDocx(options: GenerationOptions): void {
  const { templateFilePath, values, imagePlaceholderNames, outputFilePath } = options;
  const content = fs.readFileSync(templateFilePath, 'binary');
  const zip = new PizZip(content);

  // docxtemplater-image-module-free normally only treats a tag as an image if its
  // content is prefixed with "%" in the document (e.g. "{%Signature}"). Our spec
  // requires the plain "#Signature#" syntax for every placeholder, image or text,
  // so we override tag classification via setParser: any tag whose name is in
  // imagePlaceholderNames is treated as an image tag, with no special authoring
  // syntax required from office staff preparing templates.
  const imageOpts = {
    centered: false,
    setParser(placeHolderContent: string) {
      if (imagePlaceholderNames.has(placeHolderContent)) {
        return {
          type: 'placeholder',
          value: placeHolderContent,
          module: 'open-xml-templating/docxtemplater-image-module',
          centered: false,
        };
      }
      return null; // fall through to normal text-tag handling
    },
    getImage(tagValue: string) {
      return fs.readFileSync(tagValue);
    },
    getSize(_img: Buffer, tagValue: string) {
      try {
        const dims = sizeOf(tagValue);
        // Cap very large source images to a sane width so they don't blow up the page;
        // maintain aspect ratio. 150pt ~ 200px at 96dpi is a reasonable signature/logo size.
        const maxWidth = 200;
        const w = dims.width || maxWidth;
        const h = dims.height || maxWidth;
        const scale = Math.min(1, maxWidth / w);
        return [Math.round(w * scale), Math.round(h * scale)];
      } catch {
        return [150, 80];
      }
    },
  };

  const doc = new Docxtemplater(zip, {
    paragraphLoop: true,
    linebreaks: true,
    delimiters: { start: '#', end: '#' },
    modules: [new ImageModule(imageOpts)],
  });

  // Build the render data. Text values: strip line breaks per spec
  // ("User input shall automatically remove line breaks. No automatic date
  // formatting shall occur - data appears exactly as entered.").
  const data: Record<string, string> = {};
  for (const [name, rawValue] of Object.entries(values)) {
    if (imagePlaceholderNames.has(name)) {
      data[name] = rawValue; // absolute path to image file, consumed by ImageModule
    } else {
      data[name] = String(rawValue ?? '').replace(/\r?\n/g, ' ');
    }
  }

  doc.render(data);

  const buffer = doc.getZip().generate({ type: 'nodebuffer', compression: 'DEFLATE' });
  fs.mkdirSync(path.dirname(outputFilePath), { recursive: true });
  fs.writeFileSync(outputFilePath, buffer);
}
