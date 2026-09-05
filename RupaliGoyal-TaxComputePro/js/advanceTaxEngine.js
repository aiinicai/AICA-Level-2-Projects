/**
 * TaxCompute Pro - Advance Tax Schedule & Statutory Penal Interest Engine
 * Sections 208, 209, 210, 234A, 234B, and 234C of the Income Tax Act, 1961
 */

export class AdvanceTaxEngine {

  /**
   * Compute Advance Tax Schedule & Sections 234A, 234B, 234C Interest
   */
  static computeAdvanceTaxAndInterest(params) {
    const {
      totalTaxLiability = 0,
      tdsTcsClaimed = 0,
      reliefSec89_90 = 0,
      assesseeType = 'individual_general',
      isPresumptive44AD_ADA = false,
      installmentsPaid = {
        q1_june15: 0,
        q2_sept15: 0,
        q3_dec15: 0,
        q4_mar15: 0,
        q4_mar31: 0, // Any payment made between 16-31 March
      },
      filingDueDate = '2026-07-31', // '2026-07-31' for non-audit, '2026-10-31' for audit
      actualFilingDate = '2026-07-31',
      assessmentYear = '2026-27'
    } = params;

    // Assessed Tax u/s 234B/234C = Total Tax - (TDS + TCS + Relief 89/90/91)
    const assessedTax = Math.max(0, totalTaxLiability - tdsTcsClaimed - reliefSec89_90);

    // Section 208: Advance tax applicable if assessed tax is >= ₹10,000
    // Senior citizen exemption u/s 207(2): Resident senior citizen with NO business/profession income
    const isSenior = assesseeType === 'individual_senior' || assesseeType === 'individual_super_senior';
    const hasPgbp = params.hasPgbp || false;
    const isExemptSenior = isSenior && !hasPgbp;

    const isAdvanceTaxApplicable = (assessedTax >= 10000) && !isExemptSenior;

    // Actual payments made
    const paidQ1 = Number(installmentsPaid.q1_june15 || 0);
    const paidQ2 = Number(installmentsPaid.q2_sept15 || 0);
    const paidQ3 = Number(installmentsPaid.q3_dec15 || 0);
    const paidQ4 = Number(installmentsPaid.q4_mar15 || 0);
    const paidMar31 = Number(installmentsPaid.q4_mar31 || 0);

    const cumPaidQ1 = paidQ1;
    const cumPaidQ2 = cumPaidQ1 + paidQ2;
    const cumPaidQ3 = cumPaidQ2 + paidQ3;
    const cumPaidQ4 = cumPaidQ3 + paidQ4;
    const totalAdvanceTaxPaidUpto31Mar = cumPaidQ4 + paidMar31;

    // 1. SECTION 234C - DEFERMENT OF ADVANCE TAX
    let interest234C = 0;
    let schedule = [];

    if (isAdvanceTaxApplicable) {
      if (isPresumptive44AD_ADA) {
        // Presumptive taxpayers u/s 44AD / 44ADA are required to pay 100% advance tax in a single installment by 15th March
        const reqMar15 = assessedTax;
        const shortfallMar15 = Math.max(0, reqMar15 - cumPaidQ4);
        const intMar15 = Math.round(shortfallMar15 * 0.01 * 1); // 1% for 1 month
        interest234C += intMar15;

        schedule = [
          {
            installment: 'Single Installment (15 March)',
            dueDate: '15-Mar-2026',
            targetPct: 100,
            requiredCumulativeAmount: reqMar15,
            actualCumulativePaid: cumPaidQ4,
            shortfall: shortfallMar15,
            interestMonths: 1,
            interest234C: intMar15,
            status: shortfallMar15 === 0 ? 'Compliant' : 'Shortfall'
          }
        ];
      } else {
        // Standard 4 installments for regular taxpayers:
        // Q1: 15% by 15 June (Interest triggered if paid < 12%)
        const reqQ1 = Math.round(assessedTax * 0.15);
        const triggerQ1 = Math.round(assessedTax * 0.12);
        const shortfallQ1 = cumPaidQ1 < triggerQ1 ? Math.max(0, reqQ1 - cumPaidQ1) : 0;
        const intQ1 = Math.round(shortfallQ1 * 0.01 * 3); // 1% per month for 3 months

        // Q2: 45% by 15 September (Interest triggered if paid < 36%)
        const reqQ2 = Math.round(assessedTax * 0.45);
        const triggerQ2 = Math.round(assessedTax * 0.36);
        const shortfallQ2 = cumPaidQ2 < triggerQ2 ? Math.max(0, reqQ2 - cumPaidQ2) : 0;
        const intQ2 = Math.round(shortfallQ2 * 0.01 * 3); // 1% per month for 3 months

        // Q3: 75% by 15 December (Interest triggered if paid < 75%)
        const reqQ3 = Math.round(assessedTax * 0.75);
        const shortfallQ3 = Math.max(0, reqQ3 - cumPaidQ3);
        const intQ3 = Math.round(shortfallQ3 * 0.01 * 3); // 1% per month for 3 months

        // Q4: 100% by 15 March (Interest triggered if paid < 100%)
        const reqQ4 = assessedTax;
        const shortfallQ4 = Math.max(0, reqQ4 - cumPaidQ4);
        const intQ4 = Math.round(shortfallQ4 * 0.01 * 1); // 1% per month for 1 month

        interest234C = intQ1 + intQ2 + intQ3 + intQ4;

        schedule = [
          {
            installment: '1st Installment (15 June)',
            dueDate: '15-Jun-2025',
            targetPct: 15,
            requiredCumulativeAmount: reqQ1,
            actualCumulativePaid: cumPaidQ1,
            shortfall: shortfallQ1,
            interestMonths: 3,
            interest234C: intQ1,
            status: shortfallQ1 === 0 ? 'Compliant' : 'Shortfall'
          },
          {
            installment: '2nd Installment (15 September)',
            dueDate: '15-Sep-2025',
            targetPct: 45,
            requiredCumulativeAmount: reqQ2,
            actualCumulativePaid: cumPaidQ2,
            shortfall: shortfallQ2,
            interestMonths: 3,
            interest234C: intQ2,
            status: shortfallQ2 === 0 ? 'Compliant' : 'Shortfall'
          },
          {
            installment: '3rd Installment (15 December)',
            dueDate: '15-Dec-2025',
            targetPct: 75,
            requiredCumulativeAmount: reqQ3,
            actualCumulativePaid: cumPaidQ3,
            shortfall: shortfallQ3,
            interestMonths: 3,
            interest234C: intQ3,
            status: shortfallQ3 === 0 ? 'Compliant' : 'Shortfall'
          },
          {
            installment: '4th Installment (15 March)',
            dueDate: '15-Mar-2026',
            targetPct: 100,
            requiredCumulativeAmount: reqQ4,
            actualCumulativePaid: cumPaidQ4,
            shortfall: shortfallQ4,
            interestMonths: 1,
            interest234C: intQ4,
            status: shortfallQ4 === 0 ? 'Compliant' : 'Shortfall'
          }
        ];
      }
    }

    // 2. SECTION 234B - DEFAULT IN PAYMENT OF ADVANCE TAX
    // Triggered if total advance tax paid upto 31st March is < 90% of assessed tax
    let interest234B = 0;
    let is234BApplicable = false;
    let shortfall234B = 0;
    let months234B = 0;

    if (isAdvanceTaxApplicable) {
      const ninetyPctAssessed = 0.90 * assessedTax;
      if (totalAdvanceTaxPaidUpto31Mar < ninetyPctAssessed) {
        is234BApplicable = true;
        shortfall234B = Math.max(0, assessedTax - totalAdvanceTaxPaidUpto31Mar);
        
        // Months from 1st April of AY till filing date / determination
        // Calculate month difference between April 1 and actual filing date
        const fileDate = new Date(actualFilingDate);
        const ayStartYear = parseInt(assessmentYear.split('-')[0], 10);
        const ayStartDate = new Date(ayStartYear, 3, 1); // 1st April of AY

        if (fileDate >= ayStartDate) {
          const yearDiff = fileDate.getFullYear() - ayStartDate.getFullYear();
          const monthDiff = fileDate.getMonth() - ayStartDate.getMonth();
          months234B = Math.max(1, (yearDiff * 12) + monthDiff + (fileDate.getDate() > 1 ? 1 : 0));
        } else {
          months234B = 4; // default minimum months till July 31
        }

        // Round down shortfall to nearest hundred as per Rule 119A
        const roundedShortfall234B = Math.floor(shortfall234B / 100) * 100;
        interest234B = Math.round(roundedShortfall234B * 0.01 * months234B);
      }
    }

    // 3. SECTION 234A - DELAY IN FILING RETURN OF INCOME
    // Triggered if actual filing date is later than due date
    let interest234A = 0;
    let is234AApplicable = false;
    let shortfall234A = 0;
    let months234A = 0;

    const dueDateObj = new Date(filingDueDate);
    const filingDateObj = new Date(actualFilingDate);

    if (filingDateObj > dueDateObj) {
      // Amount on which 234A is charged: Tax on total income - (TDS + TCS + Advance Tax paid + Self-assessment tax paid before due date + 89/90 relief)
      shortfall234A = Math.max(0, assessedTax - totalAdvanceTaxPaidUpto31Mar);
      if (shortfall234A > 0) {
        is234AApplicable = true;
        const diffTime = filingDateObj.getTime() - dueDateObj.getTime();
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
        months234A = Math.ceil(diffDays / 30); // Any fraction of a month counts as a full month

        const roundedShortfall234A = Math.floor(shortfall234A / 100) * 100;
        interest234A = Math.round(roundedShortfall234A * 0.01 * months234A);
      }
    }

    const totalStatutoryInterest = interest234A + interest234B + interest234C;
    const finalAmountPayableWithInterest = assessedTax - totalAdvanceTaxPaidUpto31Mar + totalStatutoryInterest;

    return {
      assessedTax,
      isAdvanceTaxApplicable,
      isExemptSenior,
      schedule,
      cumPaidQ4,
      totalAdvanceTaxPaidUpto31Mar,
      interest234A: {
        amount: interest234A,
        isApplicable: is234AApplicable,
        shortfall: shortfall234A,
        months: months234A,
        filingDueDate,
        actualFilingDate
      },
      interest234B: {
        amount: interest234B,
        isApplicable: is234BApplicable,
        shortfall: shortfall234B,
        months: months234B
      },
      interest234C: {
        amount: interest234C,
        isApplicable: interest234C > 0
      },
      totalStatutoryInterest,
      finalAmountPayableWithInterest: Math.max(0, finalAmountPayableWithInterest),
      refundableAmount: finalAmountPayableWithInterest < 0 ? Math.abs(finalAmountPayableWithInterest) : 0
    };
  }
}
