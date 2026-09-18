import {
  Document,
  Paragraph,
  TextRun,
  HeadingLevel,
  Packer,
  Table,
  TableRow,
  TableCell,
  WidthType,
  BorderStyle,
  ShadingType,
  AlignmentType,
} from 'docx';
import pptxgen from 'pptxgenjs';

/**
 * Parses inline Markdown (bold **text**, italics *text*, code `code`, citations [1]) into docx TextRuns.
 */
function parseInlineRuns(
  text: string,
  baseOptions: { bold?: boolean; italics?: boolean; color?: string; size?: number } = {}
): TextRun[] {
  const runs: TextRun[] = [];
  // Tokenize bold **...**, code `...`, citation [1], [2], or normal text
  const tokens = text.split(/(\*\*[^*]+\*\*|`[^`]+`|\[\d+\])/g);

  for (const token of tokens) {
    if (!token) continue;

    if (token.startsWith('**') && token.endsWith('**') && token.length > 4) {
      runs.push(
        new TextRun({
          text: token.slice(2, -2),
          bold: true,
          color: baseOptions.color || '0F172A',
          size: baseOptions.size || 21, // 10.5 pt
        })
      );
    } else if (token.startsWith('`') && token.endsWith('`') && token.length > 2) {
      runs.push(
        new TextRun({
          text: token.slice(1, -1),
          font: 'Courier New',
          color: '2563EB',
          size: (baseOptions.size || 21) - 2,
        })
      );
    } else if (/^\[\d+\]$/.test(token)) {
      runs.push(
        new TextRun({
          text: ` ${token}`,
          bold: true,
          color: '1D4ED8', // Grounded citation blue
          size: (baseOptions.size || 21) - 2,
        })
      );
    } else {
      runs.push(
        new TextRun({
          text: token,
          bold: baseOptions.bold || false,
          italics: baseOptions.italics || false,
          color: baseOptions.color || '334155',
          size: baseOptions.size || 21,
        })
      );
    }
  }

  return runs.length > 0 ? runs : [new TextRun({ text, ...baseOptions })];
}

/**
 * Generates a polished Word (.docx) file from Markdown text and initiates download in the browser.
 */
export async function generateDocxBrowser(markdownContent: string, title: string = 'Document Synthesis') {
  const docChildren: any[] = [];

  // Clean document title
  const displayTitle = title.replace(/^#+\s*/, '').replace(/[*_`]/g, '').trim() || 'Grounded Analysis Document';

  // Title Header
  docChildren.push(
    new Paragraph({
      text: displayTitle,
      heading: HeadingLevel.TITLE,
      spacing: { before: 100, after: 120 },
    })
  );

  // Subtitle / metadata
  docChildren.push(
    new Paragraph({
      children: [
        new TextRun({
          text: `Offline NotebookLM Studio • Grounded Synthesis Export • ${new Date().toLocaleDateString('en-US', {
            month: 'long',
            day: 'numeric',
            year: 'numeric',
          })} at ${new Date().toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}`,
          italics: true,
          color: '64748B',
          size: 18, // 9 pt
        }),
      ],
      spacing: { after: 320 },
    })
  );

  const lines = markdownContent.split('\n');
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();

    // 1. Empty lines
    if (!trimmed) {
      i++;
      continue;
    }

    // 2. Code blocks (```)
    if (trimmed.startsWith('```')) {
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith('```')) {
        codeLines.push(lines[i]);
        i++;
      }
      i++; // Skip closing ```

      docChildren.push(
        new Table({
          width: { size: 100, type: WidthType.PERCENTAGE },
          rows: [
            new TableRow({
              children: [
                new TableCell({
                  shading: { fill: 'F8FAFC', type: ShadingType.CLEAR },
                  children: [
                    new Paragraph({
                      children: [
                        new TextRun({
                          text: codeLines.join('\n'),
                          font: 'Courier New',
                          size: 18,
                          color: '334155',
                        }),
                      ],
                    }),
                  ],
                }),
              ],
            }),
          ],
        })
      );
      docChildren.push(new Paragraph({ text: '', spacing: { after: 120 } }));
      continue;
    }

    // 3. Markdown Tables (| Col 1 | Col 2 |)
    if (trimmed.startsWith('|') && trimmed.endsWith('|') && trimmed.includes('|')) {
      const tableLines: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith('|') && lines[i].trim().endsWith('|')) {
        tableLines.push(lines[i].trim());
        i++;
      }

      if (tableLines.length > 0) {
        // Parse rows
        const rawRows = tableLines.filter((tl) => !/^[\|\s\-:]+$/.test(tl));
        const tableRows: TableRow[] = [];

        rawRows.forEach((rLine, rIdx) => {
          const cells = rLine
            .split('|')
            .slice(1, -1)
            .map((c) => c.trim());

          const isHeader = rIdx === 0;

          tableRows.push(
            new TableRow({
              tableHeader: isHeader,
              children: cells.map(
                (cellText) =>
                  new TableCell({
                    shading: isHeader
                      ? { fill: 'F1F5F9', type: ShadingType.CLEAR }
                      : rIdx % 2 === 1
                      ? { fill: 'FFFFFF', type: ShadingType.CLEAR }
                      : { fill: 'FAFAFA', type: ShadingType.CLEAR },
                    children: [
                      new Paragraph({
                        children: parseInlineRuns(cellText, {
                          bold: isHeader,
                          color: isHeader ? '0F172A' : '334155',
                          size: isHeader ? 19 : 18,
                        }),
                        alignment: isHeader ? AlignmentType.LEFT : AlignmentType.LEFT,
                        spacing: { before: 60, after: 60 },
                      }),
                    ],
                  })
              ),
            })
          );
        });

        if (tableRows.length > 0) {
          docChildren.push(
            new Table({
              width: { size: 100, type: WidthType.PERCENTAGE },
              borders: {
                top: { style: BorderStyle.SINGLE, size: 1, color: 'CBD5E1' },
                bottom: { style: BorderStyle.SINGLE, size: 1, color: 'CBD5E1' },
                left: { style: BorderStyle.SINGLE, size: 1, color: 'CBD5E1' },
                right: { style: BorderStyle.SINGLE, size: 1, color: 'CBD5E1' },
                insideHorizontal: { style: BorderStyle.SINGLE, size: 1, color: 'E2E8F0' },
                insideVertical: { style: BorderStyle.SINGLE, size: 1, color: 'E2E8F0' },
              },
              rows: tableRows,
            })
          );
          docChildren.push(new Paragraph({ text: '', spacing: { after: 140 } }));
        }
      }
      continue;
    }

    // 4. Headers (#, ##, ###, ####)
    if (trimmed.startsWith('# ')) {
      docChildren.push(
        new Paragraph({
          children: parseInlineRuns(trimmed.replace(/^#\s+/, ''), { bold: true, color: '0F172A', size: 28 }),
          heading: HeadingLevel.HEADING_1,
          spacing: { before: 240, after: 100 },
        })
      );
      i++;
      continue;
    }

    if (trimmed.startsWith('## ')) {
      docChildren.push(
        new Paragraph({
          children: parseInlineRuns(trimmed.replace(/^##\s+/, ''), { bold: true, color: '1E293B', size: 24 }),
          heading: HeadingLevel.HEADING_2,
          spacing: { before: 200, after: 80 },
        })
      );
      i++;
      continue;
    }

    if (trimmed.startsWith('### ')) {
      docChildren.push(
        new Paragraph({
          children: parseInlineRuns(trimmed.replace(/^###\s+/, ''), { bold: true, color: '334155', size: 22 }),
          heading: HeadingLevel.HEADING_3,
          spacing: { before: 160, after: 60 },
        })
      );
      i++;
      continue;
    }

    if (trimmed.startsWith('#### ')) {
      docChildren.push(
        new Paragraph({
          children: parseInlineRuns(trimmed.replace(/^####\s+/, ''), { bold: true, color: '475569', size: 20 }),
          heading: HeadingLevel.HEADING_4,
          spacing: { before: 120, after: 40 },
        })
      );
      i++;
      continue;
    }

    // 5. Blockquotes (>)
    if (trimmed.startsWith('>')) {
      docChildren.push(
        new Paragraph({
          children: parseInlineRuns(trimmed.replace(/^>\s*/, ''), {
            italics: true,
            color: '475569',
          }),
          spacing: { before: 80, after: 80 },
          indent: { left: 400 },
        })
      );
      i++;
      continue;
    }

    // 6. Horizontal Rules (---, ***)
    if (/^[-*_]{3,}$/.test(trimmed)) {
      docChildren.push(
        new Paragraph({
          text: '',
          border: {
            bottom: { style: BorderStyle.SINGLE, size: 1, color: 'E2E8F0' },
          },
          spacing: { before: 140, after: 140 },
        })
      );
      i++;
      continue;
    }

    // 7. Bullet Lists (•, -, *, +)
    if (/^([•\-*+]|\d+\.)\s+/.test(trimmed)) {
      const isNumbered = /^\d+\.\s+/.test(trimmed);
      const cleanText = trimmed.replace(/^([•\-*+]|\d+\.)\s+/, '');
      const indentLevel = line.search(/\S/) >= 4 ? 1 : 0;

      docChildren.push(
        new Paragraph({
          children: parseInlineRuns(cleanText),
          bullet: isNumbered ? undefined : { level: indentLevel },
          spacing: { before: 40, after: 40 },
        })
      );
      i++;
      continue;
    }

    // 8. Standard Paragraph with bold / citation runs
    docChildren.push(
      new Paragraph({
        children: parseInlineRuns(trimmed),
        spacing: { before: 40, after: 120 },
      })
    );
    i++;
  }

  const doc = new Document({
    sections: [
      {
        properties: {},
        children: docChildren,
      },
    ],
  });

  const blob = await Packer.toBlob(doc);
  const cleanFilename = displayTitle.toLowerCase().replace(/[^a-z0-9_-]/g, '_').slice(0, 50) + '.docx';

  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = cleanFilename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

/**
 * Generates a styled 16:9 PowerPoint (.pptx) file using pptxgenjs and downloads in browser.
 */
export async function generatePptxBrowser(markdownContent: string, title: string = 'Executive Presentation') {
  const pptx = new pptxgen();
  pptx.layout = 'LAYOUT_16x9';

  const displayTitle = title.replace(/^#+\s*/, '').replace(/[*_`]/g, '').trim() || 'Grounded Analysis Deck';

  // 1. Title Slide
  const titleSlide = pptx.addSlide();
  titleSlide.background = { color: '0F172A' }; // Dark Slate 900

  // Category Tag
  titleSlide.addText('OFFLINE NOTEBOOKLM STUDIO', {
    x: 1.0,
    y: 1.8,
    w: 10.0,
    h: 0.4,
    fontSize: 12,
    bold: true,
    color: '38BDF8', // Sky 400
    fontFace: 'Arial',
  });

  // Main Title
  titleSlide.addText(displayTitle, {
    x: 1.0,
    y: 2.3,
    w: 11.3,
    h: 1.8,
    fontSize: 30,
    bold: true,
    color: 'FFFFFF',
    fontFace: 'Arial',
    valign: 'top',
  });

  // Subtitle
  titleSlide.addText(
    `Grounded Intelligence & Document Synthesis • ${new Date().toLocaleDateString('en-US', {
      month: 'long',
      year: 'numeric',
    })}`,
    {
      x: 1.0,
      y: 4.3,
      w: 10.0,
      h: 0.5,
      fontSize: 14,
      color: '94A3B8',
      fontFace: 'Arial',
    }
  );

  // 2. Parse Markdown for Slide Sections
  const lines = markdownContent.split('\n');
  const slideSections: { title: string; bullets: string[] }[] = [];
  let currentTitle = '';
  let currentBullets: string[] = [];

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('|') || /^[\|\s\-:]+$/.test(trimmed)) continue;

    if (trimmed.startsWith('# ') || trimmed.startsWith('## ')) {
      if (currentTitle || currentBullets.length > 0) {
        slideSections.push({
          title: currentTitle || 'Key Findings & Analysis',
          bullets: currentBullets.length > 0 ? currentBullets : ['Analysis overview'],
        });
      }
      currentTitle = trimmed.replace(/^#+\s*/, '');
      currentBullets = [];
    } else if (trimmed.startsWith('### ')) {
      if (!currentTitle) {
        currentTitle = trimmed.replace(/^#+\s*/, '');
      } else {
        currentBullets.push(trimmed.replace(/^#+\s*/, ''));
      }
    } else if (/^([•\-*+]|\d+\.)\s+/.test(trimmed)) {
      currentBullets.push(trimmed.replace(/^([•\-*+]|\d+\.)\s+/, '').replace(/\*\*/g, ''));
    } else if (trimmed.startsWith('>')) {
      currentBullets.push('Note: ' + trimmed.replace(/^>\s*/, ''));
    } else if (trimmed.length > 10 && !trimmed.startsWith('---')) {
      currentBullets.push(trimmed.replace(/\*\*/g, ''));
    }
  }

  if (currentTitle || currentBullets.length > 0) {
    slideSections.push({
      title: currentTitle || 'Executive Summary',
      bullets: currentBullets.length > 0 ? currentBullets : ['Synthesis complete.'],
    });
  }

  if (slideSections.length === 0) {
    slideSections.push({
      title: displayTitle,
      bullets: ['Complete document synthesis extracted.'],
    });
  }

  // 3. Create Content Slides
  slideSections.forEach((section, idx) => {
    const slide = pptx.addSlide();
    slide.background = { color: 'F8FAFC' }; // Slate 50

    // White Card Shape
    slide.addShape(pptx.ShapeType.roundRect, {
      x: 0.8,
      y: 0.6,
      w: 11.7,
      h: 6.2,
      fill: { color: 'FFFFFF' },
      line: { color: 'E2E8F0', width: 1 },
      rectRadius: 0.15,
    });

    // Slide Title
    slide.addText(section.title, {
      x: 1.2,
      y: 0.9,
      w: 10.5,
      h: 0.8,
      fontSize: 22,
      bold: true,
      color: '0F172A',
      fontFace: 'Arial',
    });

    // Accent line
    slide.addShape(pptx.ShapeType.rect, {
      x: 1.2,
      y: 1.7,
      w: 2.2,
      h: 0.04,
      fill: { color: '0284C7' }, // Sky 600
      line: { color: '0284C7' },
    });

    // Slide Bullets
    const bulletsToShow = section.bullets.slice(0, 6).map((b) => ({
      text: b,
      options: {
        fontSize: 14,
        color: '334155',
        fontFace: 'Arial',
        bullet: true,
        paraSpaceAfter: 14,
      },
    }));

    if (bulletsToShow.length > 0) {
      slide.addText(bulletsToShow, {
        x: 1.2,
        y: 1.9,
        w: 10.5,
        h: 4.2,
        valign: 'top',
      });
    }

    // Slide Number Footer
    slide.addText(`Slide ${idx + 2} of ${slideSections.length + 1}`, {
      x: 9.8,
      y: 6.2,
      w: 2.2,
      h: 0.4,
      fontSize: 10,
      color: '94A3B8',
      align: 'right',
      fontFace: 'Arial',
    });
  });

  const cleanFilename = displayTitle.toLowerCase().replace(/[^a-z0-9_-]/g, '_').slice(0, 50) + '.pptx';
  await pptx.writeFile({ fileName: cleanFilename });
}

