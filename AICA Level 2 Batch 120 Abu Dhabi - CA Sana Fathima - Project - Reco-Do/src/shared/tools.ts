export type ToolId = 'pdf-to-excel' | 'excel-to-pdf' | 'merge-pdfs' | 'split-pdf' | 'merge-files' | 'data-cleaner'

export interface ToolConfig {
  id: ToolId
  name: string
  description: string
  /** Icon tile colours: foreground and soft background. */
  fg: string
  bg: string
}

export const TOOLS: ToolConfig[] = [
  {
    id: 'pdf-to-excel',
    name: 'PDF → Excel',
    description: 'Digital or scanned PDFs to formatted Excel. Raw tables or bank-statement layout. OCR built in.',
    fg: '#11865F',
    bg: '#E3F4EC'
  },
  {
    id: 'excel-to-pdf',
    name: 'Excel → PDF',
    description: 'Print-ready PDF from any sheet: repeated headers, totals, page numbers, fit to width.',
    fg: '#C0292B',
    bg: '#FDECEC'
  },
  {
    id: 'merge-pdfs',
    name: 'Merge PDFs',
    description: 'Combine several PDFs into one. Drag to reorder files and pages, remove pages.',
    fg: '#1D6FD8',
    bg: '#E6F0FC'
  },
  {
    id: 'split-pdf',
    name: 'Split PDF',
    description: 'Split by page ranges, every N pages, or extract selected pages into a new file.',
    fg: '#A86B00',
    bg: '#FDF1DC'
  },
  {
    id: 'merge-files',
    name: 'Merge Files',
    description: 'Stack many Excel / CSV / PDF statements into one sheet, with a "Source file" column.',
    fg: '#5A43D6',
    bg: '#ECE8FC'
  },
  {
    id: 'data-cleaner',
    name: 'Data Cleaner',
    description: 'Remove junk and total rows, fix text dates and numbers, split Dr/Cr, trim spaces.',
    fg: '#1E8E72',
    bg: '#E2F6F1'
  }
]

export function getTool(id: string): ToolConfig | undefined {
  return TOOLS.find((t) => t.id === id)
}
