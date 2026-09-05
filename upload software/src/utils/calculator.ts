import {
  BalanceSheetHeadConfig,
  BalanceSheetSummary,
  FixedAssetDetail,
  LedgerItem,
  ManualAdjustment,
  PLStatement,
  ReconciliationReport,
  ScheduleData,
} from '../types/accounting';

// Helper to extract Previous Year Credit - Debit (for liabilities / equity / income)
function getPyCrMinusDr(l: LedgerItem): number {
  if (l.previousYearCredit !== undefined || l.previousYearDebit !== undefined) {
    return (l.previousYearCredit || 0) - (l.previousYearDebit || 0);
  }
  if (l.previousYearAmount !== undefined) {
    return l.natureDrCr === 'Cr' ? Math.abs(l.previousYearAmount) : -Math.abs(l.previousYearAmount);
  }
  return 0;
}

// Helper to extract Previous Year Debit - Credit (for assets / expenses)
function getPyDrMinusCr(l: LedgerItem): number {
  if (l.previousYearDebit !== undefined || l.previousYearCredit !== undefined) {
    return (l.previousYearDebit || 0) - (l.previousYearCredit || 0);
  }
  if (l.previousYearAmount !== undefined) {
    return l.natureDrCr === 'Dr' ? Math.abs(l.previousYearAmount) : -Math.abs(l.previousYearAmount);
  }
  return 0;
}

export function calculatePLStatement(
  ledgers: LedgerItem[],
  adjustments: ManualAdjustment[] = []
): PLStatement {
  const plLedgers = ledgers.filter(l => l.targetType === 'PROFIT_AND_LOSS');

  // Direct Incomes (Sales / Service)
  // Algebraic net: credit - debit (so returns/discounts reduce revenue rather than add to it)
  const directIncomes = plLedgers
    .filter(l => l.plCategory === 'DIRECT_INCOME')
    .map(l => ({
      name: l.ledgerName,
      amount: (l.credit || 0) - (l.debit || 0),
      previousYearAmount: getPyCrMinusDr(l),
      ledgerId: l.id,
    }));
  const totalDirectIncome = directIncomes.reduce((acc, curr) => acc + curr.amount, 0);
  const previousYearTotalDirectIncome = directIncomes.reduce((acc, curr) => acc + (curr.previousYearAmount || 0), 0);

  // Closing Stock adjustment
  const closingStockAdj = adjustments.find(a => a.type === 'CLOSING_STOCK');
  const closingStock = closingStockAdj ? closingStockAdj.amount : 0;

  // Direct Expenses & Opening Stock
  const directExpLedgers = plLedgers.filter(l => l.plCategory === 'DIRECT_EXPENSE');
  const openingStockLedgers = directExpLedgers.filter(l => {
    const n = l.ledgerName.toLowerCase();
    const g = l.originalGroup.toLowerCase();
    return (
      n.includes('opening stock') ||
      n.includes('op stock') ||
      n.includes('op. stock') ||
      n.includes('stock opening') ||
      n.includes('stock (opening)') ||
      (g.includes('stock-in-hand') && !n.includes('closing'))
    );
  });
  const openingStock = openingStockLedgers.reduce(
    (acc, l) => acc + ((l.debit || 0) - (l.credit || 0)),
    0
  );

  const openingStockIds = new Set(openingStockLedgers.map(l => l.id));
  const directExpenses = directExpLedgers
    .filter(l => !openingStockIds.has(l.id))
    .map(l => ({
      name: l.ledgerName,
      amount: (l.debit || 0) - (l.credit || 0),
      previousYearAmount: getPyDrMinusCr(l),
      ledgerId: l.id,
    }));
  const totalDirectExpenses = directExpenses.reduce((acc, curr) => acc + curr.amount, 0) + openingStock;

  // In double entry: Current Year opening stock was Previous Year's closing stock!
  const previousYearClosingStock = openingStock > 0 ? openingStock : 0;
  const previousYearDirectExpTotal = directExpenses.reduce((acc, curr) => acc + (curr.previousYearAmount || 0), 0);
  const previousYearOpeningStock = openingStockLedgers.reduce((acc, l) => acc + getPyDrMinusCr(l), 0);
  const previousYearTotalDirectExpenses = previousYearDirectExpTotal + previousYearOpeningStock;

  // Gross Profit = (Direct Income + Closing Stock) - Total Direct Expenses (including Opening Stock)
  const grossProfit = (totalDirectIncome + closingStock) - totalDirectExpenses;
  const grossProfitPercentage = totalDirectIncome > 0 ? (grossProfit / totalDirectIncome) * 100 : 0;

  const previousYearGrossProfit = (previousYearTotalDirectIncome + previousYearClosingStock) - previousYearTotalDirectExpenses;
  const previousYearGrossProfitPercentage = previousYearTotalDirectIncome > 0 ? (previousYearGrossProfit / previousYearTotalDirectIncome) * 100 : 0;

  // Indirect Incomes
  const indirectIncomes = plLedgers
    .filter(l => l.plCategory === 'INDIRECT_INCOME')
    .map(l => ({
      name: l.ledgerName,
      amount: (l.credit || 0) - (l.debit || 0),
      previousYearAmount: getPyCrMinusDr(l),
      ledgerId: l.id,
    }));
  const totalIndirectIncome = indirectIncomes.reduce((acc, curr) => acc + curr.amount, 0);
  const previousYearTotalIndirectIncome = indirectIncomes.reduce((acc, curr) => acc + (curr.previousYearAmount || 0), 0);

  // Indirect Expenses
  const indirectExpenses = plLedgers
    .filter(l => l.plCategory === 'INDIRECT_EXPENSE')
    .map(l => ({
      name: l.ledgerName,
      amount: (l.debit || 0) - (l.credit || 0),
      previousYearAmount: getPyDrMinusCr(l),
      ledgerId: l.id,
    }));
  const totalIndirectExpenses = indirectExpenses.reduce((acc, curr) => acc + curr.amount, 0);
  const previousYearTotalIndirectExpenses = indirectExpenses.reduce((acc, curr) => acc + (curr.previousYearAmount || 0), 0);

  // Net Profit Before Tax
  const netProfitBeforeTax = grossProfit + totalIndirectIncome - totalIndirectExpenses;
  const taxProvision = 0; // Can be adjusted via tax provision entry
  const netProfitAfterTax = netProfitBeforeTax - taxProvision;

  const previousYearNetProfitBeforeTax = previousYearGrossProfit + previousYearTotalIndirectIncome - previousYearTotalIndirectExpenses;
  const previousYearTaxProvision = 0;
  const previousYearNetProfitAfterTax = previousYearNetProfitBeforeTax - previousYearTaxProvision;

  return {
    directIncomes,
    totalDirectIncome,
    previousYearTotalDirectIncome: Math.round(previousYearTotalDirectIncome * 100) / 100,
    openingStock,
    previousYearOpeningStock: Math.round(previousYearOpeningStock * 100) / 100,
    directExpenses,
    totalDirectExpenses,
    previousYearTotalDirectExpenses: Math.round(previousYearTotalDirectExpenses * 100) / 100,
    closingStock,
    previousYearClosingStock: Math.round(previousYearClosingStock * 100) / 100,
    grossProfit,
    previousYearGrossProfit: Math.round(previousYearGrossProfit * 100) / 100,
    grossProfitPercentage,
    previousYearGrossProfitPercentage: Math.round(previousYearGrossProfitPercentage * 100) / 100,
    indirectIncomes,
    totalIndirectIncome,
    previousYearTotalIndirectIncome: Math.round(previousYearTotalIndirectIncome * 100) / 100,
    indirectExpenses,
    totalIndirectExpenses,
    previousYearTotalIndirectExpenses: Math.round(previousYearTotalIndirectExpenses * 100) / 100,
    netProfitBeforeTax,
    previousYearNetProfitBeforeTax: Math.round(previousYearNetProfitBeforeTax * 100) / 100,
    taxProvision,
    previousYearTaxProvision,
    netProfitAfterTax,
    previousYearNetProfitAfterTax: Math.round(previousYearNetProfitAfterTax * 100) / 100,
  };
}

export function calculateSchedules(
  heads: BalanceSheetHeadConfig[],
  ledgers: LedgerItem[],
  plStatement: PLStatement,
  adjustments: ManualAdjustment[] = []
): ScheduleData[] {
  const activeHeads = heads
    .filter(h => h.active)
    .sort((a, b) => Number(a.scheduleNo) - Number(b.scheduleNo));

  return activeHeads.map(head => {
    // Match ledgers directly assigned to this head/schedule, plus any unmapped ledgers routed to catch-all schedules
    const matchingLedgers = ledgers.filter(l => {
      if (l.targetType === 'BALANCE_SHEET') {
        if (l.headCode === head.code || l.scheduleNo === head.scheduleNo) return true;
        // If assigned to an invalid or inactive head code, route debit to A07 and credit to L06
        const isKnownHead = activeHeads.some(h => h.code === l.headCode || h.scheduleNo === l.scheduleNo);
        if (!isKnownHead) {
          if (head.code === 'A07' && (l.debit || 0) >= (l.credit || 0)) return true;
          if (head.code === 'L06' && (l.credit || 0) > (l.debit || 0)) return true;
        }
      } else if (l.targetType === 'UNCLASSIFIED') {
        // Automatically route unclassified ledgers to Other Current Assets / Liabilities so TB balances in preview
        if (head.code === 'A07' && (l.debit || 0) >= (l.credit || 0)) return true;
        if (head.code === 'L06' && (l.credit || 0) > (l.debit || 0)) return true;
      }
      return false;
    });

    let totalAmount = 0;
    let fixedAssetDetails: FixedAssetDetail[] | undefined = undefined;

    if (head.isSpecialSchedule === 'CAPITAL' || head.code === 'L01') {
      // Calculate Capital Account with Net Profit & Drawings
      let capitalTotal = 0;
      matchingLedgers.forEach(l => {
        // In double-entry: Capital has a Credit balance. Debit balances (drawings/losses) reduce capital.
        capitalTotal += ((l.credit || 0) - (l.debit || 0));
      });
      // Add Net Profit from P&L statement
      totalAmount = capitalTotal + plStatement.netProfitAfterTax;
    } else if (head.isSpecialSchedule === 'FIXED_ASSETS' || head.code === 'A01') {
      // Fixed assets: calculate gross block and accumulated depreciation
      let grossBlock = 0;
      let accumDepr = 0;
      const rawAssetLedgers: LedgerItem[] = [];

      matchingLedgers.forEach(l => {
        const isDepr = l.ledgerName.toLowerCase().includes('depreciation') || (l.credit > l.debit);
        if (isDepr) {
          accumDepr += ((l.credit || 0) - (l.debit || 0));
        } else {
          grossBlock += ((l.debit || 0) - (l.credit || 0));
          rawAssetLedgers.push(l);
        }
      });

      // Total carrying amount in Balance Sheet:
      // If there is an accumulated depreciation ledger in TB (accumDepr > 0), the net carrying value is grossBlock - accumDepr.
      // If there is NO accumulated depreciation ledger in TB (accumDepr === 0), the asset debit balances in TB are ALREADY net of depreciation
      // (because depreciation was credited directly to the asset in the books, and debited to P&L).
      // Crucially, curYearDeprAmt must NOT be deducted again from grossBlock here, because that would double-deduct it
      // (once in P&L reducing Capital, and once here reducing Assets), causing the Balance Sheet to become imbalanced!
      totalAmount = grossBlock - accumDepr;

      // Check for current year depreciation in P&L for disclosure purposes in Schedule 8 table
      const curYearDeprLedger = ledgers.find(l => 
        l.targetType === 'PROFIT_AND_LOSS' && 
        l.ledgerName.toLowerCase().includes('depreciation')
      );
      const curYearDeprAmt = curYearDeprLedger ? Math.abs(curYearDeprLedger.debit - curYearDeprLedger.credit) : 0;
      
      const effectiveDeprForDisclosure = accumDepr > 0 ? accumDepr : curYearDeprAmt;

      const assetList: FixedAssetDetail[] = rawAssetLedgers.map((l) => {
        const amt = Math.abs(l.debit - l.credit);
        const ratio = grossBlock > 0 ? amt / grossBlock : (1 / (rawAssetLedgers.length || 1));
        const itemDepr = effectiveDeprForDisclosure * ratio;
        
        // If accumDepr === 0 and curYearDeprAmt > 0, the TB amount is already net.
        // For statutory disclosure, Opening Gross = amt + itemDepr, Depreciation = itemDepr, Net Block = amt.
        const opGross = accumDepr > 0 ? amt : amt + itemDepr;
        const clsGross = accumDepr > 0 ? amt : amt + itemDepr;
        const opDepr = accumDepr > 0 ? Math.max(0, itemDepr - (curYearDeprAmt * ratio)) : 0;
        const curDepr = curYearDeprAmt > 0 ? (curYearDeprAmt * ratio) : itemDepr;
        const clsDepr = itemDepr;
        const net = accumDepr > 0 ? Math.max(0, amt - clsDepr) : amt;
        const prevNet = accumDepr > 0 ? Math.max(0, amt - opDepr) : amt + itemDepr;

        return {
          id: l.id,
          assetName: l.ledgerName,
          openingGrossBlock: Math.round(opGross * 100) / 100,
          additionsMoreThan180Days: 0,
          additionsLessThan180Days: 0,
          deductionsGrossBlock: 0,
          closingGrossBlock: Math.round(clsGross * 100) / 100,
          openingDepreciation: Math.round(opDepr * 100) / 100,
          currentYearDepreciation: Math.round(curDepr * 100) / 100,
          depreciationOnDeletions: 0,
          closingDepreciation: Math.round(clsDepr * 100) / 100,
          netBlock: Math.round(net * 100) / 100,
          previousYearNetBlock: Math.round(prevNet * 100) / 100,
        };
      });

      fixedAssetDetails = assetList;
    } else if (head.isSpecialSchedule === 'INVENTORIES' || head.code === 'A03') {
      // Sum of inventory ledgers present in the trial balance (e.g. Raw Material Stock, WIP, Finished Goods)
      let tbStockAmount = 0;
      matchingLedgers.forEach(l => {
        tbStockAmount += ((l.debit || 0) - (l.credit || 0));
      });

      // Year-end closing stock adjustment outside the trial balance
      const closingStockAdj = adjustments.find(a => a.type === 'CLOSING_STOCK' || a.debitHead === head.code);
      const adjAmount = closingStockAdj ? closingStockAdj.amount : 0;

      // In double-entry:
      // If closingStockAdj is provided outside TB, it is credited to Trading Account (increasing Net Profit & Capital by adjAmount).
      // Thus, Schedule 10 must also include adjAmount so Assets and Liabilities match.
      // If TB already contains inventory ledgers, they are fully preserved in tbStockAmount.
      totalAmount = tbStockAmount + adjAmount;
    } else {
      // Standard schedules
      matchingLedgers.forEach(l => {
        if (head.nature === 'Liability') {
          totalAmount += ((l.credit || 0) - (l.debit || 0));
        } else {
          totalAmount += ((l.debit || 0) - (l.credit || 0));
        }
      });
    }

    // Calculate Previous Year total for this schedule
    let pyTotal = 0;
    if (head.isSpecialSchedule === 'CAPITAL' || head.code === 'L01') {
      let pyCapital = 0;
      matchingLedgers.forEach(l => {
        pyCapital += getPyCrMinusDr(l);
      });
      const pyProfit = plStatement.previousYearNetProfitAfterTax !== undefined ? plStatement.previousYearNetProfitAfterTax : 0;
      pyTotal = pyCapital + pyProfit;
    } else if (head.isSpecialSchedule === 'FIXED_ASSETS' || head.code === 'A01') {
      let pyGross = 0;
      let pyDepr = 0;
      matchingLedgers.forEach(l => {
        const isDepr = l.ledgerName.toLowerCase().includes('depreciation') || (l.credit > l.debit);
        if (isDepr) {
          pyDepr += getPyCrMinusDr(l);
        } else {
          pyGross += getPyDrMinusCr(l);
        }
      });
      pyTotal = pyGross - pyDepr;
      if (fixedAssetDetails && fixedAssetDetails.length > 0 && pyTotal === 0) {
        pyTotal = fixedAssetDetails.reduce((sum, a) => sum + (a.previousYearNetBlock || a.openingGrossBlock), 0);
      }
    } else if (head.isSpecialSchedule === 'INVENTORIES' || head.code === 'A03') {
      let pyStock = 0;
      matchingLedgers.forEach(l => {
        pyStock += getPyDrMinusCr(l);
      });
      pyTotal = pyStock > 0 ? pyStock : (plStatement.openingStock || 0);
    } else {
      matchingLedgers.forEach(l => {
        if (head.nature === 'Liability') {
          pyTotal += getPyCrMinusDr(l);
        } else {
          pyTotal += getPyDrMinusCr(l);
        }
      });
    }

    return {
      headConfig: head,
      ledgers: matchingLedgers,
      totalAmount: Math.round(totalAmount * 100) / 100,
      previousYearTotal: Math.round(pyTotal * 100) / 100,
      fixedAssetDetails,
    };
  });
}

export function calculateBalanceSheetSummary(
  heads: BalanceSheetHeadConfig[],
  schedules: ScheduleData[]
): BalanceSheetSummary {
  const liabilitiesHeads: BalanceSheetSummary['liabilitiesHeads'] = [];
  const assetsHeads: BalanceSheetSummary['assetsHeads'] = [];
  let totalPreviousYearLiabilities = 0;
  let totalPreviousYearAssets = 0;

  heads
    .filter(h => h.active)
    .sort((a, b) => Number(a.scheduleNo) - Number(b.scheduleNo))
    .forEach(head => {
      const schedule = schedules.find(s => s.headConfig.code === head.code);
      const amount = schedule ? schedule.totalAmount : 0;
      const previousYearAmount = schedule?.previousYearTotal !== undefined ? schedule.previousYearTotal : 0;

      if (head.nature === 'Liability') {
        liabilitiesHeads.push({
          headConfig: head,
          amount,
          previousYearAmount,
          scheduleNo: head.scheduleNo,
        });
        totalPreviousYearLiabilities += previousYearAmount;
      } else {
        assetsHeads.push({
          headConfig: head,
          amount,
          previousYearAmount,
          scheduleNo: head.scheduleNo,
        });
        totalPreviousYearAssets += previousYearAmount;
      }
    });

  const totalLiabilities = liabilitiesHeads.reduce((acc, curr) => acc + curr.amount, 0);
  const totalAssets = assetsHeads.reduce((acc, curr) => acc + curr.amount, 0);
  const difference = totalAssets - totalLiabilities;
  const isBalanced = Math.abs(difference) < 0.01;

  const previousYearDifference = totalPreviousYearAssets - totalPreviousYearLiabilities;
  const isPreviousYearBalanced = Math.abs(previousYearDifference) < 0.01;

  return {
    liabilitiesHeads,
    totalLiabilities,
    totalPreviousYearLiabilities: Math.round(totalPreviousYearLiabilities * 100) / 100,
    assetsHeads,
    totalAssets,
    totalPreviousYearAssets: Math.round(totalPreviousYearAssets * 100) / 100,
    difference: Math.round(difference * 100) / 100,
    previousYearDifference: Math.round(previousYearDifference * 100) / 100,
    isBalanced,
    isPreviousYearBalanced,
  };
}

export function calculateReconciliation(
  ledgers: LedgerItem[],
  balanceSheet: BalanceSheetSummary,
  plStatement: PLStatement
): ReconciliationReport {
  const totalTrialBalanceDebit = ledgers.reduce((acc, l) => acc + (l.debit || 0), 0);
  const totalTrialBalanceCredit = ledgers.reduce((acc, l) => acc + (l.credit || 0), 0);
  const trialBalanceDifference = totalTrialBalanceDebit - totalTrialBalanceCredit;
  const isTrialBalanceBalanced = Math.abs(trialBalanceDifference) < 0.01;

  const unclassifiedLedgers = ledgers.filter(l => l.targetType === 'UNCLASSIFIED' || l.status === 'REVIEW_NEEDED');
  const unclassifiedTotalAmount = unclassifiedLedgers.reduce((acc, l) => acc + Math.abs(l.debit - l.credit), 0);

  // Check negative balances
  const negativeBalances: ReconciliationReport['negativeBalances'] = [];
  ledgers.forEach(l => {
    if (l.targetType === 'BALANCE_SHEET') {
      const isBankOrCash = l.originalGroup.toLowerCase().includes('bank') || l.originalGroup.toLowerCase().includes('cash');
      const isDebtor = l.originalGroup.toLowerCase().includes('debtor');
      const isCreditor = l.originalGroup.toLowerCase().includes('creditor');

      if (isBankOrCash && l.credit > l.debit && !l.ledgerName.toLowerCase().includes('od') && !l.ledgerName.toLowerCase().includes('cc')) {
        negativeBalances.push({
          ledgerName: l.ledgerName,
          amount: l.credit - l.debit,
          expected: 'Debit (Asset)',
          actual: 'Credit Balance (Overdrawn)',
        });
      } else if (isDebtor && l.credit > l.debit) {
        negativeBalances.push({
          ledgerName: l.ledgerName,
          amount: l.credit - l.debit,
          expected: 'Debit (Receivable)',
          actual: 'Credit Balance (Advance Received)',
        });
      } else if (isCreditor && l.debit > l.credit) {
        negativeBalances.push({
          ledgerName: l.ledgerName,
          amount: l.debit - l.credit,
          expected: 'Credit (Payable)',
          actual: 'Debit Balance (Advance to Vendor)',
        });
      }
    }
  });

  let status: ReconciliationReport['status'] = 'BALANCED';
  if (!isTrialBalanceBalanced || !balanceSheet.isBalanced) {
    status = 'DIFFERENCE_EXISTS';
  } else if (unclassifiedLedgers.length > 0) {
    status = 'UNCLASSIFIED_ITEMS';
  }

  return {
    totalTrialBalanceDebit,
    totalTrialBalanceCredit,
    trialBalanceDifference,
    isTrialBalanceBalanced,
    totalAssets: balanceSheet.totalAssets,
    totalLiabilities: balanceSheet.totalLiabilities,
    balanceSheetDifference: balanceSheet.difference,
    isBalanceSheetBalanced: balanceSheet.isBalanced,
    unclassifiedLedgersCount: unclassifiedLedgers.length,
    unclassifiedTotalAmount,
    plNetProfit: plStatement.netProfitAfterTax,
    capitalProfitTransferred: plStatement.netProfitAfterTax,
    plTransferDifference: 0,
    negativeBalances,
    status,
  };
}
