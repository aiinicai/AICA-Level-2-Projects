// Small helpers for rendering a Statement the same way in Excel and in the PDF summary.

import type { Statement, StatementKind } from '../shared/contracts'

/** Nil test: 0.00 for amounts (half a cent), 0 for record counts. */
export function isZero(value: number, kind: StatementKind): boolean {
  return kind === 'record-count' ? Math.round(value) === 0 : Math.abs(value) < 0.005
}

/**
 * Index of the line that already carries the unexplained difference, or -1 when the statement
 * does not include one (the renderer then appends it from `statement.unexplainedDifference`).
 */
export function findUnexplainedIndex(statement: Statement): number {
  const byLabel = statement.lines.findIndex((l) => /unexplained/i.test(l.label))
  if (byLabel >= 0) return byLabel
  const last = statement.lines.length - 1
  if (last >= 0) {
    const line = statement.lines[last]
    const sameValue =
      statement.kind === 'record-count'
        ? Math.round(line.value) === Math.round(statement.unexplainedDifference)
        : Math.abs(line.value - statement.unexplainedDifference) < 0.005
    if (/difference/i.test(line.label) && sameValue) return last
  }
  return -1
}
