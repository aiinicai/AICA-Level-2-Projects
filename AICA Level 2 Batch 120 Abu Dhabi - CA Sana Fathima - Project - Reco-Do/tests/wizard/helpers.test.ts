import { describe, expect, it } from 'vitest'
import type { ParsedTable, SampleFile } from '@shared/contracts'
import {
  accountFromFileName,
  guessAccountLabel,
  guessPeriod,
  periodFromDates,
  pickSampleFiles,
  SAMPLE_SETS,
  shortSideNames,
  signExplanation,
  stepStatusLines,
  tierRuleText
} from '@/features/wizard/helpers'
import { initialState } from '@/features/wizard/reducer'

function dated(dates: (Date | string)[]): ParsedTable {
  return {
    fileName: 'x.xlsx',
    sheetName: 'S',
    headerRowIndex: 0,
    columns: ['Posting Date', 'Ref'],
    rows: dates.map((d, i) => ({ id: `r${i + 2}`, sourceRow: i + 1, values: { 'Posting Date': d, Ref: `R${i}` } })),
    excluded: [],
    openingBalance: null,
    closingBalance: null
  }
}

describe('account and period guesses', () => {
  it('drops file-kind words and period tokens from the file name', () => {
    expect(accountFromFileName('ENBD_Current_Statement_Sep2026.xlsx')).toBe('ENBD Current')
    expect(accountFromFileName('Our_AR_Ledger_AlNoor_Trading.xlsx')).toBe('AlNoor Trading')
    expect(accountFromFileName('C:\\files\\Gulf_Supplies_SOA.xlsx')).toBe('Gulf Supplies')
  })
  it('General uses the side names', () => {
    expect(guessAccountLabel('general', 'a.xlsx', 'HR master', 'WPS register')).toBe('HR master vs WPS register')
    expect(guessAccountLabel('bank', null, 'A', 'B')).toBe('')
  })
  it('a single month gives "Sep 2026"; a range gives both dates', () => {
    expect(periodFromDates(new Date(2026, 8, 1), new Date(2026, 8, 30))).toBe('Sep 2026')
    expect(periodFromDates(new Date(2026, 7, 1), new Date(2026, 8, 30))).toBe('01-Aug-2026 to 30-Sep-2026')
  })
  it('reads the period from the data, else from the file name', () => {
    expect(guessPeriod([dated([new Date(2026, 8, 3), new Date(2026, 8, 28)])], null)).toBe('Sep 2026')
    expect(guessPeriod([null], 'WPS_Payroll_Register_Sep2026.xlsx')).toBe('Sep 2026')
    expect(guessPeriod([], 'list.xlsx')).toBe('')
  })
  it('prefers the narrowest date column across both files', () => {
    const joins = dated([new Date(2014, 1, 16), new Date(2025, 5, 1)])
    const pay = dated([new Date(2026, 8, 28), new Date(2026, 8, 28)])
    expect(guessPeriod([joins, pay], null)).toBe('Sep 2026')
    expect(guessPeriod([joins], 'HR_Master_Sep2026.xlsx')).toBe('Sep 2026')
    expect(guessPeriod([joins], 'HR_Master.xlsx')).toBe('16-Feb-2014 to 01-Jun-2025')
  })
})

describe('labels and texts', () => {
  it('short side names', () => {
    expect(shortSideNames('bank', 'Bank statement', 'GL')).toEqual(['Bank', 'GL'])
    expect(shortSideNames('general', '  ', 'WPS')).toEqual(['File A', 'WPS'])
  })
  it('tier rule text follows the number of keys', () => {
    expect(tierRuleText(1, false)).toContain('stay unmatched')
    expect(tierRuleText(2, false)).toContain('Likely')
    expect(tierRuleText(3, true)).toBe('Records match when all 3 keys agree. 2 of 3 = Doubtful. Only one identifying key = Likely. A Date key alone can never match.')
  })
  it('sign explanation in plain English', () => {
    expect(signExplanation('bank', 'inverse', 'A', 'B')).toMatch(/^Bank Credit = GL Debit/)
    expect(signExplanation('general', 'same', 'Entity A', 'Entity B')).toContain('Entity A')
  })
  it('step status lines', () => {
    expect(stepStatusLines(initialState('bank'), [])).toEqual(['Choose two files', 'Columns, keys, sign', 'Exact match', 'AI on leftovers', 'Excel / PDF'])
  })
})

describe('sample files', () => {
  const f = (path: string): SampleFile => ({ path, name: path.split('/').pop() ?? path, folder: path.split('/')[0], size: 1 })
  const list = [
    'bank/ENBD_Current_Statement_Sep2026.xlsx',
    'bank/GL_101200_Cash_Sep2026.xlsx',
    'ar/AlNoor_Trading_SOA.xlsx',
    'ar/Our_AR_Ledger_AlNoor_Trading.xlsx',
    'ap/Gulf_Supplies_SOA.xlsx',
    'ap/Our_AP_Ledger_Gulf_Supplies.xlsx',
    'general/HR_Employee_Master.xlsx',
    'general/Intercompany_EntityA_Dubai.xlsx',
    'general/Intercompany_EntityB_AbuDhabi.xlsx',
    'general/WPS_Payroll_Register_Sep2026.xlsx'
  ].map(f)
  const names = (id: keyof typeof SAMPLE_SETS, i = 0): string[] => pickSampleFiles(SAMPLE_SETS[id][i], list).map((x) => x.name)
  it('finds both files of every set in the right order', () => {
    expect(names('bank')).toEqual(['ENBD_Current_Statement_Sep2026.xlsx', 'GL_101200_Cash_Sep2026.xlsx'])
    expect(names('ar')).toEqual(['Our_AR_Ledger_AlNoor_Trading.xlsx', 'AlNoor_Trading_SOA.xlsx'])
    expect(names('ap')).toEqual(['Our_AP_Ledger_Gulf_Supplies.xlsx', 'Gulf_Supplies_SOA.xlsx'])
    expect(names('general', 0)).toEqual(['HR_Employee_Master.xlsx', 'WPS_Payroll_Register_Sep2026.xlsx'])
    expect(names('general', 1)).toEqual(['Intercompany_EntityA_Dubai.xlsx', 'Intercompany_EntityB_AbuDhabi.xlsx'])
  })
  it('explains when samples are missing', () => {
    expect(() => pickSampleFiles(SAMPLE_SETS.bank[0], [])).toThrow(/missing/)
  })
})
