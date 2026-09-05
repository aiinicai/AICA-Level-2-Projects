/**
 * TaxCompute Pro - Multi-Assessee Tax Engine, Chapter VI-A & Regime Comparison Matrix
 * Calibrated for FY 2025-26 & FY 2026-27 (AY 2026-27 & AY 2027-28)
 */

import { MASTER_RATES } from './masterRates.js';
import { HeadsOfIncomeEngine } from './headsOfIncome.js';

export class TaxEngine {

  /**
   * Compute Chapter VI-A Deductions
   */
  static computeChapterVIA(deductionsData, salaryData, isSenior, isSuperSenior, isNewRegime = true) {
    const basic = Number(salaryData.basicSalary || 0);
    const da = Number(salaryData.da || 0);
    const salaryForNps = basic + da;

    // In New Regime u/s 115BAC, only specific deductions are allowed:
    // - Section 80CCD(2): Employer's contribution to NPS (up to 14% of salary)
    // - Section 80JJAA: Deduction in respect of employment of new employees
    // - Section 80CCH(2): Agniveer Corpus Fund
    
    // 80CCD(2) Employer NPS
    const employerNpsAmount = Number(deductionsData.sec80CCD2_employerNps || 0);
    const maxEmployerNpsAllowed = 0.14 * salaryForNps; // 14% for all non-govt/govt under revised provisions
    const allowed80CCD2 = Math.min(employerNpsAmount, maxEmployerNpsAllowed);

    // 80JJAA
    const allowed80JJAA = Number(deductionsData.sec80JJAA || 0);

    if (isNewRegime) {
      return {
        isNewRegime: true,
        sec80C_gross: 0,
        sec80C_allowed: 0,
        sec80CCD1B_allowed: 0,
        sec80CCD2_allowed: allowed80CCD2,
        sec80D_self_allowed: 0,
        sec80D_parents_allowed: 0,
        sec80D_total_allowed: 0,
        sec80E_allowed: 0,
        sec80G_allowed: 0,
        sec80TTA_TTB_allowed: 0,
        sec80JJAA_allowed: allowed80JJAA,
        otherDeductions_allowed: 0,
        totalChapterVIADeductions: allowed80CCD2 + allowed80JJAA,
        breakdown: [
          { section: '80CCD(2)', name: 'Employer NPS Contribution', claimed: employerNpsAmount, allowed: allowed80CCD2 },
          { section: '80JJAA', name: 'New Employment Generation', claimed: allowed80JJAA, allowed: allowed80JJAA }
        ].filter(item => item.allowed > 0)
      };
    }

    // --- OLD REGIME DEDUCTIONS ---

    // 1. Section 80C, 80CCC, 80CCD(1) (Capped at ₹1,50,000)
    const ppf = Number(deductionsData.sec80C_ppf || 0);
    const epf = Number(deductionsData.sec80C_epf || 0);
    const elss = Number(deductionsData.sec80C_elss || 0);
    const lic = Number(deductionsData.sec80C_lic || 0);
    const homeLoanPrincipal = Number(deductionsData.sec80C_homeLoanPrincipal || 0);
    const tuitionFees = Number(deductionsData.sec80C_tuitionFees || 0);
    const nscSukanyaOther = Number(deductionsData.sec80C_other || 0);
    const sec80CCC = Number(deductionsData.sec80CCC || 0);
    const sec80CCD1 = Number(deductionsData.sec80CCD1 || 0);

    const gross80C = ppf + epf + elss + lic + homeLoanPrincipal + tuitionFees + nscSukanyaOther + sec80CCC + sec80CCD1;
    const allowed80C = Math.min(gross80C, 150000);

    // 2. Section 80CCD(1B) Additional NPS (Capped at ₹50,000)
    const claimed80CCD1B = Number(deductionsData.sec80CCD1B || 0);
    const allowed80CCD1B = Math.min(claimed80CCD1B, 50000);

    // 3. Section 80D Mediclaim
    // Self / Family
    const healthInsuranceSelf = Number(deductionsData.sec80D_selfInsurance || 0);
    const preventiveSelf = Number(deductionsData.sec80D_preventiveCheckup || 0);
    const isSelfSenior = Boolean(isSenior || isSuperSenior || deductionsData.isSelfSenior);
    const selfCap = isSelfSenior ? 50000 : 25000;
    const allowedPreventiveSelf = Math.min(preventiveSelf, 5000);
    const allowed80D_Self = Math.min(healthInsuranceSelf + allowedPreventiveSelf, selfCap);

    // Parents
    const healthInsuranceParents = Number(deductionsData.sec80D_parentsInsurance || 0);
    const isParentsSenior = Boolean(deductionsData.isParentsSenior !== false); // default true for parents in typical profiles
    const parentsCap = isParentsSenior ? 50000 : 25000;
    const remainingPreventiveForParents = Math.max(0, 5000 - allowedPreventiveSelf);
    const preventiveParents = Math.min(Number(deductionsData.sec80D_parentsPreventive || 0), remainingPreventiveForParents);
    const allowed80D_Parents = Math.min(healthInsuranceParents + preventiveParents, parentsCap);

    const allowed80D_Total = allowed80D_Self + allowed80D_Parents;

    // 4. Section 80E Higher Education Interest (No Cap)
    const allowed80E = Number(deductionsData.sec80E_educationInterest || 0);

    // 5. Section 80EE / 80EEA Housing Interest
    const allowed80EEA = Math.min(Number(deductionsData.sec80EEA_housingInterest || 0), 150000);

    // 6. Section 80G Donations
    const allowed80G = Number(deductionsData.sec80G_donations || 0);

    // 7. Section 80TTA / 80TTB (Interest on Deposits)
    let allowed80TTA_TTB = 0;
    const savingsInterest = Number(salaryData.savingsInterest || deductionsData.savingsInterest || 0);
    const depositInterest = Number(salaryData.termDepositInterest || deductionsData.termDepositInterest || 0);
    const totalInterest = savingsInterest + depositInterest;

    if (isSenior || isSuperSenior) {
      // 80TTB: Up to ₹50,000 for Senior Citizens (Savings + FD/TD)
      allowed80TTA_TTB = Math.min(totalInterest, 50000);
    } else {
      // 80TTA: Up to ₹10,000 for Non-Seniors (Savings only)
      allowed80TTA_TTB = Math.min(savingsInterest, 10000);
    }

    // 8. Other Deductions (80U, 80DDB, 80GGC, etc.)
    const otherDeductions = Number(deductionsData.otherDeductions || 0);

    const totalChapterVIADeductions = (
      allowed80C +
      allowed80CCD1B +
      allowed80CCD2 +
      allowed80D_Total +
      allowed80E +
      allowed80EEA +
      allowed80G +
      allowed80TTA_TTB +
      allowed80JJAA +
      otherDeductions
    );

    return {
      isNewRegime: false,
      sec80C_gross: gross80C,
      sec80C_allowed: allowed80C,
      sec80CCD1B_allowed: allowed80CCD1B,
      sec80CCD2_allowed: allowed80CCD2,
      sec80D_self_allowed: allowed80D_Self,
      sec80D_parents_allowed: allowed80D_Parents,
      sec80D_total_allowed: allowed80D_Total,
      sec80E_allowed: allowed80E,
      sec80EEA_allowed: allowed80EEA,
      sec80G_allowed: allowed80G,
      sec80TTA_TTB_allowed: allowed80TTA_TTB,
      sec80JJAA_allowed: allowed80JJAA,
      otherDeductions_allowed: otherDeductions,
      totalChapterVIADeductions,
      breakdown: [
        { section: '80C/80CCC/80CCD(1)', name: 'Investments, PF, ELSS, Life Ins.', claimed: gross80C, allowed: allowed80C },
        { section: '80CCD(1B)', name: 'Additional NPS (Self)', claimed: claimed80CCD1B, allowed: allowed80CCD1B },
        { section: '80CCD(2)', name: 'Employer NPS Contribution', claimed: employerNpsAmount, allowed: allowed80CCD2 },
        { section: '80D (Self & Family)', name: 'Health Insurance & Checkup', claimed: healthInsuranceSelf + preventiveSelf, allowed: allowed80D_Self },
        { section: '80D (Parents)', name: 'Parents Health Insurance', claimed: healthInsuranceParents + preventiveParents, allowed: allowed80D_Parents },
        { section: '80E', name: 'Higher Education Loan Interest', claimed: allowed80E, allowed: allowed80E },
        { section: '80EEA', name: 'Affordable Housing Interest', claimed: allowed80EEA, allowed: allowed80EEA },
        { section: '80G', name: 'Charitable Donations', claimed: allowed80G, allowed: allowed80G },
        { section: (isSenior || isSuperSenior) ? '80TTB' : '80TTA', name: 'Interest Deduction', claimed: totalInterest, allowed: allowed80TTA_TTB },
        { section: '80JJAA / Other', name: 'Other Deductions', claimed: allowed80JJAA + otherDeductions, allowed: allowed80JJAA + otherDeductions }
      ].filter(item => item.allowed > 0)
    };
  }

  /**
   * Progressive Slab Tax Calculator
   */
  static calculateSlabTax(income, slabs) {
    let tax = 0;
    const slabBreakdown = [];

    for (const slab of slabs) {
      if (income > slab.min) {
        const taxableInThisSlab = Math.min(income, slab.max) - slab.min;
        const taxInThisSlab = taxableInThisSlab * slab.rate;
        tax += taxInThisSlab;
        slabBreakdown.push({
          slabLabel: slab.label,
          ratePct: `${(slab.rate * 100).toFixed(0)}%`,
          taxableAmount: taxableInThisSlab,
          taxAmount: taxInThisSlab
        });
      }
    }

    return { tax, slabBreakdown };
  }

  /**
   * Surcharge & Marginal Relief for Individual / HUF
   */
  static computeIndividualSurchargeAndMarginalRelief(taxableIncome, baseTax, isNewRegime = true) {
    const surchargeTiers = isNewRegime ? MASTER_RATES.SURCHARGE_INDIVIDUAL.NEW_REGIME : MASTER_RATES.SURCHARGE_INDIVIDUAL.OLD_REGIME;

    let applicableRate = 0;
    let applicableTier = null;

    for (const tier of surchargeTiers) {
      if (taxableIncome > tier.threshold) {
        applicableRate = tier.rate;
        applicableTier = tier;
        break;
      }
    }

    if (applicableRate === 0) {
      return {
        surchargeRate: 0,
        grossSurcharge: 0,
        marginalRelief: 0,
        netSurcharge: 0,
        taxWithSurcharge: baseTax
      };
    }

    const grossSurcharge = baseTax * applicableRate;
    let totalTaxWithSurcharge = baseTax + grossSurcharge;
    let marginalRelief = 0;

    // Marginal Relief Calculation:
    // Tax + Surcharge cannot exceed: (Tax on threshold income + Excess of total income over threshold)
    if (applicableTier) {
      const threshold = applicableTier.threshold;
      const excessIncome = taxableIncome - threshold;
      
      // Calculate tax at threshold
      const slabs = isNewRegime ? MASTER_RATES.SLABS.NEW_REGIME : MASTER_RATES.SLABS.OLD_REGIME_GENERAL;
      const taxAtThreshold = this.calculateSlabTax(threshold, slabs).tax;
      
      // If there was lower surcharge at threshold level
      let lowerSurchargeAtThreshold = 0;
      if (threshold === 20000000) lowerSurchargeAtThreshold = taxAtThreshold * 0.15;
      else if (threshold === 50000000) lowerSurchargeAtThreshold = taxAtThreshold * 0.25;
      else if (threshold === 10000000) lowerSurchargeAtThreshold = taxAtThreshold * 0.10;

      const maxPermissibleTax = taxAtThreshold + lowerSurchargeAtThreshold + excessIncome;

      if (totalTaxWithSurcharge > maxPermissibleTax) {
        marginalRelief = totalTaxWithSurcharge - maxPermissibleTax;
        totalTaxWithSurcharge = maxPermissibleTax;
      }
    }

    const netSurcharge = Math.max(0, grossSurcharge - marginalRelief);

    return {
      surchargeRate: applicableRate,
      grossSurcharge,
      marginalRelief,
      netSurcharge,
      taxWithSurcharge: baseTax + netSurcharge
    };
  }

  /**
   * Main Assessee Tax Computation (Individual, HUF, Firm, Company, Cooperative)
   */
  static computeTax(state, isNewRegime = true) {
    const assesseeType = state.assesseeType || 'individual_general';
    const ay = state.assessmentYear || MASTER_RATES.CURRENT_AY;

    // 1. Compute 5 Heads of Income
    const salaryResult = HeadsOfIncomeEngine.computeSalary(state.salary || {}, isNewRegime);
    const hpResult = HeadsOfIncomeEngine.computeHouseProperty(state.houseProperty?.properties || [], isNewRegime);
    const pgbpResult = HeadsOfIncomeEngine.computePGBP(state.pgbp || {});
    const cgResult = HeadsOfIncomeEngine.computeCapitalGains(state.capitalGains || {});
    const osResult = HeadsOfIncomeEngine.computeOtherSources(state.otherSources || {}, isNewRegime);

    // Gross Total Income (GTI)
    const incomeSalary = salaryResult.netSalaryIncome;
    const incomeHP = hpResult.allowableLossAgainstOtherHeads;
    const incomePGBP = pgbpResult.netPgbpIncome;
    const incomeCG = cgResult.totalTaxableCapitalGains;
    const incomeOS = osResult.totalOtherSources;

    const grossTotalIncome = Math.max(0, incomeSalary + incomeHP + incomePGBP + incomeCG + incomeOS);

    // 2. Chapter VI-A Deductions
    const isSenior = assesseeType === 'individual_senior';
    const isSuperSenior = assesseeType === 'individual_super_senior';
    
    // Deductions cannot be claimed against special rate capital gains (111A, 112A, 112) or special OS (115BB, 115BBJ, 115BBH)
    const specialRateIncomeTotal = (
      cgResult.netStcg111a +
      cgResult.taxableLtcg112a +
      cgResult.netLtcg112 +
      osResult.specialOsNet
    );
    const normalIncomeEligibleForDeductions = Math.max(0, grossTotalIncome - specialRateIncomeTotal);

    const chapterVIAResult = this.computeChapterVIA(state.deductions || {}, state.salary || {}, isSenior, isSuperSenior, isNewRegime);
    const allowedChapterVIADeductions = Math.min(chapterVIAResult.totalChapterVIADeductions, normalIncomeEligibleForDeductions);
    const totalTaxableIncome = Math.max(0, grossTotalIncome - allowedChapterVIADeductions);

    // 3. Tax Calculation based on Assessee Type
    let taxOnNormalIncome = 0;
    let normalSlabBreakdown = [];
    let taxOnSpecialIncome = 0;
    let specialTaxBreakdown = [];

    // Special Rate Taxes:
    // (a) STCG 111A @ 20%
    const taxStcg111a = cgResult.netStcg111a * MASTER_RATES.CAPITAL_GAINS.STCG_111A_RATE;
    if (cgResult.netStcg111a > 0) {
      specialTaxBreakdown.push({ item: 'STCG u/s 111A (20%)', amount: cgResult.netStcg111a, tax: taxStcg111a });
    }

    // (b) LTCG 112A @ 12.5% (above ₹1.25L)
    const taxLtcg112a = cgResult.taxableLtcg112a * MASTER_RATES.CAPITAL_GAINS.LTCG_112A_RATE;
    if (cgResult.taxableLtcg112a > 0) {
      specialTaxBreakdown.push({ item: 'LTCG u/s 112A (12.5% on excess of ₹1.25L)', amount: cgResult.taxableLtcg112a, tax: taxLtcg112a });
    }

    // (c) LTCG 112 @ 12.5%
    const taxLtcg112 = cgResult.netLtcg112 * MASTER_RATES.CAPITAL_GAINS.LTCG_112_RATE;
    if (cgResult.netLtcg112 > 0) {
      specialTaxBreakdown.push({ item: 'LTCG u/s 112 (12.5%)', amount: cgResult.netLtcg112, tax: taxLtcg112 });
    }

    // (d) Lottery u/s 115BB & Gaming u/s 115BBJ & Crypto u/s 115BBH @ 30%
    const taxSpecialOs = osResult.specialOsNet * MASTER_RATES.SPECIAL_RATES.LOTTERY_115BB;
    if (osResult.specialOsNet > 0) {
      specialTaxBreakdown.push({ item: 'Special OS (Lottery / Gaming / Crypto u/s 115BB/115BBJ/115BBH @ 30%)', amount: osResult.specialOsNet, tax: taxSpecialOs });
    }

    taxOnSpecialIncome = taxStcg111a + taxLtcg112a + taxLtcg112 + taxSpecialOs;

    // Normal Income Tax based on Assessee:
    const normalTaxableIncome = Math.max(0, totalTaxableIncome - specialRateIncomeTotal);

    let baseTaxBeforeRebate = 0;
    let rebate87A = 0;
    let rebate87AMarginalRelief = 0;

    if (assesseeType.startsWith('individual') || assesseeType === 'huf') {
      let slabs;
      if (isNewRegime) {
        slabs = MASTER_RATES.SLABS.NEW_REGIME;
      } else {
        if (isSuperSenior) slabs = MASTER_RATES.SLABS.OLD_REGIME_SUPER_SENIOR;
        else if (isSenior) slabs = MASTER_RATES.SLABS.OLD_REGIME_SENIOR;
        else slabs = MASTER_RATES.SLABS.OLD_REGIME_GENERAL;
      }

      const slabRes = this.calculateSlabTax(normalTaxableIncome, slabs);
      taxOnNormalIncome = slabRes.tax;
      normalSlabBreakdown = slabRes.slabBreakdown;

      // Section 87A Rebate Computation
      // New Regime: Full rebate up to ₹7,00,000 + Marginal relief between ₹7,00,000 and ₹7,27,777
      // Old Regime: Rebate of max ₹12,500 if total taxable income <= ₹5,00,000
      baseTaxBeforeRebate = taxOnNormalIncome + taxOnSpecialIncome;

      if (isNewRegime) {
        if (totalTaxableIncome <= MASTER_RATES.REBATE_87A.NEW_REGIME.THRESHOLD) {
          rebate87A = Math.min(baseTaxBeforeRebate, MASTER_RATES.REBATE_87A.NEW_REGIME.MAX_REBATE);
        } else if (totalTaxableIncome > 700000 && totalTaxableIncome <= 727777) {
          // Marginal relief u/s 87A: Tax payable cannot exceed (Taxable Income - ₹7,00,000)
          const excessIncomeOver7L = totalTaxableIncome - 700000;
          if (baseTaxBeforeRebate > excessIncomeOver7L) {
            rebate87AMarginalRelief = baseTaxBeforeRebate - excessIncomeOver7L;
            rebate87A = rebate87AMarginalRelief;
          }
        }
      } else {
        if (totalTaxableIncome <= MASTER_RATES.REBATE_87A.OLD_REGIME.THRESHOLD && !isSuperSenior) {
          rebate87A = Math.min(baseTaxBeforeRebate, MASTER_RATES.REBATE_87A.OLD_REGIME.MAX_REBATE);
        }
      }
    } else if (assesseeType === 'firm_llp') {
      // Partnership Firm / LLP @ flat 30%
      taxOnNormalIncome = normalTaxableIncome * MASTER_RATES.ENTITY_RATES.PARTNERSHIP_FIRM_LLP.baseRate;
      baseTaxBeforeRebate = taxOnNormalIncome + taxOnSpecialIncome;
    } else if (assesseeType === 'company_115baa') {
      // Domestic Co u/s 115BAA @ 22%
      taxOnNormalIncome = normalTaxableIncome * MASTER_RATES.ENTITY_RATES.DOMESTIC_COMPANY_115BAA.baseRate;
      baseTaxBeforeRebate = taxOnNormalIncome + taxOnSpecialIncome;
    } else if (assesseeType === 'company_115bab') {
      // Domestic Co u/s 115BAB @ 15%
      taxOnNormalIncome = normalTaxableIncome * MASTER_RATES.ENTITY_RATES.DOMESTIC_COMPANY_115BAB.baseRate;
      baseTaxBeforeRebate = taxOnNormalIncome + taxOnSpecialIncome;
    } else if (assesseeType === 'company_reg_25') {
      // Regular Co (Turnover <= 400 Cr) @ 25%
      taxOnNormalIncome = normalTaxableIncome * MASTER_RATES.ENTITY_RATES.DOMESTIC_COMPANY_REGULAR_25.baseRate;
      baseTaxBeforeRebate = taxOnNormalIncome + taxOnSpecialIncome;
    } else if (assesseeType === 'company_reg_30') {
      // Regular Co (Turnover > 400 Cr) @ 30%
      taxOnNormalIncome = normalTaxableIncome * MASTER_RATES.ENTITY_RATES.DOMESTIC_COMPANY_REGULAR_30.baseRate;
      baseTaxBeforeRebate = taxOnNormalIncome + taxOnSpecialIncome;
    } else if (assesseeType === 'company_foreign') {
      // Foreign Company @ 35% (Budget 2024 rate)
      taxOnNormalIncome = normalTaxableIncome * MASTER_RATES.ENTITY_RATES.FOREIGN_COMPANY.baseRate;
      baseTaxBeforeRebate = taxOnNormalIncome + taxOnSpecialIncome;
    } else if (assesseeType === 'cooperative_115bad') {
      taxOnNormalIncome = normalTaxableIncome * MASTER_RATES.ENTITY_RATES.COOPERATIVE_115BAD.baseRate;
      baseTaxBeforeRebate = taxOnNormalIncome + taxOnSpecialIncome;
    } else if (assesseeType === 'cooperative_regular') {
      const slabRes = this.calculateSlabTax(normalTaxableIncome, MASTER_RATES.SLABS.COOPERATIVE_SOCIETY_REGULAR);
      taxOnNormalIncome = slabRes.tax;
      normalSlabBreakdown = slabRes.slabBreakdown;
      baseTaxBeforeRebate = taxOnNormalIncome + taxOnSpecialIncome;
    }

    const netTaxAfterRebate = Math.max(0, baseTaxBeforeRebate - rebate87A);

    // 4. Surcharge & Marginal Relief
    let surchargeResult;
    if (assesseeType.startsWith('individual') || assesseeType === 'huf') {
      surchargeResult = this.computeIndividualSurchargeAndMarginalRelief(totalTaxableIncome, netTaxAfterRebate, isNewRegime);
    } else if (assesseeType === 'firm_llp') {
      const isSurchargeApplicable = totalTaxableIncome > MASTER_RATES.ENTITY_RATES.PARTNERSHIP_FIRM_LLP.surchargeThreshold;
      const rate = isSurchargeApplicable ? MASTER_RATES.ENTITY_RATES.PARTNERSHIP_FIRM_LLP.surchargeRate : 0;
      const surcharge = netTaxAfterRebate * rate;
      surchargeResult = { surchargeRate: rate, grossSurcharge: surcharge, marginalRelief: 0, netSurcharge: surcharge, taxWithSurcharge: netTaxAfterRebate + surcharge };
    } else if (assesseeType === 'company_115baa' || assesseeType === 'company_115bab' || assesseeType === 'cooperative_115bad') {
      const surcharge = netTaxAfterRebate * 0.10; // Flat 10%
      surchargeResult = { surchargeRate: 0.10, grossSurcharge: surcharge, marginalRelief: 0, netSurcharge: surcharge, taxWithSurcharge: netTaxAfterRebate + surcharge };
    } else if (assesseeType === 'company_reg_25' || assesseeType === 'company_reg_30') {
      let rate = 0;
      if (totalTaxableIncome > 100000000) rate = 0.12;
      else if (totalTaxableIncome > 10000000) rate = 0.07;
      const surcharge = netTaxAfterRebate * rate;
      surchargeResult = { surchargeRate: rate, grossSurcharge: surcharge, marginalRelief: 0, netSurcharge: surcharge, taxWithSurcharge: netTaxAfterRebate + surcharge };
    } else if (assesseeType === 'company_foreign') {
      let rate = 0;
      if (totalTaxableIncome > 100000000) rate = 0.05;
      else if (totalTaxableIncome > 10000000) rate = 0.02;
      const surcharge = netTaxAfterRebate * rate;
      surchargeResult = { surchargeRate: rate, grossSurcharge: surcharge, marginalRelief: 0, netSurcharge: surcharge, taxWithSurcharge: netTaxAfterRebate + surcharge };
    } else {
      surchargeResult = { surchargeRate: 0, grossSurcharge: 0, marginalRelief: 0, netSurcharge: 0, taxWithSurcharge: netTaxAfterRebate };
    }

    // 5. Health and Education Cess @ 4%
    const cess = Math.round(surchargeResult.taxWithSurcharge * MASTER_RATES.HEALTH_AND_EDUCATION_CESS);
    const totalTaxLiability = Math.round(surchargeResult.taxWithSurcharge + cess);

    // 6. Relief u/s 89 / 90 / 91
    const reliefSec89_90 = Number(state.reliefSec89_90 || 0);
    const netTaxPayableBeforePrepaid = Math.max(0, totalTaxLiability - reliefSec89_90);

    // 7. Prepaid Taxes (TDS, TCS, Advance Tax)
    const tdsClaimed = Number(state.prepaidTaxes?.tdsClaimed || 0);
    const tcsClaimed = Number(state.prepaidTaxes?.tcsClaimed || 0);
    const advanceTaxPaid = Number(state.prepaidTaxes?.advanceTaxPaid || 0);
    const totalPrepaidTaxes = tdsClaimed + tcsClaimed + advanceTaxPaid;

    const netTaxPayableOrRefundable = netTaxPayableBeforePrepaid - totalPrepaidTaxes;

    return {
      assesseeType,
      isNewRegime,
      assessmentYear: ay,
      heads: {
        salary: salaryResult,
        houseProperty: hpResult,
        pgbp: pgbpResult,
        capitalGains: cgResult,
        otherSources: osResult,
        summary: {
          salary: incomeSalary,
          houseProperty: incomeHP,
          pgbp: incomePGBP,
          capitalGains: incomeCG,
          otherSources: incomeOS
        }
      },
      grossTotalIncome,
      chapterVIA: chapterVIAResult,
      totalDeductionsAllowed: allowedChapterVIADeductions,
      totalTaxableIncome,
      taxComputation: {
        normalTaxableIncome,
        taxOnNormalIncome,
        normalSlabBreakdown,
        specialRateIncomeTotal,
        taxOnSpecialIncome,
        specialTaxBreakdown,
        baseTaxBeforeRebate,
        rebate87A,
        rebate87AMarginalRelief,
        netTaxAfterRebate,
        surcharge: surchargeResult,
        cess,
        totalTaxLiability,
        reliefSec89_90,
        netTaxPayableBeforePrepaid,
        prepaidTaxes: {
          tdsClaimed,
          tcsClaimed,
          advanceTaxPaid,
          totalPrepaidTaxes
        },
        netTaxPayableOrRefundable
      }
    };
  }

  /**
   * Side-by-Side Regime Comparison Matrix & Breakeven Analytics
   */
  static compareRegimes(state) {
    const newRegimeResult = this.computeTax(state, true);
    const oldRegimeResult = this.computeTax(state, false);

    const newTax = newRegimeResult.taxComputation.totalTaxLiability;
    const oldTax = oldRegimeResult.taxComputation.totalTaxLiability;
    const taxDifference = oldTax - newTax;

    const recommendedRegime = taxDifference > 0 ? 'NEW' : (taxDifference < 0 ? 'OLD' : 'EQUAL');
    const absoluteSavings = Math.abs(taxDifference);

    // Breakeven Deductions Finder:
    // How much total deduction in Old Regime is needed to make Old Regime tax <= New Regime tax?
    let breakevenDeductionsNeeded = 0;
    if (newTax === 0) {
      // In New Regime tax is 0 (income <= 7L or rebates), old regime needs income <= 5L or sufficient deductions
      const grossIncome = oldRegimeResult.grossTotalIncome;
      breakevenDeductionsNeeded = Math.max(0, grossIncome - 500000);
    } else {
      // Binary search / iterative convergence for exact breakeven deductions
      let low = 0;
      let high = oldRegimeResult.grossTotalIncome;
      let bestDeduction = high;

      for (let iter = 0; iter < 40; iter++) {
        const mid = (low + high) / 2;
        // Mock state with mid deductions
        const mockDeductions = {
          sec80C_ppf: Math.min(mid, 150000),
          sec80CCD1B: Math.min(Math.max(0, mid - 150000), 50000),
          sec80CCD2_employerNps: Number(state.deductions?.sec80CCD2_employerNps || 0),
          otherDeductions: Math.max(0, mid - 200000)
        };
        const tempState = { ...state, deductions: mockDeductions };
        const tempOldResult = this.computeTax(tempState, false);
        const tempOldTax = tempOldResult.taxComputation.totalTaxLiability;

        if (tempOldTax <= newTax) {
          bestDeduction = mid;
          high = mid;
        } else {
          low = mid;
        }
      }
      breakevenDeductionsNeeded = Math.round(bestDeduction);
    }

    const currentOldDeductions = oldRegimeResult.totalDeductionsAllowed + (oldRegimeResult.heads.salary.hraExempt || 0) + (oldRegimeResult.heads.houseProperty.allowableLossAgainstOtherHeads < 0 ? Math.abs(oldRegimeResult.heads.houseProperty.allowableLossAgainstOtherHeads) : 0);
    const deductionDeficit = Math.max(0, breakevenDeductionsNeeded - currentOldDeductions);

    return {
      newRegime: newRegimeResult,
      oldRegime: oldRegimeResult,
      taxDifference,
      recommendedRegime,
      absoluteSavings,
      breakevenAnalytics: {
        breakevenDeductionsNeeded,
        currentOldDeductions,
        deductionDeficit,
        insight: recommendedRegime === 'NEW'
          ? `You save ₹${absoluteSavings.toLocaleString('en-IN')} in New Regime. You would need total deductions & exemptions of at least ₹${breakevenDeductionsNeeded.toLocaleString('en-IN')} in Old Regime to match New Regime.`
          : `You save ₹${absoluteSavings.toLocaleString('en-IN')} in Old Regime due to deductions claimed (₹${currentOldDeductions.toLocaleString('en-IN')}).`
      }
    };
  }
}
