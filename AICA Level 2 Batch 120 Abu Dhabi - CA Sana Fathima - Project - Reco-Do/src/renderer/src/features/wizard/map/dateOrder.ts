import type { ReconConfig, Side } from '@shared/contracts'

export type Order = 'DMY' | 'MDY'

/** Whether the date-order control is worth showing, and the order each side is read in. */
export function dateOrderState(
  cfg: ReconConfig,
  detected: { a: Order | 'ambiguous'; b: Order | 'ambiguous' }
): { show: boolean; a: Order; b: Order; ambiguous: Record<Side, boolean> } {
  const hasDate = cfg.keys.some((k) => k.use && k.type === 'date')
  const a: Order = cfg.dateOrderA ?? (detected.a === 'ambiguous' ? 'DMY' : detected.a)
  const b: Order = cfg.dateOrderB ?? (detected.b === 'ambiguous' ? 'DMY' : detected.b)
  const ambiguous = { A: detected.a === 'ambiguous', B: detected.b === 'ambiguous' }
  const disagree = detected.a !== 'ambiguous' && detected.b !== 'ambiguous' && detected.a !== detected.b
  // Also shown once the user has chosen an order, so the choice can be changed back.
  const show = hasDate && (ambiguous.A || ambiguous.B || disagree || !!cfg.dateOrderA || !!cfg.dateOrderB)
  return { show, a, b, ambiguous }
}
