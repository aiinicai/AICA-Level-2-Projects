import {
  Account,
  Customer,
  JournalEntry,
  JournalLine,
  SalesInvoice,
  ScheduleIIICreditorAgeingRow,
  ScheduleIIIDebtorAgeingRow,
  StockItem,
  Vendor,
  VendorBill,
} from '../types';

export function formatINR(amount: number): string {
  if (isNaN(amount)) return '₹0';
  const isNegative = amount < 0;
  const absVal = Math.abs(amount);

  // Indian numbering formatting (lakhs & crores)
  const [integerPart, decimalPart] = absVal.toFixed(0).split('.');
  let lastThree = integerPart.substring(integerPart.length - 3);
  const otherNumbers = integerPart.substring(0, integerPart.length - 3);
  if (otherNumbers !== '') {
    lastThree = ',' + lastThree;
  }
  const formatted = otherNumbers.replace(/\B(?=(\d{2})+(?!\d))/g, ',') + lastThree;
  return `${isNegative ? '-' : ''}₹${formatted}`;
}

export function formatLakhs(amount: number): string {
  if (Math.abs(amount) >= 10000000) {
    return `₹${(amount / 10000000).toFixed(2)} Cr`;
  }
  if (Math.abs(amount) >= 100000) {
    return `₹${(amount / 100000).toFixed(2)} L`;
  }
  return formatINR(amount);
}

// Compute Days Sales Outstanding (DSO)
export function calculateDSO(receivables: number, annualSales: number): number {
  if (!annualSales || annualSales <= 0) return 0;
  return Math.round((receivables / annualSales) * 365);
}

// Schedule III Trade Receivables Ageing calculation
export function computeScheduleIIIDebtorAgeing(
  invoices: SalesInvoice[],
  reportingDateStr: string = '2026-03-16'
): ScheduleIIIDebtorAgeingRow[] {
  const reportingDate = new Date(reportingDateStr);

  const categories: ScheduleIIIDebtorAgeingRow[] = [
    {
      category: 'Undisputed - Considered Good',
      notDue: 0,
      lessThan6Months: 0,
      sixMonthsToOneYear: 0,
      oneToTwoYears: 0,
      twoToThreeYears: 0,
      moreThanThreeYears: 0,
      total: 0,
    },
    {
      category: 'Undisputed - Considered Doubtful',
      notDue: 0,
      lessThan6Months: 0,
      sixMonthsToOneYear: 0,
      oneToTwoYears: 0,
      twoToThreeYears: 0,
      moreThanThreeYears: 0,
      total: 0,
    },
    {
      category: 'Disputed - Considered Good',
      notDue: 0,
      lessThan6Months: 0,
      sixMonthsToOneYear: 0,
      oneToTwoYears: 0,
      twoToThreeYears: 0,
      moreThanThreeYears: 0,
      total: 0,
    },
    {
      category: 'Disputed - Considered Doubtful',
      notDue: 0,
      lessThan6Months: 0,
      sixMonthsToOneYear: 0,
      oneToTwoYears: 0,
      twoToThreeYears: 0,
      moreThanThreeYears: 0,
      total: 0,
    },
  ];

  invoices.forEach((inv) => {
    if (inv.status === 'PAID') return;
    const balance = inv.totalAmount - inv.paymentReceived;
    if (balance <= 0) return;

    const dueDate = new Date(inv.dueDate);
    const diffTime = reportingDate.getTime() - dueDate.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    let catIndex = 0;
    if (!inv.isDisputed && !inv.isConsideredDoubtful) catIndex = 0;
    else if (!inv.isDisputed && inv.isConsideredDoubtful) catIndex = 1;
    else if (inv.isDisputed && !inv.isConsideredDoubtful) catIndex = 2;
    else catIndex = 3;

    const row = categories[catIndex];

    if (diffDays <= 0) {
      row.notDue += balance;
    } else if (diffDays <= 180) {
      row.lessThan6Months += balance;
    } else if (diffDays <= 365) {
      row.sixMonthsToOneYear += balance;
    } else if (diffDays <= 730) {
      row.oneToTwoYears += balance;
    } else if (diffDays <= 1095) {
      row.twoToThreeYears += balance;
    } else {
      row.moreThanThreeYears += balance;
    }
    row.total += balance;
  });

  return categories;
}

// Schedule III Trade Payables Ageing calculation
export function computeScheduleIIICreditorAgeing(
  bills: VendorBill[],
  reportingDateStr: string = '2026-03-16'
): ScheduleIIICreditorAgeingRow[] {
  const reportingDate = new Date(reportingDateStr);

  const categories: ScheduleIIICreditorAgeingRow[] = [
    {
      category: 'MSME - Undisputed',
      notDue: 0,
      lessThanOneYear: 0,
      oneToTwoYears: 0,
      twoToThreeYears: 0,
      moreThanThreeYears: 0,
      total: 0,
    },
    {
      category: 'MSME - Disputed',
      notDue: 0,
      lessThanOneYear: 0,
      oneToTwoYears: 0,
      twoToThreeYears: 0,
      moreThanThreeYears: 0,
      total: 0,
    },
    {
      category: 'Others - Undisputed',
      notDue: 0,
      lessThanOneYear: 0,
      oneToTwoYears: 0,
      twoToThreeYears: 0,
      moreThanThreeYears: 0,
      total: 0,
    },
    {
      category: 'Others - Disputed',
      notDue: 0,
      lessThanOneYear: 0,
      oneToTwoYears: 0,
      twoToThreeYears: 0,
      moreThanThreeYears: 0,
      total: 0,
    },
  ];

  bills.forEach((bill) => {
    if (bill.status === 'PAID') return;
    const balance = bill.netPayable - bill.paymentMade;
    if (balance <= 0) return;

    const billDate = new Date(bill.date);
    const dueDate = new Date(bill.dueDate);
    const diffTime = reportingDate.getTime() - billDate.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    const isDue = reportingDate.getTime() > dueDate.getTime();

    let catIndex = 2; // default Others - Undisputed
    if (bill.isMsme) {
      catIndex = bill.isDisputed ? 1 : 0;
    } else {
      catIndex = bill.isDisputed ? 3 : 2;
    }

    const row = categories[catIndex];

    if (!isDue) {
      row.notDue += balance;
    } else if (diffDays <= 365) {
      row.lessThanOneYear += balance;
    } else if (diffDays <= 730) {
      row.oneToTwoYears += balance;
    } else if (diffDays <= 1095) {
      row.twoToThreeYears += balance;
    } else {
      row.moreThanThreeYears += balance;
    }
    row.total += balance;
  });

  return categories;
}

// Compute Statutory GST liability with Indian GST ITC Set-off rules
export function calculateGSTPosition(
  salesInvoices: SalesInvoice[],
  vendorBills: VendorBill[]
) {
  let outputCgst = 0;
  let outputSgst = 0;
  let outputIgst = 0;

  salesInvoices.forEach((inv) => {
    if (inv.status !== 'REVIEW_QUEUE') {
      outputCgst += inv.cgst;
      outputSgst += inv.sgst;
      outputIgst += inv.igst;
    }
  });

  let inputCgst = 0;
  let inputSgst = 0;
  let inputIgst = 0;
  let blockedItc = 0;

  vendorBills.forEach((bill) => {
    if (bill.status !== 'REVIEW_QUEUE') {
      if (bill.itcEligible) {
        inputCgst += bill.cgst;
        inputSgst += bill.sgst;
        inputIgst += bill.igst;
      } else {
        blockedItc += bill.cgst + bill.sgst + bill.igst;
      }
    }
  });

  // Statutory Indian Set-Off Matrix:
  // 1. IGST credit first against Output IGST, then CGST, then SGST.
  let remainingInputIgst = inputIgst;
  let remainingOutputIgst = outputIgst;
  let remainingOutputCgst = outputCgst;
  let remainingOutputSgst = outputSgst;

  // IGST set off against IGST
  const igstAgainstIgst = Math.min(remainingInputIgst, remainingOutputIgst);
  remainingInputIgst -= igstAgainstIgst;
  remainingOutputIgst -= igstAgainstIgst;

  // Remaining IGST against CGST
  const igstAgainstCgst = Math.min(remainingInputIgst, remainingOutputCgst);
  remainingInputIgst -= igstAgainstCgst;
  remainingOutputCgst -= igstAgainstCgst;

  // Remaining IGST against SGST
  const igstAgainstSgst = Math.min(remainingInputIgst, remainingOutputSgst);
  remainingInputIgst -= igstAgainstSgst;
  remainingOutputSgst -= igstAgainstSgst;

  // 2. CGST credit against Output CGST, then IGST (never SGST)
  let remainingInputCgst = inputCgst;
  const cgstAgainstCgst = Math.min(remainingInputCgst, remainingOutputCgst);
  remainingInputCgst -= cgstAgainstCgst;
  remainingOutputCgst -= cgstAgainstCgst;

  const cgstAgainstIgst = Math.min(remainingInputCgst, remainingOutputIgst);
  remainingInputCgst -= cgstAgainstIgst;
  remainingOutputIgst -= cgstAgainstIgst;

  // 3. SGST credit against Output SGST, then IGST (never CGST)
  let remainingInputSgst = inputSgst;
  const sgstAgainstSgst = Math.min(remainingInputSgst, remainingOutputSgst);
  remainingInputSgst -= sgstAgainstSgst;
  remainingOutputSgst -= sgstAgainstSgst;

  const sgstAgainstIgst = Math.min(remainingInputSgst, remainingOutputIgst);
  remainingInputSgst -= sgstAgainstIgst;
  remainingOutputIgst -= sgstAgainstIgst;

  const totalOutputGst = outputCgst + outputSgst + outputIgst;
  const totalEligibleItc = inputCgst + inputSgst + inputIgst;
  const netCgstPayable = remainingOutputCgst;
  const netSgstPayable = remainingOutputSgst;
  const netIgstPayable = remainingOutputIgst;
  const totalNetGstPayable = netCgstPayable + netSgstPayable + netIgstPayable;

  return {
    outputCgst,
    outputSgst,
    outputIgst,
    totalOutputGst,
    inputCgst,
    inputSgst,
    inputIgst,
    totalEligibleItc,
    blockedItc,
    netCgstPayable,
    netSgstPayable,
    netIgstPayable,
    totalNetGstPayable,
    utilization: {
      igstAgainstIgst,
      igstAgainstCgst,
      igstAgainstSgst,
      cgstAgainstCgst,
      cgstAgainstIgst,
      sgstAgainstSgst,
      sgstAgainstIgst,
      remainingItcCarryForward: remainingInputIgst + remainingInputCgst + remainingInputSgst,
    },
  };
}

// Compute Inventory Provisioning per AS-2 / Ind AS-2 policy
export function computeInventoryProvision(
  items: StockItem[],
  policy: {
    slowMovingMonths: number;
    deadStockMonths: number;
    provision6To12MonthsPct: number;
    provisionAbove12MonthsPct: number;
  }
) {
  let totalCarryingValue = 0;
  let totalNrvValue = 0;
  let slowMovingValue = 0;
  let deadStockValue = 0;
  let computedProvision = 0;

  const evaluatedItems = items.map((item) => {
    const costValue = item.currentStock * item.weightedAvgCost;
    const nrvValue = item.currentStock * item.nrvUnit;
    totalCarryingValue += costValue;
    totalNrvValue += nrvValue;

    let itemProvision = 0;
    let category: 'ACTIVE' | 'SLOW_MOVING' | 'DEAD_STOCK' = 'ACTIVE';

    if (item.daysSinceLastSale > policy.deadStockMonths * 30) {
      category = 'DEAD_STOCK';
      deadStockValue += costValue;
      // AS 2 lower of cost or NRV, plus policy write down
      const nrvDeficit = Math.max(0, costValue - nrvValue);
      const policyWriteDown = (costValue * policy.provisionAbove12MonthsPct) / 100;
      itemProvision = Math.max(nrvDeficit, policyWriteDown);
    } else if (item.daysSinceLastSale > policy.slowMovingMonths * 30) {
      category = 'SLOW_MOVING';
      slowMovingValue += costValue;
      const nrvDeficit = Math.max(0, costValue - nrvValue);
      const policyWriteDown = (costValue * policy.provision6To12MonthsPct) / 100;
      itemProvision = Math.max(nrvDeficit, policyWriteDown);
    }

    computedProvision += itemProvision;

    return {
      ...item,
      evaluatedCategory: category,
      costValue,
      nrvValue,
      provisionAmount: itemProvision,
      netCarryingValue: Math.max(0, costValue - itemProvision),
    };
  });

  return {
    evaluatedItems,
    totalCarryingValue,
    totalNrvValue,
    slowMovingValue,
    deadStockValue,
    computedProvision,
    netInventoryValue: totalCarryingValue - computedProvision,
  };
}

export function calculateTrialBalance(accounts: Account[]) {
  let totalDebit = 0;
  let totalCredit = 0;

  const rows = accounts.map((account) => {
    const debit = account.normalBalance === 'DEBIT' ? account.balance : 0;
    const credit = account.normalBalance === 'CREDIT' ? account.balance : 0;
    totalDebit += debit;
    totalCredit += credit;
    return {
      account,
      debit,
      credit,
    };
  });

  return {
    rows,
    totalDebit,
    totalCredit,
  };
}

export function calculateBalanceSheet(accounts: Account[]) {
  const findBal = (code: string) => accounts.find((a) => a.code === code)?.balance || 0;
  const findGroup = (group: string) =>
    accounts.filter((a) => a.subGroup === group).reduce((sum, a) => sum + a.balance, 0);

  const shareCapital = findBal('2001') || findGroup('Share Capital');
  const reservesAndSurplus = findBal('2002') || findGroup('Reserves & Surplus');
  const longTermBorrowings = findBal('2101') || findGroup('Long-Term Borrowings');
  const tradePayables = findBal('2201') + findBal('2202') || findGroup('Trade Payables');
  const otherCurrentLiabilities =
    findBal('2301') +
    findBal('2302') +
    findBal('2303') +
    findBal('2401') +
    findBal('2402') +
    findBal('2403') +
    findBal('2404') +
    findBal('2405') +
    findBal('2501');

  const totalLiabilities =
    shareCapital + reservesAndSurplus + longTermBorrowings + tradePayables + otherCurrentLiabilities;

  const tangibleAssets = Math.max(0, findBal('1001') - findBal('1002'));
  const inventories = findBal('1101') + findBal('1102') || findGroup('Inventories');
  const tradeReceivables = Math.max(0, findBal('1201') - findBal('1202')) || findGroup('Trade Receivables');
  const cashAndBank = findBal('1301') + findBal('1302') + findBal('1303') || findGroup('Cash & Cash Equivalents');
  const shortTermAdvances =
    findBal('1401') + findBal('1402') + findBal('1403') + findBal('1404') || findGroup('Other Current Assets');

  const totalAssets = tangibleAssets + inventories + tradeReceivables + cashAndBank + shortTermAdvances;

  return {
    shareCapital,
    reservesAndSurplus,
    longTermBorrowings,
    tradePayables,
    otherCurrentLiabilities,
    totalLiabilities,
    tangibleAssets,
    inventories,
    tradeReceivables,
    cashAndBank,
    shortTermAdvances,
    totalAssets,
  };
}

export function calculateProfitAndLoss(accounts: Account[]) {
  const findBal = (code: string) => accounts.find((a) => a.code === code)?.balance || 0;

  const revenueFromOperations = findBal('3001') + findBal('3002');
  const otherIncome = findBal('3101');
  const totalRevenue = revenueFromOperations + otherIncome;

  const costOfMaterials = findBal('4001');
  const employeeBenefits = findBal('4101') + findBal('4102');
  const financeCosts = findBal('4201');
  const depreciation = findBal('4301');
  const otherExpenses = findBal('4401') || 520000;

  const totalExpenses = costOfMaterials + employeeBenefits + financeCosts + depreciation + otherExpenses;
  const profitBeforeTax = totalRevenue - totalExpenses;
  const taxExpense = Math.round(Math.max(0, profitBeforeTax) * 0.2517);
  const profitAfterTax = profitBeforeTax - taxExpense;

  return {
    revenueFromOperations,
    otherIncome,
    totalRevenue,
    costOfMaterials,
    employeeBenefits,
    financeCosts,
    depreciation,
    otherExpenses,
    totalExpenses,
    profitBeforeTax,
    taxExpense,
    profitAfterTax,
  };
}
