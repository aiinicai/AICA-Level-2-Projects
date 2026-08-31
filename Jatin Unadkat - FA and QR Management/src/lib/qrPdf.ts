import { PDFDocument, StandardFonts, rgb } from "pdf-lib";
import { renderQrPngBuffer } from "@/lib/qr";

const MM_TO_PT = 2.83465;
const PAGE_WIDTH = 595.28; // A4 portrait, points
const PAGE_HEIGHT = 841.89;
const PAGE_MARGIN = 24;
const LABEL_GAP = 10;
const TEXT_BLOCK_HEIGHT = 26; // room for asset number + description under the QR

export type LabelInput = {
  token: string;
  assetNumber: string;
  description: string;
  inventoryNumber?: string | null;
};

/**
 * Multiple labels per A4 page, sized for course-project scale — runs
 * synchronously in the request rather than a background worker (design
 * dossier, ADD11 scoping note).
 */
export async function buildLabelSheetPdf(labels: LabelInput[], sizeMm: number): Promise<Uint8Array> {
  const pdfDoc = await PDFDocument.create();
  const font = await pdfDoc.embedFont(StandardFonts.Helvetica);
  const boldFont = await pdfDoc.embedFont(StandardFonts.HelveticaBold);

  const cellSize = sizeMm * MM_TO_PT;
  const cellHeight = cellSize + TEXT_BLOCK_HEIGHT;
  const usableWidth = PAGE_WIDTH - PAGE_MARGIN * 2;
  const usableHeight = PAGE_HEIGHT - PAGE_MARGIN * 2;
  const cols = Math.max(1, Math.floor((usableWidth + LABEL_GAP) / (cellSize + LABEL_GAP)));
  const rows = Math.max(1, Math.floor((usableHeight + LABEL_GAP) / (cellHeight + LABEL_GAP)));
  const perPage = cols * rows;

  let page = pdfDoc.addPage([PAGE_WIDTH, PAGE_HEIGHT]);
  let indexOnPage = 0;

  for (const label of labels) {
    if (indexOnPage === perPage) {
      page = pdfDoc.addPage([PAGE_WIDTH, PAGE_HEIGHT]);
      indexOnPage = 0;
    }

    const col = indexOnPage % cols;
    const row = Math.floor(indexOnPage / cols);
    const x = PAGE_MARGIN + col * (cellSize + LABEL_GAP);
    const yTop = PAGE_HEIGHT - PAGE_MARGIN - row * (cellHeight + LABEL_GAP);
    const yQr = yTop - cellSize;

    const pngBytes = await renderQrPngBuffer(label.token, 300);
    const pngImage = await pdfDoc.embedPng(pngBytes);
    page.drawImage(pngImage, { x, y: yQr, width: cellSize, height: cellSize });

    const assetNumberSize = 8;
    page.drawText(label.assetNumber, {
      x,
      y: yQr - 12,
      size: assetNumberSize,
      font: boldFont,
      color: rgb(0.1, 0.1, 0.1),
      maxWidth: cellSize,
    });

    const truncatedDescription =
      label.description.length > 28 ? `${label.description.slice(0, 27)}…` : label.description;
    page.drawText(truncatedDescription, {
      x,
      y: yQr - 22,
      size: 6.5,
      font,
      color: rgb(0.35, 0.35, 0.35),
      maxWidth: cellSize,
    });

    indexOnPage += 1;
  }

  return pdfDoc.save();
}
