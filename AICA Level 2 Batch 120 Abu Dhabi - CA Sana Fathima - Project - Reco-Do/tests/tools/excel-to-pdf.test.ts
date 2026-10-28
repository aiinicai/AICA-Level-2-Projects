// @napi-rs/canvas is not a direct dependency: it is an optional dependency of pdfjs-dist, pinned in package-lock.json
// (1.0.11, with the @napi-rs/canvas-win32-x64-msvc binary). `npm ci` on Windows installs it, so CI needs no extra step.
// It would be missing only if optional dependencies were skipped (`npm ci --omit=optional`).
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { createCanvas, type Canvas } from '@napi-rs/canvas'
import { describe, expect, it } from 'vitest'
import type { ParsedTable } from '@shared/contracts'
import { parseTable, readWorkbook } from '@shared/parsing'
import { renderThumbnail, openThumbnailSource, PASSWORD_MESSAGE, type CanvasFactory } from '@tools/common'
import { sheetToPdf, sheetToPdfDetailed } from '@tools/excel-to-pdf'
import { nodePdfjs, sample, SAMPLES } from './helpers'

function trialBalance(): ParsedTable {
  const b = readFileSync(resolve(SAMPLES, 'Sheet_to_print.xlsx'))
  const wb = readWorkbook(b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength) as ArrayBuffer, 'Sheet_to_print.xlsx')
  return parseTable(wb.sheets[0], { fileName: 'Sheet_to_print.xlsx' })
}

async function pageTexts(data: Uint8Array): Promise<string[]> {
  const doc = await nodePdfjs.getDocument({ data: data.slice(), verbosity: 0 }).promise
  const out: string[] = []
  for (let i = 1; i <= doc.numPages; i++) {
    const tc = await (await doc.getPage(i)).getTextContent()
    out.push(tc.items.map((it) => ('str' in it ? it.str : '')).join(' '))
  }
  await doc.loadingTask.destroy()
  return out
}

describe('Excel → PDF', () => {
  const table = trialBalance()

  it('reads the trial balance (121 accounts)', () => {
    expect(table.columns).toEqual(['Account Code', 'Account Name', 'Account Group', 'Debit (AED)', 'Credit (AED)'])
    expect(table.rows).toHaveLength(121)
  })

  it('prints several pages with the header repeated, page numbers, title and totals', async () => {
    const res = sheetToPdfDetailed(table, {
      title: 'Desert Pearl Trading LLC',
      subtitle: 'Trial balance as at 30-Sep-2026',
      totals: ['Debit (AED)', 'Credit (AED)']
    })
    expect(res.pages).toBeGreaterThanOrEqual(3)
    expect(res.orientation).toBe('portrait')
    const texts = await pageTexts(res.data)
    expect(texts).toHaveLength(res.pages)
    texts.forEach((t, i) => {
      expect(t).toContain('Account Code')
      expect(t).toContain('Credit (AED)')
      expect(t).toContain(`Page ${i + 1} of ${res.pages}`)
    })
    expect(texts[0]).toContain('Desert Pearl Trading LLC')
    expect(texts[0]).toContain('Trial balance as at 30-Sep-2026')
    expect(texts[1]).not.toContain('Desert Pearl Trading LLC')
    const last = texts[texts.length - 1]
    expect(last).toContain('Total')
    expect(last.match(/34,895,739\.74/g)).toHaveLength(2)
  })

  it('prints the header only once when not repeated and supports landscape and no gridlines', async () => {
    const res = sheetToPdfDetailed(table, { repeatHeader: false, orientation: 'landscape', gridlines: false, pageNumbers: false })
    expect(res.orientation).toBe('landscape')
    const texts = await pageTexts(res.data)
    expect(texts[0]).toContain('Account Code')
    expect(texts[1]).not.toContain('Account Code')
    expect(texts[0]).not.toMatch(/Page 1 of/)
  })

  it('formats numbers and dates and picks landscape for wide sheets', async () => {
    const wide: ParsedTable = {
      fileName: 'x.xlsx',
      sheetName: 'S',
      headerRowIndex: 0,
      columns: ['Date', ...Array.from({ length: 13 }, (_, i) => `Amount column ${i + 1}`)],
      rows: [{ id: 'r2', sourceRow: 1, values: { Date: new Date(2026, 8, 3), ...Object.fromEntries(Array.from({ length: 13 }, (_, i) => [`Amount column ${i + 1}`, 1234567.5])) } }],
      excluded: [],
      openingBalance: null,
      closingBalance: null
    }
    const res = sheetToPdfDetailed(wide, {})
    expect(res.orientation).toBe('landscape')
    const [text] = await pageTexts(res.data)
    expect(text).toContain('03-Sep-2026')
    expect(text).toContain('1,234,567.50')
    expect(sheetToPdf(wide, { orientation: 'portrait' })).toBeInstanceOf(Uint8Array)
  })

  it('rejects unknown columns and empty sheets in plain English', () => {
    expect(() => sheetToPdf(table, { totals: ['Nope'] })).toThrow('Totals column "Nope" is not being printed.')
    expect(() => sheetToPdf({ ...table, rows: [] })).toThrow('The sheet has no rows to print.')
  })
})

describe('Page thumbnails', () => {
  const factory: CanvasFactory<Canvas> = {
    create(w, h) {
      const canvas = createCanvas(w, h)
      return { canvas, context: canvas.getContext('2d') as unknown as CanvasRenderingContext2D }
    }
  }

  it('renders a page thumbnail at the requested width with an injected canvas', async () => {
    const t = await renderThumbnail(sample('Merge_Part1.pdf'), 1, 120, { pdfjs: nodePdfjs, canvasFactory: factory })
    expect(t.width).toBe(120)
    expect(t.height).toBe(170) // A4 ratio
    expect(t.canvas.width).toBe(120)
    const src = await openThumbnailSource(sample('Split_Me_12_pages.pdf'), { pdfjs: nodePdfjs, canvasFactory: factory })
    expect(src.pageCount).toBe(12)
    const last = await src.render(11, 80)
    expect(last.pageIndex).toBe(11)
    await expect(src.render(12, 80)).rejects.toThrow('Page 13 does not exist')
    await src.destroy()
  })

  it('refuses password-protected files', async () => {
    await expect(renderThumbnail(sample('Password_protected.pdf'), 0, 100, { pdfjs: nodePdfjs, canvasFactory: factory })).rejects.toThrow(PASSWORD_MESSAGE)
  })
})
