/**
 * Indian Income Tax Computation Engine
 * Supports New Tax Regime (u/s 115BAC) and Old Tax Regime
 * for AY 2024-25, AY 2025-26, and AY 2026-27.
 * Includes Section 87A Rebate, Marginal Relief, Surcharge, 4% Health & Education Cess,
 * and Section 288A/288B Rounding.
 */

import { CompleteITRData } from '../itr-types';
import { roundOff288A, roundOff288B } from './numberParsing';

export interface TaxCalculationBreakdown {
  taxableIncome: number;
  slabTax: number;
  specialRateTax: number;
  rebate87A: number;
  marginalRelief: number;
  taxAfterRebate: number;
  surcharge: number;
  cess: number;
  totalTaxPayable: number;
  effectiveRate: number;
}

export interface RegimeComparisonResult {
  newRegime: TaxCalculationBreakdown;
  oldRegime: TaxCalculationBreakdown;
  recommendedRegime: 'Old Regime' | 'New Regime';
  taxSavings: number;
  explanation: string;
}

/**
 * Calculates tax under New Regime u/s 115BAC
 */
export function calculateNewRegimeTax(
  taxableIncome: number,
  assessmentYear: string = '2024-25',
  specialRateTax: number = 0
): TaxCalculationBreakdown {
  const roundedIncome = roundOff288A(Math.max(0, taxableIncome));

  let slabTax = 0;

  // New Regime Slabs:
  // AY 2025-26 / AY 2026-27 (Finance Act 2024 onwards):
  // 0 - 3,00,000 : Nil
  // 3,00,001 - 7,00,000 : 5%
  // 7,00,001 - 10,00,000 : 10%
  // 10,00,001 - 12,00,000 : 15%
  // 12,00,001 - 15,00,000 : 20%
  // Above 15,00,000 : 30%
  const isAY2526OrLater = assessmentYear === '2025-26' || assessmentYear === '2026-27' || assessmentYear >= '2025';

  if (isAY2526OrLater) {
    if (roundedIncome > 1500000) {
      slabTax += (roundedIncome - 1500000) * 0.3;
      slabTax += 300000 * 0.2;  // 12L to 15L = 60,000
      slabTax += 200000 * 0.15; // 10L to 12L = 30,000
      slabTax += 300000 * 0.1;  // 7L to 10L = 30,000
      slabTax += 400000 * 0.05; // 3L to 7L = 20,000
    } else if (roundedIncome > 1200000) {
      slabTax += (roundedIncome - 1200000) * 0.2;
      slabTax += 200000 * 0.15;
      slabTax += 300000 * 0.1;
      slabTax += 400000 * 0.05;
    } else if (roundedIncome > 1000000) {
      slabTax += (roundedIncome - 1000000) * 0.15;
      slabTax += 300000 * 0.1;
      slabTax += 400000 * 0.05;
    } else if (roundedIncome > 700000) {
      slabTax += (roundedIncome - 700000) * 0.1;
      slabTax += 400000 * 0.05;
    } else if (roundedIncome > 300000) {
      slabTax += (roundedIncome - 300000) * 0.05;
    }
  } else {
    // AY 2024-25 Slabs
    if (roundedIncome > 1500000) {
      slabTax += (roundedIncome - 1500000) * 0.3;
      slabTax += 300000 * 0.2;
      slabTax += 300000 * 0.15;
      slabTax += 300000 * 0.1;
      slabTax += 300000 * 0.05;
    } else if (roundedIncome > 1200000) {
      slabTax += (roundedIncome - 1200000) * 0.2;
      slabTax += 300000 * 0.15;
      slabTax += 300000 * 0.1;
      slabTax += 300000 * 0.05;
    } else if (roundedIncome > 900000) {
      slabTax += (roundedIncome - 900000) * 0.15;
      slabTax += 300000 * 0.1;
      slabTax += 300000 * 0.05;
    } else if (roundedIncome > 600000) {
      slabTax += (roundedIncome - 600000) * 0.1;
      slabTax += 300000 * 0.05;
    } else if (roundedIncome > 300000) {
      slabTax += (roundedIncome - 300000) * 0.05;
    }
  }

  slabTax = Math.round(slabTax);

  // Rebate u/s 87A: If Taxable income <= ₹7,00,000, 100% rebate (up to ₹25,000)
  let rebate87A = 0;
  let marginalRelief = 0;

  if (roundedIncome <= 700000) {
    rebate87A = Math.min(slabTax + specialRateTax, 25000);
  } else {
    // Marginal relief under 87A if income is slightly above 7L:
    // Tax payable cannot exceed excess of income over 7,00,000
    const rawTax = slabTax + specialRateTax;
    const excessIncome = roundedIncome - 700000;
    if (rawTax > excessIncome) {
      marginalRelief = rawTax - excessIncome;
    }
  }

  const taxAfterRebateAndRelief = Math.max(0, slabTax + specialRateTax - rebate87A - marginalRelief);

  // Surcharge for High Income Earners
  let surcharge = 0;
  if (roundedIncome > 50000000) {
    surcharge = Math.round(taxAfterRebateAndRelief * 0.25); // Max 25% in new regime
  } else if (roundedIncome > 20000000) {
    surcharge = Math.round(taxAfterRebateAndRelief * 0.25);
  } else if (roundedIncome > 10000000) {
    surcharge = Math.round(taxAfterRebateAndRelief * 0.15);
  } else if (roundedIncome > 5000000) {
    surcharge = Math.round(taxAfterRebateAndRelief * 0.1);
  }

  // Health & Education Cess @ 4%
  const cess = Math.round((taxAfterRebateAndRelief + surcharge) * 0.04);
  const totalTaxPayable = roundOff288B(taxAfterRebateAndRelief + surcharge + cess);

  return {
    taxableIncome: roundedIncome,
    slabTax,
    specialRateTax,
    rebate87A,
    marginalRelief,
    taxAfterRebate: taxAfterRebateAndRelief,
    surcharge,
    cess,
    totalTaxPayable,
    effectiveRate: roundedIncome > 0 ? Number(((totalTaxPayable / roundedIncome) * 100).toFixed(2)) : 0,
  };
}

/**
 * Calculates tax under Old Tax Regime
 */
export function calculateOldRegimeTax(
  taxableIncome: number,
  isSeniorCitizen: boolean = false,
  isSuperSeniorCitizen: boolean = false,
  specialRateTax: number = 0
): TaxCalculationBreakdown {
  const roundedIncome = roundOff288A(Math.max(0, taxableIncome));

  const basicExemption = isSuperSeniorCitizen ? 500000 : isSeniorCitizen ? 300000 : 250000;

  let slabTax = 0;

  if (roundedIncome > 1000000) {
    slabTax += (roundedIncome - 1000000) * 0.3;
    slabTax += 500000 * 0.2; // 5L to 10L
    slabTax += Math.max(0, (500000 - basicExemption)) * 0.05;
  } else if (roundedIncome > 500000) {
    slabTax += (roundedIncome - 500000) * 0.2;
    slabTax += Math.max(0, (500000 - basicExemption)) * 0.05;
  } else if (roundedIncome > basicExemption) {
    slabTax += (roundedIncome - basicExemption) * 0.05;
  }

  slabTax = Math.round(slabTax);

  // Rebate 87A under Old Regime: If Total Income <= 5,00,000, max ₹12,500
  let rebate87A = 0;
  if (roundedIncome <= 500000) {
    rebate87A = Math.min(slabTax + specialRateTax, 12500);
  }

  const taxAfterRebate = Math.max(0, slabTax + specialRateTax - rebate87A);

  // Surcharge
  let surcharge = 0;
  if (roundedIncome > 50000000) {
    surcharge = Math.round(taxAfterRebate * 0.37);
  } else if (roundedIncome > 20000000) {
    surcharge = Math.round(taxAfterRebate * 0.25);
  } else if (roundedIncome > 10000000) {
    surcharge = Math.round(taxAfterRebate * 0.15);
  } else if (roundedIncome > 5000000) {
    surcharge = Math.round(taxAfterRebate * 0.1);
  }

  const cess = Math.round((taxAfterRebate + surcharge) * 0.04);
  const totalTaxPayable = roundOff288B(taxAfterRebate + surcharge + cess);

  return {
    taxableIncome: roundedIncome,
    slabTax,
    specialRateTax,
    rebate87A,
    marginalRelief: 0,
    taxAfterRebate,
    surcharge,
    cess,
    totalTaxPayable,
    effectiveRate: roundedIncome > 0 ? Number(((totalTaxPayable / roundedIncome) * 100).toFixed(2)) : 0,
  };
}

/**
 * Compares New Regime vs Old Regime for the given ITR Data
 */
export function compareTaxRegimes(data: CompleteITRData): RegimeComparisonResult {
  const inc = data.incomeHeads;
  const ded = data.deductions;

  // New Regime: GTI - 80CCD(2) employer NPS - standard deduction (if not already factored)
  const newRegimeTaxable = Math.max(0, inc.grossTotalIncome - ded.sec80CCD2);
  const newCalc = calculateNewRegimeTax(newRegimeTaxable, data.personalInfo.assessmentYear, data.taxComputation.specialRateTax);

  // Old Regime: GTI - All Chapter VI-A Deductions
  const oldRegimeTaxable = Math.max(0, inc.grossTotalIncome - ded.totalDeductions);
  const oldCalc = calculateOldRegimeTax(oldRegimeTaxable, false, false, data.taxComputation.specialRateTax);

  const diff = Math.abs(newCalc.totalTaxPayable - oldCalc.totalTaxPayable);
  const recommendedRegime = newCalc.totalTaxPayable <= oldCalc.totalTaxPayable
    ? 'New Regime'
    : 'Old Regime';

  let explanation = '';
  if (newCalc.totalTaxPayable < oldCalc.totalTaxPayable) {
    explanation = `New Regime saves ₹${diff.toLocaleString('en-IN')} in taxes due to lower tax rates.`;
  } else if (oldCalc.totalTaxPayable < newCalc.totalTaxPayable) {
    explanation = `Old Regime saves ₹${diff.toLocaleString('en-IN')} due to Chapter VI-A deductions.`;
  } else {
    explanation = `Both New Regime and Old Regime result in the exact same tax liability of ₹${newCalc.totalTaxPayable.toLocaleString('en-IN')}.`;
  }

  return {
    newRegime: newCalc,
    oldRegime: oldCalc,
    recommendedRegime,
    taxSavings: diff,
    explanation,
  };
}
