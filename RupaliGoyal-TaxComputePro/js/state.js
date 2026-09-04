/**
 * TaxCompute Pro - Central State Store & Preset Assessee Profiles
 */

export const PRESET_PROFILES = {
  SALARIED_TECH_LEAD: {
    id: 'SALARIED_TECH_LEAD',
    profileName: 'Senior Tech Lead / VP (Salaried + ESOPs + Home Loan)',
    assesseeType: 'individual_general',
    assessmentYear: '2026-27',
    financialYear: '2025-26',
    assesseeDetails: {
      name: 'Aditya Vikram Sharma',
      pan: 'ABCPS1234F',
      dob: '1988-06-15',
      residentialStatus: 'Resident',
      filingStatus: 'Individual',
      caName: 'R. K. Agrawal & Co.',
      caMembership: '054321',
      firmRegNo: '001234N',
      udin: '26054321AAAAAA1122'
    },
    salary: {
      basicSalary: 1800000,
      da: 360000,
      hraReceived: 600000,
      rentPaid: 480000,
      isMetro: true,
      ltaReceived: 100000,
      ltaExempt: 80000,
      specialAllowance: 540000,
      bonusCommission: 300000,
      perquisites: 50000,
      professionalTax: 2500,
      entertainmentAllowance: 0,
      isGovtEmployee: false
    },
    houseProperty: {
      properties: [
        {
          id: 1,
          propertyName: 'Primary Residence (Indiranagar, Bengaluru)',
          type: 'self',
          grossRent: 0,
          municipalTaxes: 12000,
          loanInterest: 240000,
          preConstructionInterest: 0
        }
      ]
    },
    pgbp: {
      mode: 'presumptive',
      presumptiveScheme: '44AD',
      sec44ad_digitalTurnover: 0,
      sec44ad_cashTurnover: 0,
      sec44ad_declaredDigitalProfit: 0,
      sec44ad_declaredCashProfit: 0
    },
    capitalGains: {
      stcg111a_gross: 120000,
      stcg111a_transferExp: 0,
      stcgNormal_gross: 0,
      stcgNormal_transferExp: 0,
      ltcg112a_gross: 250000,
      ltcg112a_transferExp: 0,
      ltcg112_gross: 0,
      ltcg112_transferExp: 0,
      rollover54: 0
    },
    otherSources: {
      savingsInterest: 35000,
      termDepositInterest: 75000,
      dividendIncome: 42000,
      familyPension: 0,
      otherRegularIncome: 0,
      allowableExpensesSec57: 0,
      lotteryIncome115BB: 0,
      onlineGaming115BBJ: 0,
      cryptoVdaIncome115BBH: 0
    },
    deductions: {
      sec80C_ppf: 100000,
      sec80C_epf: 150000,
      sec80C_elss: 50000,
      sec80C_lic: 25000,
      sec80C_homeLoanPrincipal: 85000,
      sec80C_tuitionFees: 40000,
      sec80C_other: 0,
      sec80CCC: 0,
      sec80CCD1: 0,
      sec80CCD1B: 50000,
      sec80CCD2_employerNps: 250000, // Employer NPS 14%
      sec80D_selfInsurance: 25000,
      sec80D_preventiveCheckup: 5000,
      isSelfSenior: false,
      sec80D_parentsInsurance: 45000,
      sec80D_parentsPreventive: 5000,
      isParentsSenior: true,
      sec80E_educationInterest: 0,
      sec80EEA_housingInterest: 0,
      sec80G_donations: 10000,
      sec80JJAA: 0,
      otherDeductions: 0
    },
    prepaidTaxes: {
      tdsClaimed: 450000,
      tcsClaimed: 15000,
      advanceTaxPaid: 60000
    },
    advanceTaxInstallments: {
      q1_june15: 15000,
      q2_sept15: 20000,
      q3_dec15: 15000,
      q4_mar15: 10000,
      q4_mar31: 0,
      filingDueDate: '2026-07-31',
      actualFilingDate: '2026-07-25'
    }
  },

  DOCTOR_CONSULTANT_44ADA: {
    id: 'DOCTOR_CONSULTANT_44ADA',
    profileName: 'Medical Surgeon / Consultant (Presumptive 44ADA + Rental Income)',
    assesseeType: 'individual_general',
    assessmentYear: '2026-27',
    financialYear: '2025-26',
    assesseeDetails: {
      name: 'Dr. Meenakshi Sundaram',
      pan: 'AAAPS4567M',
      dob: '1979-11-20',
      residentialStatus: 'Resident',
      filingStatus: 'Individual',
      caName: 'Sridhar & Narayanan, CAs',
      caMembership: '098765',
      firmRegNo: '005432S',
      udin: '26098765BBBBBB2233'
    },
    salary: {
      basicSalary: 0,
      da: 0,
      hraReceived: 0,
      rentPaid: 0,
      isMetro: false,
      ltaReceived: 0,
      ltaExempt: 0,
      specialAllowance: 0,
      bonusCommission: 0,
      perquisites: 0,
      professionalTax: 0,
      entertainmentAllowance: 0,
      isGovtEmployee: false
    },
    houseProperty: {
      properties: [
        {
          id: 1,
          propertyName: 'Commercial Clinic Space (Let-out to Polyclinic)',
          type: 'letout',
          grossRent: 480000,
          municipalTaxes: 24000,
          loanInterest: 150000,
          preConstructionInterest: 0
        }
      ]
    },
    pgbp: {
      mode: 'presumptive',
      presumptiveScheme: '44ADA',
      sec44ada_grossReceipts: 6200000,
      sec44ada_cashReceipts: 180000,
      sec44ada_declaredProfit: 3300000 // > 50%
    },
    capitalGains: {
      stcg111a_gross: 0,
      stcg111a_transferExp: 0,
      stcgNormal_gross: 0,
      stcgNormal_transferExp: 0,
      ltcg112a_gross: 120000,
      ltcg112a_transferExp: 0,
      ltcg112_gross: 0,
      ltcg112_transferExp: 0,
      rollover54: 0
    },
    otherSources: {
      savingsInterest: 48000,
      termDepositInterest: 180000,
      dividendIncome: 65000,
      familyPension: 0,
      otherRegularIncome: 0,
      allowableExpensesSec57: 0,
      lotteryIncome115BB: 0,
      onlineGaming115BBJ: 0,
      cryptoVdaIncome115BBH: 0
    },
    deductions: {
      sec80C_ppf: 150000,
      sec80C_epf: 0,
      sec80C_elss: 0,
      sec80C_lic: 45000,
      sec80C_homeLoanPrincipal: 0,
      sec80C_tuitionFees: 60000,
      sec80C_other: 0,
      sec80CCC: 0,
      sec80CCD1: 0,
      sec80CCD1B: 50000,
      sec80CCD2_employerNps: 0,
      sec80D_selfInsurance: 25000,
      sec80D_preventiveCheckup: 5000,
      isSelfSenior: false,
      sec80D_parentsInsurance: 50000,
      sec80D_parentsPreventive: 5000,
      isParentsSenior: true,
      sec80E_educationInterest: 0,
      sec80EEA_housingInterest: 0,
      sec80G_donations: 25000,
      sec80JJAA: 0,
      otherDeductions: 0
    },
    prepaidTaxes: {
      tdsClaimed: 580000, // 10% TDS u/s 194J
      tcsClaimed: 0,
      advanceTaxPaid: 150000
    },
    advanceTaxInstallments: {
      q1_june15: 0,
      q2_sept15: 0,
      q3_dec15: 0,
      q4_mar15: 150000, // 44ADA can pay 100% by 15 March
      q4_mar31: 0,
      filingDueDate: '2026-07-31',
      actualFilingDate: '2026-07-20'
    }
  },

  HNI_INVESTOR: {
    id: 'HNI_INVESTOR',
    profileName: 'HNI Investor (Business + Multi-Letout + Capital Gains + Crypto)',
    assesseeType: 'individual_general',
    assessmentYear: '2026-27',
    financialYear: '2025-26',
    assesseeDetails: {
      name: 'Rajiv Singhania',
      pan: 'AAAPS9988K',
      dob: '1974-03-22',
      residentialStatus: 'Resident',
      filingStatus: 'Individual',
      caName: 'Gupta, Singhal & Associates',
      caMembership: '071234',
      firmRegNo: '007788C',
      udin: '26071234CCCCCC3344'
    },
    salary: {
      basicSalary: 0,
      da: 0,
      hraReceived: 0,
      rentPaid: 0,
      isMetro: false,
      ltaReceived: 0,
      ltaExempt: 0,
      specialAllowance: 0,
      bonusCommission: 0,
      perquisites: 0,
      professionalTax: 0,
      entertainmentAllowance: 0,
      isGovtEmployee: false
    },
    houseProperty: {
      properties: [
        {
          id: 1,
          propertyName: 'Apartment 1 (Worli, Mumbai - Let Out)',
          type: 'letout',
          grossRent: 1200000,
          municipalTaxes: 80000,
          loanInterest: 350000,
          preConstructionInterest: 0
        },
        {
          id: 2,
          propertyName: 'Villa 2 (Gurugram - Let Out)',
          type: 'letout',
          grossRent: 900000,
          municipalTaxes: 45000,
          loanInterest: 280000,
          preConstructionInterest: 0
        }
      ]
    },
    pgbp: {
      mode: 'presumptive',
      presumptiveScheme: '44AD',
      sec44ad_digitalTurnover: 22000000,
      sec44ad_cashTurnover: 800000,
      sec44ad_declaredDigitalProfit: 1600000,
      sec44ad_declaredCashProfit: 80000
    },
    capitalGains: {
      stcg111a_gross: 850000,
      stcg111a_transferExp: 0,
      stcgNormal_gross: 150000,
      stcgNormal_transferExp: 0,
      ltcg112a_gross: 1500000,
      ltcg112a_transferExp: 0,
      ltcg112_gross: 3500000,
      ltcg112_transferExp: 100000,
      rollover54: 2000000 // Sec 54EC Bonds ₹20L
    },
    otherSources: {
      savingsInterest: 85000,
      termDepositInterest: 450000,
      dividendIncome: 320000,
      familyPension: 0,
      otherRegularIncome: 0,
      allowableExpensesSec57: 0,
      lotteryIncome115BB: 0,
      onlineGaming115BBJ: 0,
      cryptoVdaIncome115BBH: 400000 // Crypto flat 30%
    },
    deductions: {
      sec80C_ppf: 150000,
      sec80C_epf: 0,
      sec80C_elss: 0,
      sec80C_lic: 50000,
      sec80C_homeLoanPrincipal: 0,
      sec80C_tuitionFees: 0,
      sec80C_other: 0,
      sec80CCC: 0,
      sec80CCD1: 0,
      sec80CCD1B: 50000,
      sec80CCD2_employerNps: 0,
      sec80D_selfInsurance: 25000,
      sec80D_preventiveCheckup: 5000,
      isSelfSenior: false,
      sec80D_parentsInsurance: 50000,
      sec80D_parentsPreventive: 5000,
      isParentsSenior: true,
      sec80E_educationInterest: 0,
      sec80EEA_housingInterest: 0,
      sec80G_donations: 50000,
      sec80JJAA: 0,
      otherDeductions: 0
    },
    prepaidTaxes: {
      tdsClaimed: 280000,
      tcsClaimed: 40000,
      advanceTaxPaid: 850000
    },
    advanceTaxInstallments: {
      q1_june15: 150000,
      q2_sept15: 250000,
      q3_dec15: 250000,
      q4_mar15: 200000,
      q4_mar31: 0,
      filingDueDate: '2026-07-31',
      actualFilingDate: '2026-07-28'
    }
  },

  DOMESTIC_COMPANY_115BAA: {
    id: 'DOMESTIC_COMPANY_115BAA',
    profileName: 'AeroTech Electronics Pvt Ltd (Domestic Co u/s 115BAA @ 22%)',
    assesseeType: 'company_115baa',
    assessmentYear: '2026-27',
    financialYear: '2025-26',
    assesseeDetails: {
      name: 'AeroTech Electronics India Private Limited',
      pan: 'AABCA8899M',
      dob: '2020-04-12',
      residentialStatus: 'Resident Corporate',
      filingStatus: 'Domestic Company',
      caName: 'Deloitte, Goyal & Shah LLP',
      caMembership: '043210',
      firmRegNo: '102938W',
      udin: '26043210DDDDDD4455'
    },
    salary: { basicSalary: 0, da: 0, hraReceived: 0, rentPaid: 0, isMetro: false, ltaReceived: 0, ltaExempt: 0, specialAllowance: 0, bonusCommission: 0, perquisites: 0, professionalTax: 0, entertainmentAllowance: 0, isGovtEmployee: false },
    houseProperty: { properties: [] },
    pgbp: {
      mode: 'books',
      presumptiveScheme: '44AD',
      netProfitAsPerPL: 8500000,
      disallowanceSec40a: 450000, // TDS non-deduction
      disallowanceSec43B: 350000, // Unpaid statutory bonus/leave encashment
      disallowanceSec40A3: 50000,
      otherInadmissibleExpenses: 150000,
      bookDepreciation: 1400000,
      itDepreciationSec32: 1850000,
      incomeCreditedNotTaxableInPgbp: 200000
    },
    capitalGains: {
      stcg111a_gross: 0,
      stcg111a_transferExp: 0,
      stcgNormal_gross: 0,
      stcgNormal_transferExp: 0,
      ltcg112a_gross: 0,
      ltcg112a_transferExp: 0,
      ltcg112_gross: 400000,
      ltcg112_transferExp: 0,
      rollover54: 0
    },
    otherSources: {
      savingsInterest: 0,
      termDepositInterest: 200000,
      dividendIncome: 0,
      familyPension: 0,
      otherRegularIncome: 0,
      allowableExpensesSec57: 0,
      lotteryIncome115BB: 0,
      onlineGaming115BBJ: 0,
      cryptoVdaIncome115BBH: 0
    },
    deductions: {
      sec80C_ppf: 0,
      sec80C_epf: 0,
      sec80C_elss: 0,
      sec80C_lic: 0,
      sec80C_homeLoanPrincipal: 0,
      sec80C_tuitionFees: 0,
      sec80C_other: 0,
      sec80CCC: 0,
      sec80CCD1: 0,
      sec80CCD1B: 0,
      sec80CCD2_employerNps: 0,
      sec80D_selfInsurance: 0,
      sec80D_preventiveCheckup: 0,
      isSelfSenior: false,
      sec80D_parentsInsurance: 0,
      sec80D_parentsPreventive: 0,
      isParentsSenior: false,
      sec80E_educationInterest: 0,
      sec80EEA_housingInterest: 0,
      sec80G_donations: 0,
      sec80JJAA: 300000, // 80JJAA for 30% new employee salary
      otherDeductions: 0
    },
    prepaidTaxes: {
      tdsClaimed: 450000,
      tcsClaimed: 0,
      advanceTaxPaid: 1600000
    },
    advanceTaxInstallments: {
      q1_june15: 350000,
      q2_sept15: 650000,
      q3_dec15: 400000,
      q4_mar15: 200000,
      q4_mar31: 0,
      filingDueDate: '2026-10-31',
      actualFilingDate: '2026-10-15'
    }
  }
};

export class AppState {
  constructor() {
    this.listeners = [];
    this.state = JSON.parse(JSON.stringify(PRESET_PROFILES.SALARIED_TECH_LEAD));
  }

  getState() {
    return this.state;
  }

  setState(partialState) {
    this.state = { ...this.state, ...partialState };
    this.notify();
  }

  loadProfile(profileKey) {
    if (PRESET_PROFILES[profileKey]) {
      this.state = JSON.parse(JSON.stringify(PRESET_PROFILES[profileKey]));
      this.notify();
    }
  }

  subscribe(listener) {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener);
    };
  }

  notify() {
    this.listeners.forEach(fn => fn(this.state));
  }

  exportJson() {
    return JSON.stringify(this.state, null, 2);
  }

  importJson(jsonString) {
    try {
      const parsed = JSON.parse(jsonString);
      if (parsed && typeof parsed === 'object') {
        this.state = parsed;
        this.notify();
        return { success: true };
      }
    } catch (e) {
      return { success: false, error: e.message };
    }
    return { success: false, error: 'Invalid JSON payload' };
  }
}
