/* =============================================================================
 * calc.js — Arithmetic layer
 * -----------------------------------------------------------------------------
 * Pure functions. No legal rules, no thresholds, no DOM, no formatting decisions
 * that depend on the law. Everything here is testable in isolation and would give
 * the same answer if the Finance Act changed tomorrow.
 * ========================================================================== */

(function (global) {
  'use strict';

  var TAS = global.TAS || (global.TAS = {});

  /** Parses a user-entered amount. Returns null for blank/unparseable input so
   *  that "not entered" stays distinguishable from "entered as zero". */
  function amount(value) {
    if (value === null || value === undefined) return null;
    var s = String(value).trim();
    if (s === '') return null;
    s = s.replace(/,/g, '');
    var n = Number(s);
    if (!isFinite(n)) return null;
    return n;
  }

  /** Indian-format currency. Handles negatives and the 2-2-3 grouping. */
  function inr(n, opts) {
    opts = opts || {};
    if (n === null || n === undefined || !isFinite(n)) return '—';
    var sign = n < 0 ? '-' : '';
    var whole = Math.abs(Math.round(n)).toString();
    var last3 = whole.substring(whole.length - 3);
    var rest = whole.substring(0, whole.length - 3);
    if (rest !== '') last3 = ',' + last3;
    var grouped = rest.replace(/\B(?=(\d{2})+(?!\d))/g, ',') + last3;
    return sign + (opts.noSymbol ? '' : '₹') + grouped;
  }

  /** Renders an amount in crore / lakh words, for headroom narration. */
  function inrWords(n) {
    if (n === null || n === undefined || !isFinite(n)) return '—';
    var abs = Math.abs(n);
    var sign = n < 0 ? '-' : '';
    if (abs >= 10000000) return sign + trimZeros(abs / 10000000) + ' crore';
    if (abs >= 100000)   return sign + trimZeros(abs / 100000) + ' lakh';
    return inr(n);
  }

  function trimZeros(x) {
    var s = x.toFixed(2);
    return s.replace(/\.00$/, '').replace(/(\.\d)0$/, '$1');
  }

  /** Percentage to 2 dp. Returns null when the denominator is unusable, so the
   *  caller can distinguish "0.00%" from "cannot be computed". */
  function ratio(numerator, denominator) {
    if (numerator === null || denominator === null) return null;
    if (!isFinite(numerator) || !isFinite(denominator)) return null;
    if (denominator <= 0) return null;
    return (numerator / denominator) * 100;
  }

  function pct(n, opts) {
    opts = opts || {};
    if (n === null || n === undefined || !isFinite(n)) return '—';
    return n.toFixed(opts.dp === undefined ? 2 : opts.dp) + '%';
  }

  /** Distance to a threshold. Positive headroom means the figure is under. */
  function headroom(actual, threshold) {
    if (actual === null || threshold === null) return null;
    return threshold - actual;
  }

  /** Where a value sits between 0 and a scale maximum, clamped to 0..100.
   *  Used by the threshold meters; never used to decide anything. */
  function meterPosition(value, scaleMax) {
    if (value === null || !isFinite(value) || scaleMax <= 0) return 0;
    var p = (value / scaleMax) * 100;
    return Math.max(0, Math.min(100, p));
  }

  /** Presumptive income at a given deemed rate. */
  function presumptiveIncome(base, ratePct) {
    if (base === null || ratePct === null) return null;
    return base * (ratePct / 100);
  }

  /** Non-cash component, when both sides are known. */
  function residual(total, part) {
    if (total === null || part === null) return null;
    return total - part;
  }

  /**
   * Strict comparison helpers.
   *
   * Threshold tests in the Act are framed as "exceeds". A figure exactly equal to
   * the limit does NOT exceed it. These two helpers exist so that the boundary
   * convention is written down once rather than being re-decided at each call
   * site, which is where off-by-one errors in this kind of tool come from.
   */
  function exceeds(value, limit) {
    if (value === null || limit === null) return null;
    return value > limit;
  }

  function withinCeiling(value, ceiling) {
    if (value === null || ceiling === null) return null;
    return value <= ceiling;
  }

  /** Satisfied when the ratio is at or below the ceiling percentage. */
  function withinPctCeiling(actualPct, ceilingPct) {
    if (actualPct === null || ceilingPct === null) return null;
    return actualPct <= ceilingPct;
  }

  /**
   * The statutory cash test, written the way the Act words it: the cash amount
   * "does not exceed five per cent of the said amount".
   *
   * Compared directly — cash <= pct% x total — rather than by computing a ratio
   * and comparing percentages. The two differ only when the total is nil: a
   * ratio cannot be computed, but "nil does not exceed five per cent of nil" is
   * plainly true. So a business with no receipts at all satisfies the receipts
   * limb, which is the correct reading, instead of stalling on a division by zero.
   *
   * Integer paise arithmetic avoids a floating-point edge exactly at 5%.
   */
  function cashWithin(cash, total, pct) {
    if (cash === null || total === null) return null;
    var cashP = Math.round(cash * 100);
    var limitP = Math.round(total * 100) * pct / 100;
    return cashP <= limitP + 1e-9;
  }

  TAS.calc = {
    amount: amount,
    inr: inr,
    inrWords: inrWords,
    ratio: ratio,
    pct: pct,
    headroom: headroom,
    meterPosition: meterPosition,
    presumptiveIncome: presumptiveIncome,
    residual: residual,
    exceeds: exceeds,
    withinCeiling: withinCeiling,
    withinPctCeiling: withinPctCeiling,
    cashWithin: cashWithin
  };

})(window);
