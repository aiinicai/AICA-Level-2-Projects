/**
 * TaxCompute Pro - Statutory Verification & Calculation Test Suite
 */

import { MASTER_RATES } from './js/masterRates.js';
import { TaxEngine } from './js/taxEngine.js';
import { AdvanceTaxEngine } from './js/advanceTaxEngine.js';
import { AIAdvisoryEngine } from './js/aiAdvisoryEngine.js';
import { PRESET_PROFILES } from './js/state.js';

function runTests() {
  console.log('=====================================================');
  console.log('TAXCOMPUTE PRO - STATUTORY TAX ENGINE VERIFICATION');
  console.log('=====================================================\n');

  let passed = 0;
  let failed = 0;

  function assert(testName, actual, expected, tolerance = 1) {
    const isClose = Math.abs(actual - expected) <= tolerance;
    if (isClose) {
      console.log(`✅ [PASS] ${testName}: Expected ${expected}, got ${actual}`);
      passed++;
    } else {
      console.error(`❌ [FAIL] ${testName}: Expected ${expected}, got ${actual}`);
      failed++;
    }
  }

  // TEST 1: New Regime Slabs & Section 87A Full Rebate at ₹7,00,000 Net Taxable Income
  console.log('--- Test Suite 1: Slabs & 87A Rebate in New Regime ---');
  const testState7L = {
    assesseeType: 'individual_general',
    assessmentYear: '2026-27',
    salary: { basicSalary: 775000 }, // After ₹75k std deduction = ₹7,00,000 taxable
    deductions: {}
  };
  const res7L = TaxEngine.computeTax(testState7L, true);
  assert('GTI for ₹7.75L salary', res7L.grossTotalIncome, 700000);
  assert('Taxable income after ₹75k standard deduction', res7L.totalTaxableIncome, 700000);
  assert('Net Tax Liability after 87A Rebate at ₹7.00L', res7L.taxComputation.totalTaxLiability, 0);

  // TEST 2: Section 87A Marginal Relief in New Regime (e.g. ₹7,20,000 Taxable Income)
  console.log('\n--- Test Suite 2: Section 87A Marginal Relief ---');
  const testStateMarginal = {
    assesseeType: 'individual_general',
    assessmentYear: '2026-27',
    otherSources: { otherRegularIncome: 720000 },
    deductions: {}
  };
  const resMarginal = TaxEngine.computeTax(testStateMarginal, true);
  // Normal tax on 7.2L = (4L * 5%) + (20k * 10%) = 20k + 2k = 22k.
  // Excess income over 7L = 20k.
  // Marginal relief rebate = 22k - 20k = 2k.
  // Net tax = 20k + 4% cess = 20,800.
  assert('Taxable Income 7.2L', resMarginal.totalTaxableIncome, 720000);
  assert('Base Tax before rebate', resMarginal.taxComputation.baseTaxBeforeRebate, 22000);
  assert('87A Marginal Relief rebate', resMarginal.taxComputation.rebate87A, 2000);
  assert('Tax after 87A marginal relief', resMarginal.taxComputation.netTaxAfterRebate, 20000);

  // TEST 3: Budget 2024 Capital Gains (STCG 111A @ 20%, LTCG 112A @ 12.5% with ₹1.25L Exemption)
  console.log('\n--- Test Suite 3: Capital Gains Budget 2024 Rationalized Rates ---');
  const testStateCG = {
    assesseeType: 'individual_general',
    assessmentYear: '2026-27',
    capitalGains: {
      stcg111a_gross: 200000, // 20% of 2L = 40,000
      ltcg112a_gross: 325000, // 3.25L - 1.25L exemption = 2L @ 12.5% = 25,000
    },
    deductions: {}
  };
  const resCG = TaxEngine.computeTax(testStateCG, true);
  assert('STCG 111A net taxable', resCG.heads.capitalGains.netStcg111a, 200000);
  assert('LTCG 112A exemption u/s 112A', resCG.heads.capitalGains.exemption112A, 125000);
  assert('LTCG 112A net taxable', resCG.heads.capitalGains.taxableLtcg112a, 200000);
  assert('Special Rate Tax on CG (40k + 25k)', resCG.taxComputation.taxOnSpecialIncome, 65000);

  // TEST 4: Section 44ADA Presumptive Taxation (Doctor Profile)
  console.log('\n--- Test Suite 4: Section 44ADA Presumptive Scheme ---');
  const docProfile = PRESET_PROFILES.DOCTOR_CONSULTANT_44ADA;
  const docRes = TaxEngine.computeTax(docProfile, true);
  assert('44ADA Deemed Profit (min 50% of 62L or declared 33L)', docRes.heads.pgbp.netPgbpIncome, 3300000);

  // TEST 5: Corporate Domestic Co u/s 115BAA @ 22%
  console.log('\n--- Test Suite 5: Domestic Company Section 115BAA ---');
  const corpProfile = PRESET_PROFILES.DOMESTIC_COMPANY_115BAA;
  const corpRes = TaxEngine.computeTax(corpProfile, true);
  // Normal taxable = 88.5L (PGBP) + 2L (OS) - 3L (80JJAA) = 87.5L.
  // Tax on Normal @ 22% = 19,25,000.
  // Tax on LTCG 112 (4L @ 12.5%) = 50,000.
  // Base Tax = 19,75,000.
  // Surcharge 10% = 1,97,500.
  // Cess 4% = 86,900.
  // Total Tax Liability = 22,59,400.
  assert('Corporate Normal Income Tax @ 22%', corpRes.taxComputation.taxOnNormalIncome, 1925000, 100);
  assert('Corporate Special CG Tax @ 12.5%', corpRes.taxComputation.taxOnSpecialIncome, 50000, 100);
  assert('Corporate Surcharge @ 10%', corpRes.taxComputation.surcharge.netSurcharge, 197500, 100);
  assert('Corporate Total Tax Liability (incl. 4% cess)', corpRes.taxComputation.totalTaxLiability, 2259400, 100);

  // TEST 6: Section 234C, 234B, 234A Interest Engine
  console.log('\n--- Test Suite 6: Advance Tax & Penal Interest Engine ---');
  const advParams = {
    totalTaxLiability: 500000,
    tdsTcsClaimed: 100000, // Assessed tax = 4,00,000
    installmentsPaid: {
      q1_june15: 20000, // Req: 60k (15%), Shortfall: 40k -> 234C Int = 40k * 1% * 3 = 1200
      q2_sept15: 40000, // Cum: 60k, Req: 180k (45%), Shortfall: 120k -> 234C Int = 120k * 1% * 3 = 3600
      q3_dec15: 100000, // Cum: 160k, Req: 300k (75%), Shortfall: 140k -> 234C Int = 140k * 1% * 3 = 4200
      q4_mar15: 100000, // Cum: 260k, Req: 400k (100%), Shortfall: 140k -> 234C Int = 140k * 1% * 1 = 1400
      q4_mar31: 0
    },
    filingDueDate: '2026-07-31',
    actualFilingDate: '2026-07-25',
    assessmentYear: '2026-27'
  };
  const advRes = AdvanceTaxEngine.computeAdvanceTaxAndInterest(advParams);
  assert('Assessed Tax Liability', advRes.assessedTax, 400000);
  assert('Section 234C Total Interest (1200+3600+4200+1400)', advRes.interest234C.amount, 10400);
  assert('Section 234B Interest Triggered (< 90% paid)', advRes.interest234B.isApplicable, true);

  // TEST 7: AI Advisory Memorandum Generation
  console.log('\n--- Test Suite 7: AI Advisory Engine ---');
  const comparison = TaxEngine.compareRegimes(PRESET_PROFILES.SALARIED_TECH_LEAD);
  const advisory = AIAdvisoryEngine.generateAdvisory(comparison, advRes, PRESET_PROFILES.SALARIED_TECH_LEAD);
  assert('AI Advisory generates observations', advisory.observations.length > 0, true);
  assert('AI Advisory generates tax saving tips', advisory.taxSavingTips.length > 0, true);

  console.log('\n=====================================================');
  console.log(`TEST RESULTS: ${passed} PASSED, ${failed} FAILED`);
  console.log('=====================================================\n');

  if (failed > 0) process.exit(1);
}

runTests();
