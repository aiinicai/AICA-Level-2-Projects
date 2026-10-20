// Reco-Do matching engine: pure TypeScript (no React, no DOM). See docs/CONTRACTS.md, "Engine".

export { validateConfig, NO_IDENTIFYING_KEY_MESSAGE } from './validate'
export { buildLines, signedAmount, detectNegativeCreditColumn, detectConfigDateOrders, detectColumnDateOrder, type NegativeCreditInfo } from './lines'
export { reconcile } from './reconcile'
export { suggestKeys, detectAmountLayout, detectSignMismatch, previewFirstPair } from './suggest'
export { findGroupMatches, type GroupMatchOptions } from './smart/grouping'
export { findPartialReferenceMatches, extractTokens } from './smart/partialRef'
export { buildStatement } from './statement'
export {
  acceptPair,
  rejectPair,
  manualMatch,
  unmatchPair,
  addNote,
  addSuggestions,
  approveSuggestion,
  rejectSuggestion,
  canFinalise,
  finalise,
  createSession,
  FINALISED_MESSAGE
} from './review'
export { summariseForHistory, ageingBucket, type AgeingBucket } from './history'
export { amountFlags, isDigitSwap } from './reasons'
export { buildAiPayload, parseAiResponse, parseAiResponseDetailed, mergeSuggestions, AiResponseError, type AiRequestBody } from './smart/ai'
