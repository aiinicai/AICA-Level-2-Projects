import { describe, expect, it } from 'vitest'
import type { MatchKey } from '@shared/contracts'
import { buildStatement, reconcile } from '@engine/index'
import { amountKey, config, d, dateKey, meta, metaFor, refKey, table } from './helpers'

const dc = { kind: 'debit-credit', debit: 'Debit', credit: 'Credit' } as const
const cols = ['Date', 'Ref', 'Debit', 'Credit']

describe('bank statement', () => {
  // Bank: balance = opening + credits − debits. GL: balance = opening + debits − credits. Opening 1,000 both.
  const bank = table(cols, [
    [d(2026, 9, 1), 'T1', null, 500], // deposit, in GL
    [d(2026, 9, 2), 'C1', 200, null], // cheque, in GL
    [d(2026, 9, 3), 'X', 10, null], // bank charge, not in GL
    [d(2026, 9, 4), 'INT', null, 5], // interest, not in GL
    [d(2026, 9, 5), 'C9', 8450, null] // cheque booked 8,540 in GL (transposition)
  ])
  const gl = table(cols, [
    [d(2026, 9, 1), 'T1', 500, null],
    [d(2026, 9, 2), 'C1', null, 200],
    [d(2026, 9, 5), 'C2', null, 300], // unpresented cheque
    [d(2026, 9, 6), 'D1', 700, null], // uncredited deposit
    [d(2026, 9, 5), 'C9', null, 8540]
  ])
  const cfg = config([refKey(), dateKey(3), amountKey()], { moduleId: 'bank', sign: 'inverse', amountA: dc, amountB: dc })
  const r = reconcile(bank, gl, cfg)
  // bank closing = 1000 + 500 + 5 − 200 − 10 − 8450 = −7155; GL closing = 1000 + 500 + 700 − 200 − 300 − 8540 = −6840
  const st = buildStatement(r, meta({ balances: { openingA: 1000, closingA: -7155, openingB: 1000, closingB: -6840 } }))

  it('has every section and ties to 0.00', () => {
    expect(st.kind).toBe('bank')
    const v = Object.fromEntries(st.lines.map((l) => [l.label.split(' —')[0].split(' (')[0], l.value]))
    expect(v['Balance as per bank statement']).toBe(-7155)
    expect(v['Less: unpresented payments']).toBe(-300)
    expect(v['Add: uncredited deposits']).toBe(700)
    expect(v['Less: bank credits not in GL']).toBe(-5)
    expect(v['Add: bank debits not in GL']).toBe(10)
    expect(v['Less: possible transposition error on C9']).toBe(-90)
    expect(v['Adjusted balance']).toBe(-6840)
    expect(v['Balance as per general ledger']).toBe(-6840)
    expect(st.unexplainedDifference).toBe(0)
  })

  it('drill-down ids are attached to item lines', () => {
    expect(st.lines.find((l) => l.label.startsWith('Less: unpresented'))?.lineIds).toEqual(['B:r4'])
  })

  it('a wrong balance shows as an unexplained difference', () => {
    const off = buildStatement(r, meta({ balances: { openingA: 1000, closingA: -7155, openingB: 1000, closingB: -6800 } }))
    expect(off.unexplainedDifference).toBe(-40)
  })

  it('without balances in the files it still ties, using the lines', () => {
    expect(buildStatement(r, meta()).unexplainedDifference).toBe(0)
  })
})

describe('ledger (AR) statement', () => {
  // Ours: debit-positive (receivable). Theirs: their AP view (credit = what they owe us).
  const ours = table(cols, [
    [d(2026, 9, 1), 'INV-1', 1000, null],
    [d(2026, 9, 2), 'INV-2', 2000, null], // not booked by customer
    [d(2026, 9, 3), 'PDC-9', null, 400], // payment in transit
    [d(2026, 9, 4), 'INV-3', 6875.5, null] // disputed
  ])
  const theirs = table(cols, [
    [d(2026, 9, 2), '1', null, 1000],
    [d(2026, 9, 5), 'DN-7', 50, null], // their debit note
    [d(2026, 9, 4), '3', null, 6785.5]
  ])
  const cfg = config([refKey(), dateKey(7), amountKey()], { moduleId: 'ar', sign: 'inverse', amountA: dc, amountB: dc })
  const r = reconcile(ours, theirs, cfg)

  it('balance per our books → items → balance per their statement; unexplained 0.00', () => {
    // ours closing = 1000 + 2000 − 400 + 6875.50 = 9475.50 (opening 0); theirs = 1000 − 50 + 6785.50 = 7735.50
    const st = buildStatement(r, meta({ balances: { openingA: 0, closingA: 9475.5, openingB: 0, closingB: 7735.5 } }))
    expect(st.kind).toBe('ledger')
    const items = st.lines.filter((l) => /^(Less|Add)/.test(l.label) && l.value !== 0).map((l) => l.value)
    expect(items.sort((a, b) => a - b)).toEqual([-2000, -90, -50, 400])
    expect(st.lines.find((l) => l.label.startsWith('Balance as per customer'))?.value).toBe(7735.5)
    expect(st.unexplainedDifference).toBe(0)
  })
})

describe('general statements', () => {
  it('with an amount: balance per A → less A-only → add B-only → = balance per B', () => {
    const A = table(['Ref', 'Amount'], [['IC-1', 100], ['IC-2', 50], ['IC-3', 15300]])
    const B = table(['Ref', 'Amount'], [['IC-1', 100], ['IC-4', -20], ['IC-3', 15000]])
    const r = reconcile(A, B, config([refKey(), amountKey()], { sideAName: 'Entity A', sideBName: 'Entity B' }))
    const st = buildStatement(r, meta({ balances: { openingA: 1000, closingA: 16450, openingB: 1000, closingB: 16080 } }))
    expect(st.kind).toBe('general-amount')
    expect(st.lines[0]).toMatchObject({ label: 'Balance per Entity A (Sep 2026)', value: 16450 })
    expect(st.lines.find((l) => l.label.startsWith('Less: items in Entity A'))?.value).toBe(-50)
    expect(st.lines.find((l) => l.label.startsWith('Add: items in Entity B'))?.value).toBe(-20)
    expect(st.lines.find((l) => l.label.includes('IC-3'))?.value).toBe(-300)
    expect(st.unexplainedDifference).toBe(0)
  })

  it('without an amount: record-count statement, difference 0', () => {
    const emp: MatchKey = { id: 'e', name: 'Emp ID', type: 'id', use: true, columnA: 'Emp', columnB: 'Emp', identifying: true, textRule: 'normalised' }
    const name: MatchKey = { id: 'n', name: 'Name', type: 'text', use: true, columnA: 'Name', columnB: 'Name', identifying: false, textRule: 'normalised' }
    const A = table(['Emp', 'Name'], [['001', 'Ali'], ['002', 'Sara'], ['003', 'Omar']])
    const B = table(['Emp', 'Name'], [['1', 'Ali'], ['2', 'Sarah'], ['9', 'Ghost'], ['10', 'X']])
    const r = reconcile(A, B, config([emp, name], { amountA: undefined, amountB: undefined, sideAName: 'HR', sideBName: 'Payroll' }))
    const st = buildStatement(r, metaFor(A, B))
    expect(st.kind).toBe('record-count')
    expect(st.lines.map((l) => [l.label, l.value])).toEqual([
      ['Records in HR', 3],
      ['  = Matched', 1],
      ['  + Doubtful / Likely pending', 1],
      ['  + Only in HR', 1],
      ['Records in Payroll', 4],
      ['  = Matched', 1],
      ['  + Doubtful / Likely pending', 1],
      ['  + Only in Payroll', 2],
      ['Count difference (HR)', 0],
      ['Count difference (Payroll)', 0]
    ])
    expect(st.unexplainedDifference).toBe(0)
  })
})
