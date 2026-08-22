import * as XLSX from 'xlsx';
import {
  BALANCE_SHEET_FIELDS,
  PROFIT_LOSS_FIELDS,
  QUARTERLY_FIELDS,
  RATIO_FIELDS,
} from './fieldDictionary';

const MONTH_ABBR = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'];
// Accepts "Mar 25", "Mar'25", "June 25", "March 26", "Sep-25" etc — abbreviated or full month names.
const MONTH_STRING_RE = /^([A-Za-z]{3,9})[.\s'’-]?(\d{2,4})$/;
const HEADER_SCAN_COLS = [1, 2, 3, 4, 5, 6, 7]; // columns B..H (0-indexed)
const MIN_HEADER_MATCHES = 4;

function normalizeLabel(raw) {
  if (raw === null || raw === undefined) return '';
  return String(raw).trim().replace(/\s+/g, ' ').toLowerCase();
}

function testRule(normalized, rule) {
  if (!normalized) return false;
  if (rule.equals) return normalized === rule.equals.toLowerCase();
  if (rule.contains) return normalized.includes(rule.contains.toLowerCase());
  return false;
}

function matchLabel(normalized, rules) {
  for (const rule of rules) {
    if (testRule(normalized, rule)) return true;
  }
  return false;
}

/** Excel date serials are day-granularity; some source formulas (e.g. chained EDATE) accumulate
 * floating-point drift in the time-of-day component (seen as e.g. 23:59:50 instead of midnight).
 * Rounding to the nearest UTC day before reading month/year absorbs that drift safely. */
function roundToUtcDay(date) {
  const rounded = new Date(Math.round(date.getTime() / 86400000) * 86400000);
  return { month: rounded.getUTCMonth(), year: rounded.getUTCFullYear() };
}

/** Extract {month(0-11), year} from a header-candidate cell, or null if it doesn't look like a period label. */
function parseMonthYear(value) {
  if (value instanceof Date && !isNaN(value.getTime())) {
    return roundToUtcDay(value);
  }
  if (typeof value === 'number' && isFinite(value) && value > 20000 && value < 60000) {
    // Defensive fallback: an Excel date serial that cellDates:true failed to convert
    // (e.g. missing/unrecognized number format on the cell).
    const parsed = XLSX.SSF.parse_date_code(value);
    if (parsed && parsed.y >= 1990 && parsed.y <= 2100 && parsed.m >= 1 && parsed.m <= 12) {
      return { month: parsed.m - 1, year: parsed.y };
    }
    return null;
  }
  if (typeof value === 'string') {
    const m = value.trim().match(MONTH_STRING_RE);
    if (!m) return null;
    const monthKey = m[1].slice(0, 3).toLowerCase();
    const monthIdx = MONTH_ABBR.indexOf(monthKey);
    if (monthIdx === -1) return null;
    let year = parseInt(m[2], 10);
    if (m[2].length === 2) year += year < 70 ? 2000 : 1900;
    return { month: monthIdx, year };
  }
  return null;
}

// Only these four fiscal-quarter-end months have a defined label rule (standard Indian FY).
const RECOGNIZED_MONTHS = new Set([2, 5, 8, 11]); // Mar, Jun, Sep, Dec (0-indexed)

function detectHeaderCandidates(matrix) {
  const candidates = [];
  for (let r = 0; r < matrix.length; r++) {
    const row = matrix[r] || [];
    const parsedCols = [];
    for (const c of HEADER_SCAN_COLS) {
      const my = parseMonthYear(row[c]);
      if (my && RECOGNIZED_MONTHS.has(my.month)) {
        parsedCols.push({ col: c, ...my });
      }
    }
    if (parsedCols.length >= MIN_HEADER_MATCHES) {
      const hasQuarter = parsedCols.some((p) => p.month !== 2); // anything not March
      const kind = hasQuarter ? 'quarterly' : 'annual';
      const columns = {};
      for (const p of parsedCols) {
        let label;
        if (p.month === 2) {
          // March: FYyy in an annual block, Q4 FYyy (same year) in a quarterly block.
          label = kind === 'quarterly' ? `Q4 FY${String(p.year).slice(-2)}` : `FY${String(p.year).slice(-2)}`;
        } else {
          const qNum = p.month === 5 ? 1 : p.month === 8 ? 2 : 3; // Jun/Sep/Dec
          label = `Q${qNum} FY${String(p.year + 1).slice(-2)}`;
        }
        columns[p.col] = label;
      }
      candidates.push({ row: r, kind, columns });
    }
  }
  return candidates;
}

/** Assigns each header candidate a row range it "owns" (down to just above the next candidate). */
function buildBlocks(candidates, totalRows) {
  const sorted = [...candidates].sort((a, b) => a.row - b.row);
  return sorted.map((c, i) => {
    const nextRow = i + 1 < sorted.length ? sorted[i + 1].row : totalRows;
    return { ...c, startRow: c.row + 1, endRow: nextRow - 1 };
  });
}

function findBlockByKind(blocks, kind) {
  return blocks.find((b) => b.kind === kind) || null;
}

/** First-match, top-to-bottom lookup within a block's row range. Label in `labelCol`, values start at `valueStartCol`. */
function lookupSeries(matrix, block, labelCol, rules) {
  if (!block) return { found: false, values: {} };
  for (let r = block.startRow; r <= Math.min(block.endRow, matrix.length - 1); r++) {
    const row = matrix[r];
    if (!row) continue;
    const normalized = normalizeLabel(row[labelCol]);
    if (!normalized) continue;
    if (matchLabel(normalized, rules)) {
      const values = {};
      for (const [colStr, periodLabel] of Object.entries(block.columns)) {
        const col = Number(colStr);
        const raw = row[col];
        values[periodLabel] = typeof raw === 'number' && isFinite(raw) ? raw : null;
      }
      return { found: true, values };
    }
  }
  return { found: false, values: {} };
}

function sheetToMatrix(sheet) {
  return XLSX.utils.sheet_to_json(sheet, { header: 1, raw: true, defval: null, blankrows: true });
}

function findSheetName(workbook, exactNames) {
  const names = workbook.SheetNames;
  for (const target of exactNames) {
    const found = names.find((n) => n.trim().toLowerCase() === target.toLowerCase());
    if (found) return found;
  }
  return null;
}

const BASIS_SHEETS = {
  Standalone: { financials: 'Financials_Standalone', ratios: 'Ratio Analysis' },
  Consolidated: { financials: 'Financials_Consol', ratios: 'Ratio Analysis_Conso' },
};

function periodSortKey(label) {
  const annual = label.match(/^FY(\d{2})$/);
  if (annual) return Number(annual[1]) * 10;
  const quarterly = label.match(/^Q([1-4]) FY(\d{2})$/);
  if (quarterly) return Number(quarterly[2]) * 10 + Number(quarterly[1]) - 1;
  return 0;
}

function collectPeriods(block) {
  if (!block) return [];
  const labels = [...new Set(Object.values(block.columns))];
  return labels.sort((a, b) => periodSortKey(a) - periodSortKey(b));
}

function computeDerivedMetrics(periods, bs, pl) {
  const derived = {};
  const getVal = (dict, key, period) => (dict[key] && dict[key][period] != null ? dict[key][period] : null);
  for (const period of periods) {
    const totalRevenue =
      getVal(pl, 'total_operating_revenue', period) ?? getVal(pl, 'total_revenue', period);
    const cogs = getVal(pl, 'cogs', period);
    const purchase = getVal(pl, 'purchase_of_stock_in_trade', period) ?? 0;
    const changesInv = getVal(pl, 'changes_in_inventories', period) ?? 0;
    const employee = getVal(pl, 'employee_benefit_expense', period);
    const otherExp = getVal(pl, 'other_expenses', period);
    const depreciation = getVal(pl, 'depreciation_amortisation', period);

    let ebitda = null;
    if (totalRevenue != null && cogs != null && employee != null && otherExp != null) {
      ebitda = totalRevenue - (cogs + purchase + changesInv + employee + otherExp);
    }
    const ebitdaMargin = ebitda != null && totalRevenue ? (100 * ebitda) / totalRevenue : null;
    const ebit = ebitda != null && depreciation != null ? ebitda - depreciation : null;

    let grossProfit = null;
    if (totalRevenue != null && cogs != null) {
      grossProfit = totalRevenue - (cogs + purchase + changesInv);
    }
    const grossMargin = grossProfit != null && totalRevenue ? (100 * grossProfit) / totalRevenue : null;

    derived[period] = {
      ebitda,
      ebitda_margin_pct: ebitdaMargin,
      ebit,
      gross_profit: grossProfit,
      gross_margin_pct: grossMargin,
    };
  }
  return derived;
}

function extractSection(matrix, block, labelCol, fieldDict, sectionName, fieldReport) {
  const out = {};
  for (const [key, rules] of Object.entries(fieldDict)) {
    const { found, values } = lookupSeries(matrix, block, labelCol, rules);
    out[key] = values;
    fieldReport.push({ key, section: sectionName, found });
  }
  return out;
}

/**
 * Parses an already-read SheetJS workbook (from XLSX.read(buffer, { cellDates: true }))
 * into the app's internal financials shape. Never throws on missing data — missing
 * fields simply come back as {} (empty series), surfaced via fieldReport.
 */
export function parseWorkbook(workbook, { preferBasis = 'Standalone' } = {}) {
  const basisOrder = preferBasis === 'Consolidated' ? ['Consolidated', 'Standalone'] : ['Standalone', 'Consolidated'];

  let basis = null;
  let financialsSheetName = null;
  let ratiosSheetName = null;

  for (const candidate of basisOrder) {
    const sheets = BASIS_SHEETS[candidate];
    const fSheet = findSheetName(workbook, [sheets.financials]);
    if (fSheet) {
      basis = candidate;
      financialsSheetName = fSheet;
      ratiosSheetName = findSheetName(workbook, [sheets.ratios]);
      break;
    }
  }

  if (!financialsSheetName) {
    throw new Error(
      "This doesn't look like a Ratio-file workbook — expected a sheet named 'Financials_Standalone' or 'Financials_Consol'."
    );
  }

  const finMatrix = sheetToMatrix(workbook.Sheets[financialsSheetName]);
  const companyRaw = finMatrix[0] && finMatrix[0][0];
  const company = companyRaw && String(companyRaw).trim() ? String(companyRaw).trim() : 'Uploaded Company';

  const finCandidates = detectHeaderCandidates(finMatrix);
  const finBlocks = buildBlocks(finCandidates, finMatrix.length);
  const annualBlocks = finBlocks.filter((b) => b.kind === 'annual');
  // Balance Sheet is the first annual block, Profit & Loss the second (template stacks BS above P&L).
  const bsBlock = annualBlocks[0] || null;
  const plBlock = annualBlocks.length > 1 ? annualBlocks[1] : annualBlocks[0] || null;
  const qBlock = findBlockByKind(finBlocks, 'quarterly');

  const fieldReport = [];
  const balance_sheet = extractSection(finMatrix, bsBlock, 0, BALANCE_SHEET_FIELDS, 'balance_sheet', fieldReport);
  const profit_and_loss = extractSection(finMatrix, plBlock, 0, PROFIT_LOSS_FIELDS, 'profit_and_loss', fieldReport);
  const quarterly = extractSection(finMatrix, qBlock, 0, QUARTERLY_FIELDS, 'quarterly', fieldReport);

  let ratios = {};
  if (ratiosSheetName) {
    const ratioMatrix = sheetToMatrix(workbook.Sheets[ratiosSheetName]);
    const ratioCandidates = detectHeaderCandidates(ratioMatrix);
    const ratioBlocks = buildBlocks(ratioCandidates, ratioMatrix.length);
    const ratioBlock = ratioBlocks[0] || null;
    ratios = extractSection(ratioMatrix, ratioBlock, 1, RATIO_FIELDS, 'ratios', fieldReport);
  } else {
    for (const key of Object.keys(RATIO_FIELDS)) fieldReport.push({ key, section: 'ratios', found: false });
  }

  const periods = {
    annual: collectPeriods(bsBlock || plBlock),
    quarterly: collectPeriods(qBlock),
  };

  const derived_metrics = computeDerivedMetrics(periods.annual, balance_sheet, profit_and_loss);

  return {
    company,
    basis,
    units: 'Lakhs',
    source_sheet: { financials: financialsSheetName, ratios: ratiosSheetName },
    periods,
    balance_sheet,
    profit_and_loss,
    quarterly,
    ratios,
    derived_metrics,
    fieldReport,
  };
}

export async function parseWorkbookFromArrayBuffer(buffer, opts) {
  const workbook = XLSX.read(buffer, { cellDates: true });
  return parseWorkbook(workbook, opts);
}
