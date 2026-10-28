import ExcelJS from 'exceljs'
import { beforeAll, describe, expect, it } from 'vitest'
import { PASSWORD_MESSAGE, ToolError } from '@tools/common'
import { mergePdfs } from '@tools/merge-pdfs'
import {
  BANK_FIELDS,
  buildLines,
  extractPdf,
  reconstruct,
  repairOcrAmount,
  reshapeResult,
  shapeTables,
  suggestBankMapping,
  toWorkbook,
  type PdfExtractResult,
  type PdfFragment,
  type PdfWord
} from '@tools/pdf-to-excel'
import { documentParams, nodePdfjs, sample } from './helpers'

const base = { pdfjs: nodePdfjs, documentParams }

function col(r: PdfExtractResult, name: string): number {
  const i = r.tables[0].columns.findIndex((c) => c.name === name)
  if (i < 0) throw new Error(`no column ${name}`)
  return i
}
const cents = (v: unknown): number => (typeof v === 'number' ? Math.round(v * 100) : 0)

describe('PDF → Excel: 6-page digital bank statement', () => {
  let r: PdfExtractResult
  beforeAll(async () => {
    r = await extractPdf(sample('Bank_Statement_6_pages_digital.pdf'), { ...base, fileName: 'Bank_Statement_6_pages_digital.pdf' })
  })

  it('joins all pages into one table with the PDF headers', () => {
    expect(r.pageCount).toBe(6)
    expect(r.pages.every((p) => p.method === 'text')).toBe(true)
    expect(r.ocrPages).toEqual([])
    expect(r.tables).toHaveLength(1)
    expect(r.tables[0].columns.map((c) => c.name)).toEqual(['Date', 'Value Date', 'Description', 'Cheque / Ref', 'Withdrawals', 'Deposits', 'Balance'])
    expect(r.tables[0].pages).toEqual([1, 2, 3, 4, 5, 6])
  })

  it('has 220 transactions plus the opening and closing balance rows', () => {
    const rows = r.tables[0].rows
    expect(rows).toHaveLength(222)
    const d = col(r, 'Description')
    const b = col(r, 'Balance')
    expect(rows[0].cells[d].text).toBe('OPENING BALANCE')
    expect(rows[0].cells[b].value).toBe(876543.21)
    expect(rows[221].cells[d].text).toBe('CLOSING BALANCE')
    expect(rows[221].cells[b].value).toBe(1421546.75)
  })

  it('removes repeated headers, footers and page numbers and lists them as excluded', () => {
    const byReason = (reason: string): number => r.excluded.filter((e) => e.reason === reason).length
    expect(byReason('repeated-header')).toBe(5) // header repeated on pages 2-6
    expect(byReason('page-number')).toBe(6) // "Page x of 6"
    expect(byReason('outside-table')).toBe(0)
    expect(r.excluded.filter((e) => e.text === 'Emirates NBD Bank PJSC')).toHaveLength(6)
    expect(r.excluded.every((e) => e.reason === 'page-header-footer' || e.reason === 'repeated-header' || e.reason === 'page-number')).toBe(true)
    // No header or footer text leaks into the table.
    const d = col(r, 'Description')
    expect(r.tables[0].rows.some((row) => /Description|computer generated|Page \d/.test(row.cells[d].text))).toBe(false)
  })

  it('merges the 24 wrapped descriptions into the row above', () => {
    const rows = r.tables[0].rows
    expect(rows.filter((row) => row.lines === 2)).toHaveLength(24)
    expect(rows.some((row) => row.lines > 2)).toBe(false)
    const d = col(r, 'Description')
    const wrapped = rows.filter((row) => row.lines === 2).map((row) => row.cells[d].text)
    expect(wrapped.every((t) => t.length > 40 && !t.includes('  '))).toBe(true)
    expect(rows.find((row) => row.cells[d].text.startsWith('CHQ DEP 544424'))?.cells[d].text).toBe('CHQ DEP 544424 BLUE LAGOON MARINE SERVICES LLC')
  })

  it('parses numbers and dates into real values that reconcile to the closing balance', () => {
    const rows = r.tables[0].rows
    const [wd, dep, bal, date] = [col(r, 'Withdrawals'), col(r, 'Deposits'), col(r, 'Balance'), col(r, 'Date')]
    expect(r.tables[0].columns.map((c) => c.type)).toEqual(['date', 'date', 'text', 'id', 'amount', 'amount', 'amount'])
    let running = cents(rows[0].cells[bal].value)
    for (const row of rows.slice(1, -1)) {
      running += cents(row.cells[dep].value) - cents(row.cells[wd].value)
      expect(cents(row.cells[bal].value)).toBe(running)
    }
    expect(running).toBe(142154675)
    expect(rows.every((row) => row.cells[date].value instanceof Date)).toBe(true)
    const first = rows[1].cells[date].value as Date
    expect([first.getFullYear(), first.getMonth(), first.getDate()]).toEqual([2026, 7, 3])
    expect(r.needsDateOrder).toBe(false)
  })

  it('keeps the page of every row', () => {
    const rows = r.tables[0].rows
    expect(rows.every((row) => row.page >= 1 && row.page <= 6)).toBe(true)
    expect(rows[0].page).toBe(1)
    expect(rows[221].page).toBe(6)
    for (let i = 1; i < rows.length; i++) expect(rows[i].page).toBeGreaterThanOrEqual(rows[i - 1].page)
  })

  it('suggests a bank mapping and applies the bank layout', () => {
    expect(r.suggestedBankMapping).toEqual({
      Date: 'Date',
      'Value Date': 'Value Date',
      Description: 'Description',
      Reference: 'Cheque / Ref',
      Debit: 'Withdrawals',
      Credit: 'Deposits',
      Balance: 'Balance'
    })
    const bank = reshapeResult(r, { layout: 'bank' })
    expect(bank.tables[0].columns.map((c) => c.name)).toEqual([...BANK_FIELDS])
    expect(bank.tables[0].rows).toHaveLength(222)
    expect(bank.bankUnmapped).toEqual([])
    // Override: no Value Date column.
    const over = reshapeResult(r, { layout: 'bank', bankMapping: { 'Value Date': null } })
    expect(over.tables[0].rows.every((row) => row.cells[1].value === null)).toBe(true)
    expect(over.bankUnmapped).toEqual(['Value Date'])
  })

  it('applies column renames and type changes without re-reading', () => {
    const edited = reshapeResult(r, { columnEdits: { Withdrawals: { name: 'Debit' }, 'Cheque / Ref': { type: 'text', name: 'Ref' } } })
    expect(edited.tables[0].columns.map((c) => c.name)).toEqual(['Date', 'Value Date', 'Description', 'Ref', 'Debit', 'Deposits', 'Balance'])
    expect(edited.tables[0].columns[3].type).toBe('text')
    const raw = reshapeResult(r, { convertValues: false })
    expect(raw.tables[0].rows[0].cells[6].value).toBe('876,543.21')
  })

  it('can keep repeated headers and keep pages as separate tables', () => {
    const kept = reshapeResult(r, { removeRepeatedHeaders: false })
    expect(kept.tables[0].rows).toHaveLength(227)
    expect(kept.excluded.filter((e) => e.reason === 'repeated-header')).toHaveLength(0)
    const separate = reshapeResult(r, { joinAcrossPages: false })
    expect(separate.tables).toHaveLength(6)
    expect(separate.tables.reduce((n, t) => n + t.rows.length, 0)).toBe(222)
  })

  it('honours a page range', async () => {
    const part = await extractPdf(sample('Bank_Statement_6_pages_digital.pdf'), { ...base, pages: '2-3, 5' })
    expect(part.pages.map((p) => p.page)).toEqual([2, 3, 5])
    expect(new Set(part.tables[0].rows.map((row) => row.page))).toEqual(new Set([2, 3, 5]))
    await expect(extractPdf(sample('Bank_Statement_6_pages_digital.pdf'), { ...base, pages: '7' })).rejects.toThrow('Page 7 does not exist. This PDF has 6 pages.')
  })

  it('reports progress per page and can be cancelled', async () => {
    const seen: number[] = []
    await extractPdf(sample('Bank_Statement_6_pages_digital.pdf'), base, (p) => seen.push(p.page))
    expect(seen).toEqual([1, 2, 3, 4, 5, 6])
    const ac = new AbortController()
    const run = extractPdf(sample('Bank_Statement_6_pages_digital.pdf'), base, (p) => p.page === 2 && ac.abort(), ac.signal)
    await expect(run).rejects.toMatchObject({ code: 'cancelled' })
  })

  it('writes a formatted workbook', async () => {
    const bytes = await toWorkbook(r, { addPageColumn: true })
    const wb = new ExcelJS.Workbook()
    await wb.xlsx.load(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) as ArrayBuffer)
    expect(wb.worksheets.map((w) => w.name)).toEqual(['Data', 'Excluded rows'])
    const ws = wb.getWorksheet('Data')
    if (!ws) throw new Error('no Data sheet')
    expect(ws.getRow(1).values).toEqual([undefined, 'Date', 'Value Date', 'Description', 'Cheque / Ref', 'Withdrawals', 'Deposits', 'Balance', 'Page'])
    expect(ws.getCell('A1').font?.bold).toBe(true)
    expect(ws.views[0]).toMatchObject({ state: 'frozen', ySplit: 1 })
    expect(ws.autoFilter).toBeTruthy()
    expect(ws.rowCount).toBe(223)
    const g2 = ws.getCell('G2')
    expect(g2.value).toBe(876543.21)
    expect(g2.numFmt).toBe('#,##0.00')
    const a3 = ws.getCell('A3')
    expect(a3.numFmt).toBe('dd-mmm-yyyy')
    expect((a3.value as Date).toISOString().slice(0, 10)).toBe('2026-08-03')
    expect(ws.getCell('H223').value).toBe(6)
    expect(ws.getColumn(3).width).toBeGreaterThan(30)
    const ex = wb.getWorksheet('Excluded rows')
    expect(ex?.rowCount).toBe(r.excluded.length + 1)
  })
})

describe('PDF → Excel: price list', () => {
  it('reads 44 items in 5 columns joined across 2 pages', async () => {
    const r = await extractPdf(sample('Price_List_digital.pdf'), base)
    expect(r.pageCount).toBe(2)
    expect(r.tables).toHaveLength(1)
    const t = r.tables[0]
    expect(t.columns.map((c) => c.name)).toEqual(['Item Code', 'Description', 'UoM', 'Unit Price AED', 'VAT %'])
    expect(t.rows).toHaveLength(44)
    expect(t.pages).toEqual([1, 2])
    expect(t.rows.every((row) => /^GS-\d{6}$/.test(row.cells[0].text))).toBe(true)
    expect(t.rows.every((row) => typeof row.cells[3].value === 'number')).toBe(true)
    expect(r.excluded.filter((e) => e.reason === 'repeated-header')).toHaveLength(1)
  })

  it('writes one sheet per table or all tables on one sheet', async () => {
    const r = reshapeResult(await extractPdf(sample('Price_List_digital.pdf'), base), { joinAcrossPages: false })
    expect(r.tables).toHaveLength(2)
    const load = async (b: Uint8Array): Promise<ExcelJS.Workbook> => {
      const wb = new ExcelJS.Workbook()
      await wb.xlsx.load(b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength) as ArrayBuffer)
      return wb
    }
    const many = await load(await toWorkbook(r, { oneSheetPerTable: true, addPageColumn: false }))
    expect(many.worksheets.map((w) => w.name)).toEqual(['Table 1', 'Table 2', 'Excluded rows'])
    const one = await load(await toWorkbook(r, { oneSheetPerTable: false, addPageColumn: false }))
    const ws = one.getWorksheet('Data')
    expect(ws?.rowCount).toBe(45) // same columns: one header + 44 rows
  })
})

describe('PDF → Excel: errors', () => {
  it('refuses a password-protected PDF', async () => {
    const run = extractPdf(sample('Password_protected.pdf'), base)
    await expect(run).rejects.toBeInstanceOf(ToolError)
    await expect(extractPdf(sample('Password_protected.pdf'), base)).rejects.toThrow(PASSWORD_MESSAGE)
    expect(PASSWORD_MESSAGE).toBe('This PDF is password-protected. Remove the password first, then try again.')
  })

  it('refuses a file that is not a PDF', async () => {
    const junk = new TextEncoder().encode('not a pdf at all').buffer as ArrayBuffer
    await expect(extractPdf(junk, base)).rejects.toMatchObject({ code: 'invalid-pdf' })
  })

  it('skips scanned pages with a warning when OCR is not configured', async () => {
    const r = await extractPdf(sample('Statement_with_scanned_page.pdf'), base)
    expect(r.pages.map((p) => p.method)).toEqual(['text', 'text', 'scanned-skipped'])
    expect(r.warnings[0]).toContain('Page 3')
    expect(r.tables[0].rows).toHaveLength(69) // opening + 68 digital rows
  })
})

describe('PDF → Excel: layout and shaping units', () => {
  const w = (text: string, x0: number, top: number, size = 8, x1 = x0 + text.length * size * 0.5): PdfWord => ({ text, x0, x1, top, bottom: top + size, size })

  it('groups words into lines and segments, following a slight skew', () => {
    const lines = buildLines([w('01/02/2026', 10, 100), w('Coffee', 70, 100.6), w('beans', 98, 101.2), w('12.50', 200, 102)])
    expect(lines).toHaveLength(1)
    expect(lines[0].segments.map((s) => s.text)).toEqual(['01/02/2026', 'Coffee beans', '12.50'])
    expect(lines[0].hasDate && lines[0].hasAmount).toBe(true)
  })

  it('clusters columns by x when there is no header and merges wrapped lines', () => {
    const words = [
      w('03-Aug-2026', 10, 100), w('Payment to supplier', 80, 100), w('1,000.00', 220, 100),
      w('for August', 80, 109),
      w('04-Aug-2026', 10, 130), w('Refund', 80, 130), w('250.00', 228, 130)
    ]
    const { fragments } = reconstruct([{ page: 1, method: 'text', words }])
    expect(fragments).toHaveLength(1)
    expect(fragments[0].hasHeader).toBe(false)
    expect(fragments[0].rows.map((r) => r.cells)).toEqual([
      ['03-Aug-2026', 'Payment to supplier for August', '1,000.00'],
      ['04-Aug-2026', 'Refund', '250.00']
    ])
    expect(fragments[0].rows[0].lines).toBe(2)
  })

  it('reports ambiguous day/month order and converts with the chosen order', () => {
    const frag: PdfFragment = {
      page: 1,
      method: 'text',
      header: ['Date', 'Amount'],
      hasHeader: true,
      rows: ['03/09/2026', '07/08/2026', '11/08/2026'].map((d) => ({ page: 1, cells: [d, '1.00'], confidence: [null, null], ocr: false, lines: 1 }))
    }
    const auto = shapeTables([frag], [], {}, 85)
    expect(auto.detectedDateOrder).toBe('ambiguous')
    expect(auto.needsDateOrder).toBe(true)
    expect((auto.tables[0].rows[0].cells[0].value as Date).getMonth()).toBe(8) // DMY default: 3 Sep
    const mdy = shapeTables([frag], [], { dateOrder: 'MDY' }, 85)
    expect(mdy.needsDateOrder).toBe(false)
    expect((mdy.tables[0].rows[0].cells[0].value as Date).getMonth()).toBe(2) // 9 Mar
  })

  it('repairs OCR amounts that lost their decimal point or separators', () => {
    expect(repairOcrAmount('2142117')).toBe('21,421.17')
    expect(repairOcrAmount('8,724 50')).toBe('8,724.50')
    expect(repairOcrAmount('429 959 56')).toBe('429,959.56')
    expect(repairOcrAmount('1O5.00')).toBe('105.00')
    expect(repairOcrAmount('1,234.50')).toBeNull()
    expect(repairOcrAmount('TT2608')).toBeNull()
  })

  it('suggests bank mappings from common header names', () => {
    expect(suggestBankMapping(['Txn Date', 'Narration', 'Reference', 'Debit', 'Credit', 'Balance'])).toEqual({
      Date: 'Txn Date', 'Value Date': null, Description: 'Narration', Reference: 'Reference', Debit: 'Debit', Credit: 'Credit', Balance: 'Balance'
    })
  })
})

describe('PDF → Excel: performance', () => {
  it('reads a 54-page digital PDF in under 10 seconds', async () => {
    const one = sample('Bank_Statement_6_pages_digital.pdf')
    const big = await mergePdfs(Array.from({ length: 9 }, (_, i) => ({ name: `s${i}.pdf`, data: one })))
    const t0 = performance.now()
    const r = await extractPdf(big, base)
    const ms = performance.now() - t0
    expect(r.pageCount).toBe(54)
    expect(r.tables[0].rows).toHaveLength(222 * 9)
    expect(ms).toBeLessThan(10000)
  }, 30000)
})
