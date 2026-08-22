"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const path_1 = __importDefault(require("path"));
const placeholderParser_1 = require("../modules/templates/placeholderParser");
const FIXTURES = path_1.default.join(__dirname, 'fixtures');
describe('detectPlaceholders', () => {
    it('detects placeholders across body, table, header and footer', () => {
        const found = (0, placeholderParser_1.detectPlaceholders)(path_1.default.join(FIXTURES, 'Engagement Letter.docx'));
        const names = found.map((f) => f.name).sort();
        expect(names).toEqual([
            'Address',
            'Client Name',
            'Contact Email',
            'Contact Mobile',
            'Date',
            'Engagement Ref', // footer
            'Fee Structure', // table
            'Firm Name', // header
            'GSTIN',
            'PAN',
            'Partner Name',
            'Scope Of Services', // table
            'Signature', // image
        ].sort());
    });
    it('flags reserved image placeholder names as isImage', () => {
        const found = (0, placeholderParser_1.detectPlaceholders)(path_1.default.join(FIXTURES, 'Engagement Letter.docx'));
        const signature = found.find((f) => f.name === 'Signature');
        expect(signature?.isImage).toBe(true);
        const clientName = found.find((f) => f.name === 'Client Name');
        expect(clientName?.isImage).toBe(false);
    });
    it('deduplicates repeated placeholders', () => {
        // "Client Name" appears twice in the Certificate template body
        const found = (0, placeholderParser_1.detectPlaceholders)(path_1.default.join(FIXTURES, 'Certificate of Due Diligence.docx'));
        const clientNameOccurrences = found.filter((f) => f.name === 'Client Name');
        expect(clientNameOccurrences).toHaveLength(1);
    });
    it('detects both Logo and Signature as image placeholders', () => {
        const found = (0, placeholderParser_1.detectPlaceholders)(path_1.default.join(FIXTURES, 'Certificate of Due Diligence.docx'));
        expect(found.find((f) => f.name === 'Logo')?.isImage).toBe(true);
        expect(found.find((f) => f.name === 'Signature')?.isImage).toBe(true);
    });
});
//# sourceMappingURL=placeholderParser.test.js.map