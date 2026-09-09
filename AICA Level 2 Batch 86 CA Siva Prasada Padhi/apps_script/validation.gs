/**
 * BANK GUARANTEE MONITORING SYSTEM
 * Retained Google Apps Script — cell-level data validation only.
 *
 * The monitoring engine itself was migrated to Python (see /src). This file
 * is all that remains inside the spreadsheet, because validation must operate
 * at the moment of entry, inside Google Sheets, where an external program
 * cannot reach.
 *
 * IMPORTANT — no time-based trigger may be created for this project. If both
 * this script and the Python engine were to despatch notices, vendors would
 * receive every notice twice. Confirm the Triggers page is empty before the
 * Python scheduled task is enabled.
 *
 * Installation:
 *   Extensions > Apps Script > paste this file > Save > reload the spreadsheet.
 *   The menu appears as "BG Monitoring System".
 */

const BG_SHEET_NAME = "BG";

/**
 * Adds the spreadsheet menu when the workbook is opened.
 */
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('BG Monitoring System')
    .addItem('Apply Data Validations (Cols E, H, M)', 'applySheetDataValidations')
    .addToUi();
}

/**
 * Applies chronological validation rules to the BG register.
 *
 *   Column H (BG Date)        must be on or after Column E (Contract Date)
 *   Column M (Date of Expiry) must be strictly later than Column H (BG Date)
 *
 * Run once at implementation, and again whenever rows are added beyond the
 * validated range.
 */
function applySheetDataValidations() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const bgSheet = ss.getSheetByName(BG_SHEET_NAME);

  if (!bgSheet) {
    SpreadsheetApp.getUi().alert("Sheet '" + BG_SHEET_NAME + "' not found.");
    return;
  }

  const maxRows = Math.max(bgSheet.getMaxRows(), 1000);

  // Column H — a guarantee cannot predate the contract it secures
  const bgDateRule = SpreadsheetApp.newDataValidation()
    .requireFormulaSatisfied('=H2>=E2')
    .setHelpText('INVALID BG DATE: BG DATE CANNOT BE EARLIER THAN THE CONTRACT DATE.')
    .setAllowInvalid(false)
    .build();
  bgSheet.getRange(2, 8, maxRows - 1, 1).setDataValidation(bgDateRule);

  // Column M — validity must run forward from the date of issue
  const expiryDateRule = SpreadsheetApp.newDataValidation()
    .requireFormulaSatisfied('=M2>H2')
    .setHelpText('INVALID EXPIRY DATE: DATE OF EXPIRY MUST BE LATER THAN THE BG DATE.')
    .setAllowInvalid(false)
    .build();
  bgSheet.getRange(2, 13, maxRows - 1, 1).setDataValidation(expiryDateRule);

  SpreadsheetApp.getUi().alert(
    'Data validations applied to Columns H (BG Date) and M (Date of Expiry) across all rows.');
}
