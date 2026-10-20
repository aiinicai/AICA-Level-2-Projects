// Regression tests for the tool review findings (P2, P3, P4, P8, P9, P10, P13, Q4, Q12, Q14, Q17, Q21b, R13, P5).
import ExcelJS from 'exceljs'
import { PDFDocument, StandardFonts, degrees } from 'pdf-lib'
import { describe, expect, it, vi } from 'vitest'
import type { CellValue, ParsedTable } from '@shared/contracts'
import {
  closePdfJsDocument,
  EDIT_PROTECTED_MESSAGE,
  loadEditablePdf,
  openPdfJsDocument,
  PASSWORD_MESSAGE,
  pdfProtection,
  ToolError,
  type PdfJsLib
} from '@tools/common'
import { sheetToPdfDetailed } from '@tools/excel-to-pdf'
import { mergePdfs } from '@tools/merge-pdfs'
import {
  assertLocalOcrAssets,
  createOcrEngine,
  extractPdf,
  isLocalAssetPath,
  OCR_ASSETS_MISSING_MESSAGE,
  tesseractLoader,
  toWorkbook,
  uniqueColumnNames
} from '@tools/pdf-to-excel'
import { MAX_SPLIT_NAME, splitFileName, splitPdf } from '@tools/split-pdf'
import { ownerProtectedPdf, STATEMENT_ROWS, STATEMENT_XS } from './encryptedPdf'
import { documentParams, nodeOcr, nodePdfjs, sample } from './helpers'

async function pdfText(data: Uint8Array): Promise<string> {
  const doc = await nodePdfjs.getDocument({ data: data.slice(), verbosity: 0 }).promise
  const tc = await (await doc.getPage(1)).getTextContent()
  const s = tc.items.map((it) => ('str' in it ? it.str : '')).filter((x) => x.trim() !== '').join(' | ')
  await doc.loadingTask.destroy()
  return s
}

function table(columns: string[], rows: CellValue[][]): ParsedTable {
  return {
    fileName: 'x.xlsx',
    sheetName: 'S',
    headerRowIndex: 0,
    columns,
    rows: rows.map((r, i) => ({ id: `r${i + 2}`, sourceRow: i + 1, values: Object.fromEntries(columns.map((c, k) => [c, r[k] ?? null])) })),
    excluded: [],
    openingBalance: null,
    closingBalance: null
  }
}

describe('Excel → PDF review fixes', () => {
  const t = table(
    ['Date', 'Description', 'Amount', 'Posted'],
    [
      ['03/09/2026', 'a', '500.00 DR', new Date(2026, 8, 3)],
      ['04/09/2026', 'b', '500.00 CR', new Date(2026, 8, 4)],
      ['05/09/2026', 'c', '100.00 CR', new Date(2026, 8, 5)]
    ]
  )

  it('P2: prints the CR/DR marker and totals with Dr added and Cr subtracted', async () => {
    const text = await pdfText(sheetToPdfDetailed(t, { totals: ['Amount'] }).data)
    expect(text).toContain('500.00 Dr')
    expect(text).toContain('500.00 Cr')
    expect(text).toMatch(/Total \| 100\.00 Cr/)
    expect(text).not.toContain('1,100.00')
  })

  it('P3: unformatted dates print the local calendar day (no shift to the previous day east of UTC)', async () => {
    const text = await pdfText(sheetToPdfDetailed(t, { keepFormatting: false }).data)
    expect(text).toContain('2026-09-03')
    expect(text).toContain('2026-09-05')
  })

  it('P8: checks the day/month order per date column and reports columns that read both ways', async () => {
    const ambiguous = sheetToPdfDetailed(t, {})
    expect(ambiguous.ambiguousDateColumns).toEqual(['Date'])
    expect(await pdfText(ambiguous.data)).toContain('03-Sep-2026')
    const mdy = sheetToPdfDetailed(t, { dateOrder: 'MDY' })
    expect(await pdfText(mdy.data)).toContain('09-Mar-2026')
    const decided = table(['Date', 'X'], [['09/13/2026', 'a'], ['09/03/2026', 'b']])
    const r = sheetToPdfDetailed(decided, {})
    expect(r.ambiguousDateColumns).toEqual([])
    expect(await pdfText(r.data)).toContain('03-Sep-2026')
  })

  it('Q14: totals a decimal-comma column correctly ("1.234" is one thousand two hundred and thirty-four)', async () => {
    const eu = table(['Item', 'Amount'], [['a', '1.234,56'], ['b', '1.234'], ['c', '12,50']])
    const text = await pdfText(sheetToPdfDetailed(eu, { totals: ['Amount'], columnTypes: { Amount: 'amount' } }).data)
    expect(text).toContain('1,234.00')
    expect(text).toMatch(/Total \| 2,481\.06/)
  })
})

describe('PDF protection (P4)', () => {
  const texts = STATEMENT_ROWS.flatMap((row, r) => row.map((text, c) => ({ text, x: STATEMENT_XS[c], y: 780 - r * 14 })).filter((x) => x.text !== ''))
  const pdf = ownerProtectedPdf(texts)

  it('opens an owner-password-only PDF with pdf.js and converts it to Excel', async () => {
    expect(await pdfProtection(pdf, nodePdfjs)).toBe('edit-only')
    const r = await extractPdf(pdf, { pdfjs: nodePdfjs, fileName: 'protected.pdf' })
    expect(r.tables[0].rows).toHaveLength(3)
    expect(r.tables[0].columns.map((c) => c.name)).toEqual(['Date', 'Description', 'Debit', 'Credit', 'Balance'])
  })

  it('Merge / Split say "protected against editing" instead of asking for a password', async () => {
    await expect(loadEditablePdf(pdf, undefined, nodePdfjs)).rejects.toThrow(EDIT_PROTECTED_MESSAGE)
    await expect(splitPdf(pdf, { mode: 'single' }, { pdfjs: nodePdfjs })).rejects.toMatchObject({ code: 'edit-protected' })
    await expect(mergePdfs([{ name: 'p.pdf', data: pdf }], { pdfjs: nodePdfjs })).rejects.toThrow(`p.pdf: ${EDIT_PROTECTED_MESSAGE}`)
    // A PDF that needs a password to open keeps the password message.
    await expect(loadEditablePdf(sample('Password_protected.pdf'), undefined, nodePdfjs)).rejects.toThrow(PASSWORD_MESSAGE)
  })
})

describe('pdf.js document lifetime (P9)', () => {
  function fakeLib(promise: Promise<unknown>): { lib: PdfJsLib; destroy: ReturnType<typeof vi.fn> } {
    const destroy = vi.fn(async () => undefined)
    const lib = { getDocument: () => ({ promise, destroy }), VerbosityLevel: nodePdfjs.VerbosityLevel } as unknown as PdfJsLib
    return { lib, destroy }
  }

  it('destroys the loading task when the file fails to open', async () => {
    const err = Object.assign(new Error('Invalid PDF structure.'), { name: 'InvalidPDFException' })
    const { lib, destroy } = fakeLib(Promise.reject(err))
    await expect(openPdfJsDocument(new Uint8Array([1, 2, 3]), { pdfjs: lib })).rejects.toMatchObject({ code: 'invalid-pdf' })
    expect(destroy).toHaveBeenCalledTimes(1)
  })

  it('destroys the document when the job is cancelled while it opens', async () => {
    const ctrl = new AbortController()
    const { lib, destroy } = fakeLib(
      new Promise((resolve) =>
        setTimeout(() => {
          ctrl.abort()
          resolve({ numPages: 1 })
        }, 0)
      )
    )
    await expect(openPdfJsDocument(new Uint8Array([1]), { pdfjs: lib }, ctrl.signal)).rejects.toMatchObject({ code: 'cancelled' })
    expect(destroy).toHaveBeenCalledTimes(1)
  })

  it('still opens and closes real files', async () => {
    const doc = await openPdfJsDocument(sample('Split_Me_12_pages.pdf'), { pdfjs: nodePdfjs })
    expect(doc.numPages).toBe(12)
    await closePdfJsDocument(doc)
  })
})

describe('OCR engine set-up (P10, R13, Q21b)', () => {
  it('R13: refuses to start without explicit local worker, core and language paths', async () => {
    expect(isLocalAssetPath('C:\\Program Files\\Reco-Do\\ocr\\worker.min.js')).toBe(true)
    expect(isLocalAssetPath('/opt/reco-do/ocr/lang')).toBe(true)
    expect(isLocalAssetPath('app://reco-do/ocr/core')).toBe(true)
    expect(isLocalAssetPath('http://localhost:5173/ocr/lang')).toBe(true)
    expect(isLocalAssetPath('https://cdn.jsdelivr.net/npm/tesseract.js@7/dist/worker.min.js')).toBe(false)
    expect(isLocalAssetPath('')).toBe(false)
    expect(() => assertLocalOcrAssets({ ...nodeOcr, workerPath: undefined as unknown as string })).toThrow(OCR_ASSETS_MISSING_MESSAGE)
    await expect(createOcrEngine({ ...nodeOcr, langPath: 'https://tessdata.projectnaptha.com/4.0.0' })).rejects.toMatchObject({
      code: 'ocr-failed',
      message: OCR_ASSETS_MISSING_MESSAGE
    })
  })

  it('P10: terminates the worker when it starts but cannot be configured', async () => {
    const terminate = vi.fn(async () => undefined)
    const original = tesseractLoader.load
    tesseractLoader.load = async () => ({
      createWorker: async () => ({
        recognize: async () => ({ data: { blocks: [] } }),
        setParameters: async () => {
          throw new Error('bad parameter')
        },
        terminate
      })
    })
    try {
      await expect(createOcrEngine(nodeOcr)).rejects.toBeInstanceOf(ToolError)
      expect(terminate).toHaveBeenCalledTimes(1)
    } finally {
      tesseractLoader.load = original
    }
  })

  it('Q21b: an OCR engine that cannot start skips only the scanned page; digital pages are still read', async () => {
    const r = await extractPdf(sample('Statement_with_scanned_page.pdf'), {
      pdfjs: nodePdfjs,
      documentParams,
      ocr: { ...nodeOcr, corePath: 'https://cdn.jsdelivr.net/npm/tesseract.js-core@7' },
      fileName: 'Statement_with_scanned_page.pdf'
    })
    expect(r.pages.map((p) => p.method)).toEqual(['text', 'text', 'scanned-skipped'])
    expect(r.tables[0].rows.length).toBeGreaterThan(60)
    expect(r.warnings.join(' ')).toMatch(/Page 3 .*could not start/)
  })
})

/** A landscape statement stored as a rotated portrait page (/Rotate 90 or 270), text upright on screen. */
async function rotatedStatement(rotation: 90 | 270, upright = true): Promise<Uint8Array> {
  const doc = await PDFDocument.create()
  const font = await doc.embedFont(StandardFonts.Helvetica)
  const page = doc.addPage([595, 842])
  page.setRotation(degrees(rotation))
  const xs = STATEMENT_XS.map((x) => x * 1.4)
  STATEMENT_ROWS.forEach((row, r) => {
    const top = 60 + r * 14 // distance from the top of the displayed (landscape) page
    row.forEach((text, c) => {
      if (!text) return
      const X = xs[c]
      if (!upright) page.drawText(text, { x: X, y: 500 - r * 14, size: 9, font })
      else if (rotation === 90) page.drawText(text, { x: top, y: X, size: 9, font, rotate: degrees(90) })
      else page.drawText(text, { x: 595 - top, y: 842 - X, size: 9, font, rotate: degrees(-90) })
    })
  })
  return doc.save()
}

describe('PDF → Excel layout fixes (Q4, Q12, P13)', () => {
  for (const rotation of [90, 270] as const) {
    it(`Q4: reads a landscape statement stored with /Rotate ${rotation}`, async () => {
      const r = await extractPdf(await rotatedStatement(rotation), { pdfjs: nodePdfjs, fileName: 'landscape.pdf' })
      const t = r.tables[0]
      expect(t.columns.map((c) => c.name)).toEqual(['Date', 'Description', 'Debit', 'Credit', 'Balance'])
      expect(t.rows.map((row) => row.cells[1].value)).toEqual(['Opening salary transfer', 'DEWA bill payment', 'Card purchase CARREFOUR'])
      expect(t.rows[2].cells[2].value).toBe(1234.56)
    })
  }

  it('Q4: text that is still sideways on the displayed page is ignored', async () => {
    await expect(extractPdf(await rotatedStatement(90, false), { pdfjs: nodePdfjs })).rejects.toMatchObject({ code: 'empty-result' })
  })

  it('Q12: merges a two-line column header', async () => {
    const doc = await PDFDocument.create()
    const font = await doc.embedFont(StandardFonts.Helvetica)
    const page = doc.addPage([595, 842])
    const top = ['Txn', 'Transaction', 'Withdrawal', 'Deposit', 'Running']
    const low = ['Date', 'Details', 'Amount (AED)', 'Amount (AED)', 'Balance (AED)']
    top.forEach((t, i) => page.drawText(t, { x: STATEMENT_XS[i], y: 780, size: 9, font }))
    low.forEach((t, i) => page.drawText(t, { x: STATEMENT_XS[i], y: 768, size: 9, font }))
    STATEMENT_ROWS.slice(1).forEach((row, r) => row.forEach((t, i) => t && page.drawText(t, { x: STATEMENT_XS[i], y: 752 - r * 14, size: 9, font })))
    const r = await extractPdf(await doc.save(), { pdfjs: nodePdfjs })
    expect(r.tables[0].columns.map((c) => c.name)).toEqual([
      'Txn Date',
      'Transaction Details',
      'Withdrawal Amount (AED)',
      'Deposit Amount (AED)',
      'Running Balance (AED)'
    ])
    expect(r.tables[0].rows).toHaveLength(3)
    expect(r.excluded).toEqual([])
  })

  it('P13: column names are always unique', () => {
    expect(uniqueColumnNames(['Debit', 'Debit (2)', 'Debit'])).toEqual(['Debit', 'Debit (2)', 'Debit (3)'])
    expect(uniqueColumnNames(['Column 2', '', ''])).toEqual(['Column 2', 'Column 2 (2)', 'Column 3'])
  })
})

describe('Split PDF file names (Q17)', () => {
  it('keeps names short for long page lists and long base names', () => {
    const pages = Array.from({ length: 300 }, (_, i) => i * 2 + 1)
    const name = splitFileName('Bank Statement September 2026', pages)
    expect(name).toBe('Bank Statement September 2026_p1-599_selected.pdf')
    expect(splitFileName('x'.repeat(300), [1, 2, 3]).length).toBeLessThanOrEqual(MAX_SPLIT_NAME)
    expect(splitFileName('Statement', [2, 5, 6])).toBe('Statement_p2_5-6.pdf')
  })
})

describe('Long ID numbers in PDF → Excel output (P5)', () => {
  it('writes 12+ digit whole numbers in text columns as text', async () => {
    const res = await extractPdf(sample('Price_List_digital.pdf'), { pdfjs: nodePdfjs, fileName: 'p.pdf' })
    const t = res.tables[0]
    const withId = {
      ...res,
      tables: [{ ...t, columns: [...t.columns, { key: 'Acct', name: 'Acct', type: 'text' as const }], rows: t.rows.map((r) => ({ ...r, cells: [...r.cells, { value: 1234567890123456, text: '1234567890123456', confidence: null, lowConfidence: false }] })) }]
    }
    const bytes = await toWorkbook(withId, { addPageColumn: false })
    const wb = new ExcelJS.Workbook()
    await wb.xlsx.load(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) as ArrayBuffer)
    const ws = wb.worksheets[0]
    expect(ws.getRow(2).getCell(t.columns.length + 1).value).toBe('1234567890123456')
  })
})
