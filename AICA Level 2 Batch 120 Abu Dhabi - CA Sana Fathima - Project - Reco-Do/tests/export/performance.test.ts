import { describe, expect, it } from 'vitest'
import ExcelJS from 'exceljs'
import { buildReconWorkbook, buildSummaryHtml } from '@export/index'
import { largeFixture } from './fixtures'

describe('export performance', () => {
  it('builds a workbook for 50,000 lines per side in under 10 seconds', async () => {
    const { session, statement } = largeFixture(50_000)
    const t0 = performance.now()
    const bytes = await buildReconWorkbook(session, statement)
    const ms = performance.now() - t0
    expect(ms).toBeLessThan(10_000)
    expect(bytes.byteLength).toBeGreaterThan(100_000)

    const wb = new ExcelJS.Workbook()
    await wb.xlsx.load(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) as ArrayBuffer)
    // 40,000 pairs + header, blank and total rows
    expect(wb.getWorksheet('Matched (100%)')?.rowCount).toBe(40_003)
    // 10,000 open items + header, blank, total, blank, note
    expect(wb.getWorksheet('To Reconcile — Bank statement')?.rowCount).toBe(10_005)
  }, 60_000)

  it('builds the HTML summary for 50,000 lines quickly', () => {
    const { session, statement } = largeFixture(50_000)
    const t0 = performance.now()
    const html = buildSummaryHtml(session, statement)
    expect(performance.now() - t0).toBeLessThan(3_000)
    expect(html.length).toBeLessThan(300_000)
  })
})
