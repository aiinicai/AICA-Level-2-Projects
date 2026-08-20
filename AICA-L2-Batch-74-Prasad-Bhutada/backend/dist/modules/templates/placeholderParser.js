"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.detectPlaceholders = detectPlaceholders;
const fs_1 = __importDefault(require("fs"));
const pizzip_1 = __importDefault(require("pizzip"));
const docxtemplater_1 = __importDefault(require("docxtemplater"));
/**
 * Detects every #Placeholder# occurrence in a .docx file.
 *
 * Why Docxtemplater's internal XML text model instead of naive regex-on-XML:
 * Microsoft Word frequently splits a single visual word across multiple
 * <w:r> (run) elements internally (e.g. for spellcheck markers, or when a
 * user paused mid-typing). A raw regex over document.xml would miss a
 * placeholder split across runs. Docxtemplater's `getFullText()` resolves
 * the OOXML tree per part (document body, each header, each footer, and
 * any nested text boxes/shapes contained in that part's XML) into flat,
 * already-concatenated text, which is exactly what we need for reliable
 * detection - and guarantees whatever we detect is also exactly what the
 * generation engine (docxEngine.ts), built on the same library, can replace.
 *
 * Known limitation (documented, matches "where technically feasible" in the
 * spec): placeholder text embedded inside SmartArt diagram data or inside
 * an image's alt-text is not scanned, since that content lives in separate
 * drawingml/diagram XML parts outside Docxtemplater's text model. Ordinary
 * text boxes and shapes ARE covered because their XML is nested inside the
 * same part (document.xml / header*.xml / footer*.xml).
 */
const PLACEHOLDER_REGEX = /#([^#\r\n]{1,80}?)#/g;
const IMAGE_PLACEHOLDER_NAMES = new Set(['signature', 'logo', 'photograph', 'photo']);
function detectPlaceholders(filePath) {
    const content = fs_1.default.readFileSync(filePath, 'binary');
    const zip = new pizzip_1.default(content);
    const doc = new docxtemplater_1.default(zip, {
        paragraphLoop: true,
        linebreaks: true,
        delimiters: { start: '#', end: '#' },
    });
    const foundNames = new Set();
    // Collect every XML part that can contain visible text: main body,
    // every header, every footer. (Text boxes/shapes are nested inside these.)
    const zipFiles = Object.keys(zip.files).filter((name) => name === 'word/document.xml' ||
        /^word\/header\d*\.xml$/.test(name) ||
        /^word\/footer\d*\.xml$/.test(name));
    for (const part of zipFiles) {
        let text;
        try {
            // getFullText(path) returns the flattened, run-merged plain text for that part
            text = doc.getFullText(part);
        }
        catch {
            continue; // part not resolvable (e.g. template has no headers/footers) - skip safely
        }
        let match;
        PLACEHOLDER_REGEX.lastIndex = 0;
        while ((match = PLACEHOLDER_REGEX.exec(text)) !== null) {
            const raw = match[1].trim();
            if (raw.length === 0)
                continue;
            foundNames.add(raw);
        }
    }
    return Array.from(foundNames).map((name) => ({
        name,
        isImage: IMAGE_PLACEHOLDER_NAMES.has(name.toLowerCase()),
    }));
}
//# sourceMappingURL=placeholderParser.js.map