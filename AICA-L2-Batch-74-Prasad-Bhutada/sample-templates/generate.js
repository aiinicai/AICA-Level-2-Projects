const fs = require('fs');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType,
  Header, Footer, AlignmentType, BorderStyle, HeadingLevel, ShadingType, VerticalAlign,
} = require('docx');

const PAGE = { size: { width: 12240, height: 15840 } }; // US Letter, DXA

function saveDoc(doc, filename) {
  return Packer.toBuffer(doc).then((buf) => fs.writeFileSync(filename, buf));
}

// ---------------------------------------------------------------------------
// 1. Engagement Letter - placeholders in body, a table, header AND footer.
// ---------------------------------------------------------------------------
const engagementLetter = new Document({
  sections: [
    {
      properties: { page: PAGE },
      headers: {
        default: new Header({
          children: [
            new Paragraph({
              alignment: AlignmentType.CENTER,
              children: [new TextRun({ text: '#Firm Name#', bold: true, size: 24, color: '1C3A80' })],
            }),
          ],
        }),
      },
      footers: {
        default: new Footer({
          children: [
            new Paragraph({
              alignment: AlignmentType.CENTER,
              children: [
                new TextRun({ text: 'Prepared for #Client Name# | Ref: #Engagement Ref#', size: 16, italics: true }),
              ],
            }),
          ],
        }),
      },
      children: [
        new Paragraph({ text: 'Engagement Letter', heading: HeadingLevel.TITLE, alignment: AlignmentType.CENTER }),
        new Paragraph({ text: '' }),
        new Paragraph({ children: [new TextRun('Date: '), new TextRun({ text: '#Date#', bold: true })] }),
        new Paragraph({ text: '' }),
        new Paragraph({
          children: [
            new TextRun('To,'),
          ],
        }),
        new Paragraph({ children: [new TextRun({ text: '#Client Name#', bold: true, size: 24 })] }),
        new Paragraph({ children: [new TextRun('#Address#')] }),
        new Paragraph({ text: '' }),
        new Paragraph({
          children: [
            new TextRun('Dear Sir/Madam,'),
          ],
        }),
        new Paragraph({ text: '' }),
        new Paragraph({
          children: [
            new TextRun(
              'This letter confirms our understanding of the terms and objectives of our engagement to provide professional services to ',
            ),
            new TextRun({ text: '#Client Name#', bold: true }),
            new TextRun(' (PAN: '),
            new TextRun({ text: '#PAN#', underline: {} }),
            new TextRun(', GSTIN: '),
            new TextRun({ text: '#GSTIN#', underline: {} }),
            new TextRun(').'),
          ],
        }),
        new Paragraph({ text: '' }),
        new Paragraph({
          children: [
            new TextRun('Our contact person for this engagement is available at '),
            new TextRun({ text: '#Contact Mobile#', color: '2F5FD8' }),
            new TextRun(' or '),
            new TextRun({ text: '#Contact Email#', color: '2F5FD8' }),
            new TextRun('.'),
          ],
        }),
        new Paragraph({ text: '' }),
        new Table({
          width: { size: 9350, type: WidthType.DXA },
          columnWidths: [4675, 4675],
          rows: [
            new TableRow({
              children: [
                cell('Scope of Services', 4675, true),
                cell('Fee Structure', 4675, true),
              ],
            }),
            new TableRow({
              children: [
                cell('#Scope Of Services#', 4675, false),
                cell('#Fee Structure#', 4675, false),
              ],
            }),
          ],
        }),
        new Paragraph({ text: '' }),
        new Paragraph({ children: [new TextRun('Yours faithfully,')] }),
        new Paragraph({ text: '' }),
        new Paragraph({ children: [new TextRun({ text: '#Signature#' })] }),
        new Paragraph({ children: [new TextRun({ text: '#Partner Name#', bold: true })] }),
      ],
    },
  ],
});

function cell(text, width, header) {
  return new TableCell({
    width: { size: width, type: WidthType.DXA },
    shading: header ? { type: ShadingType.CLEAR, fill: 'E8EEFB' } : undefined,
    verticalAlign: VerticalAlign.CENTER,
    children: [new Paragraph({ children: [new TextRun({ text, bold: header })] })],
  });
}

// ---------------------------------------------------------------------------
// 2. Certificate - centered, decorative, image (Logo + Signature) placeholders.
// ---------------------------------------------------------------------------
const certificate = new Document({
  sections: [
    {
      properties: { page: PAGE },
      children: [
        new Paragraph({ children: [new TextRun({ text: '#Logo#' })], alignment: AlignmentType.CENTER }),
        new Paragraph({ text: '' }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ text: 'CERTIFICATE', bold: true, size: 40, color: '1C3A80' })],
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ text: 'OF DUE DILIGENCE', bold: true, size: 24 })],
        }),
        new Paragraph({ text: '' }),
        new Paragraph({ text: '' }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [
            new TextRun('This is to certify that '),
            new TextRun({ text: '#Client Name#', bold: true, size: 26, highlight: 'yellow' }),
            new TextRun(', having its registered office at '),
            new TextRun({ text: '#Address#', italics: true }),
            new TextRun(
              ', has been examined by us and the records produced were found to be in order as on #Date#.',
            ),
          ],
        }),
        new Paragraph({ text: '' }),
        new Paragraph({ text: '' }),
        new Paragraph({
          alignment: AlignmentType.RIGHT,
          children: [new TextRun({ text: '#Signature#' })],
        }),
        new Paragraph({
          alignment: AlignmentType.RIGHT,
          children: [new TextRun({ text: '#Partner Name#', bold: true })],
        }),
        new Paragraph({
          alignment: AlignmentType.RIGHT,
          children: [new TextRun({ text: 'Membership No. #Membership Number#', size: 18 })],
        }),
      ],
    },
  ],
});

(async () => {
  await saveDoc(engagementLetter, 'Engagement Letter.docx');
  await saveDoc(certificate, 'Certificate of Due Diligence.docx');
  console.log('Sample templates generated.');
})();
