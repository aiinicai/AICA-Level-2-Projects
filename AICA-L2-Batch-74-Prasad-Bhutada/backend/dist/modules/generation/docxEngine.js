"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.generateDocx = generateDocx;
const fs_1 = __importDefault(require("fs"));
const path_1 = __importDefault(require("path"));
const pizzip_1 = __importDefault(require("pizzip"));
const docxtemplater_1 = __importDefault(require("docxtemplater"));
// @ts-ignore - no bundled types
const docxtemplater_image_module_free_1 = __importDefault(require("docxtemplater-image-module-free"));
const image_size_1 = __importDefault(require("image-size"));
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
function generateDocx(options) {
    const { templateFilePath, values, imagePlaceholderNames, outputFilePath } = options;
    const content = fs_1.default.readFileSync(templateFilePath, 'binary');
    const zip = new pizzip_1.default(content);
    // docxtemplater-image-module-free normally only treats a tag as an image if its
    // content is prefixed with "%" in the document (e.g. "{%Signature}"). Our spec
    // requires the plain "#Signature#" syntax for every placeholder, image or text,
    // so we override tag classification via setParser: any tag whose name is in
    // imagePlaceholderNames is treated as an image tag, with no special authoring
    // syntax required from office staff preparing templates.
    const imageOpts = {
        centered: false,
        setParser(placeHolderContent) {
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
        getImage(tagValue) {
            return fs_1.default.readFileSync(tagValue);
        },
        getSize(_img, tagValue) {
            try {
                const dims = (0, image_size_1.default)(tagValue);
                // Cap very large source images to a sane width so they don't blow up the page;
                // maintain aspect ratio. 150pt ~ 200px at 96dpi is a reasonable signature/logo size.
                const maxWidth = 200;
                const w = dims.width || maxWidth;
                const h = dims.height || maxWidth;
                const scale = Math.min(1, maxWidth / w);
                return [Math.round(w * scale), Math.round(h * scale)];
            }
            catch {
                return [150, 80];
            }
        },
    };
    const doc = new docxtemplater_1.default(zip, {
        paragraphLoop: true,
        linebreaks: true,
        delimiters: { start: '#', end: '#' },
        modules: [new docxtemplater_image_module_free_1.default(imageOpts)],
    });
    // Build the render data. Text values: strip line breaks per spec
    // ("User input shall automatically remove line breaks. No automatic date
    // formatting shall occur - data appears exactly as entered.").
    const data = {};
    for (const [name, rawValue] of Object.entries(values)) {
        if (imagePlaceholderNames.has(name)) {
            data[name] = rawValue; // absolute path to image file, consumed by ImageModule
        }
        else {
            data[name] = String(rawValue ?? '').replace(/\r?\n/g, ' ');
        }
    }
    doc.render(data);
    const buffer = doc.getZip().generate({ type: 'nodebuffer', compression: 'DEFLATE' });
    fs_1.default.mkdirSync(path_1.default.dirname(outputFilePath), { recursive: true });
    fs_1.default.writeFileSync(outputFilePath, buffer);
}
//# sourceMappingURL=docxEngine.js.map