"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const fs_1 = __importDefault(require("fs"));
const os_1 = __importDefault(require("os"));
const path_1 = __importDefault(require("path"));
const pizzip_1 = __importDefault(require("pizzip"));
const docxtemplater_1 = __importDefault(require("docxtemplater"));
const docxEngine_1 = require("../modules/generation/docxEngine");
const FIXTURES = path_1.default.join(__dirname, 'fixtures');
function readGeneratedText(filePath) {
    const content = fs_1.default.readFileSync(filePath, 'binary');
    const zip = new pizzip_1.default(content);
    const doc = new docxtemplater_1.default(zip, { paragraphLoop: true, linebreaks: true });
    return doc.getFullText();
}
describe('generateDocx', () => {
    const outDir = fs_1.default.mkdtempSync(path_1.default.join(os_1.default.tmpdir(), 'cadocs-test-'));
    afterAll(() => {
        fs_1.default.rmSync(outDir, { recursive: true, force: true });
    });
    it('replaces text placeholders and never mutates the master template', () => {
        const templatePath = path_1.default.join(FIXTURES, 'Engagement Letter.docx');
        const originalBytes = fs_1.default.readFileSync(templatePath);
        const outPath = path_1.default.join(outDir, 'out1.docx');
        (0, docxEngine_1.generateDocx)({
            templateFilePath: templatePath,
            values: {
                'Client Name': 'Test Client Pvt Ltd',
                Date: '06/08/2026',
                Address: '1 Test Street',
                PAN: 'ABCDE1234F',
                GSTIN: '29ABCDE1234F1Z5',
                'Contact Mobile': '9999999999',
                'Contact Email': 'test@example.com',
                'Scope Of Services': 'Testing',
                'Fee Structure': 'Rs. 1',
                'Partner Name': 'CA Test',
                'Firm Name': 'Test & Co',
                'Engagement Ref': 'REF-1',
            },
            imagePlaceholderNames: new Set(['Signature']),
            outputFilePath: outPath,
        });
        // Master template untouched
        expect(fs_1.default.readFileSync(templatePath).equals(originalBytes)).toBe(true);
        // Output contains replaced values and no leftover placeholder markers
        const text = readGeneratedText(outPath);
        expect(text).toContain('Test Client Pvt Ltd');
        expect(text).not.toMatch(/#Client Name#/);
        expect(text).not.toMatch(/#Date#/);
    });
    it('replaces an image placeholder with an actual embedded image', () => {
        const templatePath = path_1.default.join(FIXTURES, 'Engagement Letter.docx');
        const outPath = path_1.default.join(outDir, 'out2.docx');
        (0, docxEngine_1.generateDocx)({
            templateFilePath: templatePath,
            values: {
                'Client Name': 'Test Client',
                Date: '06/08/2026',
                Address: 'Addr',
                PAN: 'ABCDE1234F',
                GSTIN: '29ABCDE1234F1Z5',
                'Contact Mobile': '9999999999',
                'Contact Email': 'test@example.com',
                'Scope Of Services': 'Testing',
                'Fee Structure': 'Rs. 1',
                'Partner Name': 'CA Test',
                'Firm Name': 'Test & Co',
                'Engagement Ref': 'REF-1',
                Signature: path_1.default.join(FIXTURES, 'signature.png'),
            },
            imagePlaceholderNames: new Set(['Signature']),
            outputFilePath: outPath,
        });
        const content = fs_1.default.readFileSync(outPath, 'binary');
        const zip = new pizzip_1.default(content);
        // A real image should have been embedded into word/media
        const mediaFiles = Object.keys(zip.files).filter((f) => f.startsWith('word/media/'));
        expect(mediaFiles.length).toBeGreaterThan(0);
        // The literal placeholder text should be gone from the document body
        const text = readGeneratedText(outPath);
        expect(text).not.toContain('signature.png');
    });
    it('strips line breaks from user-entered text values', () => {
        const templatePath = path_1.default.join(FIXTURES, 'Engagement Letter.docx');
        const outPath = path_1.default.join(outDir, 'out3.docx');
        (0, docxEngine_1.generateDocx)({
            templateFilePath: templatePath,
            values: {
                'Client Name': 'Line1\nLine2',
                Date: '06/08/2026',
                Address: 'Addr',
                PAN: 'ABCDE1234F',
                GSTIN: '29ABCDE1234F1Z5',
                'Contact Mobile': '9999999999',
                'Contact Email': 'test@example.com',
                'Scope Of Services': 'Testing',
                'Fee Structure': 'Rs. 1',
                'Partner Name': 'CA Test',
                'Firm Name': 'Test & Co',
                'Engagement Ref': 'REF-1',
            },
            imagePlaceholderNames: new Set(['Signature']),
            outputFilePath: outPath,
        });
        const text = readGeneratedText(outPath);
        expect(text).toContain('Line1 Line2');
        expect(text).not.toContain('Line1\nLine2');
    });
});
//# sourceMappingURL=docxEngine.test.js.map