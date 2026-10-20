// Self-contained, print-ready HTML summary of a reconciliation (rendered to PDF by Electron printToPDF).
// No external resources: inline CSS only, system fonts, no scripts, no images, no URLs.

import type { ReconSession, Statement } from '../shared/contracts'
import { formatAmount, formatDate } from '../shared/format'
import {
  OPEN_STATUS_LABELS,
  TIER_COLOURS,
  buildExportModel,
  cellToText,
  excelRowOf,
  formatDateTime,
  parseIso,
  type DisplayTier,
  type ExportModel,
  type OpenItem
} from './model'
import { findUnexplainedIndex, isZero } from './statement'
import type { ExportOptions } from './workbook'

export const TOP_OPEN_ITEMS = 25

const ESCAPES: Record<string, string> = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }

export function escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (c) => ESCAPES[c])
}

/** Escapes text for a CSS string literal (used in @page margin boxes). */
function cssString(s: string): string {
  // < and > become CSS escapes so user text can never close the <style> element.
  const body = s
    .replace(/[\\"]/g, (c) => `\\${c}`)
    .replace(/</g, '\\3C ')
    .replace(/>/g, '\\3E ')
    .replace(/[\r\n]+/g, ' ')
  return `"${body}"`
}

function count(n: number): string {
  return Math.round(n).toLocaleString('en-US')
}

function amount(n: number | null): string {
  return n === null ? '' : formatAmount(n)
}

function topOpenItems(m: ExportModel, items: OpenItem[]): OpenItem[] {
  const copy = [...items]
  if (m.hasAmount) {
    copy.sort((a, b) => Math.abs(b.line.amount ?? 0) - Math.abs(a.line.amount ?? 0))
  } else {
    copy.sort((a, b) => (b.ageDays ?? -1) - (a.ageDays ?? -1))
  }
  return copy.slice(0, TOP_OPEN_ITEMS)
}

function kpiTile(label: string, tier: DisplayTier | null, countText: string, sub: string | null): string {
  const colour = tier ? TIER_COLOURS[tier] : '#3E4A5C'
  return `<div class="kpi" style="border-top-color:${colour}">
  <div class="kpi-label" style="color:${colour}">${escapeHtml(label)}</div>
  <div class="kpi-count">${escapeHtml(countText)}</div>
  ${sub !== null ? `<div class="kpi-sub">${escapeHtml(sub)}</div>` : ''}
</div>`
}

function statementTable(m: ExportModel, statement: Statement): string {
  const isCount = statement.kind === 'record-count'
  const fmt = (v: number): string => (isCount ? count(v) : formatAmount(v))
  const idx = findUnexplainedIndex(statement)
  const diffRow = (label: string, value: number): string => {
    const ok = isZero(value, statement.kind)
    return `<tr class="diff ${ok ? 'ok' : 'bad'}"><td>${escapeHtml(label)}</td><td class="num">${fmt(value)}</td></tr>`
  }
  const rows = statement.lines.map((l, i) => {
    if (i === idx) return diffRow(l.label, l.value)
    return `<tr class="${l.isTotal ? 'total' : 'item'}"><td>${escapeHtml(l.label)}</td><td class="num">${fmt(l.value)}</td></tr>`
  })
  if (idx < 0) {
    rows.push(diffRow(isCount ? 'Unexplained count difference' : 'Unexplained difference', statement.unexplainedDifference))
  }
  return `<table class="statement">
  <thead><tr><th>${escapeHtml(statement.title)}</th><th class="num">${isCount ? 'Records' : escapeHtml(`Amount (${m.currency})`)}</th></tr></thead>
  <tbody>${rows.join('')}</tbody>
</table>`
}

function openItemsTable(m: ExportModel, side: 'A' | 'B'): string {
  const items = side === 'A' ? m.openA : m.openB
  const name = side === 'A' ? m.sideAName : m.sideBName
  const keyCols = side === 'A' ? m.keyColumnsA : m.keyColumnsB
  const hasDate = side === 'A' ? m.hasDateA : m.hasDateB
  const top = topOpenItems(m, items)
  const heading = `<h3>${escapeHtml(name)}: top open items</h3>`
  if (items.length === 0) return `${heading}<p class="muted">No open items on this side.</p>`
  const head = [
    '<th>Row</th>',
    hasDate ? '<th>Date</th>' : '',
    `<th>${escapeHtml(keyCols.map((k) => k.column).join(' · ') || 'Details')}</th>`,
    '<th>Status</th>',
    hasDate && m.asOf ? '<th class="num">Age (days)</th>' : '',
    m.hasAmount ? `<th class="num">Amount (${escapeHtml(m.currency)})</th>` : ''
  ].join('')
  const body = top
    .map((it) => {
      const l = it.line
      const details = keyCols
        .map((k) => cellToText(l.values[k.column] ?? null))
        .filter((t) => t !== '')
        .join(' · ')
      return `<tr>
<td>${escapeHtml(excelRowOf(l.rowId))}</td>
${hasDate ? `<td class="nowrap">${l.date ? formatDate(l.date) : ''}</td>` : ''}
<td>${escapeHtml(details)}${it.comment ? `<div class="comment">${escapeHtml(it.comment)}</div>` : ''}</td>
<td class="nowrap">${escapeHtml(OPEN_STATUS_LABELS[it.status])}</td>
${hasDate && m.asOf ? `<td class="num">${it.ageDays === null ? '' : count(it.ageDays)}</td>` : ''}
${m.hasAmount ? `<td class="num">${amount(l.amount)}</td>` : ''}
</tr>`
    })
    .join('')
  const more =
    items.length > top.length
      ? `<p class="muted small">Showing the ${m.hasAmount ? 'largest' : 'oldest'} ${top.length} of ${count(items.length)} open items. The full list is in the Excel export.</p>`
      : ''
  return `${heading}<table class="items"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>${more}`
}

const CSS = `
@page {
  size: A4 portrait;
  margin: 14mm 12mm 16mm 12mm;
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
  font-family: 'Segoe UI', 'Inter Variable', Arial, Helvetica, sans-serif;
  font-size: 9.5pt;
  color: #1a2433;
  background: #ffffff;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}
.num { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
.nowrap { white-space: nowrap; }
.muted { color: #5b6676; }
.small { font-size: 8pt; }
header.brand {
  display: flex; align-items: center; justify-content: space-between;
  background: #0f2a44; color: #ffffff; padding: 10px 14px; border-radius: 6px;
}
.logo { display: flex; align-items: center; gap: 8px; font-weight: 700; font-size: 15pt; letter-spacing: 0.2px; }
.logo-mark {
  display: inline-block; width: 22px; height: 22px; border-radius: 5px; background: #3fc3a0;
  color: #0f2a44; font-size: 11pt; line-height: 22px; text-align: center; font-weight: 800;
}
.brand-right { text-align: right; font-size: 8.5pt; color: #c9d6e6; }
.brand-right strong { color: #ffffff; font-size: 10pt; }
h1 { font-size: 15pt; margin: 14px 0 2px 0; color: #0f2a44; }
h2 { font-size: 11.5pt; margin: 16px 0 6px 0; color: #0f2a44; border-bottom: 1px solid #e3e8ef; padding-bottom: 3px; }
h3 { font-size: 10pt; margin: 12px 0 4px 0; color: #1b3a5c; }
.status-pill {
  display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 8.5pt; font-weight: 600;
}
.status-final { background: #e3f4ec; color: #0d6a4b; }
.status-draft { background: #fdf0dc; color: #7e5000; }
table { width: 100%; border-collapse: collapse; }
table.meta td { padding: 3px 6px; vertical-align: top; border-bottom: 1px solid #eef1f5; }
table.meta td.k { width: 28%; color: #5b6676; font-weight: 600; }
.kpis { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 4px; }
.kpi {
  flex: 1 1 0; min-width: 22mm; border: 1px solid #e3e8ef; border-top: 3px solid #3e4a5c; border-radius: 5px;
  padding: 6px 7px; break-inside: avoid;
}
.kpi-label { font-size: 7.5pt; font-weight: 700; text-transform: uppercase; letter-spacing: 0.3px; }
.kpi-count { font-size: 14pt; font-weight: 700; margin-top: 2px; }
.kpi-sub { font-size: 8pt; color: #5b6676; font-variant-numeric: tabular-nums; }
table.statement { margin-top: 2px; }
table.statement th { text-align: left; background: #e8ecf2; padding: 5px 8px; font-size: 9pt; }
table.statement th.num { text-align: right; }
table.statement td { padding: 4px 8px; border-bottom: 1px solid #eef1f5; }
table.statement tr.item td:first-child { padding-left: 20px; }
table.statement tr.total td { font-weight: 700; border-top: 1px solid #1a2433; }
table.statement tr.diff td { font-weight: 700; border-top: 1px solid; border-bottom: 3px double; }
table.statement tr.diff.ok td { background: #e3f4ec; color: #0d6a4b; border-color: #11865f; }
table.statement tr.diff.bad td { background: #fbe4e4; color: #9a2022; border-color: #c0292b; }
table.items { font-size: 8.5pt; }
table.items th { text-align: left; background: #f4f6f9; padding: 4px 6px; border-bottom: 1px solid #c9d1dc; }
table.items th.num { text-align: right; }
table.items td { padding: 3px 6px; border-bottom: 1px solid #eef1f5; vertical-align: top; }
table.items tr { break-inside: avoid; }
.comment { color: #c25500; font-size: 7.5pt; margin-top: 1px; }
section { break-inside: auto; }
.signoff { display: flex; gap: 10px; margin-top: 6px; break-inside: avoid; }
.sign-box { flex: 1 1 0; border: 1px solid #e3e8ef; border-radius: 5px; padding: 8px 10px; min-height: 26mm; }
.sign-box .k { font-size: 7.5pt; text-transform: uppercase; color: #5b6676; font-weight: 700; letter-spacing: 0.3px; }
.sign-box .v { font-size: 10pt; font-weight: 600; margin-top: 3px; }
.sign-line { border-bottom: 1px solid #8a97ab; height: 14mm; }
footer.doc-end { margin-top: 14px; padding-top: 6px; border-top: 1px solid #e3e8ef; font-size: 7.5pt; color: #5b6676; display: flex; justify-content: space-between; }
`

/** Builds the print-ready HTML summary for Electron printToPDF (A4). */
export function buildSummaryHtml(session: ReconSession, statement: Statement, options: ExportOptions = {}): string {
  const m = buildExportModel(session, { generatedAt: options.generatedAt })
  const { meta } = session
  const t = m.totals
  const finalised = session.finalised
  const finalisedAt = finalised ? parseIso(finalised.at) : null
  const generated = formatDateTime(m.generatedAt)
  const amt = (n: number | null): string | null => (m.hasAmount && n !== null ? `${m.currency} ${formatAmount(n)}` : null)
  const lines = (a: number, b: number): string => `${count(a)} ${escapeHtml(m.sideAName)} / ${count(b)} ${escapeHtml(m.sideBName)} lines`

  const kpis = [
    kpiTile('Matched', 'matched', count(t.matched.pairs), amt(t.matched.amount) ?? `${count(t.matched.linesA + t.matched.linesB)} lines`),
    kpiTile('Doubtful', 'doubtful', count(t.doubtful.pairs), amt(t.doubtful.amount) ?? 'pending review'),
    kpiTile('Likely', 'likely', count(t.likely.pairs), amt(t.likely.amount) ?? 'pending review'),
    kpiTile(`Unmatched – ${m.sideAName}`, 'unmatched', count(t.unmatchedA.linesA), amt(t.unmatchedA.amount) ?? 'lines'),
    kpiTile(`Unmatched – ${m.sideBName}`, 'unmatched', count(t.unmatchedB.linesB), amt(t.unmatchedB.amount) ?? 'lines'),
    kpiTile('AI assisted', 'ai', count(t.assisted.pairs), amt(t.assisted.amount) ?? `${count(t.aiPending)} pending`)
  ].join('')

  const statusPill = finalised
    ? `<span class="status-pill status-final">Finalised</span>`
    : `<span class="status-pill status-draft">Draft, not finalised</span>`

  const metaRows: Array<[string, string]> = [
    ['Module', m.moduleName],
    ['Account', meta.accountLabel],
    ['Period', meta.period],
    ['Sides', `${m.sideAName} (A) vs ${m.sideBName} (B)`],
    [`File – ${m.sideAName}`, `${meta.fileA.name} · sheet "${meta.fileA.sheet}" · ${count(meta.fileA.rows)} rows`],
    [`File – ${m.sideBName}`, `${meta.fileB.name} · sheet "${meta.fileB.sheet}" · ${count(meta.fileB.rows)} rows`],
    ['Mapping / template', meta.mappingName || 'None (mapped manually)'],
    ['Matching keys', m.keys.filter((k) => k.use).map((k) => k.name).join(', ') || 'None'],
    ['Currency', m.currency],
    ['Ageing as of', m.asOf ? `${formatDate(m.asOf)} (${m.asOfSource === 'period-end' ? 'period end' : 'latest date in the data'})` : 'No dates in the data']
  ]

  const footerLeft = `Reco-Do · ${meta.accountLabel} · ${meta.period}`
  const footerCss = `
@page {
  @bottom-left { content: ${cssString(footerLeft)}; font-family: 'Segoe UI', Arial, sans-serif; font-size: 7.5pt; color: #5b6676; }
  @bottom-right { content: "Page " counter(page) " of " counter(pages); font-family: 'Segoe UI', Arial, sans-serif; font-size: 7.5pt; color: #5b6676; }
}`

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${escapeHtml(`Reco-Do – ${m.moduleName} – ${meta.accountLabel} – ${meta.period}`)}</title>
<style>${CSS}${footerCss}</style>
</head>
<body>
<header class="brand">
  <div class="logo"><span class="logo-mark">R</span><span>Reco-Do</span></div>
  <div class="brand-right"><strong>${escapeHtml(m.moduleName)}</strong><br>Generated ${escapeHtml(generated)}</div>
</header>

<h1>${escapeHtml(meta.accountLabel)}</h1>
<div class="muted">${escapeHtml(meta.period)} · ${escapeHtml(m.sideAName)} vs ${escapeHtml(m.sideBName)} · ${statusPill}</div>

<section>
<h2>Summary</h2>
<table class="meta"><tbody>
${metaRows.map(([k, v]) => `<tr><td class="k">${escapeHtml(k)}</td><td>${escapeHtml(v)}</td></tr>`).join('\n')}
</tbody></table>
</section>

<section>
<h2>Results by tier</h2>
<div class="kpis">${kpis}</div>
<p class="muted small">Matched, Doubtful and Likely show pairs; Unmatched shows lines. ${
    m.hasAmount ? `Amounts are absolute sums (${escapeHtml(m.sideAName)} lines for pairs, each file's own lines for unmatched), as on screen. ` : ''
  }AI assisted pairs are included in Matched. Total lines: ${lines(m.session.result.linesA.length, m.session.result.linesB.length)}.</p>
</section>

<section>
<h2>Reconciliation statement</h2>
${statementTable(m, statement)}
</section>

<section>
<h2>Top open items</h2>
${openItemsTable(m, 'A')}
${openItemsTable(m, 'B')}
</section>

<section>
<h2>Sign-off</h2>
<div class="signoff">
  <div class="sign-box"><div class="k">Prepared by</div><div class="v">${escapeHtml(meta.preparer || 'Not recorded')}</div><div class="muted small">Prepared ${escapeHtml(
    formatDateFromIso(session.createdAt) ?? generated
  )}</div></div>
  <div class="sign-box"><div class="k">Finalised</div><div class="v">${
    finalised
      ? `${escapeHtml(finalised.by)}${finalisedAt ? `<div class="muted small">${escapeHtml(formatDateTime(finalisedAt))}</div>` : ''}`
      : 'Draft, not finalised'
  }</div></div>
  <div class="sign-box"><div class="k">Reviewed by (signature)</div><div class="sign-line"></div><div class="muted small">Date:</div></div>
</div>
</section>

<footer class="doc-end">
  <span>Reco-Do · ${escapeHtml(m.moduleName)} · ${escapeHtml(meta.accountLabel)} · ${escapeHtml(meta.period)}</span>
  <span>Generated ${escapeHtml(generated)} · ${count(session.audit.length)} audit entries</span>
</footer>
</body>
</html>`
}

function formatDateFromIso(iso: string): string | null {
  const d = parseIso(iso)
  return d ? formatDate(d) : null
}
