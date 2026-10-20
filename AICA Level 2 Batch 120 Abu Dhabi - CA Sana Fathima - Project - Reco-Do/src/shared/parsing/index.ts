// Shared parsing module: used by the recon wizard, the matching engine and the tools.

export { readWorkbook, detectDelimiter, parseCsv, decodeText, type WorkbookReadResult } from './workbook'
export { detectHeaderRow, looksLikeDataRow, findTwoRowHeader, mergeHeaderRows } from './header'
export { parseTable, buildColumnNames, NO_HEADER_ROW, type ParseTableOptions } from './table'
export { parseAmount, detectDecimalSeparator, type ParsedAmount, type ParseAmountOptions } from './amount'
export {
  parseDate,
  detectDateOrder,
  excelSerialToDate,
  isDateLike,
  makeDate,
  EXCEL_SERIAL_MIN,
  EXCEL_SERIAL_MAX,
  type DateOrder
} from './date'
export { inferColumnType } from './column-type'
export { normaliseText, valueOverlap, cellKey, DEFAULT_REFERENCE_PREFIXES, type ValueOverlapOptions } from './text'
export { headerSimilarity, levenshtein } from './similarity'
