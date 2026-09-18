import {
  BalanceSheetHeadConfig,
  ClassificationStatus,
  ClassificationTarget,
  ConfidenceLevel,
  LedgerItem,
  PLCategory,
  SavedClassificationRule,
} from '../types/accounting';
import {
  getSavedRulesMap,
  findMatchingRule,
} from './classificationRulesService';

export interface ClassificationRuleResult {
  targetType: ClassificationTarget;
  headCode?: string;
  mainHead?: string;
  subHead?: string;
  scheduleNo?: number | string;
  plCategory?: PLCategory;
  status: ClassificationStatus;
  confidence: ConfidenceLevel;
  confidenceReason: string;
  hasSavedRule?: boolean;
  savedRuleNature?: string;
}

export function classifySingleLedger(
  ledgerName: string,
  group: string,
  debit: number,
  credit: number,
  availableHeads: BalanceSheetHeadConfig[],
  existingMappings?: Record<string, string | SavedClassificationRule> // ledgerName -> headCode or plCategory or full rule
): ClassificationRuleResult {
  const normName = (ledgerName || '').toLowerCase().trim();
  const normGroup = (group || '').toLowerCase().trim();
  const isDebit = debit > credit || (debit > 0 && credit === 0);
  const netAmount = debit - credit;

  // 1. Check persistent saved classification rules (User-chosen heads & natures)
  const rulesMap = existingMappings
    ? (existingMappings as any)
    : getSavedRulesMap();

  const matchedSavedRule: SavedClassificationRule | undefined = findMatchingRule(ledgerName, rulesMap);

  if (matchedSavedRule) {
    if (matchedSavedRule.targetType === 'BALANCE_SHEET') {
      const matchedHead = availableHeads.find(
        h => h.code === matchedSavedRule.headCode || h.subHead.toLowerCase() === (matchedSavedRule.subHead || '').toLowerCase()
      );
      return {
        targetType: 'BALANCE_SHEET',
        headCode: matchedHead?.code || matchedSavedRule.headCode,
        mainHead: matchedHead?.mainHead || (matchedSavedRule.headNature === 'Liability' ? 'Capital & Liabilities' : 'Assets'),
        subHead: matchedHead?.subHead || matchedSavedRule.subHead,
        scheduleNo: matchedHead?.scheduleNo || matchedSavedRule.scheduleNo,
        status: 'CONFIRMED',
        confidence: 'HIGH',
        confidenceReason: matchedSavedRule.classificationNature
          ? `Saved Classification Rule: ${matchedSavedRule.classificationNature}`
          : `Saved rule: Schedule ${matchedSavedRule.scheduleNo} - ${matchedSavedRule.subHead}`,
        hasSavedRule: true,
        savedRuleNature: matchedSavedRule.classificationNature,
      };
    } else if (matchedSavedRule.targetType === 'PROFIT_AND_LOSS') {
      return {
        targetType: 'PROFIT_AND_LOSS',
        plCategory: matchedSavedRule.plCategory || 'INDIRECT_EXPENSE',
        status: 'CONFIRMED',
        confidence: 'HIGH',
        confidenceReason: matchedSavedRule.classificationNature
          ? `Saved Classification Rule: ${matchedSavedRule.classificationNature}`
          : `Saved rule: P&L ${(matchedSavedRule.plCategory || 'Expense').replace('_', ' ')}`,
        hasSavedRule: true,
        savedRuleNature: matchedSavedRule.classificationNature,
      };
    } else if (matchedSavedRule.targetType === 'UNCLASSIFIED') {
      return {
        targetType: 'UNCLASSIFIED',
        status: 'REVIEW_NEEDED',
        confidence: 'LOW',
        confidenceReason: 'Saved rule: Unclassified account',
        hasSavedRule: true,
        savedRuleNature: 'Unclassified',
      };
    }
  }

  // Fallback for simple string mappings
  if (existingMappings && (existingMappings[ledgerName] || existingMappings[normName])) {
    const rawSaved = existingMappings[ledgerName] || existingMappings[normName];
    if (typeof rawSaved === 'string') {
      if (rawSaved.startsWith('PL_')) {
        const plCat = rawSaved.replace('PL_', '') as PLCategory;
        return {
          targetType: 'PROFIT_AND_LOSS',
          plCategory: plCat,
          status: 'CONFIRMED',
          confidence: 'HIGH',
          confidenceReason: 'Applied previously saved user mapping',
          hasSavedRule: true,
        };
      } else {
        const matchedHead = availableHeads.find(h => h.code === rawSaved || h.id === rawSaved);
        if (matchedHead) {
          return {
            targetType: 'BALANCE_SHEET',
            headCode: matchedHead.code,
            mainHead: matchedHead.mainHead,
            subHead: matchedHead.subHead,
            scheduleNo: matchedHead.scheduleNo,
            status: 'CONFIRMED',
            confidence: 'HIGH',
            confidenceReason: `Applied previously saved user mapping (${matchedHead.subHead})`,
            hasSavedRule: true,
            savedRuleNature: `${matchedHead.nature} (Sch ${matchedHead.scheduleNo})`,
          };
        }
      }
    }
  }

  // Find head helpers
  const findHeadByCode = (code: string) => availableHeads.find(h => h.code === code && h.active);
  const findHeadByType = (type: string) => availableHeads.find(h => h.isSpecialSchedule === type && h.active);
  const findHeadByKeywords = (keywords: string[]) => 
    availableHeads.find(h => h.active && keywords.some(k => h.subHead.toLowerCase().includes(k) || (h.description || '').toLowerCase().includes(k)));

  // =========================================================================
  // 2. CAPITAL ACCOUNT & DRAWINGS (Schedule 1 - L01)
  // =========================================================================
  if (
    normGroup.includes('capital account') ||
    normGroup.includes('partner capital') ||
    normGroup.includes('proprietor capital') ||
    normGroup.includes('share capital') ||
    normGroup.includes('owners fund') ||
    normName.includes('capital a/c') ||
    normName.includes('capital account') ||
    normName.includes('partner capital') ||
    normName.includes('partners capital') ||
    normName.includes('proprietor capital') ||
    normName.includes('proprietor\'s capital') ||
    normName.includes('equity share capital') ||
    normName.includes('preference share') ||
    normName.includes('share application') ||
    normName.includes('partner current a/c') ||
    normName.includes('partners current account') ||
    normName.includes('proprietor current')
  ) {
    const head = findHeadByType('CAPITAL') || findHeadByCode('L01') || findHeadByKeywords(['capital']);
    if (head) {
      return {
        targetType: 'BALANCE_SHEET',
        headCode: head.code,
        mainHead: head.mainHead,
        subHead: head.subHead,
        scheduleNo: head.scheduleNo,
        status: 'CONFIRMED',
        confidence: 'HIGH',
        confidenceReason: 'Identified as Capital / Partner\'s Equity Account (Schedule 1)',
      };
    }
  }

  // Drawings / Personal Taxes of Proprietor/Partner (Deducted from Capital in Schedule 1)
  if (
    normGroup.includes('drawings') ||
    normName.includes('drawing') ||
    normName.includes('drawings') ||
    normName.includes('proprietor drawings') ||
    normName.includes('partner drawings') ||
    normName.includes('withdrawal for personal') ||
    normName.includes('personal expense') ||
    normName.includes('lic of partner') ||
    normName.includes('lic of proprietor') ||
    normName.includes('life insurance premium of proprietor') ||
    normName.includes('income tax of proprietor') ||
    normName.includes('income tax of partner')
  ) {
    const head = findHeadByType('CAPITAL') || findHeadByCode('L01');
    if (head) {
      return {
        targetType: 'BALANCE_SHEET',
        headCode: head.code,
        mainHead: head.mainHead,
        subHead: head.subHead,
        scheduleNo: head.scheduleNo,
        status: 'CONFIRMED',
        confidence: 'HIGH',
        confidenceReason: 'Proprietor/Partner Drawings deducted from Capital in Schedule 1',
      };
    }
  }

  // =========================================================================
  // 3. RESERVES & SURPLUS (Schedule 2 - L02)
  // =========================================================================
  if (
    normGroup.includes('reserves & surplus') ||
    normGroup.includes('reserves and surplus') ||
    normGroup.includes('reserve') ||
    normName.includes('general reserve') ||
    normName.includes('capital reserve') ||
    normName.includes('securities premium') ||
    normName.includes('revaluation reserve') ||
    normName.includes('contingency reserve') ||
    normName.includes('p&l balance b/f') ||
    normName.includes('profit & loss account (opening)') ||
    normName.includes('retained earnings')
  ) {
    const head = findHeadByCode('L02') || findHeadByKeywords(['reserves', 'surplus']);
    if (head) {
      return {
        targetType: 'BALANCE_SHEET',
        headCode: head.code,
        mainHead: head.mainHead,
        subHead: head.subHead,
        scheduleNo: head.scheduleNo,
        status: 'CONFIRMED',
        confidence: 'HIGH',
        confidenceReason: 'Reserves & Surplus / Retained Earnings (Schedule 2)',
      };
    }
  }

  // =========================================================================
  // 4. LONG-TERM BORROWINGS / SECURED LOANS (Schedule 3 - L03)
  // =========================================================================
  if (
    normGroup.includes('secured loans') ||
    normGroup.includes('secured loan') ||
    normGroup.includes('term loans') ||
    normGroup.includes('term loan') ||
    normName.includes('term loan') ||
    normName.includes('car loan') ||
    normName.includes('vehicle loan') ||
    normName.includes('housing loan') ||
    normName.includes('home loan') ||
    normName.includes('machinery loan') ||
    normName.includes('equipment loan') ||
    normName.includes('mortgage loan') ||
    normName.includes('loan against property') ||
    normName.includes('lap a/c') ||
    normName.includes('working capital term loan') ||
    normName.includes('gecl loan') ||
    normName.includes('eclgs loan') ||
    normName.includes('sidbi loan') ||
    normName.includes('hypothecation loan')
  ) {
    const head = findHeadByCode('L03') || findHeadByKeywords(['secured', 'borrowings']);
    if (head) {
      return {
        targetType: 'BALANCE_SHEET',
        headCode: head.code,
        mainHead: head.mainHead,
        subHead: head.subHead,
        scheduleNo: head.scheduleNo,
        status: 'CONFIRMED',
        confidence: 'HIGH',
        confidenceReason: 'Secured Long-Term Borrowing from Banks / Financial Institutions (Schedule 3)',
      };
    }
  }

  // =========================================================================
  // 5. UNSECURED LOANS / OTHER LONG-TERM LIABILITIES (Schedule 4 - L04)
  // =========================================================================
  if (
    normGroup.includes('unsecured loans') ||
    normGroup.includes('unsecured loan') ||
    normGroup.includes('loans (liability)') ||
    normName.includes('unsecured loan') ||
    normName.includes('loan from director') ||
    normName.includes('loan from partner') ||
    normName.includes('loan from relative') ||
    normName.includes('loan from friend') ||
    normName.includes('loan from promoters') ||
    normName.includes('inter corporate deposit') ||
    normName.includes('icd a/c') ||
    normName.includes('bajaj finance loan') ||
    normName.includes('tata capital unsecured') ||
    normName.includes('nbfc loan') ||
    normName.includes('hand loan') ||
    normName.includes('private loan')
  ) {
    const head = findHeadByCode('L04') || findHeadByKeywords(['unsecured', 'long-term liabilities']);
    if (head) {
      return {
        targetType: 'BALANCE_SHEET',
        headCode: head.code,
        mainHead: head.mainHead,
        subHead: head.subHead,
        scheduleNo: head.scheduleNo,
        status: 'CONFIRMED',
        confidence: 'HIGH',
        confidenceReason: 'Unsecured Borrowing from Directors, Partners, Relatives or NBFCs (Schedule 4)',
      };
    }
  }

  // =========================================================================
  // 6. SUNDRY CREDITORS / TRADE PAYABLES (Schedule 5 - L05)
  // =========================================================================
  if (
    normGroup.includes('sundry creditors') ||
    normGroup.includes('sundry creditor') ||
    normGroup.includes('trade payables') ||
    normGroup.includes('trade payable') ||
    normGroup.includes('creditors for goods') ||
    normGroup.includes('creditors for raw material') ||
    normGroup.includes('creditors for expenses') ||
    normName.includes('creditors') ||
    normName.includes('creditor for') ||
    normName.includes('supplier') ||
    normName.includes('vendor') ||
    normName.includes('bills payable') ||
    normName.includes('b/p a/c') ||
    normName.includes('trade payable')
  ) {
    const head = findHeadByType('TRADE_PAYABLES') || findHeadByCode('L05') || findHeadByKeywords(['trade payables', 'creditors']);
    if (head) {
      const isAbnormal = isDebit && netAmount > 0;
      return {
        targetType: 'BALANCE_SHEET',
        headCode: head.code,
        mainHead: head.mainHead,
        subHead: head.subHead,
        scheduleNo: head.scheduleNo,
        status: isAbnormal ? 'REVIEW_NEEDED' : 'CONFIRMED',
        confidence: isAbnormal ? 'MEDIUM' : 'HIGH',
        confidenceReason: isAbnormal
          ? 'Creditor has abnormal Debit balance (May be Advance to Supplier - verify in Schedule 5 or reclassify to Schedule 13)'
          : 'Trade Payables / Sundry Creditors (Schedule 5)',
      };
    }
  }

  // =========================================================================
  // 7. OTHER CURRENT LIABILITIES & STATUTORY DUES (Schedule 6 - L06)
  // =========================================================================
  if (
    normGroup.includes('duties & taxes') ||
    normGroup.includes('duties and taxes') ||
    normGroup.includes('current liabilities') ||
    normGroup.includes('statutory dues') ||
    normName.includes('gst payable') ||
    normName.includes('output gst') ||
    normName.includes('output cgst') ||
    normName.includes('output sgst') ||
    normName.includes('output igst') ||
    normName.includes('tds payable') ||
    normName.includes('tcs payable') ||
    normName.includes('pf payable') ||
    normName.includes('epf payable') ||
    normName.includes('esi payable') ||
    normName.includes('professional tax payable') ||
    normName.includes('pt payable') ||
    normName.includes('salary payable') ||
    normName.includes('salaries payable') ||
    normName.includes('wages payable') ||
    normName.includes('rent payable') ||
    normName.includes('electricity charges payable') ||
    normName.includes('audit fees payable') ||
    normName.includes('accounting charges payable') ||
    normName.includes('outstanding expenses') ||
    normName.includes('expenses payable') ||
    normName.includes('advance from customer') ||
    normName.includes('advance from client') ||
    normName.includes('customer advance') ||
    normName.includes('interest accrued but not due') ||
    normName.includes('unearned revenue')
  ) {
    const head = findHeadByCode('L06') || findHeadByKeywords(['other current liabilities', 'duties']);
    if (head) {
      return {
        targetType: 'BALANCE_SHEET',
        headCode: head.code,
        mainHead: head.mainHead,
        subHead: head.subHead,
        scheduleNo: head.scheduleNo,
        status: 'CONFIRMED',
        confidence: 'HIGH',
        confidenceReason: 'Statutory Dues, Taxes Payable, Accrued Expenses or Customer Advances (Schedule 6)',
      };
    }
  }

  // =========================================================================
  // 8. SHORT-TERM BORROWINGS & PROVISIONS (Schedule 7 - L07)
  // =========================================================================
  if (
    normGroup.includes('provisions') ||
    normGroup.includes('short term provisions') ||
    normGroup.includes('bank od') ||
    normGroup.includes('bank o/d') ||
    normGroup.includes('bank occ') ||
    normName.includes('provision for tax') ||
    normName.includes('provision for income tax') ||
    normName.includes('provision for audit') ||
    normName.includes('provision for bonus') ||
    normName.includes('provision for gratuity') ||
    normName.includes('provision for expenses') ||
    normName.includes('provision for bad') ||
    normName.includes('bank od a/c') ||
    normName.includes('bank o/d a/c') ||
    normName.includes('cc a/c') ||
    normName.includes('cash credit a/c') ||
    normName.includes('overdraft account') ||
    normName.includes('short term loan')
  ) {
    const head = findHeadByCode('L07') || findHeadByKeywords(['short-term borrowings', 'provisions']);
    if (head) {
      return {
        targetType: 'BALANCE_SHEET',
        headCode: head.code,
        mainHead: head.mainHead,
        subHead: head.subHead,
        scheduleNo: head.scheduleNo,
        status: 'CONFIRMED',
        confidence: 'HIGH',
        confidenceReason: 'Bank OD / Cash Credit / Short-Term Provision (Schedule 7)',
      };
    }
  }

  // =========================================================================
  // 9. PROPERTY, PLANT & EQUIPMENT / FIXED ASSETS (Schedule 8 - A01)
  // =========================================================================
  if (
    normGroup.includes('fixed assets') ||
    normGroup.includes('fixed asset') ||
    normGroup.includes('tangible assets') ||
    normGroup.includes('property, plant') ||
    normGroup.includes('ppe') ||
    normName.includes('plant & machinery') ||
    normName.includes('plant and machinery') ||
    normName.includes('machinery') ||
    normName.includes('land & building') ||
    normName.includes('freehold land') ||
    normName.includes('factory building') ||
    normName.includes('office building') ||
    normName.includes('building') ||
    normName.includes('furniture & fixtures') ||
    normName.includes('furniture and fixtures') ||
    normName.includes('furniture') ||
    normName.includes('computer') ||
    normName.includes('laptop') ||
    normName.includes('printer') ||
    normName.includes('motor car') ||
    normName.includes('motor vehicle') ||
    normName.includes('truck') ||
    normName.includes('scooter') ||
    normName.includes('delivery van') ||
    normName.includes('office equipment') ||
    normName.includes('air conditioner') ||
    normName.includes('ac a/c') ||
    normName.includes('electrical installation') ||
    normName.includes('electrical fitting') ||
    normName.includes('tools & dies') ||
    normName.includes('software / licence') ||
    normName.includes('accumulated depreciation') ||
    normName.includes('depreciation fund') ||
    normName.includes('depreciation provision')
  ) {
    const head = findHeadByType('FIXED_ASSETS') || findHeadByCode('A01') || findHeadByKeywords(['fixed assets', 'property']);
    if (head) {
      return {
        targetType: 'BALANCE_SHEET',
        headCode: head.code,
        mainHead: head.mainHead,
        subHead: head.subHead,
        scheduleNo: head.scheduleNo,
        status: 'CONFIRMED',
        confidence: 'HIGH',
        confidenceReason: 'Property, Plant & Equipment / Tangible Fixed Asset (Schedule 8)',
      };
    }
  }

  // =========================================================================
  // 10. NON-CURRENT INVESTMENTS & LONG-TERM ASSETS (Schedule 9 - A02)
  // =========================================================================
  if (
    normGroup.includes('investments') ||
    normGroup.includes('investment') ||
    normGroup.includes('non current investment') ||
    normName.includes('fixed deposit') ||
    normName.includes('bank fd') ||
    normName.includes('term deposit') ||
    normName.includes('shares of') ||
    normName.includes('equity shares') ||
    normName.includes('mutual fund') ||
    normName.includes('rbi bonds') ||
    normName.includes('sovereign gold bond') ||
    normName.includes('government securities') ||
    normName.includes('nsc a/c') ||
    normName.includes('national saving certificate') ||
    normName.includes('kisan vikas patra') ||
    normName.includes('kvp') ||
    normName.includes('ppf account') ||
    normName.includes('security deposit with') ||
    normName.includes('electricity deposit') ||
    normName.includes('telephone deposit') ||
    normName.includes('rent deposit (long term)')
  ) {
    const head = findHeadByType('INVESTMENTS') || findHeadByCode('A02') || findHeadByKeywords(['investments', 'non-current']);
    if (head) {
      return {
        targetType: 'BALANCE_SHEET',
        headCode: head.code,
        mainHead: head.mainHead,
        subHead: head.subHead,
        scheduleNo: head.scheduleNo,
        status: 'CONFIRMED',
        confidence: 'HIGH',
        confidenceReason: 'Non-Current Investment / Bank FD / Security Deposit (Schedule 9)',
      };
    }
  }

  // =========================================================================
  // 11. INVENTORIES (Stock-in-Trade) (Schedule 10 - A03)
  // =========================================================================
  // Crucial: Opening Stock belongs to Trading Account (Direct Expense), NOT Balance Sheet!
  const isOpeningStock =
    normName.includes('opening stock') ||
    normName.includes('op stock') ||
    normName.includes('op. stock') ||
    normName.includes('stock opening') ||
    normName.includes('stock (opening)') ||
    (normGroup.includes('stock-in-hand') && (normName.includes('opening') || normName.includes('op.')));

  if (isOpeningStock) {
    return {
      targetType: 'PROFIT_AND_LOSS',
      plCategory: 'DIRECT_EXPENSE',
      status: 'CONFIRMED',
      confidence: 'HIGH',
      confidenceReason: 'Opening Stock for Trading Account (Direct Expense)',
    };
  }

  if (
    normGroup.includes('stock-in-hand') ||
    normGroup.includes('stock in hand') ||
    normGroup.includes('inventories') ||
    normGroup.includes('inventory') ||
    normName.includes('closing stock') ||
    normName.includes('stock in trade') ||
    normName.includes('raw material stock') ||
    normName.includes('work in progress') ||
    normName.includes('wip stock') ||
    normName.includes('finished goods stock') ||
    normName.includes('packing material stock') ||
    normName.includes('stores & spares stock')
  ) {
    const head = findHeadByType('INVENTORIES') || findHeadByCode('A03') || findHeadByKeywords(['inventories', 'stock']);
    if (head) {
      return {
        targetType: 'BALANCE_SHEET',
        headCode: head.code,
        mainHead: head.mainHead,
        subHead: head.subHead,
        scheduleNo: head.scheduleNo,
        status: 'CONFIRMED',
        confidence: 'HIGH',
        confidenceReason: 'Inventories / Stock-in-Trade (Schedule 10)',
      };
    }
  }

  // =========================================================================
  // 12. SUNDRY DEBTORS / TRADE RECEIVABLES (Schedule 11 - A04)
  // =========================================================================
  if (
    normGroup.includes('sundry debtors') ||
    normGroup.includes('sundry debtor') ||
    normGroup.includes('trade receivables') ||
    normGroup.includes('trade receivable') ||
    normGroup.includes('debtors') ||
    normName.includes('customer') ||
    normName.includes('client') ||
    normName.includes('trade receivable') ||
    normName.includes('bills receivable') ||
    normName.includes('b/r a/c') ||
    normName.includes('debtors for goods') ||
    normName.includes('book debts')
  ) {
    const head = findHeadByType('TRADE_RECEIVABLES') || findHeadByCode('A04') || findHeadByKeywords(['trade receivables', 'debtors']);
    if (head) {
      const isAbnormal = !isDebit && netAmount < 0;
      return {
        targetType: 'BALANCE_SHEET',
        headCode: head.code,
        mainHead: head.mainHead,
        subHead: head.subHead,
        scheduleNo: head.scheduleNo,
        status: isAbnormal ? 'REVIEW_NEEDED' : 'CONFIRMED',
        confidence: isAbnormal ? 'MEDIUM' : 'HIGH',
        confidenceReason: isAbnormal
          ? 'Debtor has abnormal Credit balance (Customer advance / credit note - verify in Schedule 11)'
          : 'Trade Receivables / Sundry Debtors (Schedule 11)',
      };
    }
  }

  // =========================================================================
  // 13. CASH & BANK BALANCES (Schedule 12 - A05)
  // =========================================================================
  if (
    normGroup.includes('bank accounts') ||
    normGroup.includes('bank account') ||
    normGroup.includes('cash-in-hand') ||
    normGroup.includes('cash in hand') ||
    normGroup.includes('cash accounts') ||
    normName.includes('cash in hand') ||
    normName.includes('petty cash') ||
    normName.includes('imprest cash') ||
    normName.includes('bank a/c') ||
    normName.includes('current a/c') ||
    normName.includes('savings a/c') ||
    normName.includes('auto sweep') ||
    normName.includes('flexi deposit') ||
    normName.includes('hdfc bank') ||
    normName.includes('sbi bank') ||
    normName.includes('icici bank') ||
    normName.includes('axis bank') ||
    normName.includes('pnb bank') ||
    normName.includes('bob bank') ||
    normName.includes('kotak bank') ||
    normName.includes('canara bank') ||
    normName.includes('indusind bank') ||
    normName.includes('yes bank') ||
    normName.includes('union bank') ||
    normName.includes('bank of baroda') ||
    normName.includes('state bank of india')
  ) {
    // If Overdraft / CC Account, route to Schedule 7 (Short-Term Borrowings)
    if (!isDebit && (normGroup.includes('bank o/d') || normGroup.includes('bank od') || normName.includes('cc a/c') || normName.includes('od a/c') || normName.includes('cash credit'))) {
      const odHead = findHeadByCode('L07') || findHeadByCode('L03');
      if (odHead) {
        return {
          targetType: 'BALANCE_SHEET',
          headCode: odHead.code,
          mainHead: odHead.mainHead,
          subHead: odHead.subHead,
          scheduleNo: odHead.scheduleNo,
          status: 'CONFIRMED',
          confidence: 'HIGH',
          confidenceReason: 'Bank Overdraft / Cash Credit account (Schedule 7)',
        };
      }
    }

    const head = findHeadByType('CASH_BANK') || findHeadByCode('A05') || findHeadByKeywords(['cash', 'bank']);
    if (head) {
      const isCreditBalance = !isDebit && netAmount < 0;
      return {
        targetType: 'BALANCE_SHEET',
        headCode: head.code,
        mainHead: head.mainHead,
        subHead: head.subHead,
        scheduleNo: head.scheduleNo,
        status: isCreditBalance ? 'REVIEW_NEEDED' : 'CONFIRMED',
        confidence: isCreditBalance ? 'MEDIUM' : 'HIGH',
        confidenceReason: isCreditBalance
          ? 'Bank ledger has credit balance (Check for unpresented cheques or Bank OD facility)'
          : 'Cash in Hand & Bank Balances (Schedule 12)',
      };
    }
  }

  // =========================================================================
  // 14. SHORT-TERM LOANS, ADVANCES & TAX CREDITS (Schedule 13 - A06)
  // =========================================================================
  if (
    normGroup.includes('loans & advances (asset)') ||
    normGroup.includes('loans and advances (asset)') ||
    normGroup.includes('deposits (asset)') ||
    normName.includes('advance to supplier') ||
    normName.includes('advance to vendor') ||
    normName.includes('supplier advance') ||
    normName.includes('staff advance') ||
    normName.includes('employee advance') ||
    normName.includes('staff loan') ||
    normName.includes('advance tax') ||
    normName.includes('self assessment tax') ||
    normName.includes('tds receivable') ||
    normName.includes('tds deducted by customer') ||
    normName.includes('tcs receivable') ||
    normName.includes('input tax credit') ||
    normName.includes('gst itc') ||
    normName.includes('input cgst') ||
    normName.includes('input sgst') ||
    normName.includes('input igst') ||
    normName.includes('electronic credit ledger') ||
    normName.includes('electronic cash ledger') ||
    normName.includes('gst cash ledger') ||
    normName.includes('rcm input tax') ||
    normName.includes('mat credit')
  ) {
    const head = findHeadByCode('A06') || findHeadByKeywords(['short-term loans', 'advances']);
    if (head) {
      return {
        targetType: 'BALANCE_SHEET',
        headCode: head.code,
        mainHead: head.mainHead,
        subHead: head.subHead,
        scheduleNo: head.scheduleNo,
        status: 'CONFIRMED',
        confidence: 'HIGH',
        confidenceReason: 'Short-Term Loans, Supplier Advances, GST ITC or Advance Tax / TDS (Schedule 13)',
      };
    }
  }

  // =========================================================================
  // 15. OTHER CURRENT ASSETS (Schedule 14 - A07)
  // =========================================================================
  if (
    normGroup.includes('other current assets') ||
    normName.includes('prepaid') ||
    normName.includes('prepaid insurance') ||
    normName.includes('prepaid rent') ||
    normName.includes('prepaid amc') ||
    normName.includes('prepaid expenses') ||
    normName.includes('accrued interest') ||
    normName.includes('interest accrued on fd') ||
    normName.includes('interest receivable') ||
    normName.includes('insurance claim receivable')
  ) {
    const head = findHeadByCode('A07') || findHeadByKeywords(['other current assets']);
    if (head) {
      return {
        targetType: 'BALANCE_SHEET',
        headCode: head.code,
        mainHead: head.mainHead,
        subHead: head.subHead,
        scheduleNo: head.scheduleNo,
        status: 'CONFIRMED',
        confidence: 'HIGH',
        confidenceReason: 'Prepaid Expenses / Accrued Interest Receivable (Schedule 14)',
      };
    }
  }

  // =========================================================================
  // 16. PROFIT & LOSS: DIRECT INCOMES / REVENUE (Trading Cr)
  // =========================================================================
  if (
    normGroup.includes('sales accounts') ||
    normGroup.includes('direct incomes') ||
    normGroup.includes('direct income') ||
    normGroup.includes('revenue from operations') ||
    normName.includes('sales') ||
    normName.includes('revenue from operations') ||
    normName.includes('gross turnover') ||
    normName.includes('job work charges received') ||
    normName.includes('job work receipt') ||
    normName.includes('service revenue') ||
    normName.includes('scrap sales') ||
    normName.includes('freight recovered') ||
    normName.includes('export sales') ||
    normName.includes('domestic sales')
  ) {
    return {
      targetType: 'PROFIT_AND_LOSS',
      plCategory: 'DIRECT_INCOME',
      status: 'CONFIRMED',
      confidence: 'HIGH',
      confidenceReason: 'Direct Operational Revenue / Sales (Trading Account Cr)',
    };
  }

  // =========================================================================
  // 17. PROFIT & LOSS: DIRECT EXPENSES / PURCHASES (Trading Dr)
  // =========================================================================
  if (
    normGroup.includes('purchase accounts') ||
    normGroup.includes('direct expenses') ||
    normGroup.includes('direct expense') ||
    normGroup.includes('manufacturing expenses') ||
    normName.includes('purchase') ||
    normName.includes('purchases') ||
    normName.includes('opening stock') ||
    normName.includes('wages') ||
    normName.includes('direct labour') ||
    normName.includes('freight inward') ||
    normName.includes('carriage inward') ||
    normName.includes('cartage') ||
    normName.includes('octroi') ||
    normName.includes('custom duty') ||
    normName.includes('clearing & forwarding') ||
    normName.includes('power & fuel') ||
    normName.includes('factory power') ||
    normName.includes('fuel & oil') ||
    normName.includes('consumable stores') ||
    normName.includes('factory rent') ||
    normName.includes('job work charges paid') ||
    normName.includes('sub-contracting charges') ||
    normName.includes('packaging material consumed')
  ) {
    return {
      targetType: 'PROFIT_AND_LOSS',
      plCategory: 'DIRECT_EXPENSE',
      status: 'CONFIRMED',
      confidence: 'HIGH',
      confidenceReason: 'Direct Cost of Goods Sold / Manufacturing Expense (Trading Account Dr)',
    };
  }

  // =========================================================================
  // 18. PROFIT & LOSS: INDIRECT INCOMES (P&L Cr)
  // =========================================================================
  if (
    normGroup.includes('indirect incomes') ||
    normGroup.includes('indirect income') ||
    normName.includes('interest received') ||
    normName.includes('interest on fd') ||
    normName.includes('interest on savings') ||
    normName.includes('interest on income tax refund') ||
    normName.includes('discount received') ||
    normName.includes('commission received') ||
    normName.includes('dividend received') ||
    normName.includes('profit on sale of asset') ||
    normName.includes('profit on sale of investment') ||
    normName.includes('bad debts recovered') ||
    normName.includes('rental income') ||
    normName.includes('rent received') ||
    normName.includes('foreign exchange gain') ||
    normName.includes('forex gain') ||
    normName.includes('sundry balances written back') ||
    normName.includes('cash discount received') ||
    normName.includes('subsidy received') ||
    normName.includes('miscellaneous income')
  ) {
    return {
      targetType: 'PROFIT_AND_LOSS',
      plCategory: 'INDIRECT_INCOME',
      status: 'CONFIRMED',
      confidence: 'HIGH',
      confidenceReason: 'Non-Operating Indirect Income (Profit & Loss Cr)',
    };
  }

  // =========================================================================
  // 19. PROFIT & LOSS: INDIRECT EXPENSES (P&L Dr)
  // =========================================================================
  if (
    normGroup.includes('indirect expenses') ||
    normGroup.includes('indirect expense') ||
    normGroup.includes('administrative') ||
    normGroup.includes('operating expenses') ||
    normName.includes('salary') ||
    normName.includes('salaries') ||
    normName.includes('remuneration to partner') ||
    normName.includes('director remuneration') ||
    normName.includes('staff welfare') ||
    normName.includes('staff bonus') ||
    normName.includes('gratuity') ||
    normName.includes('office rent') ||
    normName.includes('rent a/c') ||
    normName.includes('rent paid') ||
    normName.includes('rates & taxes') ||
    normName.includes('office electricity') ||
    normName.includes('electricity expenses') ||
    normName.includes('printing') ||
    normName.includes('stationery') ||
    normName.includes('postage') ||
    normName.includes('courier') ||
    normName.includes('telephone') ||
    normName.includes('mobile') ||
    normName.includes('internet') ||
    normName.includes('broadband') ||
    normName.includes('audit fee') ||
    normName.includes('audit fees') ||
    normName.includes('tax audit fee') ||
    normName.includes('legal charges') ||
    normName.includes('legal & professional') ||
    normName.includes('professional fees') ||
    normName.includes('accounting charges') ||
    normName.includes('bank charges') ||
    normName.includes('processing fee') ||
    normName.includes('interest on loan') ||
    normName.includes('interest on cc') ||
    normName.includes('interest on od') ||
    normName.includes('interest paid') ||
    normName.includes('interest on gst') ||
    normName.includes('interest on tds') ||
    normName.includes('interest on income tax') ||
    normName.includes('depreciation') ||
    normName.includes('amortization') ||
    normName.includes('insurance') ||
    normName.includes('office insurance') ||
    normName.includes('vehicle insurance') ||
    normName.includes('fire insurance') ||
    normName.includes('travelling') ||
    normName.includes('conveyance') ||
    normName.includes('petrol') ||
    normName.includes('diesel') ||
    normName.includes('vehicle running') ||
    normName.includes('repairs') ||
    normName.includes('maintenance') ||
    normName.includes('amc charges') ||
    normName.includes('advertisement') ||
    normName.includes('marketing') ||
    normName.includes('sales promotion') ||
    normName.includes('business promotion') ||
    normName.includes('exhibition') ||
    normName.includes('commission on sales') ||
    normName.includes('brokerage') ||
    normName.includes('discount allowed') ||
    normName.includes('freight outward') ||
    normName.includes('carriage outward') ||
    normName.includes('bad debts') ||
    normName.includes('security expenses') ||
    normName.includes('housekeeping') ||
    normName.includes('cleaning') ||
    normName.includes('software subscription') ||
    normName.includes('saas charges') ||
    normName.includes('cloud hosting') ||
    normName.includes('festival expenses') ||
    normName.includes('diwali expenses') ||
    normName.includes('donation') ||
    normName.includes('csr') ||
    normName.includes('loss on sale of asset') ||
    normName.includes('miscellaneous expenses') ||
    normName.includes('general expenses')
  ) {
    return {
      targetType: 'PROFIT_AND_LOSS',
      plCategory: 'INDIRECT_EXPENSE',
      status: 'CONFIRMED',
      confidence: 'HIGH',
      confidenceReason: 'Operating, Administrative or Financial Expense (Profit & Loss Dr)',
    };
  }

  // =========================================================================
  // 20. HEURISTIC FALLBACKS (Based on Debit / Credit Balance & Substring Clues)
  // =========================================================================
  if (!isDebit) {
    // Credit balance fallback
    // Check if looks more like an income or a liability
    const isLikelyIncome = normName.includes('income') || normName.includes('receipt') || normName.includes('fees') || normName.includes('gain');
    if (isLikelyIncome) {
      return {
        targetType: 'PROFIT_AND_LOSS',
        plCategory: 'INDIRECT_INCOME',
        status: 'REVIEW_NEEDED',
        confidence: 'MEDIUM',
        confidenceReason: 'Credit balance detected - Categorized as Indirect Income for review',
      };
    }

    const liabHead = findHeadByCode('L06') || findHeadByCode('L05') || availableHeads.find(h => h.nature === 'Liability');
    return {
      targetType: 'BALANCE_SHEET',
      headCode: liabHead?.code || 'L06',
      mainHead: liabHead?.mainHead || 'Capital & Liabilities',
      subHead: liabHead?.subHead || 'Other Current Liabilities',
      scheduleNo: liabHead?.scheduleNo || 6,
      status: 'REVIEW_NEEDED',
      confidence: 'LOW',
      confidenceReason: 'Credit balance detected - Review whether Current Liability (Schedule 6) or Income',
    };
  } else {
    // Debit balance fallback
    // Check if looks more like an expense or an asset
    const isLikelyExpense = normName.includes('exp') || normName.includes('charge') || normName.includes('cost') || normName.includes('fee') || normName.includes('tax');
    if (isLikelyExpense) {
      return {
        targetType: 'PROFIT_AND_LOSS',
        plCategory: 'INDIRECT_EXPENSE',
        status: 'REVIEW_NEEDED',
        confidence: 'MEDIUM',
        confidenceReason: 'Debit balance detected - Categorized as Indirect Expense for review',
      };
    }

    const assetHead = findHeadByCode('A07') || findHeadByCode('A06') || availableHeads.find(h => h.nature === 'Asset');
    return {
      targetType: 'BALANCE_SHEET',
      headCode: assetHead?.code || 'A07',
      mainHead: assetHead?.mainHead || 'Assets',
      subHead: assetHead?.subHead || 'Other Current Assets',
      scheduleNo: assetHead?.scheduleNo || 14,
      status: 'REVIEW_NEEDED',
      confidence: 'LOW',
      confidenceReason: 'Debit balance detected - Review whether Current Asset (Schedule 14) or Expense',
    };
  }
}

export function batchClassifyLedgers(
  ledgers: Omit<LedgerItem, 'targetType' | 'status' | 'confidence'>[],
  availableHeads: BalanceSheetHeadConfig[],
  savedMappings?: Record<string, string | SavedClassificationRule>
): LedgerItem[] {
  return ledgers.map(item => {
    const result = classifySingleLedger(
      item.ledgerName,
      item.originalGroup,
      item.debit,
      item.credit,
      availableHeads,
      savedMappings
    );

    return {
      ...item,
      targetType: result.targetType,
      headCode: result.headCode,
      mainHead: result.mainHead,
      subHead: result.subHead,
      scheduleNo: result.scheduleNo,
      plCategory: result.plCategory,
      status: result.status,
      confidence: result.confidence,
      confidenceReason: result.confidenceReason,
      hasSavedRule: result.hasSavedRule,
      savedRuleNature: result.savedRuleNature,
      isUserModified: result.hasSavedRule ? true : (item as LedgerItem).isUserModified,
    } as LedgerItem;
  });
}

export const classifyLedgersWithRuleEngine = batchClassifyLedgers;
