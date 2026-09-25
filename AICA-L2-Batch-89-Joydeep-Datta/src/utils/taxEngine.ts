import {
  EmployeeMaster,
  EmployeeDeclaration,
  TaxConfig,
  TaxRegime,
  TaxCalculationBreakdown,
  TaxSlab,
} from '../types/payroll';

export function calculateAge(dobStr: string, fyEndYear: number = 2027): number {
  if (!dobStr) return 30;
  const parts = dobStr.includes('-') ? dobStr.split('-') : dobStr.split('/');
  let birthYear = 1990;
  if (parts.length === 3) {
    if (parts[0].length === 4) {
      birthYear = parseInt(parts[0], 10);
    } else {
      birthYear = parseInt(parts[2], 10);
    }
  }
  return isNaN(birthYear) ? 30 : fyEndYear - birthYear;
}

export function computeSlabTax(income: number, slabs: TaxSlab[]): number {
  let tax = 0;
  for (const slab of slabs) {
    if (income > slab.from) {
      const taxableInSlab = slab.to !== null ? Math.min(income, slab.to) - slab.from : income - slab.from;
      if (taxableInSlab > 0) {
        tax += taxableInSlab * slab.rate;
      }
    }
  }
  return tax;
}

export function computeSurcharge(tax: number, income: number, surchargeSlabs: TaxSlab[]): number {
  let rate = 0;
  for (const slab of surchargeSlabs) {
    if (income > slab.from) {
      if (slab.to === null || income <= slab.to) {
        rate = slab.rate;
      }
    }
  }
  return tax * rate;
}

export function computeTaxBreakdown(
  emp: EmployeeMaster,
  decl: EmployeeDeclaration | undefined,
  config: TaxConfig,
  regime: TaxRegime,
  projectedAnnualGross: number,
  projectedAnnualBasic: number,
  projectedAnnualHra: number,
  annualEmployeePf: number,
  monthsRemaining: number = 12,
  tdsDeductedYtd: number = 0
): TaxCalculationBreakdown {
  const fyYear = parseInt(config.financialYear.split('-')[0], 10) + 1;
  const age = calculateAge(emp.dateOfBirth, fyYear);

  const prevEmployerGross = decl?.prevEmployerGrossSalary || 0;
  const prevEmployerTds = decl?.prevEmployerTdsDeducted || 0;
  const prevEmployerPf = decl?.prevEmployerPfDeducted || 0;

  const totalGrossSalary = projectedAnnualGross + prevEmployerGross;

  // 1. Section 10 Exemptions (Old Regime Only)
  let hraExemption = 0;
  let ceaExemption = 0;
  let ltaExemption = 0;
  const otherSec10 = (decl?.otherExemptionSec10 || 0) + (decl?.prevEmployerExemptionsSec10 || 0);

  if (regime === 'Old') {
    // HRA Exemption: Least of 3
    const rentPaid = decl?.rentPaidAnnual || 0;
    const isMetro = (decl?.rentedCityMetro || emp.metroFlag) === 'Y';
    const metroPercent = isMetro ? config.common.hraMetroPctOfBasic : config.common.hraNonMetroPctOfBasic;
    const rentMinusTenPercentBasic = Math.max(0, rentPaid - config.common.hraRentLessPctOfBasic * projectedAnnualBasic);
    const basicLimit = metroPercent * projectedAnnualBasic;

    if (rentPaid > 0) {
      hraExemption = Math.min(projectedAnnualHra, rentMinusTenPercentBasic, basicLimit);
    }

    // Children Education Allowance
    if (emp.childrenEducationAllowanceMonthly > 0) {
      const children = Math.min(config.regimes.OLD.allows.maxChildrenForCea, 2);
      const maxCea = children * config.regimes.OLD.allows.childrenEducationAllowancePerChildPm * 12;
      ceaExemption = Math.min(emp.childrenEducationAllowanceMonthly * 12, maxCea);
    }

    // LTA Exemption
    if (decl?.ltaExemptionClaimed) {
      ltaExemption = Math.min(decl.ltaExemptionClaimed, emp.ltaMonthly * 12);
    }
  }

  const totalSec10 = hraExemption + ceaExemption + ltaExemption + otherSec10;
  const grossAfterSec10 = Math.max(0, totalGrossSalary - totalSec10);

  // 2. Standard Deduction
  const standardDeduction =
    regime === 'Old' ? config.regimes.OLD.standardDeduction : config.regimes.NEW.standardDeduction;

  const incomeUnderSalaries = Math.max(0, grossAfterSec10 - standardDeduction);

  // 3. Income from House Property
  let housePropertyIncome = 0;
  if (regime === 'Old') {
    const selfOccupiedInterest = decl?.housingLoanInterestSelfOccupied || 0;
    const cappedSelfInterest = Math.min(selfOccupiedInterest, config.regimes.OLD.allows.sec24bSelfOccupiedCap);
    const letOutNet = decl?.letOutPropertyNetIncome || 0;
    const rawHp = letOutNet - cappedSelfInterest;
    // Setoff of house property loss capped at 2,00,000
    if (rawHp < 0) {
      housePropertyIncome = Math.max(rawHp, -config.regimes.OLD.chapterViaCaps.house_property_loss_setoff_cap);
    } else {
      housePropertyIncome = rawHp;
    }
  } else {
    // New regime: let-out property income can be declared, but self-occupied interest is zero
    housePropertyIncome = Math.max(0, decl?.letOutPropertyNetIncome || 0);
  }

  // 4. Income from Other Sources
  const savingsInterest = decl?.savingsBankInterest || 0;
  const fdInterest = decl?.fixedDepositInterest || 0;
  const otherIncome = decl?.otherIncomeDeclared || 0;
  const totalOtherSources = savingsInterest + fdInterest + otherIncome;

  const grossTotalIncome = Math.max(0, incomeUnderSalaries + housePropertyIncome + totalOtherSources);

  // 5. Chapter VI-A Deductions
  let sec80C = 0;
  let sec80CCD1B = 0;
  let sec80CCD2 = 0;
  let sec80D = 0;
  let sec80E = 0;
  let sec80EEB = 0;
  let sec80G = 0;
  let sec80DD = 0;
  let sec80U = 0;
  let sec80TTA_TTB = 0;

  if (regime === 'Old') {
    // 80C
    const raw80c =
      (decl?.housingLoanPrincipal || 0) +
      (decl?.ppf || 0) +
      (decl?.licPremium || 0) +
      (decl?.elssMutualFund || 0) +
      (decl?.nsc || 0) +
      (decl?.tuitionFees || 0) +
      (decl?.sukanyaSamriddhi || 0) +
      (decl?.taxSaverFd5yr || 0) +
      (decl?.other80C || 0) +
      annualEmployeePf +
      prevEmployerPf;
    sec80C = Math.min(raw80c, config.regimes.OLD.chapterViaCaps['80C']);

    // 80CCD(1B) Self NPS
    sec80CCD1B = Math.min(decl?.npsSelf80CCD1B || 0, config.regimes.OLD.chapterViaCaps['80CCD1B']);

    // 80CCD(2) Employer NPS (10% of Basic)
    if (decl?.optInEmployerNps80CCD2 === 'Y' || emp.employerNpsMonthly > 0) {
      sec80CCD2 = Math.min(
        emp.employerNpsMonthly * 12,
        projectedAnnualBasic * config.regimes.OLD.allows.sec80CCD2EmployerNpsPctOfBasic
      );
    }

    // 80D Health Insurance
    const isSelfSenior = age >= config.common.seniorAge;
    const isParentsSenior = decl?.parentsSeniorCitizen === 'Y';
    const selfCap = isSelfSenior
      ? config.regimes.OLD.chapterViaCaps['80D_self_family_senior']
      : config.regimes.OLD.chapterViaCaps['80D_self_family'];
    const parentsCap = isParentsSenior
      ? config.regimes.OLD.chapterViaCaps['80D_parents_senior']
      : config.regimes.OLD.chapterViaCaps['80D_parents'];

    const rawSelf = (decl?.mediclaimSelfFamily || 0) + Math.min(decl?.preventiveHealthCheckup || 0, 5000);
    const selfDeduction = Math.min(rawSelf, selfCap);
    const parentsDeduction = Math.min(decl?.mediclaimParents || 0, parentsCap);
    sec80D = selfDeduction + parentsDeduction;

    // 80E (Education Loan Interest)
    sec80E = decl?.sec80EEducationLoanInterest || 0;

    // 80EEB (EV Loan)
    sec80EEB = Math.min(decl?.sec80EEBEVLoanInterest || 0, config.regimes.OLD.chapterViaCaps['80EEB']);

    // 80G
    sec80G = (decl?.sec80GDonation100pct || 0) + (decl?.sec80GDonation50pct || 0) * 0.5;

    // 80DD Disability Dependent
    if (decl?.sec80DDDisabledDependent === 'Severe Disability') {
      sec80DD = config.regimes.OLD.chapterViaCaps['80DD_severe'];
    } else if (decl?.sec80DDDisabledDependent === 'Disability') {
      sec80DD = config.regimes.OLD.chapterViaCaps['80DD_disability'];
    }

    // 80U Self Disability
    if (decl?.sec80USelfDisability === 'Severe Disability') {
      sec80U = config.regimes.OLD.chapterViaCaps['80U_severe'];
    } else if (decl?.sec80USelfDisability === 'Disability') {
      sec80U = config.regimes.OLD.chapterViaCaps['80U_disability'];
    }

    // 80TTA / 80TTB
    if (age >= config.common.seniorAge) {
      sec80TTA_TTB = Math.min(savingsInterest + fdInterest, config.regimes.OLD.chapterViaCaps['80TTB']);
    } else {
      sec80TTA_TTB = Math.min(savingsInterest, config.regimes.OLD.chapterViaCaps['80TTA']);
    }
  } else {
    // New Regime: ONLY Employer NPS 80CCD(2) allowed (14% of Basic)
    if (decl?.optInEmployerNps80CCD2 === 'Y' || emp.employerNpsMonthly > 0) {
      const allowedAmount = projectedAnnualBasic * config.regimes.NEW.allows.sec80CCD2EmployerNpsPctOfBasic;
      sec80CCD2 = Math.min(emp.employerNpsMonthly * 12, allowedAmount);
    }
  }

  const totalChapterVia =
    sec80C +
    sec80CCD1B +
    sec80CCD2 +
    sec80D +
    sec80E +
    sec80EEB +
    sec80G +
    sec80DD +
    sec80U +
    sec80TTA_TTB;

  // 6. Net Taxable Income
  const netTaxableIncome = Math.max(0, grossTotalIncome - totalChapterVia);

  // 7. Slab Tax
  let taxOnIncome = 0;
  if (regime === 'Old') {
    let slabKey: 'NORMAL' | 'SENIOR' | 'SUPER_SENIOR' = 'NORMAL';
    if (age >= config.common.superSeniorAge) {
      slabKey = 'SUPER_SENIOR';
    } else if (age >= config.common.seniorAge) {
      slabKey = 'SENIOR';
    }
    taxOnIncome = computeSlabTax(netTaxableIncome, config.regimes.OLD.slabs[slabKey]);
  } else {
    taxOnIncome = computeSlabTax(netTaxableIncome, config.regimes.NEW.slabs.ALL);
  }

  // 8. Section 87A Rebate
  let rebate87A = 0;
  if (regime === 'Old') {
    if (netTaxableIncome <= config.regimes.OLD.rebate87A.incomeCeiling) {
      rebate87A = Math.min(taxOnIncome, config.regimes.OLD.rebate87A.maxRebate);
    }
  } else {
    // New regime rebate
    const ceiling = config.regimes.NEW.rebate87A.incomeCeiling;
    if (netTaxableIncome <= ceiling) {
      rebate87A = Math.min(taxOnIncome, config.regimes.NEW.rebate87A.maxRebate);
    } else if (config.regimes.NEW.rebate87A.marginalRelief) {
      // Marginal relief when income slightly exceeds ceiling (e.g. 12L):
      // Tax payable cannot exceed (netTaxableIncome - ceiling)
      const excessIncome = netTaxableIncome - ceiling;
      if (taxOnIncome > excessIncome) {
        rebate87A = taxOnIncome - excessIncome;
      }
    }
  }

  const taxAfterRebate = Math.max(0, taxOnIncome - rebate87A);

  // 9. Surcharge
  const surchargeSlabs = regime === 'Old' ? config.regimes.OLD.surcharge : config.regimes.NEW.surcharge;
  const surcharge = taxAfterRebate > 0 ? computeSurcharge(taxAfterRebate, netTaxableIncome, surchargeSlabs) : 0;

  // 10. Health & Education Cess (4%)
  const cessRate = regime === 'Old' ? config.regimes.OLD.cessRate : config.regimes.NEW.cessRate;
  const cess = Math.round((taxAfterRebate + surcharge) * cessRate);

  const totalAnnualTaxLiability = taxAfterRebate + surcharge + cess;

  // 11. TDS Spreading
  const remainingTaxToDeduct = Math.max(0, totalAnnualTaxLiability - prevEmployerTds - tdsDeductedYtd);
  const remainingMonthsClamped = Math.max(1, monthsRemaining);
  const currentMonthTds = Math.round(remainingTaxToDeduct / remainingMonthsClamped);

  return {
    regime,
    annualGrossSalary: totalGrossSalary,
    exemptionsSec10: {
      hra: hraExemption,
      cea: ceaExemption,
      lta: ltaExemption,
      other: otherSec10,
      total: totalSec10,
    },
    grossSalaryAfterSec10: grossAfterSec10,
    standardDeduction,
    incomeUnderHeadSalaries: incomeUnderSalaries,
    incomeFromHouseProperty: housePropertyIncome,
    incomeFromOtherSources: totalOtherSources,
    grossTotalIncome,
    chapterViaDeductions: {
      sec80C,
      sec80CCD1B,
      sec80CCD2,
      sec80D,
      sec80E,
      sec80EEB,
      sec80G,
      sec80DD,
      sec80U,
      sec80TTA_TTB,
      total: totalChapterVia,
    },
    netTaxableIncome,
    taxOnIncome,
    rebate87A,
    taxAfterRebate,
    surcharge,
    cess,
    totalAnnualTaxLiability,
    tdsCreditPreviousEmployer: prevEmployerTds,
    tdsDeductedYtd,
    remainingTaxToDeduct,
    remainingMonths: remainingMonthsClamped,
    currentMonthTds,
  };
}
