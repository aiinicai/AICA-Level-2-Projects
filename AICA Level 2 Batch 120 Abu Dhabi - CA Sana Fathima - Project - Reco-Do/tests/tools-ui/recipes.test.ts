// Recipe save and re-apply for PDF → Excel, Merge Files and Data Cleaner (IndexedDB through lib/db.ts).
import 'fake-indexeddb/auto'
import { afterEach, describe, expect, it } from 'vitest'
import { readWorkbook } from '@shared/parsing'
import { prepareSheet, runCleaner, suggestOptions, withDefaults } from '@tools/data-cleaner'
import { mappingFromRecipe, recipeFromMapping, renameOutputColumn, sourcesFromWorkbook, suggestMapping } from '@tools/merge-files'
import { closeDb, listRecipes, saveRecipe } from '../../src/renderer/src/lib/db'
import { asDataCleanerRecipe, asMergeFilesRecipe, asPdfToExcelRecipe, buildRecipe, dataCleanerRecipe } from '../../src/renderer/src/features/tools/recipes'
import { sample } from './helpers'

let n = 0
const id = (): string => `id-${++n}`

afterEach(async () => {
  await closeDb()
  indexedDB.deleteDatabase('reco-do')
})

describe('recipes', () => {
  it('saves a PDF → Excel recipe and reads it back validated', async () => {
    const r = buildRecipe(
      'pdf-to-excel',
      '  ADCB   statement ',
      { layout: 'bank', bankMapping: { Debit: 'Withdrawals', Credit: null }, columnEdits: { Particulars: { name: 'Narration', type: 'text' } }, pages: '1-3', addPageColumn: false },
      [],
      id
    )
    expect(r.name).toBe('ADCB statement')
    await saveRecipe(r)
    const [stored] = await listRecipes('pdf-to-excel')
    const opts = asPdfToExcelRecipe(stored.options)
    expect(opts).toEqual({
      layout: 'bank',
      bankMapping: { Debit: 'Withdrawals', Credit: null },
      columnEdits: { Particulars: { name: 'Narration', type: 'text' } },
      pages: '1-3',
      addPageColumn: false
    })
    // Bad values are dropped, not trusted.
    expect(asPdfToExcelRecipe({ layout: 'sideways', columnEdits: { A: { type: 'colour' } } })).toEqual({ columnEdits: { A: {} } })
    expect(asPdfToExcelRecipe('nonsense')).toBeNull()
  })

  it('replaces a recipe with the same name and keeps its id', () => {
    const first = buildRecipe('merge-files', 'Monthly', { columns: [], headerMap: {} }, [], id, new Date('2026-09-01'))
    const second = buildRecipe('merge-files', 'monthly', { columns: ['A'], headerMap: {} }, [first], id, new Date('2026-10-01'))
    expect(second.id).toBe(first.id)
    expect(second.createdAt).toBe(first.createdAt)
    expect(second.updatedAt).not.toBe(first.updatedAt)
    expect(() => buildRecipe('merge-files', '   ', {}, [], id)).toThrow(/name/)
  })

  it('re-applies a Merge Files recipe to next month', async () => {
    const files = ['Statement_Jul2026.xlsx', 'Statement_Aug2026.xlsx'].flatMap((f, i) => sourcesFromWorkbook(sample(f), f, { fileIndex: i }))
    let m = suggestMapping(files)
    m = renameOutputColumn(m, 'Txn Date', 'Date')
    const opts = recipeFromMapping(m, files, { sortBy: 'Date', sortDirection: 'desc', addSourceColumns: false, convertValues: true })
    await saveRecipe(buildRecipe('merge-files', 'Al Safa', opts, [], id))
    const [stored] = await listRecipes('merge-files')
    const recipe = asMergeFilesRecipe(stored.options)!
    expect(recipe.sortDirection).toBe('desc')
    const next = sourcesFromWorkbook(sample('Statement_Sep2026.xlsx'), 'Statement_Sep2026.xlsx')
    const again = mappingFromRecipe(next, recipe)
    expect(again.columns[0]).toBe('Date')
    expect(again.sources[next[0].id].Date).toBe('Date')
    expect(again.sources[next[0].id]['Debit (AED)']).toBe('Debit')
  })

  it('re-applies a Data Cleaner recipe', async () => {
    const wb = readWorkbook(sample('Messy_Data_for_Cleaner.xlsx'), 'Messy_Data_for_Cleaner.xlsx')
    const p = prepareSheet(wb.sheets[0], 'Messy_Data_for_Cleaner.xlsx')
    const o = suggestOptions(p)
    o.duplicates.mode = 'remove'
    o.textCase = { enabled: true, columns: ['Paid By'], mode: 'upper' }
    await saveRecipe(buildRecipe('data-cleaner', 'Expense export', dataCleanerRecipe(o, 'Expense export'), [], id))
    const [stored] = await listRecipes('data-cleaner')
    const r = asDataCleanerRecipe(stored.options)!
    expect(r.sheetName).toBe('Expense export')
    const applied = withDefaults(p, r.options)
    expect(applied).toEqual(o)
    const result = runCleaner(p, applied)
    expect(result.table.rows).toHaveLength(40)
    expect(result.table.rows[0].cells[5].value).toBe('PETTY CASH')
  })
})
