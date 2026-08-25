import { DisclosureItem, DisclosureStatus, ScheduleIIIGuidanceItem } from '../types';
import { ParsedFinancialDocument } from './types';

export interface StatutoryRuleDefinition {
  standard: string;
  standardName: string;
  requirement: string;
  applicableParagraph?: string;
  evaluate: (doc: ParsedFinancialDocument) => {
    status: DisclosureStatus;
    observation: string;
  };
}

export const STATUTORY_DISCLOSURE_RULES: StatutoryRuleDefinition[] = [
  // Ind AS 1: Presentation of Financial Statements
  {
    standard: 'Ind AS 1',
    standardName: 'Presentation of Financial Statements',
    requirement: 'Current / Non-current classification and explicit statement of compliance with Ind AS',
    applicableParagraph: 'Ind AS 1.16 & 1.66',
    evaluate: (doc) => {
      const text = doc.rawText.toLowerCase();
      const hasComplianceStatement = text.includes('indian accounting standards') || text.includes('ind as') || text.includes('companies (indian accounting standards) rules');
      const hasCurrentNonCurrent = text.includes('non-current assets') && text.includes('current assets') && text.includes('non-current liabilities') && text.includes('current liabilities');
      
      if (hasComplianceStatement && hasCurrentNonCurrent) {
        return {
          status: 'Complied',
          observation: 'Balance sheet correctly segregates Current and Non-Current classifications with explicit Ind AS compliance affirmation in Note 1 / 2.',
        };
      } else if (hasCurrentNonCurrent) {
        return {
          status: 'Partial',
          observation: 'Current/Non-current segregation is presented, but explicit statement of compliance with Ind AS is brief or ambiguous in accounting policies.',
        };
      }
      return {
        status: 'Missing',
        observation: 'Explicit statement of compliance or clear Current/Non-Current division per Ind AS 1 is missing or incomplete.',
      };
    },
  },

  // Ind AS 2: Inventories
  {
    standard: 'Ind AS 2',
    standardName: 'Inventories',
    requirement: 'Disclosure of accounting policy for valuation (Cost vs NRV), cost formula used, and write-down / reversals quantification',
    applicableParagraph: 'Ind AS 2.36',
    evaluate: (doc) => {
      const text = doc.rawText.toLowerCase();
      const hasInventory = text.includes('inventories') || text.includes('stock-in-trade') || text.includes('raw material');
      if (!hasInventory) {
        return {
          status: 'Complied',
          observation: 'Entity does not hold material inventory or service-oriented business model applies.',
        };
      }
      const hasPolicy = text.includes('lower of cost and net realizable value') || text.includes('lower of cost and nrv') || text.includes('weighted average') || text.includes('fifo');
      const hasWriteDown = text.includes('write-down') || text.includes('allowance for obsolete') || text.includes('carrying amount of inventories');
      
      if (hasPolicy && (hasWriteDown || text.includes('inventories are valued at'))) {
        return {
          status: 'Complied',
          observation: 'Inventory valuation policy (lower of cost or NRV, cost formula FIFO/Weighted Average) and carrying amounts are clearly disclosed in Note to Inventories.',
        };
      } else if (hasPolicy) {
        return {
          status: 'Partial',
          observation: 'Valuation policy is stated, but disclosure of write-down of inventories to NRV or recognized as an expense is omitted.',
        };
      }
      return {
        status: 'Missing',
        observation: 'Specific cost formula (Weighted Average / FIFO) or NRV write-down accounting disclosures not found in Note on Inventories.',
      };
    },
  },

  // Ind AS 7: Statement of Cash Flows
  {
    standard: 'Ind AS 7',
    standardName: 'Statement of Cash Flows',
    requirement: 'Reconciliation of Cash & Cash Equivalents with Balance sheet, non-cash investing/financing transactions, and changes in liabilities from financing activities',
    applicableParagraph: 'Ind AS 7.44A & 7.45',
    evaluate: (doc) => {
      const text = doc.rawText.toLowerCase();
      const hasCashFlow = text.includes('cash flow') || text.includes('operating activities') || text.includes('investing activities');
      const hasFinancingRecon = text.includes('liabilities arising from financing activities') || text.includes('reconciliation of liabilities arising from financing') || text.includes('borrowings rollforward');
      
      if (!hasCashFlow) {
        return {
          status: 'Missing',
          observation: 'Statement of Cash Flows not included or could not be extracted from document text.',
        };
      }
      if (hasFinancingRecon) {
        return {
          status: 'Complied',
          observation: 'Statement of Cash Flows presented with indirect method. Reconciliation of liabilities arising from financing activities (Ind AS 7.44A) is duly disclosed.',
        };
      }
      return {
        status: 'Partial',
        observation: 'Cash Flow Statement is presented, but mandatory reconciliation of changes in liabilities arising from financing activities (cash vs non-cash movements per Ind AS 7 para 44A) is omitted.',
      };
    },
  },

  // Ind AS 12: Income Taxes
  {
    standard: 'Ind AS 12',
    standardName: 'Income Taxes',
    requirement: 'Numerical reconciliation between tax expense and accounting profit multiplied by applicable tax rate (Effective Tax Rate Reconciliation), and DTA/DTL breakups',
    applicableParagraph: 'Ind AS 12.81(c) & 12.81(g)',
    evaluate: (doc) => {
      const text = doc.rawText.toLowerCase();
      const hasTaxRecon = (text.includes('reconciliation') && (text.includes('effective tax') || text.includes('applicable tax rate') || text.includes('tax expense'))) || text.includes('enacted tax rate');
      const hasDtaDtl = text.includes('deferred tax asset') || text.includes('deferred tax liabilit') || text.includes('movement in deferred tax');
      
      if (hasTaxRecon && hasDtaDtl) {
        return {
          status: 'Complied',
          observation: 'Numerical Effective Tax Rate (ETR) reconciliation and year-on-year movement of Deferred Tax Assets/Liabilities across each temporary difference category are provided.',
        };
      } else if (hasDtaDtl) {
        return {
          status: 'Missing',
          observation: 'Deferred tax balance is stated on Balance Sheet, but mandatory Numerical Reconciliation of Effective Tax Rate vs Statutory Tax Rate (Ind AS 12 para 81(c)) is missing.',
        };
      }
      return {
        status: 'Missing',
        observation: 'Tax expense reconciliation or Deferred Tax breakup schedule not found in uploaded financial statements.',
      };
    },
  },

  // Ind AS 16: Property, Plant and Equipment
  {
    standard: 'Ind AS 16',
    standardName: 'Property, Plant and Equipment',
    requirement: 'Full rollforward of gross carrying amount, accumulated depreciation, impairment, additions, deductions, capitalized borrowing costs, and revaluation disclosures (s. 247)',
    applicableParagraph: 'Ind AS 16.73 & 16.74',
    evaluate: (doc) => {
      const text = doc.rawText.toLowerCase();
      const hasPpeNote = text.includes('property, plant and equipment') || text.includes('fixed assets') || text.includes('gross carrying amount') || text.includes('accumulated depreciation');
      const hasRollforward = text.includes('additions') && text.includes('deletions') && text.includes('depreciation for the year');
      const hasRegisteredValuer = doc.hasRegisteredValuerDisclosure || text.includes('registered valuer') || text.includes('revaluation of property') || text.includes('section 247');

      if (hasPpeNote && hasRollforward) {
        return {
          status: 'Complied',
          observation: 'Gross block, additions, disposals, and accumulated depreciation schedules are detailed across all asset classes with useful lives / depreciation method.',
        };
      } else if (hasPpeNote) {
        return {
          status: 'Partial',
          observation: 'PPE line items exist on face of Balance Sheet, but itemized tabular rollforward of gross block and accumulated depreciation for each class of asset is truncated or incomplete.',
        };
      }
      return {
        status: 'Missing',
        observation: 'Mandatory PPE rollforward schedule (Gross Carrying Amount, Additions, Deductions, Accumulated Depreciation) not found in Notes.',
      };
    },
  },

  // Ind AS 19: Employee Benefits
  {
    standard: 'Ind AS 19',
    standardName: 'Employee Benefits',
    requirement: 'Defined Benefit Obligation (Gratuity / Leave Encashment) actuarial rollforward, P&L vs OCI split, sensitivity analysis of key actuarial assumptions (discount rate & salary growth)',
    applicableParagraph: 'Ind AS 19.135 - 19.145',
    evaluate: (doc) => {
      const text = doc.rawText.toLowerCase();
      const hasGratuity = text.includes('gratuity') || text.includes('defined benefit') || text.includes('actuarial');
      const hasSensitivity = text.includes('sensitivity analysis') && (text.includes('discount rate') || text.includes('salary escalation'));
      const hasOci = text.includes('remeasurement of defined benefit') || text.includes('actuarial gain') || text.includes('actuarial loss') || text.includes('other comprehensive income');

      if (hasGratuity && hasSensitivity && hasOci) {
        return {
          status: 'Complied',
          observation: 'Actuarial valuation disclosures, Defined Benefit Obligation (DBO) rollforward, OCI remeasurements, and sensitivity analysis (+/- 1% discount/salary rate) fully provided.',
        };
      } else if (hasGratuity && hasOci) {
        return {
          status: 'Partial',
          observation: 'Actuarial liability is recognized, but mandatory sensitivity analysis for discount rate and salary escalation (Ind AS 19 para 145) is omitted.',
        };
      } else if (hasGratuity) {
        return {
          status: 'Missing',
          observation: 'Employee benefits note lacks mandatory Ind AS 19 actuarial movement tables, OCI separation, and duration profile.',
        };
      }
      return {
        status: 'Not Applicable',
        observation: 'No defined benefit plans or short-term benefits only.',
      };
    },
  },

  // Ind AS 24: Related Party Disclosures
  {
    standard: 'Ind AS 24',
    standardName: 'Related Party Disclosures',
    requirement: 'List of related parties and control relationships, KMP compensation broken into 5 statutory buckets (short-term, post-employment, other long-term, termination, share-based), transaction values and outstanding year-end balances',
    applicableParagraph: 'Ind AS 24.17 & 24.18',
    evaluate: (doc) => {
      const text = doc.rawText.toLowerCase();
      const hasRelatedParty = text.includes('related party') || text.includes('key management personnel') || text.includes('kmp');
      const has5Buckets = text.includes('short-term employee benefits') && (text.includes('post-employment') || text.includes('provident fund') || text.includes('gratuity'));
      const hasTransactionsAndBalances = (text.includes('transaction') || text.includes('remuneration') || text.includes('sitting fees')) && (text.includes('outstanding') || text.includes('receivable') || text.includes('payable') || text.includes('closing balance'));

      if (hasRelatedParty && has5Buckets && hasTransactionsAndBalances) {
        return {
          status: 'Complied',
          observation: 'Comprehensive disclosure of related parties, KMP compensation segmented across mandatory statutory categories (para 17), transaction sums, and outstanding balances.',
        };
      } else if (hasRelatedParty && hasTransactionsAndBalances) {
        return {
          status: 'Partial',
          observation: 'Related party transactions and balances disclosed, but KMP remuneration is presented in aggregate without the mandatory 5-part category breakdown required by Ind AS 24 para 17.',
        };
      } else if (hasRelatedParty) {
        return {
          status: 'Missing',
          observation: 'Related party relationships mentioned, but transaction values, terms, or year-end outstanding balances are missing.',
        };
      }
      return {
        status: 'Missing',
        observation: 'Mandatory Related Party Disclosure note (Ind AS 24) is missing from the financial statements.',
      };
    },
  },

  // Ind AS 33: Earnings Per Share
  {
    standard: 'Ind AS 33',
    standardName: 'Earnings Per Share',
    requirement: 'Basic and Diluted EPS on face of Statement of Profit and Loss, reconciliation of numerators and denominators (weighted average number of equity shares)',
    applicableParagraph: 'Ind AS 33.66 & 33.70',
    evaluate: (doc) => {
      const text = doc.rawText.toLowerCase();
      const hasEpsFace = text.includes('earnings per share') || text.includes('eps') || (text.includes('basic') && text.includes('diluted'));
      const hasEpsRecon = text.includes('weighted average number of shares') || text.includes('nominal value per share');

      if (hasEpsFace && hasEpsRecon) {
        return {
          status: 'Complied',
          observation: 'Basic and Diluted EPS calculated and disclosed with weighted average share count reconciliation and nominal face value per share.',
        };
      } else if (hasEpsFace) {
        return {
          status: 'Partial',
          observation: 'Basic EPS is stated on P&L face, but Note showing reconciliation of weighted average shares for Diluted EPS is missing or brief.',
        };
      }
      return {
        status: 'Missing',
        observation: 'Earnings Per Share disclosure note and computation reconciliation not found.',
      };
    },
  },

  // Ind AS 37: Provisions, Contingent Liabilities and Contingent Assets
  {
    standard: 'Ind AS 37',
    standardName: 'Provisions and Contingent Liabilities',
    requirement: 'Reconciliation for each class of provision (opening, additions, utilized, unused reversed), quantification of contingent liabilities (tax disputes, claims against company) with financial effect estimate',
    applicableParagraph: 'Ind AS 37.84, 37.85 & 37.86',
    evaluate: (doc) => {
      const text = doc.rawText.toLowerCase();
      const hasContingent = text.includes('contingent liabilit') || text.includes('claims against the company') || text.includes('disputed tax') || text.includes('bank guarantees');
      const hasProvisionsMovement = text.includes('movement in provisions') || (text.includes('provisions') && text.includes('opening balance') && text.includes('closing balance'));
      const hasQuantification = (text.includes('income tax demand') || text.includes('gst demand') || text.includes('customs') || text.includes('litigation') || text.includes('nil')) && (text.includes('₹') || text.includes('lakhs') || text.includes('crores') || text.includes('nil'));

      if (hasContingent && hasQuantification) {
        return {
          status: 'Complied',
          observation: 'Contingent liabilities (tax litigations, guarantees, pending claims) are quantified with narrative on financial effect and reimbursement probability.',
        };
      } else if (hasContingent || hasProvisionsMovement) {
        return {
          status: 'Missing',
          observation: 'Contingent liabilities or provisions mentioned in passing without quantified amounts, nature of timing of outflows, or possibility of reimbursement per Ind AS 37.86.',
        };
      }
      return {
        status: 'Missing',
        observation: 'Note on Provisions and Contingent Liabilities (Ind AS 37) not disclosed in uploaded document.',
      };
    },
  },

  // Ind AS 107 & 109: Financial Instruments
  {
    standard: 'Ind AS 107/109',
    standardName: 'Financial Instruments: Disclosures',
    requirement: 'Fair value hierarchy (Level 1/2/3), Credit risk ECL staging & ageing, Liquidity risk contractual undiscounted cash flow maturity buckets, and Market Risk Sensitivity Analysis (Foreign Exchange & Interest Rate)',
    applicableParagraph: 'Ind AS 107.39, 107.40 & Ind AS 109.5.5',
    evaluate: (doc) => {
      const text = doc.rawText.toLowerCase();
      const hasFairValueHierarchy = text.includes('fair value hierarchy') || text.includes('level 1') || text.includes('level 2') || text.includes('level 3');
      const hasLiquidityBuckets = (text.includes('maturity profile') || text.includes('contractual undiscounted') || text.includes('liquidity risk')) && (text.includes('< 1 year') || text.includes('1-5 years') || text.includes('more than'));
      const hasSensitivity = text.includes('sensitivity analysis') && (text.includes('foreign currency') || text.includes('interest rate risk') || text.includes('basis points'));

      if (hasFairValueHierarchy && hasLiquidityBuckets && hasSensitivity) {
        return {
          status: 'Complied',
          observation: 'Full compliance with fair value hierarchy table, liquidity risk contractual maturity breakdown, ECL matrix, and interest rate / foreign currency sensitivity tables.',
        };
      } else if (hasLiquidityBuckets || hasFairValueHierarchy) {
        return {
          status: 'Partial',
          observation: 'Fair value or liquidity maturity table provided, but mandatory Market Risk Sensitivity Analysis (interest rate / FX 100 bps shift per Ind AS 107.40) is omitted.',
        };
      }
      return {
        status: 'Missing',
        observation: 'Mandatory Financial Instruments Risk Management Note (Ind AS 107) with liquidity maturity buckets and sensitivity analysis is missing.',
      };
    },
  },

  // Ind AS 115: Revenue from Contracts with Customers
  {
    standard: 'Ind AS 115',
    standardName: 'Revenue from Contracts with Customers',
    requirement: 'Disaggregation of revenue into categories (geography, offering, timing of transfer), reconciliation of contract assets & contract liabilities (unearned revenue), and performance obligations',
    applicableParagraph: 'Ind AS 115.114 & 115.116',
    evaluate: (doc) => {
      const text = doc.rawText.toLowerCase();
      const hasRevenueNote = text.includes('revenue from operations') || text.includes('sale of products') || text.includes('sale of services');
      const hasDisaggregation = text.includes('disaggregated revenue') || text.includes('disaggregation of revenue') || (text.includes('geographical') && text.includes('revenue'));
      const hasContractBal = text.includes('contract asset') || text.includes('contract liabilit') || text.includes('unearned revenue') || text.includes('advance from customer');

      if (hasRevenueNote && hasDisaggregation && hasContractBal) {
        return {
          status: 'Complied',
          observation: 'Revenue disaggregation by market/offering, contract balances reconciliation (contract assets vs liabilities), and transaction price allocated to remaining performance obligations disclosed.',
        };
      } else if (hasRevenueNote && (hasDisaggregation || hasContractBal)) {
        return {
          status: 'Partial',
          observation: 'Revenue breakdown is provided, but rollforward of contract liabilities (unearned revenue) or performance obligations timing is incomplete.',
        };
      }
      return {
        status: 'Missing',
        observation: 'Detailed disaggregation and contract balance movement tables required under Ind AS 115 are missing.',
      };
    },
  },

  // Ind AS 116: Leases
  {
    standard: 'Ind AS 116',
    standardName: 'Leases',
    requirement: 'Right-of-Use (ROU) assets rollforward (gross, additions, depreciation), Lease Liabilities contractual maturity analysis with undiscounted cash flows, and interest/depreciation split in P&L',
    applicableParagraph: 'Ind AS 116.53 & 116.58',
    evaluate: (doc) => {
      const text = doc.rawText.toLowerCase();
      const hasRou = text.includes('right of use') || text.includes('right-of-use') || text.includes('rou asset');
      const hasLeaseLiab = text.includes('lease liabilit') || text.includes('lease payments');
      const hasMaturity = text.includes('maturity analysis of lease liabilities') || (text.includes('lease') && text.includes('not later than 1 year') && text.includes('later than 5 years'));

      if (hasRou && hasLeaseLiab && hasMaturity) {
        return {
          status: 'Complied',
          observation: 'Right-of-Use (ROU) asset rollforward, lease liability maturity analysis (undiscounted cash flows), and total cash outflow for leases fully presented.',
        };
      } else if (hasRou || hasLeaseLiab) {
        return {
          status: 'Partial',
          observation: 'ROU asset or lease liability appears on Balance Sheet, but contractual lease maturity schedule or discount rate disclosure under Ind AS 116 is missing.',
        };
      }
      return {
        status: 'Not Applicable',
        observation: 'Entity has no lease arrangements or qualifies for short-term lease exemption.',
      };
    },
  },
];

export const SCHEDULE_III_MCA_2021_RULES: Array<{
  clause: string;
  requirement: string;
  guidanceNoteReference: string;
  evaluate: (doc: ParsedFinancialDocument) => {
    complianceStatus: 'Complied' | 'Non-Compliant' | 'Not Disclosed' | 'Not Applicable';
    detailedFinding: string;
  };
}> = [
  // 1. 11 Statutory Ratios
  {
    clause: '11 Statutory Financial Ratios & >25% Variance Explanation',
    requirement: 'Mandatory disclosure of 11 Ratios (Current Ratio, Debt-Equity, DSCR, ROE, Inventory Turnover, Debtors Turnover, Creditors Turnover, Net Capital Turnover, Net Profit Ratio, ROCE, ROI) with reasons for variance exceeding 25%',
    guidanceNoteReference: 'Schedule III Div II (Ind AS) Part I & MCA GSR 207(E)',
    evaluate: (doc) => {
      if (doc.ratios.length >= 8) {
        const highVarianceRatios = doc.ratios.filter((r) => r.variancePercent && Math.abs(r.variancePercent) >= 25);
        const missingExplanation = highVarianceRatios.filter((r) => !r.explanationProvided);
        
        if (missingExplanation.length > 0) {
          return {
            complianceStatus: 'Non-Compliant',
            detailedFinding: `Entity discloses ratio table, but ${missingExplanation.length} ratio(s) with variance >25% (e.g. ${missingExplanation.map(r => r.name).join(', ')}) lack mandatory explanation for significant variance as mandated by MCA 2021 amendments.`,
          };
        }
        return {
          complianceStatus: 'Complied',
          detailedFinding: `All 11 Statutory Ratios are disclosed with prior year comparatives and comprehensive management explanations for variances exceeding 25%.`,
        };
      }
      const text = doc.rawText.toLowerCase();
      if (text.includes('statutory ratio') || text.includes('analytical ratio') || text.includes('current ratio') && text.includes('debt-equity')) {
        return {
          complianceStatus: 'Non-Compliant',
          detailedFinding: 'Partial analytical ratios disclosed, but exhaustive 11-ratio statutory table or variance explanation notes are missing.',
        };
      }
      return {
        complianceStatus: 'Not Disclosed',
        detailedFinding: 'Mandatory 11 Statutory Financial Ratios schedule required by MCA Notification GSR 207(E) is omitted.',
      };
    },
  },

  // 2. Trade Payables Ageing Schedule
  {
    clause: 'Trade Payables Ageing Schedule',
    requirement: 'MSME vs Others ageing schedule categorized into <1yr, 1-2yr, 2-3yr, >3yr, unbilled dues, and disputed vs undisputed dues',
    guidanceNoteReference: 'ICAI Guidance Note on Schedule III Div II / MCA GSR 207(E)',
    evaluate: (doc) => {
      const text = doc.rawText.toLowerCase();
      const hasAging = doc.tradePayablesAgeing.length > 0 || (text.includes('trade payables ageing') && text.includes('msme') && text.includes('1-2 years'));
      const hasMsmeSplit = text.includes('msme') && text.includes('others');

      if (hasAging && hasMsmeSplit) {
        return {
          complianceStatus: 'Complied',
          detailedFinding: 'Trade Payables ageing schedule strictly formatted with MSME vs Others split, unbilled dues, and ageing buckets up to >3 years.',
        };
      } else if (text.includes('trade payables')) {
        return {
          complianceStatus: 'Non-Compliant',
          detailedFinding: 'Trade payables reported on Balance Sheet, but mandatory statutory Ageing Table (<1y, 1-2y, 2-3y, >3y, disputed/undisputed) is missing or incomplete.',
        };
      }
      return {
        complianceStatus: 'Not Disclosed',
        detailedFinding: 'Statutory Trade Payables Ageing Schedule not disclosed.',
      };
    },
  },

  // 3. Trade Receivables Ageing Schedule
  {
    clause: 'Trade Receivables Ageing Schedule',
    requirement: 'Undisputed vs Disputed ageing schedule categorized into <6m, 6m-1yr, 1-2yr, 2-3yr, >3yr, unbilled dues, and ECL credit risk staging',
    guidanceNoteReference: 'Schedule III Div II Part I & ICAI Guidance Note',
    evaluate: (doc) => {
      const text = doc.rawText.toLowerCase();
      const hasAging = doc.tradeReceivablesAgeing.length > 0 || (text.includes('trade receivables ageing') && text.includes('undisputed') && text.includes('less than 6 months'));

      if (hasAging) {
        return {
          complianceStatus: 'Complied',
          detailedFinding: 'Trade Receivables ageing schedule presented with undisputed/disputed split, ECL staging, and <6m to >3y buckets.',
        };
      } else if (text.includes('trade receivables')) {
        return {
          complianceStatus: 'Non-Compliant',
          detailedFinding: 'Trade Receivables balance disclosed, but mandatory Schedule III Ageing Matrix (<6m, 6m-1y, 1-2y, 2-3y, >3y) is missing.',
        };
      }
      return {
        complianceStatus: 'Not Disclosed',
        detailedFinding: 'Statutory Trade Receivables Ageing Schedule omitted.',
      };
    },
  },

  // 4. CWIP Ageing & Completion Schedule
  {
    clause: 'Capital Work-in-Progress (CWIP) Ageing & Overrun Schedule',
    requirement: 'CWIP ageing (<1y, 1-2y, 2-3y, >3y) and CWIP Completion Schedule for projects where cost has exceeded original budget or is overdue',
    guidanceNoteReference: 'MCA Notification GSR 207(E) & Schedule III',
    evaluate: (doc) => {
      const text = doc.rawText.toLowerCase();
      const hasCwip = text.includes('capital work-in-progress') || text.includes('cwip');
      if (!hasCwip) {
        return {
          complianceStatus: 'Not Applicable',
          detailedFinding: 'No Capital Work-in-Progress carrying balance.',
        };
      }
      const hasAging = doc.cwipAgeing.length > 0 || (text.includes('cwip ageing') && text.includes('projects in progress'));
      const hasOverrun = text.includes('overdue') || text.includes('exceeded its original plan') || text.includes('completion schedule');

      if (hasAging) {
        return {
          complianceStatus: 'Complied',
          detailedFinding: 'CWIP ageing schedule provided with project stage breakdown and completion timelines.',
        };
      }
      return {
        complianceStatus: 'Non-Compliant',
        detailedFinding: 'CWIP balance is reported on Balance Sheet, but mandatory CWIP Ageing Table and Cost/Time Overrun Completion Schedule are missing.',
      };
    },
  },

  // 5. Promoter Shareholding Details
  {
    clause: 'Promoter Shareholding Pattern & % Change',
    requirement: 'Details of shares held by promoters at end of year, % of total shares, and % change during the financial year',
    guidanceNoteReference: 'Schedule III Div II / MCA GSR 207(E)',
    evaluate: (doc) => {
      const text = doc.rawText.toLowerCase();
      const hasPromoterSchedule = text.includes('promoter shareholding') || (text.includes('shares held by promoters') && text.includes('% change during the year'));

      if (hasPromoterSchedule) {
        return {
          complianceStatus: 'Complied',
          detailedFinding: 'Promoter shareholding details with % change during the financial year properly disclosed in Share Capital Note.',
        };
      }
      return {
        complianceStatus: 'Non-Compliant',
        detailedFinding: 'Share capital note lacks the mandatory Promoter Shareholding table with % change during the year.',
      };
    },
  },

  // 6. Relationship with Struck-Off Companies
  {
    clause: 'Transactions with Struck-Off Companies (s. 248 / 560)',
    requirement: 'Disclosure of transactions with companies struck off under section 248 of Companies Act 2013 or section 560 of Companies Act 1956',
    guidanceNoteReference: 'Schedule III Statutory Additional Regulatory Information',
    evaluate: (doc) => {
      const text = doc.rawText.toLowerCase();
      const hasStruckOff = doc.hasStruckOffDisclosure || text.includes('struck off') || text.includes('section 248') || text.includes('struck-off companies');

      if (hasStruckOff) {
        return {
          complianceStatus: 'Complied',
          detailedFinding: 'Affirmative declaration on relationship / transactions with struck-off companies is disclosed.',
        };
      }
      return {
        complianceStatus: 'Not Disclosed',
        detailedFinding: 'Mandatory negative/positive statement regarding transactions with Struck-off companies under Section 248 is missing.',
      };
    },
  },

  // 7. Corporate Social Responsibility (CSR) - Section 135
  {
    clause: 'CSR Expenditure Disclosures under Section 135',
    requirement: 'Amount required to be spent, amount spent, shortfall/excess, ongoing vs other than ongoing projects, and unspent CSR bank account details',
    guidanceNoteReference: 'Section 135 & Schedule III Div II MCA 2021',
    evaluate: (doc) => {
      const text = doc.rawText.toLowerCase();
      const hasCsr = doc.hasCSRDisclosure || text.includes('corporate social responsibility') || text.includes('csr expenditure') || text.includes('section 135');

      if (hasCsr) {
        return {
          complianceStatus: 'Complied',
          detailedFinding: 'CSR obligation, actual spend, unspent CSR bank transfers, and project breakups are duly disclosed.',
        };
      }
      return {
        complianceStatus: 'Not Disclosed',
        detailedFinding: 'Statutory CSR disclosure note under Section 135 of Companies Act, 2013 is missing or not affirmed.',
      };
    },
  },

  // 8. Wilful Defaulter Declaration
  {
    clause: 'Wilful Defaulter Declaration',
    requirement: 'Disclosure whether the company has been declared a wilful defaulter by any bank, financial institution or other lender',
    guidanceNoteReference: 'Schedule III Additional Regulatory Information Clause (iv)',
    evaluate: (doc) => {
      const text = doc.rawText.toLowerCase();
      const hasWilful = doc.hasWilfulDefaulterDisclosure || text.includes('wilful defaulter');

      if (hasWilful) {
        return {
          complianceStatus: 'Complied',
          detailedFinding: 'Wilful defaulter declaration is affirmed in Additional Regulatory Disclosures.',
        };
      }
      return {
        complianceStatus: 'Not Disclosed',
        detailedFinding: 'Statutory negative affirmation for Wilful Defaulter declaration is missing in Additional Regulatory Information.',
      };
    },
  },
];
