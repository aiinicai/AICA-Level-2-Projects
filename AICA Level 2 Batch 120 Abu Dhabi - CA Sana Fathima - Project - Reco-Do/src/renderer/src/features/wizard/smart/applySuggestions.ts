import type { ReconSession, Suggestion } from '@shared/contracts'
import { addSuggestions } from '@engine/index'

/**
 * Adds Smart Recon results to the NEWEST session. Smart Recon can run for minutes while the user keeps
 * reviewing, so the results must never be applied to the session captured when the run started (that would
 * silently undo every decision made meanwhile).
 */
export function applySuggestions(latest: ReconSession, list: Suggestion[]): { next: ReconSession; added: number } {
  const next = addSuggestions(latest, list)
  return { next, added: next.suggestions.length - latest.suggestions.length }
}
