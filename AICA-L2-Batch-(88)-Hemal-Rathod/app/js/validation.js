/* =============================================================================
 * validation.js — Arithmetic integrity
 * -----------------------------------------------------------------------------
 * Two kinds of finding:
 *
 *   error    the figures are impossible (a negative amount, cash exceeding the
 *            total it is part of). The decision cannot be drawn until corrected,
 *            and the user is taken straight to the field.
 *   caution  consistent but unusual. The decision IS drawn; the point is carried
 *            into the working paper as a note for the reviewer.
 *
 * Which fields are REQUIRED is decided by the engine, not here, because it
 * depends on the path the law takes through the facts (see engine.js).
 * ========================================================================== */

(function (global) {
  'use strict';

  var TAS = global.TAS || (global.TAS = {});
  var calc = TAS.calc;

  function issue(kind, field, message) {
    return { kind: kind, field: field, message: message };
  }

  function validate(f) {
    var errors = [], cautions = [];
    var isBusiness = f.nature === 'business';
    var tLabel = isBusiness ? 'Turnover' : 'Gross receipts';

    function nonNegative(field, value, label) {
      if (value !== null && value < 0) errors.push(issue('error', field, label + ' cannot be negative.'));
    }

    nonNegative('turnover', f.turnover, tLabel);
    nonNegative('cashReceipts', f.cashReceipts, 'Amounts received in cash');

    if (isBusiness) {
      nonNegative('totalReceipts', f.totalReceipts, 'Total amounts received');
      nonNegative('totalPayments', f.totalPayments, 'Total payments');
      nonNegative('cashPayments', f.cashPayments, 'Payments made in cash');
      nonNegative('turnoverNonBanking', f.turnoverNonBanking, 'Turnover not received through banking channels');

      if (f.cashReceipts !== null && f.totalReceipts !== null && f.cashReceipts > f.totalReceipts) {
        errors.push(issue('error', 'cashReceipts',
          'Cash received (' + calc.inr(f.cashReceipts) + ') cannot exceed total amounts received (' +
          calc.inr(f.totalReceipts) + ').'));
      }
      if (f.cashPayments !== null && f.totalPayments !== null && f.cashPayments > f.totalPayments) {
        errors.push(issue('error', 'cashPayments',
          'Cash paid (' + calc.inr(f.cashPayments) + ') cannot exceed total payments (' +
          calc.inr(f.totalPayments) + ').'));
      }
      if (f.turnoverNonBanking !== null && f.turnover !== null && f.turnoverNonBanking > f.turnover) {
        errors.push(issue('error', 'turnoverNonBanking',
          'This amount (' + calc.inr(f.turnoverNonBanking) + ') is part of turnover and cannot exceed it (' +
          calc.inr(f.turnover) + ').'));
      }

      if (f.turnover !== null && f.turnover > 0 && f.totalReceipts === 0) {
        cautions.push(issue('caution', 'totalReceipts',
          'Total amounts received are nil while turnover is ' + calc.inr(f.turnover) + '. The receipts limb of ' +
          'the cash test is treated as satisfied, because nil cash does not exceed 5% of nil. Confirm that ' +
          'nothing was realised during the year.'));
      }
      if (f.turnover !== null && f.turnover > 0 && f.totalPayments === 0) {
        cautions.push(issue('caution', 'totalPayments',
          'Total payments are nil while turnover is ' + calc.inr(f.turnover) + '. The payments limb is treated ' +
          'as satisfied. Confirm that no payment of any kind was made during the year.'));
      }
    } else {
      if (f.cashReceipts !== null && f.turnover !== null && f.turnover > 0 && f.cashReceipts > f.turnover) {
        cautions.push(issue('caution', 'cashReceipts',
          'Cash received exceeds gross receipts. Confirm the figures.'));
      }
    }

    if (f.profit !== null && f.turnover !== null && f.turnover > 0 && f.profit > f.turnover) {
      cautions.push(issue('caution', 'profit',
        'Declared profit exceeds ' + tLabel.toLowerCase() + '. Confirm whether other income is included.'));
    }
    if (f.profit !== null && f.profit < 0) {
      cautions.push(issue('caution', 'profit',
        'A loss has been declared. On the low-profit limbs a loss is lower than any deemed income.'));
    }
    if (f.pan && !/^[A-Z]{5}[0-9]{4}[A-Z]$/.test(f.pan.trim().toUpperCase())) {
      cautions.push(issue('caution', 'pan', 'PAN does not match the ten-character format.'));
    }

    return { errors: errors, cautions: cautions, ok: errors.length === 0 };
  }

  TAS.validation = { validate: validate };

})(window);
