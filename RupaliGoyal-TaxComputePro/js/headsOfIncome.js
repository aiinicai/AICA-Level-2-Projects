/**
 * TaxCompute Pro - Five Heads of Income Statutory Computation Engine
 * Section 15 to Section 59 of the Income Tax Act, 1961
 */

import { MASTER_RATES } from './masterRates.js';

export class HeadsOfIncomeEngine {

  /**
   * 1. SALARIES (Sec 15 to 17)
   */
  static computeSalary(salaryData, isNewRegime = true) {
    const basic = Number(salaryData.basicSalary || 0);
    const da = Number(salaryData.da || 0);
    const hraReceived = Number(salaryData.hraReceived || 0);
    const rentPaid = Number(salaryData.rentPaid || 0);
    const isMetro = Boolean(salaryData.isMetro);
    const ltaReceived = Number(salaryData.ltaReceived || 0);
    const ltaExemptionClaimed = Number(salaryData.ltaExempt || 0);
    const specialAllowance = Number(salaryData.specialAllowance || 0);
    const bonusCommission = Number(salaryData.bonusCommission || 0);
    const perquisites = Number(salaryData.perquisites || 0);
    const professionalTax = Number(salaryData.professionalTax || 0);
    const entertainmentAllowance = Number(salaryData.entertainmentAllowance || 0);
    const isGovtEmployee = Boolean(salaryData.isGovtEmployee);

    // Gross Salary under Sec 17(1)
    const grossSalary = basic + da + hraReceived + ltaReceived + specialAllowance + bonusCommission + perquisites;

    // HRA Exemption Calculation u/s 10(13A) (Applicable ONLY in Old Tax Regime)
    let hraExempt = 0;
    let hraBreakdown = { actualHra: hraReceived, excessRent: 0, salaryPct: 0, minAllowed: 0 };

    if (!isNewRegime && hraReceived > 0 && rentPaid > 0) {
      const salaryForHra = basic + da; // Basic + DA forming part of retirement benefits
      const excessRent = Math.max(0, rentPaid - (0.10 * salaryForHra));
      const salaryPctLimit = isMetro ? (0.50 * salaryForHra) : (0.40 * salaryForHra);
      hraExempt = Math.min(hraReceived, excessRent, salaryPctLimit);
      hraBreakdown = {
        actualHra: hraReceived,
        excessRent: excessRent,
        salaryPct: salaryPctLimit,
        minAllowed: hraExempt
      };
    }

    // LTA Exemption u/s 10(5) (Applicable ONLY in Old Tax Regime)
    const ltaExempt = isNewRegime ? 0 : Math.min(ltaReceived, ltaExemptionClaimed);

    // Total Sec 10 Exemptions
    const totalSec10Exemptions = hraExempt + ltaExempt;
    const salaryAfterSec10 = Math.max(0, grossSalary - totalSec10Exemptions);

    // Deductions u/s 16
    // 16(ia) Standard Deduction: ₹75,000 (New Regime) / ₹50,000 (Old Regime)
    const stdDeductionLimit = isNewRegime ? MASTER_RATES.STANDARD_DEDUCTION.NEW_REGIME : MASTER_RATES.STANDARD_DEDUCTION.OLD_REGIME;
    const standardDeduction = Math.min(salaryAfterSec10, stdDeductionLimit);

    // 16(ii) Entertainment Allowance (Only Govt employees in Old Regime, max ₹5,000 or 1/5th basic)
    let entertainmentDeduction = 0;
    if (!isNewRegime && isGovtEmployee && entertainmentAllowance > 0) {
      entertainmentDeduction = Math.min(5000, 0.20 * basic, entertainmentAllowance);
    }

    // 16(iii) Professional Tax (Allowed only in Old Regime, max ₹2,500)
    const profTaxDeduction = isNewRegime ? 0 : Math.min(2500, professionalTax);

    const totalSec16Deductions = standardDeduction + entertainmentDeduction + profTaxDeduction;
    const netSalaryIncome = Math.max(0, salaryAfterSec10 - totalSec16Deductions);

    return {
      grossSalary,
      hraExempt,
      hraBreakdown,
      ltaExempt,
      totalSec10Exemptions,
      salaryAfterSec10,
      standardDeduction,
      entertainmentDeduction,
      profTaxDeduction,
      totalSec16Deductions,
      netSalaryIncome
    };
  }

  /**
   * 2. HOUSE PROPERTY (Sec 22 to 27)
   * Multi-property calculation with Sec 24(a) 30% repair deduction and Sec 24(b) loan interest limits.
   */
  static computeHouseProperty(properties = [], isNewRegime = true) {
    let totalHpIncome = 0;
    const computedProperties = [];

    let selfOccupiedInterestSum = 0;

    properties.forEach((prop, index) => {
      const type = prop.type || 'self'; // 'self', 'letout', 'deemed'
      const grossRent = Number(prop.grossRent || 0);
      const municipalTaxes = Number(prop.municipalTaxes || 0);
      const loanInterest = Number(prop.loanInterest || 0);
      const preConstructionInterest = Number(prop.preConstructionInterest || 0);
      const totalLoanInterest = loanInterest + preConstructionInterest;

      let gav = 0;
      let nav = 0;
      let stdDeduction24a = 0;
      let allowedInterest24b = 0;
      let netPropertyIncome = 0;

      if (type === 'self') {
        // Self-Occupied Property: GAV is NIL, Municipal taxes not deductible
        gav = 0;
        nav = 0;
        stdDeduction24a = 0;

        if (isNewRegime) {
          // In New Regime u/s 115BAC, interest on self-occupied house property is NOT ALLOWED (0)
          allowedInterest24b = 0;
          netPropertyIncome = 0;
        } else {
          // In Old Regime: Cap of ₹2,00,000 aggregate across all self-occupied properties
          const remainingSelfCap = Math.max(0, 200000 - selfOccupiedInterestSum);
          allowedInterest24b = Math.min(totalLoanInterest, remainingSelfCap);
          selfOccupiedInterestSum += allowedInterest24b;
          netPropertyIncome = -allowedInterest24b; // Loss from self-occupied
        }
      } else {
        // Let-out / Deemed Let-out Property
        gav = grossRent;
        nav = Math.max(0, gav - municipalTaxes);
        // Statutory 30% deduction u/s 24(a)
        stdDeduction24a = 0.30 * nav;
        // In let-out property, actual interest is deductible without the ₹2L cap u/s 24(b)
        allowedInterest24b = totalLoanInterest;
        netPropertyIncome = nav - stdDeduction24a - allowedInterest24b;
      }

      totalHpIncome += netPropertyIncome;
      computedProperties.push({
        id: prop.id || index + 1,
        propertyName: prop.propertyName || `Property ${index + 1}`,
        type,
        gav,
        municipalTaxes: type === 'self' ? 0 : municipalTaxes,
        nav,
        stdDeduction24a,
        totalLoanInterest,
        allowedInterest24b,
        netPropertyIncome
      });
    });

    // Section 71(3A) Inter-Head Loss Set-off restriction:
    // Loss under House Property can be set off against other heads up to max ₹2,00,000 only.
    // In New Regime, loss from let-out cannot be set off against other heads.
    let allowableLossAgainstOtherHeads = 0;
    let carryForwardHpLoss = 0;

    if (totalHpIncome < 0) {
      if (isNewRegime) {
        // Under New Regime u/s 115BAC(2), HP loss cannot be set off against any other head
        allowableLossAgainstOtherHeads = 0;
        carryForwardHpLoss = Math.abs(totalHpIncome);
      } else {
        const grossLoss = Math.abs(totalHpIncome);
        allowableLossAgainstOtherHeads = Math.min(grossLoss, 200000);
        carryForwardHpLoss = Math.max(0, grossLoss - 200000);
      }
    }

    return {
      properties: computedProperties,
      totalHpIncome,
      allowableLossAgainstOtherHeads: totalHpIncome < 0 ? -allowableLossAgainstOtherHeads : totalHpIncome,
      carryForwardHpLoss
    };
  }

  /**
   * 3. PROFITS AND GAINS OF BUSINESS OR PROFESSION (PGBP - Sec 28 to 44)
   * Supports Presumptive (44AD, 44ADA, 44AE) & Regular Books with Sec 40(a)/43B adjustments & Sec 32 Block Depreciation.
   */
  static computePGBP(pgbpData) {
    const mode = pgbpData.mode || 'presumptive'; // 'presumptive' or 'books'
    let netPgbpIncome = 0;
    let details = {};

    if (mode === 'presumptive') {
      const scheme = pgbpData.presumptiveScheme || '44AD'; // '44AD', '44ADA', '44AE'

      if (scheme === '44AD') {
        const digitalTurnover = Number(pgbpData.sec44ad_digitalTurnover || 0);
        const cashTurnover = Number(pgbpData.sec44ad_cashTurnover || 0);
        const declaredDigitalProfit = Number(pgbpData.sec44ad_declaredDigitalProfit || 0);
        const declaredCashProfit = Number(pgbpData.sec44ad_declaredCashProfit || 0);

        const totalTurnover = digitalTurnover + cashTurnover;
        const minDigitalProfit = 0.06 * digitalTurnover;
        const minCashProfit = 0.08 * cashTurnover;

        const finalDigitalProfit = Math.max(minDigitalProfit, declaredDigitalProfit);
        const finalCashProfit = Math.max(minCashProfit, declaredCashProfit);
        netPgbpIncome = finalDigitalProfit + finalCashProfit;

        // Eligibility check
        const isDigitalThresholdMet = (digitalTurnover / (totalTurnover || 1)) >= 0.95;
        const maxEligibleTurnover = isDigitalThresholdMet ? 30000000 : 20000000;
        const isEligible = totalTurnover <= maxEligibleTurnover;

        details = {
          scheme: '44AD',
          totalTurnover,
          digitalTurnover,
          cashTurnover,
          minDeemedProfit: minDigitalProfit + minCashProfit,
          declaredProfit: declaredDigitalProfit + declaredCashProfit,
          isEligible,
          maxEligibleTurnover,
          auditRequired: !isEligible || (declaredDigitalProfit + declaredCashProfit < minDigitalProfit + minCashProfit)
        };
      } else if (scheme === '44ADA') {
        const grossReceipts = Number(pgbpData.sec44ada_grossReceipts || 0);
        const cashReceipts = Number(pgbpData.sec44ada_cashReceipts || 0);
        const declaredProfit = Number(pgbpData.sec44ada_declaredProfit || 0);

        const minProfit = 0.50 * grossReceipts; // 50% deemed profit
        netPgbpIncome = Math.max(minProfit, declaredProfit);

        const isCashEligible = (cashReceipts / (grossReceipts || 1)) <= 0.05;
        const maxEligibleLimit = isCashEligible ? 7500000 : 5000000;
        const isEligible = grossReceipts <= maxEligibleLimit;

        details = {
          scheme: '44ADA',
          grossReceipts,
          minDeemedProfit: minProfit,
          declaredProfit,
          isEligible,
          maxEligibleLimit,
          auditRequired: !isEligible || (declaredProfit < minProfit)
        };
      } else if (scheme === '44AE') {
        const heavyVehicleTons = Number(pgbpData.sec44ae_heavyVehicleTons || 0);
        const heavyVehicleMonths = Number(pgbpData.sec44ae_heavyVehicleMonths || 0);
        const otherVehiclesCount = Number(pgbpData.sec44ae_otherVehiclesCount || 0);
        const otherVehicleMonths = Number(pgbpData.sec44ae_otherVehicleMonths || 0);

        const heavyIncome = heavyVehicleTons * heavyVehicleMonths * 1000;
        const otherIncome = otherVehiclesCount * otherVehicleMonths * 7500;
        netPgbpIncome = heavyIncome + otherIncome;

        details = {
          scheme: '44AE',
          heavyIncome,
          otherIncome
        };
      }
    } else {
      // Regular Books of Accounts
      const netProfitAsPerPL = Number(pgbpData.netProfitAsPerPL || 0);
      const disallowanceSec40a = Number(pgbpData.disallowanceSec40a || 0); // TDS non-deduction 30%/100%
      const disallowanceSec43B = Number(pgbpData.disallowanceSec43B || 0); // Unpaid statutory dues
      const disallowanceSec40A3 = Number(pgbpData.disallowanceSec40A3 || 0); // Cash payment > ₹10k
      const otherInadmissibleExpenses = Number(pgbpData.otherInadmissibleExpenses || 0);
      
      const bookDepreciation = Number(pgbpData.bookDepreciation || 0); // Added back
      const itDepreciationSec32 = Number(pgbpData.itDepreciationSec32 || 0); // Deducted
      const incomeCreditedNotTaxableInPgbp = Number(pgbpData.incomeCreditedNotTaxableInPgbp || 0); // Dividend/CG in P&L

      const totalAddbacks = disallowanceSec40a + disallowanceSec43B + disallowanceSec40A3 + otherInadmissibleExpenses + bookDepreciation;
      const totalDeductions = itDepreciationSec32 + incomeCreditedNotTaxableInPgbp;

      netPgbpIncome = netProfitAsPerPL + totalAddbacks - totalDeductions;

      details = {
        scheme: 'Regular Books',
        netProfitAsPerPL,
        totalAddbacks,
        totalDeductions,
        bookDepreciation,
        itDepreciationSec32
      };
    }

    return {
      mode,
      netPgbpIncome: Math.max(0, netPgbpIncome),
      details
    };
  }

  /**
   * 4. CAPITAL GAINS (Sec 45 to 55A)
   * Post Budget 2024 rationalized rates:
   * - STCG 111A: 20%
   * - STCG Normal: Slab rates
   * - LTCG 112A: 12.5% (with ₹1.25L exemption u/s 112A)
   * - LTCG 112: 12.5% (or 20% grandfathered)
   * - Rollover exemptions u/s 54, 54EC, 54F, 54B
   */
  static computeCapitalGains(cgData) {
    // STCG 111A (Listed Equity/Equity MFs with STT)
    const stcg111a_gross = Number(cgData.stcg111a_gross || 0);
    const stcg111a_transferExp = Number(cgData.stcg111a_transferExp || 0);
    const netStcg111a = Math.max(0, stcg111a_gross - stcg111a_transferExp);

    // STCG Normal / Other
    const stcgNormal_gross = Number(cgData.stcgNormal_gross || 0);
    const stcgNormal_transferExp = Number(cgData.stcgNormal_transferExp || 0);
    const netStcgNormal = Math.max(0, stcgNormal_gross - stcgNormal_transferExp);

    // LTCG 112A (Listed Equity/MFs)
    const ltcg112a_gross = Number(cgData.ltcg112a_gross || 0);
    const ltcg112a_transferExp = Number(cgData.ltcg112a_transferExp || 0);
    const netLtcg112aBeforeExemption = Math.max(0, ltcg112a_gross - ltcg112a_transferExp);
    
    // Statutory ₹1,25,000 exemption u/s 112A (Budget 2024 enhanced from ₹1,00,000)
    const exemption112A = Math.min(netLtcg112aBeforeExemption, MASTER_RATES.CAPITAL_GAINS.LTCG_112A_EXEMPTION);
    const taxableLtcg112a = Math.max(0, netLtcg112aBeforeExemption - exemption112A);

    // LTCG 112 (Immovable Property, Unlisted Shares, Gold, etc.)
    const ltcg112_gross = Number(cgData.ltcg112_gross || 0);
    const ltcg112_transferExp = Number(cgData.ltcg112_transferExp || 0);
    const ltcg112_rollover54 = Number(cgData.rollover54 || 0); // Sec 54, 54F, 54EC
    const netLtcg112 = Math.max(0, ltcg112_gross - ltcg112_transferExp - ltcg112_rollover54);

    // Total Capital Gains for GTI
    const totalTaxableCapitalGains = netStcg111a + netStcgNormal + taxableLtcg112a + netLtcg112;

    // Capital Loss Tracking
    const stclCarriedForward = Number(cgData.stclCarriedForward || 0);
    const ltclCarriedForward = Number(cgData.ltclCarriedForward || 0);

    return {
      netStcg111a,
      netStcgNormal,
      netLtcg112aBeforeExemption,
      exemption112A,
      taxableLtcg112a,
      netLtcg112,
      rollover54Exemptions: ltcg112_rollover54,
      totalTaxableCapitalGains,
      breakdown: {
        specialRateGains: netStcg111a + taxableLtcg112a + netLtcg112,
        normalSlabGains: netStcgNormal
      }
    };
  }

  /**
   * 5. INCOME FROM OTHER SOURCES (Sec 56 to 59)
   * Includes standard savings/FD interest, family pension deduction (₹25k New / ₹15k Old),
   * and special flat 30% rate incomes (115BB Lotteries, 115BBJ Online Gaming, 115BBH Crypto/VDA).
   */
  static computeOtherSources(osData, isNewRegime = true) {
    const savingsInterest = Number(osData.savingsInterest || 0);
    const termDepositInterest = Number(osData.termDepositInterest || 0); // FD/RD
    const dividendIncome = Number(osData.dividendIncome || 0);
    const familyPension = Number(osData.familyPension || 0);
    const otherRegularIncome = Number(osData.otherRegularIncome || 0);
    const allowableExpensesSec57 = Number(osData.allowableExpensesSec57 || 0);

    // Special rate incomes
    const lotteryIncome115BB = Number(osData.lotteryIncome115BB || 0);
    const onlineGaming115BBJ = Number(osData.onlineGaming115BBJ || 0);
    const cryptoVdaIncome115BBH = Number(osData.cryptoVdaIncome115BBH || 0);

    // Family Pension deduction u/s 57(iia)
    // 1/3rd of pension or ₹25,000 (New Regime) / ₹15,000 (Old Regime)
    const maxFamilyPensionDed = isNewRegime ? MASTER_RATES.FAMILY_PENSION_DEDUCTION.NEW_REGIME_MAX : MASTER_RATES.FAMILY_PENSION_DEDUCTION.OLD_REGIME_MAX;
    const familyPensionDeduction = familyPension > 0 ? Math.min(familyPension / 3, maxFamilyPensionDed) : 0;
    const netFamilyPension = Math.max(0, familyPension - familyPensionDeduction);

    // Normal OS Income (subject to slab rates)
    const normalOsGross = savingsInterest + termDepositInterest + dividendIncome + netFamilyPension + otherRegularIncome;
    const normalOsNet = Math.max(0, normalOsGross - allowableExpensesSec57);

    // Special OS Income (subject to flat 30%)
    const specialOsNet = lotteryIncome115BB + onlineGaming115BBJ + cryptoVdaIncome115BBH;

    const totalOtherSources = normalOsNet + specialOsNet;

    return {
      savingsInterest,
      termDepositInterest,
      dividendIncome,
      familyPension,
      familyPensionDeduction,
      netFamilyPension,
      otherRegularIncome,
      normalOsNet,
      lotteryIncome115BB,
      onlineGaming115BBJ,
      cryptoVdaIncome115BBH,
      specialOsNet,
      totalOtherSources
    };
  }
}
