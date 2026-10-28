import JSZip from 'jszip'
import { PDFDocument } from 'pdf-lib'
import { describe, expect, it } from 'vitest'
import { formatPageList, parsePageRanges, parsePageSelection, PASSWORD_MESSAGE, zipFiles } from '@tools/common'
import { mergePdfs, pdfInfo } from '@tools/merge-pdfs'
import { planGroups, splitPdf } from '@tools/split-pdf'
import { nodePdfjs, sample } from './helpers'

/** Text of each page, via pdf.js. */
async function pageTexts(data: Uint8Array): Promise<string[]> {
  const doc = await nodePdfjs.getDocument({ data: data.slice(), verbosity: 0 }).promise
  const out: string[] = []
  for (let i = 1; i <= doc.numPages; i++) {
    const page = await doc.getPage(i)
    const tc = await page.getTextContent()
    out.push(tc.items.map((it) => ('str' in it ? it.str : '')).join(' '))
  }
  await doc.loadingTask.destroy()
  return out
}

describe('Merge PDFs', () => {
  it('merges 3 + 2 pages into 5 pages in order', async () => {
    const out = await mergePdfs([
      { name: 'Merge_Part1.pdf', data: sample('Merge_Part1.pdf') },
      { name: 'Merge_Part2.pdf', data: sample('Merge_Part2.pdf') }
    ])
    const texts = await pageTexts(out)
    expect(texts).toHaveLength(5)
    expect(texts.map((t) => /Merge Part (\d)/.exec(t)?.[1] + ':' + /Page (\d) of/.exec(t)?.[1])).toEqual(['1:1', '1:2', '1:3', '2:1', '2:2'])
  })

  it('applies file order, page selection and rotation', async () => {
    const out = await mergePdfs([
      { name: 'Merge_Part2.pdf', data: sample('Merge_Part2.pdf'), pages: [{ index: 1, rotate: 90 }, { index: 0, rotate: 0 }] },
      { name: 'Merge_Part1.pdf', data: sample('Merge_Part1.pdf'), pages: [{ index: 2, rotate: 180 }] }
    ])
    const doc = await PDFDocument.load(out)
    expect(doc.getPageCount()).toBe(3)
    expect(doc.getPages().map((p) => p.getRotation().angle)).toEqual([90, 0, 180])
    const texts = await pageTexts(out)
    expect(texts[0]).toContain('Merge Part 2')
    expect(texts[0]).toContain('Page 2 of 2')
    expect(texts[2]).toContain('Page 3 of 3')
  })

  it('refuses password-protected files and bad page numbers', async () => {
    await expect(mergePdfs([{ name: 'Password_protected.pdf', data: sample('Password_protected.pdf') }])).rejects.toThrow(`Password_protected.pdf: ${PASSWORD_MESSAGE}`)
    await expect(mergePdfs([{ name: 'a.pdf', data: sample('Merge_Part2.pdf'), pages: [{ index: 5, rotate: 0 }] }])).rejects.toMatchObject({ code: 'invalid-option' })
    await expect(mergePdfs([])).rejects.toMatchObject({ code: 'empty-result' })
  })

  it('reports page count and encryption', async () => {
    expect(await pdfInfo(sample('Split_Me_12_pages.pdf'))).toMatchObject({ pages: 12, encrypted: false })
    expect((await pdfInfo(sample('Password_protected.pdf'))).encrypted).toBe(true)
  })
})

describe('Split PDF', () => {
  const data = sample('Split_Me_12_pages.pdf')
  const counts = async (files: { data: Uint8Array }[]): Promise<number[]> =>
    Promise.all(files.map(async (f) => (await PDFDocument.load(f.data)).getPageCount()))

  it('splits every 5 pages into 5, 5 and 2 pages', async () => {
    const files = await splitPdf(data, { mode: 'every', pages: 5 }, { fileName: 'Split_Me_12_pages.pdf' })
    expect(files.map((f) => f.name)).toEqual(['Split_Me_12_pages_p1-5.pdf', 'Split_Me_12_pages_p6-10.pdf', 'Split_Me_12_pages_p11-12.pdf'])
    expect(await counts(files)).toEqual([5, 5, 2])
    const texts = await pageTexts(files[2].data)
    expect(texts[0]).toContain('Page 11 of 12')
  })

  it('splits by custom ranges, one file per range', async () => {
    const files = await splitPdf(data, { mode: 'ranges', ranges: '1-3, 4-6, 7' }, { fileName: 'Statement.pdf' })
    expect(files.map((f) => f.name)).toEqual(['Statement_p1-3.pdf', 'Statement_p4-6.pdf', 'Statement_p7.pdf'])
    expect(await counts(files)).toEqual([3, 3, 1])
  })

  it('extracts selected pages into one file and splits one file per page', async () => {
    const sel = await splitPdf(data, { mode: 'select', pages: [2, 5, 6] }, { fileName: 'Statement.pdf' })
    expect(sel.map((f) => f.name)).toEqual(['Statement_p2_5-6.pdf'])
    expect(await counts(sel)).toEqual([3])
    const single = await splitPdf(data, { mode: 'single' }, { fileName: 'Statement.pdf' })
    expect(single).toHaveLength(12)
    expect(single[11].name).toBe('Statement_p12.pdf')
  })

  it('zips several files', async () => {
    const files = await splitPdf(data, { mode: 'every', pages: 5 }, { fileName: 'Split_Me_12_pages.pdf' })
    const zip = await JSZip.loadAsync(await zipFiles(files))
    expect(Object.keys(zip.files).sort()).toEqual(files.map((f) => f.name).sort())
  })

  it('validates plans and refuses encrypted files', async () => {
    expect(planGroups({ mode: 'every', pages: 3 }, 12)).toHaveLength(4)
    expect(() => planGroups({ mode: 'every', pages: 0 }, 12)).toThrow('Enter how many pages')
    expect(() => planGroups({ mode: 'ranges', ranges: '1-3, 14' }, 12)).toThrow('Page 14 does not exist. This PDF has 12 pages.')
    await expect(splitPdf(sample('Password_protected.pdf'), { mode: 'single' })).rejects.toThrow(PASSWORD_MESSAGE)
  })
})

describe('Page ranges', () => {
  it('parses and formats ranges', () => {
    expect(parsePageRanges('1-3, 5, 8-', 10)).toEqual([{ from: 1, to: 3 }, { from: 5, to: 5 }, { from: 8, to: 10 }])
    expect(parsePageSelection('', 3)).toEqual([1, 2, 3])
    expect(parsePageSelection('all', 2)).toEqual([1, 2])
    expect(parsePageSelection('3, 1-2, 2', 5)).toEqual([1, 2, 3])
    expect(() => parsePageRanges('5-2', 10)).toThrow('runs backwards')
    expect(() => parsePageRanges('abc', 10)).toThrow('is not a page or page range')
    expect(formatPageList([1, 2, 3, 5, 7, 8])).toBe('1-3, 5, 7-8')
  })
})
