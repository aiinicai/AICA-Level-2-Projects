import { describe, expect, it } from 'vitest'
import { buildSummaryHtml, escapeHtml } from '@export/index'
import { bankFixture, generalNoAmountFixture, largeFixture } from './fixtures'

const GENERATED = new Date(2026, 9, 3, 14, 30)

function assertSelfContained(html: string): void {
  expect(html).not.toMatch(/https?:\/\//i)
  expect(html).not.toMatch(/\/\/[a-z0-9.-]+\.[a-z]{2,}/i)
  expect(html).not.toMatch(/<script/i)
  expect(html).not.toMatch(/<link/i)
  expect(html).not.toMatch(/<img/i)
  expect(html).not.toMatch(/url\(/i)
  expect(html).not.toMatch(/@import/i)
  expect(html).not.toMatch(/\ssrc=/i)
}

describe('buildSummaryHtml (bank)', () => {
  const { session, statement } = bankFixture()
  const html = buildSummaryHtml(session, statement, { generatedAt: GENERATED })

  it('is a complete, self-contained A4 document', () => {
    expect(html.startsWith('<!DOCTYPE html>')).toBe(true)
    expect(html).toContain('</html>')
    expect(html).toContain('size: A4')
    expect(html).toContain('counter(page)')
    assertSelfContained(html)
  })

  it('has the Reco-Do header and summary details', () => {
    expect(html).toContain('<span>Reco-Do</span>')
    expect(html).toContain('Bank Reconciliation')
    expect(html).toContain('ENBD Current A/c')
    expect(html).toContain('September 2026')
    expect(html).toContain('ENBD_Current_Statement_Sep2026.xlsx')
    expect(html).toContain('ENBD Current A/c ↔ GL 101200')
    expect(html).toContain('Generated 03-Oct-2026 14:30')
  })

  it('shows KPI tiles per tier with amounts', () => {
    expect(html).toContain('class="kpi"')
    // Absolute sums, consistent with the on-screen KPI cards.
    expect(html).toContain('AED 48,150.00')
    expect(html).toContain('AED 8,540.00')
    expect(html).not.toContain('AED -8,540.00')
    expect(html).toContain('Unmatched – Bank statement')
    expect(html).toContain('Unmatched – General ledger extract')
    expect(html).toContain('AI assisted')
  })

  it('renders the statement and a nil unexplained difference', () => {
    expect(html).toContain('Balance as per bank statement')
    expect(html).toContain('100,000.00')
    expect(html).toContain('103,742.25')
    expect(html).toMatch(/<tr class="diff ok"><td>Unexplained difference<\/td><td class="num">0\.00<\/td><\/tr>/)
  })

  it('lists top open items, largest first, with auto labels', () => {
    const a = html.indexOf('Bank statement: top open items')
    const b = html.indexOf('General ledger extract: top open items')
    expect(a).toBeGreaterThan(0)
    expect(b).toBeGreaterThan(a)
    const sideA = html.slice(a, b)
    expect(sideA.indexOf('-8,540.00')).toBeLessThan(sideA.indexOf('-1,200.00'))
    expect(sideA).toContain('Probable bank charge – post JV')
  })

  it('has a sign-off block showing draft status', () => {
    expect(html).toContain('Prepared by')
    expect(html).toContain('Sana Fathima')
    expect(html).toContain('Draft, not finalised')
  })

  it('escapes user text', () => {
    const fx = bankFixture()
    fx.session.meta.accountLabel = '<b>Cash & "Bank"</b>'
    const out = buildSummaryHtml(fx.session, fx.statement, { generatedAt: GENERATED })
    expect(out).not.toContain('<b>Cash')
    expect(out).toContain(escapeHtml('<b>Cash & "Bank"</b>'))
  })
})

describe('buildSummaryHtml (General, no amount)', () => {
  const { session, statement } = generalNoAmountFixture()
  const html = buildSummaryHtml(session, statement, { generatedAt: GENERATED })

  it('shows counts, finalised status and no amounts', () => {
    assertSelfContained(html)
    expect(html).toContain('Finalised')
    expect(html).not.toContain('Draft, not finalised')
    expect(html).not.toContain('AED 0.00')
    expect(html).not.toMatch(/Amount \(AED\)/)
    expect(html).toContain('Records')
    expect(html).toMatch(/<tr class="diff ok"><td>Count difference<\/td><td class="num">0<\/td><\/tr>/)
    expect(html).toContain('HR master: top open items')
    expect(html).toContain('E005')
  })
})

describe('buildSummaryHtml (large)', () => {
  it('caps open items at 25 per side', () => {
    const { session, statement } = largeFixture(2000)
    const html = buildSummaryHtml(session, statement, { generatedAt: GENERATED })
    expect(html).toContain('Showing the largest 25 of 400 open items')
    assertSelfContained(html)
  })
})
