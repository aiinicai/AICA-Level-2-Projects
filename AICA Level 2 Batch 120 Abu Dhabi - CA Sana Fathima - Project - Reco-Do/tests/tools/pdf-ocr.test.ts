// Full-PDF OCR in Node: pdf.js renders page 3 with its @napi-rs/canvas factory, tesseract.js reads it
// with the English 4.0.0 traineddata from node_modules (no network).
// @napi-rs/canvas is not a direct dependency: it is an optional dependency of pdfjs-dist, pinned in package-lock.json
// (1.0.11, with the @napi-rs/canvas-win32-x64-msvc binary). `npm ci` on Windows installs it, so CI needs no extra step.
// It would be missing only if optional dependencies were skipped (`npm ci --omit=optional`).
import ExcelJS from 'exceljs'
import { beforeAll, describe, expect, it } from 'vitest'
import { extractPdf, toWorkbook, LOW_CONFIDENCE_FILL, type PdfExtractResult } from '@tools/pdf-to-excel'
import { documentParams, nodeOcr, nodePdfjs, sample } from './helpers'

const cents = (v: unknown): number | null => (typeof v === 'number' ? Math.round(v * 100) : null)

describe('PDF → Excel: statement with a scanned page (OCR)', () => {
  let r: PdfExtractResult
  const stages: string[] = []
  beforeAll(async () => {
    r = await extractPdf(
      sample('Statement_with_scanned_page.pdf'),
      { pdfjs: nodePdfjs, documentParams, ocr: nodeOcr, fileName: 'Statement_with_scanned_page.pdf' },
      (p) => stages.push(`${p.page}:${p.stage}`)
    )
  }, 120000)

  it('detects page 3 as scanned and reads it with OCR', () => {
    expect(r.pages.map((p) => p.method)).toEqual(['text', 'text', 'ocr'])
    expect(r.ocrPages).toEqual([3])
    expect(stages).toEqual(['1:text', '2:text', '3:text', '3:ocr'])
    expect(r.pages[2].ocrConfidence).toBeGreaterThan(70)
  })

  it('joins the OCR rows to the digital table: 22 rows + closing balance from page 3', () => {
    expect(r.tables).toHaveLength(1)
    const t = r.tables[0]
    expect(t.columns.map((c) => c.name)).toEqual(['Date', 'Description', 'Reference', 'Debit', 'Credit', 'Balance'])
    const page3 = t.rows.filter((row) => row.page === 3)
    expect(page3).toHaveLength(23)
    expect(page3.every((row) => row.ocr)).toBe(true)
    expect(t.rows).toHaveLength(1 + 68 + 23)
    const last = page3[22]
    expect(last.cells[1].text).toBe('CLOSING BALANCE')
    expect(last.cells[5].value).toBe(503143.57)
    // The repeated bank header and column header on page 3 are excluded like on digital pages.
    expect(r.excluded.filter((e) => e.page === 3 && e.reason === 'repeated-header')).toHaveLength(1)
    expect(r.excluded.some((e) => e.page === 3 && e.reason === 'page-number')).toBe(true)
  })

  it('reads dates and amounts well enough that the running balance holds for most OCR rows', () => {
    const rows = r.tables[0].rows
    const start = rows.findIndex((row) => row.page === 3)
    const page3 = rows.slice(start, start + 22)
    expect(page3.filter((row) => row.cells[0].value instanceof Date)).toHaveLength(22)
    let ok = 0
    for (let i = 0; i < page3.length; i++) {
      const prev = cents((i === 0 ? rows[start - 1] : page3[i - 1]).cells[5].value)
      const row = page3[i]
      const bal = cents(row.cells[5].value)
      if (prev === null || bal === null) continue
      if (prev + (cents(row.cells[4].value) ?? 0) - (cents(row.cells[3].value) ?? 0) === bal) ok++
    }
    expect(ok).toBeGreaterThanOrEqual(20)
  })

  it('flags low-confidence OCR cells and only OCR cells', () => {
    const rows = r.tables[0].rows
    expect(rows.filter((row) => !row.ocr).some((row) => row.cells.some((c) => c.lowConfidence))).toBe(false)
    const ocrCells = rows.filter((row) => row.ocr).flatMap((row) => row.cells.filter((c) => c.text !== ''))
    expect(ocrCells.every((c) => c.confidence !== null)).toBe(true)
    expect(ocrCells.filter((c) => c.lowConfidence).every((c) => (c.confidence as number) < 85 || /\d/.test(c.text))).toBe(true)
  })

  it('shades low-confidence cells amber and adds a Read me sheet', async () => {
    const bytes = await toWorkbook(r)
    const wb = new ExcelJS.Workbook()
    await wb.xlsx.load(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) as ArrayBuffer)
    expect(wb.worksheets.map((w) => w.name)).toEqual(['Data', 'Excluded rows', 'Read me'])
    const ws = wb.getWorksheet('Data')
    if (!ws) throw new Error('no Data sheet')
    const lowCount = r.tables[0].rows.reduce((n, row) => n + row.cells.filter((c) => c.lowConfidence).length, 0)
    let amber = 0
    ws.eachRow((row) =>
      row.eachCell((cell) => {
        const fill = cell.fill as ExcelJS.FillPattern | undefined
        if (fill?.type === 'pattern' && fill.fgColor?.argb === LOW_CONFIDENCE_FILL) amber++
      })
    )
    expect(amber).toBe(lowCount)
    const readMe = wb.getWorksheet('Read me')
    const text: string[] = []
    readMe?.eachRow((row) => text.push(String(row.getCell(1).value ?? '')))
    expect(text.join('\n')).toContain('Page 3 had no text layer')
  })
})
