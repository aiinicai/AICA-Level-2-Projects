import fs from 'fs';
import os from 'os';
import path from 'path';
import PizZip from 'pizzip';
import Docxtemplater from 'docxtemplater';
import { generateDocx } from '../modules/generation/docxEngine';

const FIXTURES = path.join(__dirname, 'fixtures');

function readGeneratedText(filePath: string): string {
  const content = fs.readFileSync(filePath, 'binary');
  const zip = new PizZip(content);
  const doc = new Docxtemplater(zip, { paragraphLoop: true, linebreaks: true });
  return (doc as any).getFullText();
}

describe('generateDocx', () => {
  const outDir = fs.mkdtempSync(path.join(os.tmpdir(), 'cadocs-test-'));

  afterAll(() => {
    fs.rmSync(outDir, { recursive: true, force: true });
  });

  it('replaces text placeholders and never mutates the master template', () => {
    const templatePath = path.join(FIXTURES, 'Engagement Letter.docx');
    const originalBytes = fs.readFileSync(templatePath);
    const outPath = path.join(outDir, 'out1.docx');

    generateDocx({
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
    expect(fs.readFileSync(templatePath).equals(originalBytes)).toBe(true);

    // Output contains replaced values and no leftover placeholder markers
    const text = readGeneratedText(outPath);
    expect(text).toContain('Test Client Pvt Ltd');
    expect(text).not.toMatch(/#Client Name#/);
    expect(text).not.toMatch(/#Date#/);
  });

  it('replaces an image placeholder with an actual embedded image', () => {
    const templatePath = path.join(FIXTURES, 'Engagement Letter.docx');
    const outPath = path.join(outDir, 'out2.docx');

    generateDocx({
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
        Signature: path.join(FIXTURES, 'signature.png'),
      },
      imagePlaceholderNames: new Set(['Signature']),
      outputFilePath: outPath,
    });

    const content = fs.readFileSync(outPath, 'binary');
    const zip = new PizZip(content);
    // A real image should have been embedded into word/media
    const mediaFiles = Object.keys(zip.files).filter((f) => f.startsWith('word/media/'));
    expect(mediaFiles.length).toBeGreaterThan(0);

    // The literal placeholder text should be gone from the document body
    const text = readGeneratedText(outPath);
    expect(text).not.toContain('signature.png');
  });

  it('strips line breaks from user-entered text values', () => {
    const templatePath = path.join(FIXTURES, 'Engagement Letter.docx');
    const outPath = path.join(outDir, 'out3.docx');

    generateDocx({
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
