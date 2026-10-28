// Builds the starting Map & Rules configuration and the session metadata. Pure (engine + parsing only).

import type { ParsedTable, ReconConfig, ReconMeta, SavedMapping } from '@shared/contracts'
import { getModule, type ModuleId } from '@shared/modules'
import { DEFAULT_REFERENCE_PREFIXES } from '@shared/parsing'
import { suggestKeys } from '@engine/index'
import { sortedHeaders, syncAmountKey } from './keys'

export function suggestedConfig(moduleId: ModuleId, tableA: ParsedTable, tableB: ParsedTable, sideAName: string, sideBName: string, currency: string): ReconConfig {
  const m = getModule(moduleId)
  const s = suggestKeys(moduleId, tableA, tableB)
  const keys =
    moduleId === 'general'
      ? s.keys.map((k) => {
          // Short key names ("Emp ID" rather than "Emp ID ↔ Employee No"); the columns are shown beside it.
          return k.name.includes('↔') ? { ...k, name: k.columnA } : k
        })
      : s.keys
  return syncAmountKey({
    moduleId,
    sideAName,
    sideBName,
    keys,
    amountA: s.amountA,
    amountB: s.amountB,
    sign: m?.defaultSign ?? 'same',
    partyColumnA: s.partyColumnA,
    partyColumnB: s.partyColumnB,
    referencePrefixes: [...DEFAULT_REFERENCE_PREFIXES],
    currency
  })
}

/** A saved mapping/template's config adapted to this run (current currency; module labels for fixed modules). */
export function configFromSaved(saved: SavedMapping, moduleId: ModuleId, currency: string): ReconConfig {
  const m = getModule(moduleId)
  const cfg: ReconConfig = { ...saved.config, moduleId, currency, keys: saved.config.keys.map((k) => ({ ...k })) }
  if (!m?.editableSideNames) {
    cfg.sideAName = m?.sideA ?? cfg.sideAName
    cfg.sideBName = m?.sideB ?? cfg.sideBName
  }
  return cfg
}

export function savedRecord(input: {
  id: string
  name: string
  moduleId: ModuleId
  tableA: ParsedTable
  tableB: ParsedTable
  config: ReconConfig
  createdAt?: string
}): SavedMapping {
  const now = new Date().toISOString()
  return {
    id: input.id,
    name: input.name.trim(),
    moduleId: input.moduleId,
    headersA: sortedHeaders(input.tableA.columns),
    headersB: sortedHeaders(input.tableB.columns),
    config: input.config,
    createdAt: input.createdAt ?? now,
    updatedAt: now
  }
}

export function buildMeta(input: {
  accountLabel: string
  period: string
  tableA: ParsedTable
  tableB: ParsedTable
  mappingName?: string
  preparer: string
  currency: string
}): ReconMeta {
  const { tableA: a, tableB: b } = input
  return {
    accountLabel: input.accountLabel.trim() || 'Untitled reconciliation',
    period: input.period.trim(),
    fileA: { name: a.fileName, sheet: a.sheetName, rows: a.rows.length },
    fileB: { name: b.fileName, sheet: b.sheetName, rows: b.rows.length },
    mappingName: input.mappingName,
    preparer: input.preparer,
    currency: input.currency,
    balances: { openingA: a.openingBalance, closingA: a.closingBalance, openingB: b.openingBalance, closingB: b.closingBalance }
  }
}

/** Final config for a run: current side names and currency. */
export function finalConfig(cfg: ReconConfig, sideAName: string, sideBName: string, currency: string): ReconConfig {
  return syncAmountKey({ ...cfg, sideAName: sideAName.trim() || 'File A', sideBName: sideBName.trim() || 'File B', currency })
}
