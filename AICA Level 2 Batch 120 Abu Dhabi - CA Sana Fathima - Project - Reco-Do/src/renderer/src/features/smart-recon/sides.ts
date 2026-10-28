// Short side names for Smart Recon labels ("1 bank : many GL"), and line descriptions for suggestion cards.

import type { EngineLine, ReconConfig, ReconResult, Side } from '@shared/contracts'

/** Short, capitalised side word: Bank / GL, Ours / Theirs, Card / GL, or the General side names. */
export function shortSide(cfg: ReconConfig, side: Side): string {
  switch (cfg.moduleId) {
    case 'bank':
      return side === 'A' ? 'Bank' : 'GL'
    case 'cc':
      return side === 'A' ? 'Card' : 'GL'
    case 'ar':
    case 'ap':
      return side === 'A' ? 'Ours' : 'Theirs'
    default:
      return (side === 'A' ? cfg.sideAName : cfg.sideBName) || (side === 'A' ? 'File A' : 'File B')
  }
}

export function lineIndex(result: ReconResult): Map<string, EngineLine> {
  const m = new Map<string, EngineLine>()
  for (const l of result.linesA) m.set(l.id, l)
  for (const l of result.linesB) m.set(l.id, l)
  return m
}

function cellText(v: unknown): string {
  if (v === null || v === undefined) return ''
  if (v instanceof Date) return ''
  return String(v).replace(/\s+/g, ' ').trim()
}

/** The line's reference/description: the first mapped ID/text key with a value, then the party. */
export function lineLabel(cfg: ReconConfig, l: EngineLine): { text: string; party: string } {
  let text = ''
  for (const k of cfg.keys) {
    if (!k.use || (k.type !== 'id' && k.type !== 'text' && k.type !== 'number')) continue
    const v = cellText(l.values[l.side === 'A' ? k.columnA : k.columnB])
    if (v) {
      text = v
      break
    }
  }
  const partyCol = l.side === 'A' ? cfg.partyColumnA : cfg.partyColumnB
  const party = partyCol ? cellText(l.values[partyCol]) : ''
  return { text, party: party && !text.toUpperCase().includes(party.toUpperCase()) ? party : '' }
}
