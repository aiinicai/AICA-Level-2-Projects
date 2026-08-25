import { Invoice, RateMasterEntry, StatutoryRuleConfig, TrancheCalculation, InvoiceInterestResult, AgeingBucketSummary, MSMECategory } from '../types';
import { getDaysDifference, addDaysToDate } from './formatters';

/**
 * Calculates the statutory MSME Due Date
 * Acceptance Date -> Agreed Credit Period -> Statutory Limit -> Final Due Date
 */
export function calculateMSMEDueDate(
  mrnDate: string,
  acceptanceDate: string,
  hasWrittenAgreement: boolean,
  agreedCreditDays: number,
  isMSME: boolean,
  rules: StatutoryRuleConfig
): {
  effectiveAcceptanceDate: string;
  deemedAcceptanceDate: string;
  statutoryLimitDays: number;
  effectiveCreditDays: number;
  finalDueDate: string;
  statutoryExplanation: string;
} {
  // Deemed acceptance is MRN + 15 days if no explicit acceptance date
  const deemedAcceptanceDate = mrnDate ? addDaysToDate(mrnDate, rules.deemedAcceptanceWindowDays) : acceptanceDate;
  const effectiveAcceptanceDate = acceptanceDate || deemedAcceptanceDate || mrnDate;

  let statutoryLimitDays = rules.maxCreditDaysWithAgreement; // 45 days default
  let effectiveCreditDays = agreedCreditDays || 0;

  if (!isMSME) {
    // Non-MSME vendors follow commercial terms without MSMED statutory cap
    statutoryLimitDays = agreedCreditDays || 60;
    effectiveCreditDays = agreedCreditDays || 60;
  } else {
    if (!hasWrittenAgreement) {
      // Without written agreement, statutory limit is 15 days (Section 15 MSMED Act)
      statutoryLimitDays = rules.maxCreditDaysWithoutAgreement; // 15
      effectiveCreditDays = Math.min(effectiveCreditDays || rules.maxCreditDaysWithoutAgreement, rules.maxCreditDaysWithoutAgreement);
    } else {
      // With written agreement, statutory limit is capped at 45 days (Section 15 MSMED Act)
      statutoryLimitDays = rules.maxCreditDaysWithAgreement; // 45
      effectiveCreditDays = Math.min(effectiveCreditDays || rules.maxCreditDaysWithAgreement, rules.maxCreditDaysWithAgreement);
    }
  }

  const finalDueDate = addDaysToDate(effectiveAcceptanceDate, effectiveCreditDays);

  let statutoryExplanation = '';
  if (!isMSME) {
    statutoryExplanation = `Non-MSME: Commercial credit period of ${effectiveCreditDays} days applied from acceptance (${effectiveAcceptanceDate}).`;
  } else if (!hasWrittenAgreement) {
    statutoryExplanation = `Section 15 MSMED: No written agreement recorded. Statutory limit of 15 days applied from acceptance (${effectiveAcceptanceDate}).`;
  } else if (agreedCreditDays > rules.maxCreditDaysWithAgreement) {
    statutoryExplanation = `Section 15 MSMED: Agreed term was ${agreedCreditDays} days, but statutory limit caps maximum credit period to ${rules.maxCreditDaysWithAgreement} days from acceptance.`;
  } else {
    statutoryExplanation = `Section 15 MSMED: Agreed credit term of ${effectiveCreditDays} days (<= ${rules.maxCreditDaysWithAgreement} days) applied from acceptance (${effectiveAcceptanceDate}).`;
  }

  return {
    effectiveAcceptanceDate,
    deemedAcceptanceDate,
    statutoryLimitDays,
    effectiveCreditDays,
    finalDueDate,
    statutoryExplanation,
  };
}

/**
 * Finds the applicable interest rate from Rate Master for a given date
 */
export function getApplicableRateForDate(
  dateString: string,
  rateMaster: RateMasterEntry[]
): {
  referenceRate: number;
  multiplier: number;
  applicableMSMERate: number;
  rateEffectiveFrom: string;
  rateEffectiveTo: string;
  notificationNo: string;
} {
  const targetDate = dateString ? new Date(dateString) : new Date();

  // Find matching rate in master by date range
  const matched = rateMaster.find((entry) => {
    const from = new Date(entry.effectiveFrom);
    const to = entry.effectiveTo === '9999-12-31' || !entry.effectiveTo ? new Date('2099-12-31') : new Date(entry.effectiveTo);
    return targetDate >= from && targetDate <= to;
  });

  if (matched) {
    return {
      referenceRate: matched.referenceRate,
      multiplier: matched.multiplier,
      applicableMSMERate: matched.applicableMSMERate,
      rateEffectiveFrom: matched.effectiveFrom,
      rateEffectiveTo: matched.effectiveTo,
      notificationNo: matched.rbiNotificationNo,
    };
  }

  // Fallback to the latest available rate
  const sorted = [...rateMaster].sort((a, b) => new Date(b.effectiveFrom).getTime() - new Date(a.effectiveFrom).getTime());
  const fallback = sorted[0] || {
    referenceRate: 6.50,
    multiplier: 3,
    applicableMSMERate: 19.50,
    effectiveFrom: '2024-04-01',
    effectiveTo: '9999-12-31',
    rbiNotificationNo: 'RBI/2024-25/11',
  };

  return {
    referenceRate: fallback.referenceRate,
    multiplier: fallback.multiplier,
    applicableMSMERate: fallback.applicableMSMERate,
    rateEffectiveFrom: fallback.effectiveFrom,
    rateEffectiveTo: fallback.effectiveTo,
    notificationNo: fallback.rbiNotificationNo,
  };
}

/**
 * Calculates interest on a principal for a given delay period
 * Support both Monthly Compounding (Section 16 statutory) and Simple Interest
 */
export function calculateInterestForPeriod(
  principal: number,
  annualRatePct: number,
  delayDays: number,
  compoundingMethod: 'Monthly Rest' | 'Simple Interest' = 'Monthly Rest',
  yearDayBasis: 365 | 366 = 365
): number {
  if (principal <= 0 || delayDays <= 0 || annualRatePct <= 0) {
    return 0;
  }

  if (compoundingMethod === 'Simple Interest') {
    return (principal * annualRatePct * delayDays) / (100 * yearDayBasis);
  }

  // Monthly Rest Compounding under Section 16 MSMED Act 2006
  // Formula: Amount = Principal * (1 + r/12)^months * (1 + (r * remDays)/(yearDayBasis * 100)) - Principal
  const fullMonths = Math.floor(delayDays / 30);
  const remDays = delayDays % 30;
  const monthlyRateDecimal = (annualRatePct / 100) / 12;

  let compoundedPrincipal = principal;
  for (let i = 0; i < fullMonths; i++) {
    compoundedPrincipal = compoundedPrincipal * (1 + monthlyRateDecimal);
  }

  if (remDays > 0) {
    const brokenPeriodFactor = 1 + (annualRatePct * remDays) / (100 * yearDayBasis);
    compoundedPrincipal = compoundedPrincipal * brokenPeriodFactor;
  }

  return Math.max(0, compoundedPrincipal - principal);
}

/**
 * Computes end-to-end interest calculation for an invoice with part payments
 */
export function calculateInvoiceInterest(
  invoice: Invoice,
  rateMaster: RateMasterEntry[],
  rules: StatutoryRuleConfig,
  asOfDate: string = new Date().toISOString().split('T')[0]
): InvoiceInterestResult {
  const isMSME = invoice.isMSME && invoice.msmeCategory !== 'Not Applicable';
  
  // Non-MSME invoices do not attract Section 16 statutory interest
  if (!isMSME) {
    return {
      invoiceId: invoice.id,
      invoiceNumber: invoice.invoiceNumber,
      vendorId: invoice.vendorId,
      vendorName: invoice.vendorName,
      msmeCategory: invoice.msmeCategory,
      invoiceDate: invoice.invoiceDate,
      totalInvoiceAmount: invoice.totalInvoiceAmount,
      acceptanceDate: invoice.acceptanceDate,
      finalDueDate: invoice.finalDueDate,
      actualSettlementDate: invoice.payments.length > 0 ? invoice.payments[invoice.payments.length - 1].paymentDate : undefined,
      asOfDate,
      isOverdue: false,
      totalDelayDays: 0,
      totalPaid: invoice.amountPaid,
      outstandingPrincipal: invoice.outstandingAmount,
      applicableAnnualRate: 0,
      referenceRate: 0,
      totalInterestPayable: 0,
      totalAmountPayable: invoice.outstandingAmount,
      interestPaid: 0,
      interestOutstanding: 0,
      tranches: [],
      section43BHRisk: false,
      status: 'Compliant',
    };
  }

  const dueDate = invoice.finalDueDate;
  const sortedPayments = [...(invoice.payments || [])].sort(
    (a, b) => new Date(a.paymentDate).getTime() - new Date(b.paymentDate).getTime()
  );

  let currentPrincipal = invoice.totalInvoiceAmount;
  let totalInterest = 0;
  let tranches: TrancheCalculation[] = [];
  let previousDate = dueDate;
  let trancheIndex = 1;
  let totalDelayDays = 0;

  // Tranches for each part payment
  for (const payment of sortedPayments) {
    const paymentDate = payment.paymentDate;
    
    // Check if payment was made after due date
    if (new Date(paymentDate) > new Date(dueDate)) {
      const trancheStartDate = new Date(previousDate) > new Date(dueDate) ? previousDate : dueDate;
      const delayDays = Math.max(0, getDaysDifference(trancheStartDate, paymentDate));
      
      if (delayDays > 0 && currentPrincipal > 0) {
        const rateInfo = getApplicableRateForDate(trancheStartDate, rateMaster);
        const interest = calculateInterestForPeriod(
          currentPrincipal,
          rateInfo.applicableMSMERate,
          delayDays,
          rules.compoundingMethod,
          rules.yearDayBasis
        );

        totalInterest += interest;
        totalDelayDays += delayDays;

        tranches.push({
          trancheNumber: trancheIndex++,
          periodStart: trancheStartDate,
          periodEnd: paymentDate,
          principalBase: currentPrincipal,
          applicableRate: rateInfo.applicableMSMERate,
          referenceRate: rateInfo.referenceRate,
          delayDays,
          interestAmount: interest,
          paymentApplied: payment.amount,
          closingBalance: Math.max(0, currentPrincipal - payment.amount),
          calculationMethod: rules.compoundingMethod,
          rateEffectiveFrom: rateInfo.rateEffectiveFrom,
          rateEffectiveTo: rateInfo.rateEffectiveTo,
        });
      }
    }

    currentPrincipal = Math.max(0, currentPrincipal - payment.amount);
    previousDate = paymentDate;
  }

  // If there is still outstanding balance after all payments up to asOfDate
  if (currentPrincipal > 0) {
    const periodStart = new Date(previousDate) > new Date(dueDate) ? previousDate : dueDate;
    
    if (new Date(asOfDate) > new Date(periodStart)) {
      const delayDays = Math.max(0, getDaysDifference(periodStart, asOfDate));
      
      if (delayDays > 0) {
        const rateInfo = getApplicableRateForDate(periodStart, rateMaster);
        const interest = calculateInterestForPeriod(
          currentPrincipal,
          rateInfo.applicableMSMERate,
          delayDays,
          rules.compoundingMethod,
          rules.yearDayBasis
        );

        totalInterest += interest;
        totalDelayDays += delayDays;

        tranches.push({
          trancheNumber: trancheIndex++,
          periodStart,
          periodEnd: asOfDate,
          principalBase: currentPrincipal,
          applicableRate: rateInfo.applicableMSMERate,
          referenceRate: rateInfo.referenceRate,
          delayDays,
          interestAmount: interest,
          paymentApplied: 0,
          closingBalance: currentPrincipal,
          calculationMethod: rules.compoundingMethod,
          rateEffectiveFrom: rateInfo.rateEffectiveFrom,
          rateEffectiveTo: rateInfo.rateEffectiveTo,
        });
      }
    }
  }

  // Get current applicable rate
  const currentRateInfo = getApplicableRateForDate(asOfDate, rateMaster);

  const isOverdue = invoice.outstandingAmount > 0 && new Date(asOfDate) > new Date(dueDate);
  
  // Section 43B(h) tax disallowance risk: Micro & Small enterprises unpaid past due date
  const section43BHRisk = rules.isSection43BHApplicable && 
    (invoice.msmeCategory === 'Micro' || invoice.msmeCategory === 'Small') &&
    invoice.outstandingAmount > 0 &&
    isOverdue;

  let status: 'Compliant' | 'Approaching Due' | 'Overdue' = 'Compliant';
  if (isOverdue) {
    status = 'Overdue';
  } else if (invoice.outstandingAmount > 0) {
    const daysUntilDue = getDaysDifference(asOfDate, dueDate);
    if (daysUntilDue <= 7 && daysUntilDue >= 0) {
      status = 'Approaching Due';
    }
  }

  const latestPayment = sortedPayments[sortedPayments.length - 1];

  return {
    invoiceId: invoice.id,
    invoiceNumber: invoice.invoiceNumber,
    vendorId: invoice.vendorId,
    vendorName: invoice.vendorName,
    msmeCategory: invoice.msmeCategory,
    invoiceDate: invoice.invoiceDate,
    totalInvoiceAmount: invoice.totalInvoiceAmount,
    acceptanceDate: invoice.acceptanceDate,
    finalDueDate: invoice.finalDueDate,
    actualSettlementDate: invoice.outstandingAmount === 0 && latestPayment ? latestPayment.paymentDate : undefined,
    asOfDate,
    isOverdue,
    totalDelayDays,
    totalPaid: invoice.amountPaid,
    outstandingPrincipal: invoice.outstandingAmount,
    applicableAnnualRate: currentRateInfo.applicableMSMERate,
    referenceRate: currentRateInfo.referenceRate,
    totalInterestPayable: Math.round(totalInterest * 100) / 100,
    totalAmountPayable: Math.round((invoice.outstandingAmount + totalInterest) * 100) / 100,
    interestPaid: 0,
    interestOutstanding: Math.round(totalInterest * 100) / 100,
    tranches,
    section43BHRisk,
    status,
  };
}

/**
 * Calculates Ageing buckets for all invoices
 */
export function calculateAgeingBuckets(
  invoices: Invoice[],
  rateMaster: RateMasterEntry[],
  rules: StatutoryRuleConfig,
  asOfDate: string = new Date().toISOString().split('T')[0]
): {
  buckets: AgeingBucketSummary[];
  totalPrincipal: number;
  totalInterest: number;
  totalPayable: number;
} {
  const bucketDefs: {
    key: AgeingBucketSummary['bucketKey'];
    name: string;
    minDays: number;
    maxDays: number | null;
  }[] = [
    { key: 'not_due', name: 'Not Due', minDays: -99999, maxDays: 0 },
    { key: '0_30', name: '0–30 Days', minDays: 1, maxDays: 30 },
    { key: '31_45', name: '31–45 Days', minDays: 31, maxDays: 45 },
    { key: '46_90', name: '46–90 Days', minDays: 46, maxDays: 90 },
    { key: '91_180', name: '91–180 Days', minDays: 91, maxDays: 180 },
    { key: 'above_180', name: 'Above 180 Days', minDays: 181, maxDays: null },
  ];

  const bucketMap = new Map<string, {
    count: number;
    principal: number;
    interest: number;
    vendors: Set<string>;
  }>();

  bucketDefs.forEach((b) => {
    bucketMap.set(b.key, { count: 0, principal: 0, interest: 0, vendors: new Set() });
  });

  invoices.forEach((inv) => {
    // We only age outstanding amounts
    if (inv.outstandingAmount <= 0) return;

    const interestResult = calculateInvoiceInterest(inv, rateMaster, rules, asOfDate);
    const delayDays = getDaysDifference(inv.finalDueDate, asOfDate);

    let targetKey: AgeingBucketSummary['bucketKey'] = 'not_due';
    if (delayDays <= 0) {
      targetKey = 'not_due';
    } else if (delayDays <= 30) {
      targetKey = '0_30';
    } else if (delayDays <= 45) {
      targetKey = '31_45';
    } else if (delayDays <= 90) {
      targetKey = '46_90';
    } else if (delayDays <= 180) {
      targetKey = '91_180';
    } else {
      targetKey = 'above_180';
    }

    const bData = bucketMap.get(targetKey)!;
    bData.count += 1;
    bData.principal += inv.outstandingAmount;
    bData.interest += interestResult.totalInterestPayable;
    bData.vendors.add(inv.vendorId);
  });

  let grandPrincipal = 0;
  let grandInterest = 0;

  const buckets: AgeingBucketSummary[] = bucketDefs.map((b) => {
    const bData = bucketMap.get(b.key)!;
    grandPrincipal += bData.principal;
    grandInterest += bData.interest;

    return {
      bucketName: b.name,
      bucketKey: b.key,
      minDays: b.minDays,
      maxDays: b.maxDays,
      invoiceCount: bData.count,
      totalPrincipal: Math.round(bData.principal * 100) / 100,
      totalInterest: Math.round(bData.interest * 100) / 100,
      totalPayable: Math.round((bData.principal + bData.interest) * 100) / 100,
      vendorCount: bData.vendors.size,
    };
  });

  return {
    buckets,
    totalPrincipal: Math.round(grandPrincipal * 100) / 100,
    totalInterest: Math.round(grandInterest * 100) / 100,
    totalPayable: Math.round((grandPrincipal + grandInterest) * 100) / 100,
  };
}
