import { CompanyEntity } from '../types/finance';

// Helper generator to create structured multi-period corporate financials
function makeCompany(
  id: string,
  ticker: string,
  bseCode: string,
  name: string,
  shortName: string,
  sector: any,
  foundedYear: number,
  headquarters: string,
  ceo: string,
  description: string,
  baseRev: number,
  baseEbitdaPct: number,
  baseInterest: number,
  baseDeprPct: number,
  baseTaxPct: number,
  debtEquityRatio: number,
  pe: number,
  pb: number,
  evEbitda: number,
  divYield: number,
  price: number,
  mcap: number,
  high52: number,
  low52: number,
  revGrowthQoQ: number = 0.03,
  yoYSalesGrowth: number = 0.12,
  yoYPatGrowth: number = 0.14,
  otherIncomePct: number = 0.02
): CompanyEntity {
  const q4Rev = baseRev;
  const q4OtherInc = Math.round(baseRev * otherIncomePct);
  const q4TotalRev = q4Rev + q4OtherInc;
  const rawMatPct = 0.45;
  const empPct = 0.12;
  const opexPct = Math.max(0.05, 1 - baseEbitdaPct - rawMatPct - empPct);
  const q4RawMat = Math.round(q4Rev * Math.max(0.05, rawMatPct));
  const q4Emp = Math.round(q4Rev * Math.max(0.06, empPct));
  const q4Opex = Math.round(q4Rev * q4OpexPct(baseEbitdaPct));
  const q4Ebitda = q4Rev - (q4RawMat + q4Emp + q4Opex);
  const q4Depr = Math.round(q4Rev * baseDeprPct);
  const q4Ebit = q4Ebitda + q4OtherInc - q4Depr;
  const q4Interest = baseInterest;
  const q4Ebt = q4Ebit - q4Interest;
  const q4Tax = Math.round(Math.max(0, q4Ebt) * baseTaxPct);
  const q4Pat = q4Ebt - q4Tax;

  const netWorth = Math.round(mcap / Math.max(0.5, pb));
  const shareCapital = Math.round(Math.min(2000, netWorth * 0.05));
  const reserves = netWorth - shareCapital;
  const totalDebt = Math.round(netWorth * debtEquityRatio);
  const longTermDebt = Math.round(totalDebt * 0.75);
  const shortTermDebt = totalDebt - longTermDebt;
  const totalAssets = netWorth + totalDebt + Math.round(baseRev * 0.25);
  const fixedAssets = Math.round(totalAssets * 0.55);
  const cash = Math.round(Math.max(100, totalAssets * 0.08));

  // Prior Year / Comparable metrics for Waterfall
  const prevRev = Math.round(q4Rev / (1 + yoYSalesGrowth));
  const prevPat = Math.round(q4Pat / (1 + yoYPatGrowth));
  const prevEbitda = Math.round(q4Ebitda / (1 + (yoYSalesGrowth * 0.95)));

  const periods: any = {
    'Q4 FY25': {
      pl: {
        revenueFromOperations: q4Rev,
        otherIncome: q4OtherInc,
        totalRevenue: q4TotalRev,
        costOfMaterialsConsumed: Math.round(q4RawMat * 0.7),
        purchaseOfStockInTrade: Math.round(q4RawMat * 0.2),
        changesInInventories: Math.round(q4RawMat * 0.1),
        employeeBenefitExpenses: q4Emp,
        financeCosts: q4Interest,
        depreciationAndAmortization: q4Depr,
        otherExpenses: q4Opex,
        totalExpenses: q4RawMat + q4Emp + q4Opex + q4Interest + q4Depr,
        profitBeforeTax: q4Ebt,
        taxExpense: q4Tax,
        profitAfterTax: q4Pat,
        prevYearRevenue: prevRev,
        prevYearPAT: prevPat,
        prevYearEBITDA: prevEbitda
      },
      balanceSheet: {
        equityShareCapital: shareCapital,
        reservesAndSurplus: reserves,
        longTermBorrowings: longTermDebt,
        shortTermBorrowings: shortTermDebt,
        otherLiabilities: Math.round(baseRev * 0.25),
        totalAssets,
        fixedAssetsNet: fixedAssets,
        capitalWorkInProgress: Math.round(fixedAssets * 0.08),
        investments: Math.round(totalAssets * 0.15),
        cashAndEquivalents: cash,
        currentAssetsOther: totalAssets - fixedAssets - Math.round(fixedAssets * 0.08) - Math.round(totalAssets * 0.15) - cash
      },
      valuation: {
        stockPrice: price,
        marketCap: mcap,
        peRatio: pe,
        pbRatio: pb,
        evEbitdaRatio: evEbitda,
        dividendYield: divYield,
        fiftyTwoWeekHigh: high52,
        fiftyTwoWeekLow: low52,
        sharesOutstandingCr: Math.round((mcap / price) * 100) / 100
      }
    },
    'Q3 FY25': {
      pl: {
        revenueFromOperations: Math.round(q4Rev * 0.97),
        otherIncome: Math.round(q4OtherInc * 0.95),
        totalRevenue: Math.round(q4TotalRev * 0.97),
        costOfMaterialsConsumed: Math.round(q4RawMat * 0.68),
        purchaseOfStockInTrade: Math.round(q4RawMat * 0.19),
        changesInInventories: Math.round(q4RawMat * 0.1),
        employeeBenefitExpenses: Math.round(q4Emp * 0.98),
        financeCosts: q4Interest,
        depreciationAndAmortization: q4Depr,
        otherExpenses: Math.round(q4Opex * 0.97),
        totalExpenses: Math.round((q4RawMat + q4Emp + q4Opex + q4Interest + q4Depr) * 0.97),
        profitBeforeTax: Math.round(q4Ebt * 0.96),
        taxExpense: Math.round(q4Tax * 0.96),
        profitAfterTax: Math.round(q4Pat * 0.96),
        prevYearRevenue: Math.round(prevRev * 0.95),
        prevYearPAT: Math.round(prevPat * 0.95),
        prevYearEBITDA: Math.round(prevEbitda * 0.95)
      },
      balanceSheet: {
        equityShareCapital: shareCapital,
        reservesAndSurplus: Math.round(reserves * 0.98),
        longTermBorrowings: Math.round(longTermDebt * 1.02),
        shortTermBorrowings: shortTermDebt,
        otherLiabilities: Math.round(baseRev * 0.24),
        totalAssets: Math.round(totalAssets * 0.98),
        fixedAssetsNet: Math.round(fixedAssets * 0.99),
        capitalWorkInProgress: Math.round(fixedAssets * 0.09),
        investments: Math.round(totalAssets * 0.14),
        cashAndEquivalents: Math.round(cash * 0.95),
        currentAssetsOther: Math.round(totalAssets * 0.22)
      },
      valuation: {
        stockPrice: Math.round(price * 0.96),
        marketCap: Math.round(mcap * 0.96),
        peRatio: Math.round(pe * 0.98 * 10) / 10,
        pbRatio: pb,
        evEbitdaRatio: evEbitda,
        dividendYield: divYield,
        fiftyTwoWeekHigh: high52,
        fiftyTwoWeekLow: low52,
        sharesOutstandingCr: Math.round((mcap / price) * 100) / 100
      }
    },
    'Q2 FY25': {
      pl: {
        revenueFromOperations: Math.round(q4Rev * 0.94),
        otherIncome: Math.round(q4OtherInc * 0.9),
        totalRevenue: Math.round(q4TotalRev * 0.94),
        costOfMaterialsConsumed: Math.round(q4RawMat * 0.65),
        purchaseOfStockInTrade: Math.round(q4RawMat * 0.18),
        changesInInventories: Math.round(q4RawMat * 0.11),
        employeeBenefitExpenses: Math.round(q4Emp * 0.96),
        financeCosts: Math.round(q4Interest * 1.05),
        depreciationAndAmortization: q4Depr,
        otherExpenses: Math.round(q4Opex * 0.94),
        totalExpenses: Math.round((q4RawMat + q4Emp + q4Opex + q4Interest + q4Depr) * 0.95),
        profitBeforeTax: Math.round(q4Ebt * 0.92),
        taxExpense: Math.round(q4Tax * 0.92),
        profitAfterTax: Math.round(q4Pat * 0.92),
        prevYearRevenue: Math.round(prevRev * 0.92),
        prevYearPAT: Math.round(prevPat * 0.91),
        prevYearEBITDA: Math.round(prevEbitda * 0.92)
      },
      balanceSheet: {
        equityShareCapital: shareCapital,
        reservesAndSurplus: Math.round(reserves * 0.96),
        longTermBorrowings: Math.round(longTermDebt * 1.04),
        shortTermBorrowings: shortTermDebt,
        otherLiabilities: Math.round(baseRev * 0.23),
        totalAssets: Math.round(totalAssets * 0.96),
        fixedAssetsNet: Math.round(fixedAssets * 0.98),
        capitalWorkInProgress: Math.round(fixedAssets * 0.1),
        investments: Math.round(totalAssets * 0.14),
        cashAndEquivalents: Math.round(cash * 0.92),
        currentAssetsOther: Math.round(totalAssets * 0.21)
      },
      valuation: {
        stockPrice: Math.round(price * 0.92),
        marketCap: Math.round(mcap * 0.92),
        peRatio: Math.round(pe * 0.95 * 10) / 10,
        pbRatio: pb,
        evEbitdaRatio: evEbitda,
        dividendYield: divYield,
        fiftyTwoWeekHigh: high52,
        fiftyTwoWeekLow: low52,
        sharesOutstandingCr: Math.round((mcap / price) * 100) / 100
      }
    },
    'FY24': {
      pl: {
        revenueFromOperations: Math.round(q4Rev * 3.8),
        otherIncome: Math.round(q4OtherInc * 3.8),
        totalRevenue: Math.round(q4TotalRev * 3.8),
        costOfMaterialsConsumed: Math.round(q4RawMat * 2.6),
        purchaseOfStockInTrade: Math.round(q4RawMat * 0.7),
        changesInInventories: Math.round(q4RawMat * 0.5),
        employeeBenefitExpenses: Math.round(q4Emp * 3.8),
        financeCosts: Math.round(q4Interest * 4.0),
        depreciationAndAmortization: Math.round(q4Depr * 3.9),
        otherExpenses: Math.round(q4Opex * 3.8),
        totalExpenses: Math.round((q4RawMat + q4Emp + q4Opex + q4Interest + q4Depr) * 3.8),
        profitBeforeTax: Math.round(q4Ebt * 3.75),
        taxExpense: Math.round(q4Tax * 3.75),
        profitAfterTax: Math.round(q4Pat * 3.75),
        prevYearRevenue: Math.round(prevRev * 3.5),
        prevYearPAT: Math.round(prevPat * 3.4),
        prevYearEBITDA: Math.round(prevEbitda * 3.5)
      },
      balanceSheet: {
        equityShareCapital: shareCapital,
        reservesAndSurplus: Math.round(reserves * 0.88),
        longTermBorrowings: Math.round(longTermDebt * 1.08),
        shortTermBorrowings: shortTermDebt,
        otherLiabilities: Math.round(baseRev * 0.9),
        totalAssets: Math.round(totalAssets * 0.92),
        fixedAssetsNet: Math.round(fixedAssets * 0.94),
        capitalWorkInProgress: Math.round(fixedAssets * 0.12),
        investments: Math.round(totalAssets * 0.13),
        cashAndEquivalents: Math.round(cash * 0.85),
        currentAssetsOther: Math.round(totalAssets * 0.2)
      },
      valuation: {
        stockPrice: Math.round(price * 0.85),
        marketCap: Math.round(mcap * 0.85),
        peRatio: Math.round(pe * 0.9 * 10) / 10,
        pbRatio: Math.round(pb * 0.92 * 10) / 10,
        evEbitdaRatio: evEbitda,
        dividendYield: Math.round((divYield * 1.1) * 100) / 100,
        fiftyTwoWeekHigh: high52,
        fiftyTwoWeekLow: low52,
        sharesOutstandingCr: Math.round((mcap / price) * 100) / 100
      }
    },
    'FY23': {
      pl: {
        revenueFromOperations: Math.round(q4Rev * 3.3),
        otherIncome: Math.round(q4OtherInc * 3.2),
        totalRevenue: Math.round(q4TotalRev * 3.3),
        costOfMaterialsConsumed: Math.round(q4RawMat * 2.3),
        purchaseOfStockInTrade: Math.round(q4RawMat * 0.6),
        changesInInventories: Math.round(q4RawMat * 0.4),
        employeeBenefitExpenses: Math.round(q4Emp * 3.3),
        financeCosts: Math.round(q4Interest * 4.2),
        depreciationAndAmortization: Math.round(q4Depr * 3.6),
        otherExpenses: Math.round(q4Opex * 3.3),
        totalExpenses: Math.round((q4RawMat + q4Emp + q4Opex + q4Interest + q4Depr) * 3.3),
        profitBeforeTax: Math.round(q4Ebt * 3.2),
        taxExpense: Math.round(q4Tax * 3.2),
        profitAfterTax: Math.round(q4Pat * 3.2),
        prevYearRevenue: Math.round(prevRev * 3.0),
        prevYearPAT: Math.round(prevPat * 2.9),
        prevYearEBITDA: Math.round(prevEbitda * 3.0)
      },
      balanceSheet: {
        equityShareCapital: shareCapital,
        reservesAndSurplus: Math.round(reserves * 0.78),
        longTermBorrowings: Math.round(longTermDebt * 1.15),
        shortTermBorrowings: shortTermDebt,
        otherLiabilities: Math.round(baseRev * 0.8),
        totalAssets: Math.round(totalAssets * 0.85),
        fixedAssetsNet: Math.round(fixedAssets * 0.88),
        capitalWorkInProgress: Math.round(fixedAssets * 0.15),
        investments: Math.round(totalAssets * 0.12),
        cashAndEquivalents: Math.round(cash * 0.75),
        currentAssetsOther: Math.round(totalAssets * 0.18)
      },
      valuation: {
        stockPrice: Math.round(price * 0.72),
        marketCap: Math.round(mcap * 0.72),
        peRatio: Math.round(pe * 0.85 * 10) / 10,
        pbRatio: Math.round(pb * 0.85 * 10) / 10,
        evEbitdaRatio: evEbitda,
        dividendYield: Math.round((divYield * 1.2) * 100) / 100,
        fiftyTwoWeekHigh: high52,
        fiftyTwoWeekLow: low52,
        sharesOutstandingCr: Math.round((mcap / price) * 100) / 100
      }
    }
  };

  return {
    id,
    ticker,
    bseCode,
    name,
    shortName,
    sector,
    foundedYear,
    headquarters,
    ceo,
    description,
    benchmarkCostOfCapital: 10.0,
    periods
  };
}

function q4OpexPct(ebitdaPct: number): number {
  return Math.max(0.04, 1.0 - ebitdaPct - 0.45 - 0.12);
}

export const ENTERPRISE_UNIVERSE: CompanyEntity[] = [
  // 1. Automobiles & Auto Ancillaries (14 companies)
  makeCompany('tatamotors', 'TATAMOTORS', '500570', 'Tata Motors Limited', 'Tata Motors', 'Automobiles & Auto Ancillaries', 1945, 'Mumbai, Maharashtra', 'Shailesh Chandra', 'Global automotive manufacturer of commercial and passenger vehicles, luxury JLR SUVs, and electric mobility solutions.', 119986, 0.142, 2350, 0.052, 0.22, 0.65, 9.8, 2.4, 4.8, 1.8, 975, 323000, 1179, 642, 0.04, 0.133, 0.38, 0.015),
  makeCompany('maruti', 'MARUTI', '532500', 'Maruti Suzuki India Limited', 'Maruti Suzuki', 'Automobiles & Auto Ancillaries', 1981, 'New Delhi, Delhi', 'Hisashi Takeuchi', 'India’s largest passenger car manufacturer commanding over 40% domestic market share.', 38235, 0.126, 45, 0.024, 0.24, 0.02, 26.5, 3.8, 17.2, 1.1, 12450, 391500, 13680, 9750, 0.03, 0.191, 0.47, 0.032),
  makeCompany('mm', 'M&M', '500520', 'Mahindra & Mahindra Limited', 'M&M', 'Automobiles & Auto Ancillaries', 1945, 'Mumbai, Maharashtra', 'Anish Shah', 'Automotive and farm equipment conglomerate leading in SUVs, tractors, and commercial vehicles.', 35372, 0.145, 120, 0.032, 0.25, 0.18, 28.4, 4.6, 18.5, 0.9, 2980, 370800, 3222, 1495, 0.05, 0.218, 0.28, 0.021),
  makeCompany('bajajauto', 'BAJAJ-AUTO', '532977', 'Bajaj Auto Limited', 'Bajaj Auto', 'Automobiles & Auto Ancillaries', 1945, 'Pune, Maharashtra', 'Rajiv Bajaj', 'World’s third-largest manufacturer of motorcycles and largest three-wheeler manufacturer.', 11485, 0.198, 12, 0.018, 0.23, 0.01, 33.2, 8.4, 23.5, 2.0, 9420, 263500, 12774, 5820, 0.02, 0.215, 0.19, 0.042),
  makeCompany('eichermot', 'EICHERMOT', '505200', 'Eicher Motors Limited', 'Eicher Motors', 'Automobiles & Auto Ancillaries', 1982, 'Gurugram, Haryana', 'Siddhartha Lal', 'Global leader in middleweight motorcycles with Royal Enfield and commercial vehicles via VECV.', 4256, 0.264, 9, 0.028, 0.24, 0.01, 31.8, 6.2, 21.4, 1.2, 4850, 132900, 5104, 3377, 0.03, 0.142, 0.18, 0.038),
  makeCompany('tvsmotor', 'TVSMOTOR', '532343', 'TVS Motor Company Limited', 'TVS Motor', 'Automobiles & Auto Ancillaries', 1978, 'Chennai, Tamil Nadu', 'K.N. Radhakrishnan', 'Third largest two-wheeler manufacturer in India and prominent EV contender (iQube).', 8169, 0.112, 145, 0.029, 0.24, 0.85, 42.5, 11.2, 24.8, 0.4, 2420, 114900, 2600, 1485, 0.04, 0.154, 0.22, 0.012),
  makeCompany('heromotoco', 'HEROMOTOCO', '500182', 'Hero MotoCorp Limited', 'Hero MotoCorp', 'Automobiles & Auto Ancillaries', 1984, 'New Delhi, Delhi', 'Niranjan Gupta', 'Largest manufacturer of two-wheelers in the world by volume for over two decades.', 9519, 0.143, 14, 0.021, 0.25, 0.01, 22.4, 4.8, 14.5, 2.8, 4680, 93600, 5894, 2925, 0.01, 0.146, 0.18, 0.025),
  makeCompany('bharatforg', 'BHARATFORG', '500493', 'Bharat Forge Limited', 'Bharat Forge', 'Automobiles & Auto Ancillaries', 1961, 'Pune, Maharashtra', 'B. N. Kalyani', 'Global forging powerhouse supplying powertrain & chassis components and defence artillery.', 4164, 0.178, 125, 0.045, 0.24, 0.78, 38.6, 6.1, 19.8, 0.6, 1315, 61200, 1780, 985, 0.03, 0.165, 0.29, 0.018),
  makeCompany('motherson', 'MOTHERSON', '517334', 'Samvardhana Motherson International', 'Motherson', 'Automobiles & Auto Ancillaries', 1986, 'Noida, Uttar Pradesh', 'Vivek Chaand Sehgal', 'Global Tier-1 automotive systems and vision components supplier to world OEMs.', 27812, 0.098, 480, 0.041, 0.25, 0.62, 34.5, 4.5, 13.2, 0.5, 168, 118400, 217, 86, 0.05, 0.201, 0.32, 0.014),
  makeCompany('ashokley', 'ASHOKLEY', '500477', 'Ashok Leyland Limited', 'Ashok Leyland', 'Automobiles & Auto Ancillaries', 1948, 'Chennai, Tamil Nadu', 'Shenu Agarwal', 'Second largest commercial vehicle manufacturer in India and leader in electric buses (Switch).', 11267, 0.128, 220, 0.031, 0.24, 0.88, 22.1, 4.9, 13.6, 2.2, 221, 64900, 258, 157, 0.02, 0.089, -0.05, 0.011),
  makeCompany('sonablw', 'SONACOMS', '543300', 'Sona BLW Precision Forgings Limited', 'Sona BLW', 'Automobiles & Auto Ancillaries', 1995, 'Gurugram, Haryana', 'Vivek Vikram Singh', 'Global EV drivetrain and starter motor design innovator.', 945, 0.285, 12, 0.045, 0.24, 0.08, 68.5, 12.8, 38.5, 0.3, 720, 42300, 780, 510, 0.05, 0.245, 0.32, 0.015),
  makeCompany('bosch', 'BOSCHLTD', '500530', 'Bosch Limited', 'Bosch India', 'Automobiles & Auto Ancillaries', 1951, 'Bengaluru, Karnataka', 'Guruprasad Mudlapur', 'Leading automotive electronics, fuel injection, and industrial tech provider.', 4580, 0.138, 18, 0.028, 0.24, 0.01, 44.5, 8.2, 28.5, 1.2, 34500, 101800, 38500, 18500, 0.03, 0.115, 0.165, 0.042),
  makeCompany('unoinda', 'UNOMINDA', '532539', 'UNO Minda Limited', 'UNO Minda', 'Automobiles & Auto Ancillaries', 1958, 'Gurugram, Haryana', 'Nirmal K. Minda', 'Manufacturer of automotive switching systems, lighting, acoustic, and alloy wheels.', 3780, 0.115, 32, 0.038, 0.24, 0.28, 48.5, 8.9, 24.5, 0.3, 1080, 62100, 1240, 560, 0.04, 0.215, 0.285, 0.018),
  makeCompany('exideind', 'EXIDEIND', '500086', 'Exide Industries Limited', 'Exide Ind', 'Automobiles & Auto Ancillaries', 1947, 'Kolkata, West Bengal', 'Avik Roy', 'India’s pioneer battery storage manufacturer advancing into lithium-ion cell gigafactory.', 4250, 0.118, 22, 0.032, 0.24, 0.08, 38.5, 3.4, 18.5, 0.5, 485, 41200, 620, 240, 0.03, 0.125, 0.165, 0.035),

  // 2. Banking & Financial Services (15 companies)
  makeCompany('hdfcbank', 'HDFCBANK', '500180', 'HDFC Bank Limited', 'HDFC Bank', 'Banking & Financial Services', 1994, 'Mumbai, Maharashtra', 'Sashidhar Jagdishan', 'Largest private sector bank in India offering wholesale, retail banking, and treasury solutions.', 85450, 0.385, 34200, 0.012, 0.24, 5.80, 18.2, 2.6, 14.2, 1.2, 1680, 1280000, 1794, 1363, 0.04, 0.175, 0.16, 0.085),
  makeCompany('icicibank', 'ICICIBANK', '532174', 'ICICI Bank Limited', 'ICICI Bank', 'Banking & Financial Services', 1994, 'Mumbai, Maharashtra', 'Sandeep Bakhshi', 'Leading private sector bank with robust digital platforms (iMobile) and corporate franchise.', 43610, 0.442, 16500, 0.015, 0.25, 5.20, 17.5, 3.1, 13.8, 0.9, 1245, 876000, 1332, 928, 0.03, 0.198, 0.21, 0.092),
  makeCompany('sbi', 'SBIN', '500112', 'State Bank of India', 'SBI', 'Banking & Financial Services', 1955, 'Mumbai, Maharashtra', 'C.S. Setty', 'Nation’s largest public sector commercial bank commanding ~24% deposit and loan market share.', 111450, 0.325, 62100, 0.018, 0.24, 6.90, 10.4, 1.4, 8.5, 1.8, 815, 727000, 912, 555, 0.02, 0.135, 0.11, 0.075),
  makeCompany('kotakbank', 'KOTAKBANK', '500247', 'Kotak Mahindra Bank Limited', 'Kotak Bank', 'Banking & Financial Services', 1985, 'Mumbai, Maharashtra', 'Ashok Vaswani', 'Premier private bank known for strong capital adequacy, risk management, and wealth management.', 15820, 0.415, 6100, 0.014, 0.24, 3.90, 19.8, 2.7, 14.5, 0.1, 1790, 356000, 1908, 1543, 0.02, 0.142, 0.12, 0.082),
  makeCompany('axisbank', 'AXISBANK', '532215', 'Axis Bank Limited', 'Axis Bank', 'Banking & Financial Services', 1993, 'Mumbai, Maharashtra', 'Amitabh Chaudhry', 'Third largest private sector bank with extensive retail and corporate branch network.', 31250, 0.365, 13400, 0.016, 0.24, 5.40, 12.8, 1.9, 10.5, 0.1, 1160, 358500, 1339, 933, 0.03, 0.165, 0.14, 0.068),
  makeCompany('bajfinance', 'BAJFINANCE', '500034', 'Bajaj Finance Limited', 'Bajaj Finance', 'Banking & Financial Services', 1987, 'Pune, Maharashtra', 'Rajeev Jain', 'Largest non-banking financial company (NBFC) specializing in consumer lending and digital credit.', 14850, 0.485, 4920, 0.018, 0.25, 3.80, 26.5, 4.9, 18.2, 0.6, 6890, 426000, 7890, 6160, 0.05, 0.245, 0.22, 0.025),
  makeCompany('indusindbk', 'INDUSINDBK', '532187', 'IndusInd Bank Limited', 'IndusInd Bank', 'Banking & Financial Services', 1994, 'Pune, Maharashtra', 'Sumant Kathpalia', 'Universal bank known for vehicle finance, microfinance, and corporate lending.', 14750, 0.342, 6900, 0.015, 0.24, 4.80, 11.2, 1.5, 9.2, 1.2, 1320, 102800, 1694, 1240, 0.01, 0.115, 0.04, 0.058),
  makeCompany('bankbaroda', 'BANKBARODA', '532134', 'Bank of Baroda', 'Bank of Baroda', 'Banking & Financial Services', 1908, 'Vadodara, Gujarat', 'Debadatta Chand', 'Leading public sector bank with substantial international presence and strong retail book.', 32180, 0.315, 18500, 0.014, 0.23, 7.10, 6.8, 1.0, 5.6, 3.2, 245, 126700, 298, 188, 0.02, 0.128, 0.10, 0.049),
  makeCompany('pnb', 'PNB', '532461', 'Punjab National Bank', 'PNB', 'Banking & Financial Services', 1894, 'New Delhi, Delhi', 'Atul Kumar Goel', 'Second largest nationalized bank in India serving over 180 million customers.', 30120, 0.285, 17800, 0.015, 0.24, 7.80, 8.4, 0.9, 6.2, 1.5, 98, 112400, 142, 58, 0.03, 0.155, 0.85, 0.041),
  makeCompany('shriramfin', 'SHRIRAMFIN', '511218', 'Shriram Finance Limited', 'Shriram Finance', 'Banking & Financial Services', 1979, 'Chennai, Tamil Nadu', 'Y.S. Chakravarti', 'Largest retail asset financing NBFC in India catering to CVs, passenger vehicles, and MSMEs.', 9840, 0.465, 3450, 0.012, 0.24, 3.90, 14.8, 2.2, 11.4, 1.4, 3150, 118400, 3652, 1740, 0.04, 0.198, 0.18, 0.035),
  makeCompany('muthootfin', 'MUTHOOTFIN', '533398', 'Muthoot Finance Limited', 'Muthoot Finance', 'Banking & Financial Services', 1939, 'Kochi, Kerala', 'George Alexander Muthoot', 'India’s largest gold financing company with extensive rural & semi-urban network.', 4120, 0.585, 1450, 0.015, 0.25, 3.20, 16.5, 3.1, 13.8, 1.2, 1980, 79500, 2140, 1240, 0.04, 0.225, 0.24, 0.015),
  makeCompany('chola', 'CHOLAFIN', '511243', 'Cholamandalam Investment and Finance', 'Chola Finance', 'Banking & Financial Services', 1978, 'Chennai, Tamil Nadu', 'Ravindra Kumar Kundu', 'Murugappa group vehicle finance and home loan major.', 5820, 0.445, 2350, 0.018, 0.24, 4.50, 28.5, 4.8, 18.5, 0.2, 1450, 121800, 1640, 1020, 0.05, 0.285, 0.295, 0.018),
  makeCompany('hdfclife', 'HDFCLIFE', '540777', 'HDFC Life Insurance Company Limited', 'HDFC Life', 'Banking & Financial Services', 2000, 'Mumbai, Maharashtra', 'Vibha Padalkar', 'Leading long-term life insurance solutions provider in India.', 24800, 0.085, 45, 0.012, 0.08, 0.05, 78.5, 8.9, 45.2, 0.3, 715, 153700, 780, 560, 0.03, 0.145, 0.165, 0.025),
  makeCompany('sbilife', 'SBILIFE', '540719', 'SBI Life Insurance Company Limited', 'SBI Life', 'Banking & Financial Services', 2001, 'Mumbai, Maharashtra', 'Amit Jhingran', 'Joint venture life insurer leveraging State Bank of India branch network.', 28900, 0.075, 25, 0.011, 0.08, 0.02, 68.5, 8.2, 38.5, 0.2, 1580, 158200, 1935, 1340, 0.03, 0.155, 0.185, 0.022),
  makeCompany('icicilomb', 'ICICIGI', '540716', 'ICICI Lombard General Insurance', 'ICICI Lombard', 'Banking & Financial Services', 2001, 'Mumbai, Maharashtra', 'Sanjeev Mantri', 'Largest private non-life general insurer in India across motor, health, and fire.', 5620, 0.165, 12, 0.015, 0.24, 0.04, 38.5, 6.8, 24.5, 0.6, 1890, 93100, 2280, 1420, 0.03, 0.165, 0.215, 0.085),

  // 3. IT - Software & Services (14 companies)
  makeCompany('tcs', 'TCS', '532540', 'Tata Consultancy Services Limited', 'TCS', 'IT - Software & Services', 1968, 'Mumbai, Maharashtra', 'K. Krithivasan', 'Largest IT services exporter in Asia offering digital transformation, cloud, and AI solutions.', 64259, 0.268, 185, 0.021, 0.24, 0.05, 29.5, 12.8, 21.2, 1.9, 4120, 1490000, 4585, 3313, 0.02, 0.058, 0.085, 0.035),
  makeCompany('infy', 'INFY', '500209', 'Infosys Limited', 'Infosys', 'IT - Software & Services', 1981, 'Bengaluru, Karnataka', 'Salil Parekh', 'Global leader in next-generation digital services and consulting with Topaz AI suite.', 40986, 0.238, 115, 0.024, 0.24, 0.04, 27.8, 8.9, 19.5, 2.2, 1860, 772000, 1991, 1358, 0.03, 0.065, 0.072, 0.042),
  makeCompany('hcltech', 'HCLTECH', '532281', 'HCL Technologies Limited', 'HCL Tech', 'IT - Software & Services', 1991, 'Noida, Uttar Pradesh', 'C Vijayakumar', 'Global technology company supercharging business with digital, engineering, and cloud capabilities.', 28862, 0.215, 95, 0.032, 0.23, 0.06, 26.2, 6.8, 17.5, 2.9, 1780, 483000, 1897, 1120, 0.02, 0.082, 0.105, 0.031),
  makeCompany('wipro', 'WIPRO', '507685', 'Wipro Limited', 'Wipro', 'IT - Software & Services', 1945, 'Bengaluru, Karnataka', 'Srini Pallia', 'Leading technology services and consulting company focused on building innovative solutions.', 22208, 0.185, 180, 0.035, 0.23, 0.22, 23.4, 3.8, 14.8, 0.2, 545, 285000, 588, 375, 0.01, -0.015, -0.045, 0.048),
  makeCompany('ltim', 'LTIM', '540005', 'LTIMindtree Limited', 'LTIMindtree', 'IT - Software & Services', 1996, 'Mumbai, Maharashtra', 'Debashis Chatterjee', 'Global technology consulting and digital solutions company formed by merger of L&T Infotech & Mindtree.', 9460, 0.178, 42, 0.028, 0.24, 0.03, 33.5, 6.5, 22.4, 1.2, 5650, 167300, 6442, 4500, 0.02, 0.078, 0.065, 0.025),
  makeCompany('techm', 'TECHM', '532755', 'Tech Mahindra Limited', 'Tech Mahindra', 'IT - Software & Services', 1986, 'Pune, Maharashtra', 'Mohit Joshi', 'Specialist in digital transformation, consulting and business re-engineering services for telecoms & enterprises.', 13313, 0.132, 78, 0.034, 0.24, 0.12, 42.5, 5.2, 24.5, 1.8, 1620, 158500, 1720, 1080, 0.03, 0.045, 0.35, 0.021),
  makeCompany('persistent', 'PERSISTENT', '533179', 'Persistent Systems Limited', 'Persistent Systems', 'IT - Software & Services', 1990, 'Pune, Maharashtra', 'Sandeep Kalra', 'Pioneer in digital engineering, enterprise modernization, and software product development.', 2897, 0.165, 18, 0.031, 0.24, 0.08, 58.2, 11.8, 38.5, 0.8, 5420, 83400, 5950, 3550, 0.05, 0.215, 0.24, 0.018),
  makeCompany('coforge', 'COFORGE', '532541', 'Coforge Limited', 'Coforge', 'IT - Software & Services', 1992, 'Noida, Uttar Pradesh', 'Sudhir Singh', 'Digital services and solutions provider specializing in BFS, Insurance, and Travel sectors.', 2645, 0.172, 38, 0.035, 0.23, 0.35, 48.5, 7.8, 28.2, 0.9, 7850, 52300, 8400, 4300, 0.06, 0.185, 0.15, 0.015),
  makeCompany('kpit', 'KPITTECH', '542651', 'KPIT Technologies Limited', 'KPIT Tech', 'IT - Software & Services', 1990, 'Pune, Maharashtra', 'Ravi Pandit', 'Specialized automotive engineering software and autonomous mobility solutions partner.', 1475, 0.208, 14, 0.032, 0.24, 0.15, 62.4, 14.5, 42.1, 0.4, 1620, 44400, 1928, 1315, 0.05, 0.254, 0.38, 0.012),
  makeCompany('tataelxsi', 'TATAELXSI', '500408', 'Tata Elxsi Limited', 'Tata Elxsi', 'IT - Software & Services', 1989, 'Bengaluru, Karnataka', 'Manoj Raghavan', 'Design and technology services leader across automotive, broadcast, communications, and healthcare.', 955, 0.285, 8, 0.028, 0.24, 0.02, 54.2, 14.8, 36.4, 1.1, 7150, 44500, 9200, 6411, 0.01, 0.062, 0.045, 0.028),
  makeCompany('mphasis', 'MPHASIS', '526299', 'Mphasis Limited', 'Mphasis', 'IT - Software & Services', 1992, 'Bengaluru, Karnataka', 'Nitin Rakesh', 'Cloud and cognitive solutions specialist serving top global BFSI institutions.', 3540, 0.158, 38, 0.028, 0.24, 0.22, 28.5, 5.2, 18.5, 2.0, 2980, 56200, 3240, 2180, 0.02, 0.065, 0.085, 0.021),
  makeCompany('ltts', 'LTTS', '540115', 'L&T Technology Services Limited', 'LTTS', 'IT - Software & Services', 2012, 'Mumbai, Maharashtra', 'Amit Chadha', 'Pure-play engineering research & development (ER&D) services company.', 2580, 0.175, 22, 0.029, 0.24, 0.05, 42.5, 8.9, 28.5, 1.0, 5450, 57600, 6080, 4200, 0.02, 0.075, 0.065, 0.025),
  makeCompany('cyient', 'CYIENT', '532175', 'Cyient Limited', 'Cyient', 'IT - Software & Services', 1991, 'Hyderabad, Telangana', 'Karthikeyan Natarajan', 'Engineering, manufacturing, geospatial networks, and digital operations specialist.', 1890, 0.152, 28, 0.032, 0.24, 0.35, 32.5, 4.8, 19.8, 1.4, 1880, 20800, 2450, 1680, 0.03, 0.085, 0.092, 0.018),
  makeCompany('ofss', 'OFSS', '532466', 'Oracle Financial Services Software', 'Oracle Fin Serv', 'IT - Software & Services', 1989, 'Mumbai, Maharashtra', 'Chaitanya Kamat', 'World-leading core banking and financial software solutions provider (FLEXCUBE).', 1680, 0.445, 4, 0.015, 0.24, 0.01, 34.5, 12.8, 22.4, 2.8, 11450, 98800, 12900, 4200, 0.03, 0.145, 0.225, 0.045),

  // 4. Oil, Gas & Petroleum (11 companies)
  makeCompany('reliance', 'RELIANCE', '500325', 'Reliance Industries Limited', 'Reliance', 'Oil, Gas & Petroleum', 1973, 'Mumbai, Maharashtra', 'Mukesh D. Ambani', 'India’s largest conglomerate with world-scale refining, petrochemicals, telecom (Jio), and retail.', 240715, 0.178, 5760, 0.052, 0.24, 0.44, 25.8, 2.4, 13.5, 0.3, 2985, 2020000, 3217, 2220, 0.03, 0.115, 0.128, 0.038),
  makeCompany('ongc', 'ONGC', '500312', 'Oil and Natural Gas Corporation', 'ONGC', 'Oil, Gas & Petroleum', 1956, 'New Delhi, Delhi', 'Arun Kumar Singh', 'Largest crude oil and natural gas exploration and production enterprise in India.', 164250, 0.185, 2150, 0.075, 0.25, 0.38, 7.8, 1.1, 4.8, 4.5, 292, 367300, 344, 172, 0.02, 0.042, 0.065, 0.045),
  makeCompany('bpcl', 'BPCL', '500547', 'Bharat Petroleum Corporation', 'BPCL', 'Oil, Gas & Petroleum', 1952, 'Mumbai, Maharashtra', 'G. Krishnakumar', 'Maharatna PSU enterprise engaged in refining, supply, and marketing of petroleum products.', 132100, 0.082, 620, 0.032, 0.24, 0.68, 7.5, 1.4, 5.2, 6.2, 348, 151000, 388, 168, 0.01, 0.028, -0.18, 0.015),
  makeCompany('ioc', 'IOC', '530965', 'Indian Oil Corporation Limited', 'Indian Oil', 'Oil, Gas & Petroleum', 1959, 'New Delhi, Delhi', 'V. Satish Kumar', 'Largest commercial oil company in India with extensive refining and nationwide fuel pump network.', 219800, 0.065, 1850, 0.038, 0.24, 0.85, 8.2, 1.1, 5.5, 4.8, 168, 237400, 196, 88, 0.02, 0.031, -0.22, 0.012),
  makeCompany('hpcl', 'HPCL', '500104', 'Hindustan Petroleum Corporation', 'HPCL', 'Oil, Gas & Petroleum', 1974, 'Mumbai, Maharashtra', 'Vikas Kaushal', 'Major downstream refining and petroleum retailing enterprise with Pan-India marketing footprint.', 118400, 0.058, 780, 0.035, 0.24, 1.45, 6.9, 1.3, 5.8, 4.2, 385, 81900, 442, 230, 0.01, 0.045, -0.15, 0.014),
  makeCompany('gail', 'GAIL', '532155', 'GAIL (India) Limited', 'GAIL', 'Oil, Gas & Petroleum', 1984, 'New Delhi, Delhi', 'Sandeep Kumar Gupta', 'Pioneer in natural gas transmission, city gas distribution, petrochemicals, and LPG extraction.', 34200, 0.125, 185, 0.038, 0.24, 0.24, 12.5, 1.8, 8.4, 3.2, 222, 145900, 246, 115, 0.03, 0.085, 0.35, 0.021),
  makeCompany('petronet', 'PETRONET', '532522', 'Petronet LNG Limited', 'Petronet LNG', 'Oil, Gas & Petroleum', 1998, 'New Delhi, Delhi', 'A.K. Singh', 'Major LNG importer and regasification terminal operator at Dahej and Kochi.', 13850, 0.115, 78, 0.032, 0.24, 0.18, 13.8, 2.6, 8.9, 3.5, 345, 51750, 384, 218, 0.02, 0.052, 0.085, 0.038),
  makeCompany('gujgasltd', 'GUJGASLTD', '539336', 'Gujarat Gas Limited', 'Gujarat Gas', 'Oil, Gas & Petroleum', 1980, 'Ahmedabad, Gujarat', 'Sanjeev Kumar', 'Largest city gas distribution company in India with major industrial customer stronghold in Morbi.', 4280, 0.138, 12, 0.028, 0.24, 0.01, 28.5, 4.2, 17.5, 1.2, 575, 39600, 680, 432, 0.03, 0.065, 0.092, 0.018),
  makeCompany('igl', 'IGL', '532514', 'Indraprastha Gas Limited', 'IGL', 'Oil, Gas & Petroleum', 1998, 'New Delhi, Delhi', 'Kamal Kishore Chatiwal', 'City gas utility supplying CNG to automobiles and PNG to households in Delhi-NCR region.', 3980, 0.182, 6, 0.035, 0.24, 0.01, 19.5, 3.4, 11.8, 1.8, 485, 33950, 560, 375, 0.02, 0.075, 0.045, 0.025),
  makeCompany('mgl', 'MGL', '539957', 'Mahanagar Gas Limited', 'MGL', 'Oil, Gas & Petroleum', 1995, 'Mumbai, Maharashtra', 'Ashu Shinghal', 'Sole authorized distributor of compressed natural gas (CNG) and piped gas (PNG) in Mumbai.', 1780, 0.245, 4, 0.038, 0.24, 0.01, 14.8, 2.9, 9.4, 2.4, 1680, 16600, 1988, 1010, 0.03, 0.125, 0.145, 0.032),
  makeCompany('oilindia', 'OIL', '533106', 'Oil India Limited', 'Oil India', 'Oil, Gas & Petroleum', 1959, 'Duliajan, Assam', 'Ranjit Rath', 'Navratna upstream E&P player operating extensive fields in Northeast India and Numaligarh Refinery.', 6120, 0.345, 185, 0.078, 0.24, 0.38, 12.8, 2.2, 7.5, 2.8, 545, 88600, 767, 280, 0.03, 0.145, 0.285, 0.045),

  // 5. Metals & Mining (11 companies)
  makeCompany('tatasteel', 'TATASTEEL', '500470', 'Tata Steel Limited', 'Tata Steel', 'Metals & Mining', 1907, 'Mumbai, Maharashtra', 'T. V. Narendran', 'Global top-tier steel producer with integrated operations in India, UK, and Netherlands.', 58687, 0.125, 1820, 0.045, 0.24, 0.85, 24.2, 1.8, 8.9, 2.1, 155, 193500, 184, 114, 0.02, 0.035, -0.28, 0.018),
  makeCompany('jswsteel', 'JSWSTEEL', '500228', 'JSW Steel Limited', 'JSW Steel', 'Metals & Mining', 1982, 'Mumbai, Maharashtra', 'Jayant Acharya', 'Flagship company of JSW Group, leading manufacturer of flat and long steel products.', 42943, 0.148, 1680, 0.051, 0.24, 1.15, 32.5, 2.8, 11.2, 0.8, 985, 240800, 1066, 737, 0.03, 0.082, -0.065, 0.015),
  makeCompany('hindalco', 'HINDALCO', '500440', 'Hindalco Industries Limited', 'Hindalco', 'Metals & Mining', 1958, 'Mumbai, Maharashtra', 'Satish Pai', 'World’s largest aluminum flat-rolled products company and leading copper producer (Novelis).', 58203, 0.135, 1020, 0.039, 0.24, 0.52, 15.2, 1.6, 7.2, 0.5, 685, 153900, 715, 452, 0.04, 0.095, 0.285, 0.022),
  makeCompany('vedl', 'VEDL', '500295', 'Vedanta Limited', 'Vedanta', 'Metals & Mining', 1965, 'Mumbai, Maharashtra', 'Arun Misra', 'Diversified natural resources major with zinc, lead, silver, oil & gas, aluminum, and power assets.', 38240, 0.248, 2350, 0.068, 0.25, 2.15, 14.5, 3.4, 6.8, 8.5, 455, 169800, 506, 211, 0.03, 0.142, 0.45, 0.035),
  makeCompany('coalindia', 'COALINDIA', '533278', 'Coal India Limited', 'Coal India', 'Metals & Mining', 1975, 'Kolkata, West Bengal', 'P. M. Prasad', 'World’s largest single coal producer accounting for ~80% of India’s domestic coal production.', 38550, 0.295, 120, 0.042, 0.24, 0.04, 8.2, 2.8, 4.8, 6.2, 485, 298900, 543, 260, 0.02, 0.048, 0.095, 0.065),
  makeCompany('sail', 'SAIL', '500113', 'Steel Authority of India Limited', 'SAIL', 'Metals & Mining', 1954, 'New Delhi, Delhi', 'Amarendu Prakash', 'Central public sector enterprise operating 5 integrated steel plants with heavy capital base.', 27950, 0.078, 620, 0.052, 0.24, 1.18, 18.5, 0.9, 9.2, 1.4, 138, 57000, 175, 84, 0.01, 0.025, -0.42, 0.011),
  makeCompany('jindalstel', 'JINDALSTEL', '532286', 'Jindal Steel & Power Limited', 'JSPL', 'Metals & Mining', 1979, 'New Delhi, Delhi', 'Bimlendra Jha', 'Leading steelmaker with dedicated port, rail, and heavy engineering facilities.', 13890, 0.185, 290, 0.048, 0.24, 0.32, 16.8, 2.1, 7.8, 0.2, 945, 96400, 1075, 620, 0.04, 0.112, 0.18, 0.014),
  makeCompany('nmdc', 'NMDC', '526371', 'NMDC Limited', 'NMDC', 'Metals & Mining', 1958, 'Hyderabad, Telangana', 'Amitava Mukherjee', 'India’s largest iron ore miner with low cost per ton extraction across Bailadila & Donimalai.', 6480, 0.345, 25, 0.028, 0.24, 0.01, 10.4, 2.6, 6.8, 3.8, 235, 68800, 286, 135, 0.03, 0.165, 0.22, 0.045),
  makeCompany('nalco', 'NATIONALUM', '532234', 'National Aluminium Company Limited', 'NALCO', 'Metals & Mining', 1981, 'Bhubaneswar, Odisha', 'Sridhar Patra', 'Lowest-cost producer of metallurgical grade alumina and high-purity aluminum ingots in the world.', 3620, 0.285, 12, 0.035, 0.24, 0.01, 14.5, 2.4, 8.5, 3.2, 218, 40000, 248, 90, 0.04, 0.225, 0.88, 0.038),
  makeCompany('hindzinc', 'HINDZINC', '500188', 'Hindustan Zinc Limited', 'Hindustan Zinc', 'Metals & Mining', 1966, 'Udaipur, Rajasthan', 'Arun Misra', 'World’s second-largest zinc-lead miner and third-largest silver producer.', 8250, 0.485, 220, 0.078, 0.24, 0.72, 24.5, 14.2, 13.8, 5.8, 515, 217600, 807, 285, 0.03, 0.185, 0.24, 0.025),
  makeCompany('aplapollo', 'APLAPOLLO', '533758', 'APL Apollo Tubes Limited', 'APL Apollo', 'Metals & Mining', 1986, 'Noida, Uttar Pradesh', 'Sanjay Gupta', 'Largest producer of structural steel tubes in India with 50%+ domestic market share.', 4680, 0.078, 28, 0.024, 0.24, 0.25, 48.5, 8.9, 28.5, 0.3, 1480, 41100, 1820, 1380, 0.04, 0.155, 0.092, 0.012),

  // 6. Pharmaceuticals & Healthcare (15 companies)
  makeCompany('sunpharma', 'SUNPHARMA', '524715', 'Sun Pharmaceutical Industries Limited', 'Sun Pharma', 'Pharmaceuticals & Healthcare', 1983, 'Mumbai, Maharashtra', 'Dilip Shanghvi', 'India’s largest pharma company and 4th largest global specialty generic enterprise.', 13291, 0.278, 62, 0.045, 0.22, 0.04, 38.5, 5.8, 26.2, 0.8, 1780, 427000, 1960, 1110, 0.03, 0.112, 0.165, 0.032),
  makeCompany('drreddy', 'DRREDDY', '500124', 'Dr. Reddy\'s Laboratories Limited', 'Dr. Reddy\'s', 'Pharmaceuticals & Healthcare', 1984, 'Hyderabad, Telangana', 'G. V. Prasad', 'Global generic API and biosimilars giant with strong US, Europe, and emerging markets presence.', 7820, 0.285, 48, 0.048, 0.23, 0.08, 21.2, 3.6, 14.8, 0.6, 6450, 107700, 7100, 5200, 0.04, 0.145, 0.185, 0.035),
  makeCompany('cipla', 'CIPLA', '500087', 'Cipla Limited', 'Cipla', 'Pharmaceuticals & Healthcare', 1935, 'Mumbai, Maharashtra', 'Umang Vohra', 'Pioneer in respiratory therapies, anti-retrovirals, and domestic consumer healthcare.', 6820, 0.262, 28, 0.041, 0.24, 0.02, 28.5, 4.4, 18.2, 0.9, 1540, 124300, 1702, 1132, 0.02, 0.092, 0.142, 0.028),
  makeCompany('divis', 'DIVISLAB', '532488', 'Divi\'s Laboratories Limited', 'Divi\'s Lab', 'Pharmaceuticals & Healthcare', 1990, 'Hyderabad, Telangana', 'Murali K. Divi', 'Custom synthesis and leading manufacturer of active pharmaceutical ingredients (APIs).', 2450, 0.325, 8, 0.045, 0.22, 0.01, 72.5, 9.8, 48.5, 0.7, 5890, 156300, 6245, 3420, 0.04, 0.225, 0.35, 0.038),
  makeCompany('apollohosp', 'APOLLOHOSP', '508869', 'Apollo Hospitals Enterprise Limited', 'Apollo Hospitals', 'Pharmaceuticals & Healthcare', 1983, 'Chennai, Tamil Nadu', 'Prathap C. Reddy', 'Integrated healthcare chain operating multi-specialty hospitals, pharmacies, and Apollo 24/7.', 5580, 0.142, 115, 0.042, 0.24, 0.42, 78.5, 9.5, 32.5, 0.3, 6980, 100400, 7550, 4710, 0.05, 0.152, 0.48, 0.015),
  makeCompany('torrentpharm', 'TORNTPHARM', '500420', 'Torrent Pharmaceuticals Limited', 'Torrent Pharma', 'Pharmaceuticals & Healthcare', 1959, 'Ahmedabad, Gujarat', 'Samir Mehta', 'Dominant player in cardiovascular, CNS, gastrointestinal, and women healthcare segments.', 2980, 0.315, 85, 0.052, 0.24, 0.72, 58.5, 12.4, 28.5, 0.9, 3250, 109900, 3580, 1880, 0.03, 0.125, 0.24, 0.018),
  makeCompany('lupin', 'LUPIN', '500257', 'Lupin Limited', 'Lupin', 'Pharmaceuticals & Healthcare', 1968, 'Mumbai, Maharashtra', 'Vinita Gupta', 'Global pharma enterprise leading in anti-TB, respiratory, diabetes, and generic injectables.', 5620, 0.198, 72, 0.042, 0.23, 0.28, 38.5, 4.8, 19.8, 0.4, 2180, 99500, 2315, 1050, 0.04, 0.148, 0.52, 0.012),
  makeCompany('zyduslife', 'ZYDUSLIFE', '532321', 'Zydus Lifesciences Limited', 'Zydus Life', 'Pharmaceuticals & Healthcare', 1952, 'Ahmedabad, Gujarat', 'Sharvil Patel', 'Innovator pharma company producing generics, biologics, vaccines, and consumer wellness products.', 5420, 0.285, 32, 0.039, 0.22, 0.12, 26.5, 4.2, 16.5, 0.4, 1080, 108600, 1324, 580, 0.03, 0.165, 0.31, 0.022),
  makeCompany('maxhealth', 'MAXHEALTH', '543220', 'Max Healthcare Institute Limited', 'Max Health', 'Pharmaceuticals & Healthcare', 2001, 'New Delhi, Delhi', 'Abhay Soi', 'Premier quaternary healthcare network with premium beds across Delhi-NCR and Mumbai.', 2150, 0.275, 28, 0.038, 0.24, 0.15, 68.2, 9.8, 34.2, 0.2, 1020, 99200, 1140, 560, 0.05, 0.215, 0.28, 0.014),
  makeCompany('biocon', 'BIOCON', '532523', 'Biocon Limited', 'Biocon', 'Pharmaceuticals & Healthcare', 1978, 'Bengaluru, Karnataka', 'Kiran Mazumdar-Shaw', 'Asia’s premier biopharmaceutical company focused on affordable insulins and oncology biosimilars.', 3980, 0.195, 320, 0.075, 0.24, 0.85, 42.5, 2.1, 14.8, 0.4, 345, 41400, 395, 225, 0.02, 0.082, -0.15, 0.015),
  makeCompany('auropharma', 'AUROPHARMA', '524804', 'Aurobindo Pharma Limited', 'Aurobindo', 'Pharmaceuticals & Healthcare', 1986, 'Hyderabad, Telangana', 'K. Nithyananda Reddy', 'Top-tier generic exporter with massive manufacturing scale and injectable portfolio.', 7580, 0.215, 38, 0.045, 0.24, 0.12, 22.5, 2.8, 12.4, 0.4, 1420, 83200, 1590, 810, 0.03, 0.125, 0.285, 0.025),
  makeCompany('fortis', 'FORTIS', '532843', 'Fortis Healthcare Limited', 'Fortis Health', 'Pharmaceuticals & Healthcare', 1996, 'Gurugram, Haryana', 'Ashutosh Raghuvanshi', 'Leading integrated healthcare services provider operating 27 hospitals and SRL Diagnostics.', 1890, 0.195, 45, 0.048, 0.24, 0.18, 48.5, 4.2, 22.5, 0.2, 545, 41100, 625, 310, 0.04, 0.145, 0.32, 0.018),
  makeCompany('alkem', 'ALKEM', '539523', 'Alkem Laboratories Limited', 'Alkem Labs', 'Pharmaceuticals & Healthcare', 1973, 'Mumbai, Maharashtra', 'Sandeep Singh', 'Market leader in anti-infectives and prominent generic pharmaceutical enterprise.', 3450, 0.205, 18, 0.035, 0.24, 0.08, 34.5, 5.8, 22.4, 0.7, 5450, 65200, 6200, 3950, 0.03, 0.115, 0.215, 0.028),
  makeCompany('glenmark', 'GLENMARK', '532296', 'Glenmark Pharmaceuticals Limited', 'Glenmark', 'Pharmaceuticals & Healthcare', 1977, 'Mumbai, Maharashtra', 'Glenn Saldanha', 'Research-led global pharmaceutical enterprise with strong presence in dermatology and respiratory.', 3680, 0.178, 68, 0.045, 0.24, 0.45, 28.5, 3.2, 14.5, 0.2, 1580, 44600, 1820, 750, 0.03, 0.095, 0.42, 0.015),
  makeCompany('granules', 'GRANULES', '532482', 'Granules India Limited', 'Granules India', 'Pharmaceuticals & Healthcare', 1991, 'Hyderabad, Telangana', 'Krishna Prasad Chigurupati', 'High-volume vertically integrated manufacturer of Paracetamol, Ibuprofen, and Metformin.', 1280, 0.215, 28, 0.052, 0.24, 0.38, 24.5, 3.4, 14.8, 0.3, 560, 13500, 685, 280, 0.03, 0.125, 0.245, 0.014),

  // 7. FMCG (14 companies)
  makeCompany('hul', 'HINDUNILVR', '500696', 'Hindustan Unilever Limited', 'HUL', 'Fast Moving Consumer Goods (FMCG)', 1933, 'Mumbai, Maharashtra', 'Rohit Jawa', 'India’s largest FMCG conglomerate touching 9 out of 10 Indian households across beauty, foods & homecare.', 15820, 0.238, 75, 0.019, 0.25, 0.02, 54.2, 11.8, 36.5, 1.8, 2450, 575700, 3035, 2170, 0.02, 0.045, 0.038, 0.042),
  makeCompany('itc', 'ITC', '500875', 'ITC Limited', 'ITC', 'Fast Moving Consumer Goods (FMCG)', 1910, 'Kolkata, West Bengal', 'Sanjiv Puri', 'Diversified conglomerate spanning cigarettes, FMCG foods & personal care, paperboards, and agri-business.', 18450, 0.365, 18, 0.024, 0.24, 0.01, 26.8, 7.5, 18.2, 3.2, 475, 592800, 528, 399, 0.02, 0.075, 0.085, 0.055),
  makeCompany('nestleind', 'NESTLEIND', '500790', 'Nestlé India Limited', 'Nestle India', 'Fast Moving Consumer Goods (FMCG)', 1959, 'Gurugram, Haryana', 'Suresh Narayanan', 'Food & beverage major commanding leadership in instant noodles (Maggi), dairy, and infant nutrition.', 5280, 0.242, 38, 0.028, 0.25, 0.05, 74.5, 45.2, 48.5, 1.1, 2380, 229500, 2770, 2145, 0.01, 0.065, 0.048, 0.018),
  makeCompany('britannia', 'BRITANNIA', '500825', 'Britannia Industries Limited', 'Britannia', 'Fast Moving Consumer Goods (FMCG)', 1892, 'Bengaluru, Karnataka', 'Varun Berry', 'India’s iconic bakery foods manufacturer commanding supreme biscuit market share (Good Day, Marie Gold).', 4580, 0.185, 52, 0.021, 0.25, 0.65, 58.2, 28.5, 38.2, 1.4, 5250, 126400, 6040, 4350, 0.02, 0.058, 0.072, 0.025),
  makeCompany('godrejcp', 'GODREJCP', '532424', 'Godrej Consumer Products Limited', 'Godrej Consumer', 'Fast Moving Consumer Goods (FMCG)', 2001, 'Mumbai, Maharashtra', 'Sudhir Sitapati', 'Leader in household insecticides (Goodknight, HIT), personal wash (Cinthol, Godrej No. 1), and hair color.', 3820, 0.205, 68, 0.032, 0.24, 0.32, 62.5, 7.8, 34.5, 1.2, 1280, 130900, 1540, 970, 0.03, 0.082, 0.115, 0.028),
  makeCompany('dabur', 'DABUR', '500096', 'Dabur India Limited', 'Dabur', 'Fast Moving Consumer Goods (FMCG)', 1884, 'Ghaziabad, Uttar Pradesh', 'Mohit Malhotra', 'World leader in Ayurveda and natural healthcare, oral care, foods (Real juice), and hair oils.', 3150, 0.192, 32, 0.031, 0.24, 0.12, 52.4, 8.9, 35.8, 1.1, 545, 96500, 672, 490, 0.01, 0.045, 0.032, 0.035),
  makeCompany('marico', 'MARICO', '531642', 'Marico Limited', 'Marico', 'Fast Moving Consumer Goods (FMCG)', 1990, 'Mumbai, Maharashtra', 'Saugata Gupta', 'Pioneer in coconut oil (Parachute), value-added hair oils, and premium healthy foods (Saffola).', 2650, 0.212, 15, 0.021, 0.23, 0.14, 54.8, 17.5, 36.2, 1.6, 685, 88700, 715, 485, 0.03, 0.085, 0.095, 0.032),
  makeCompany('vbl', 'VBL', '540180', 'Varun Beverages Limited', 'Varun Beverages', 'Fast Moving Consumer Goods (FMCG)', 1995, 'Gurugram, Haryana', 'Ravi Jaipuria', 'Key franchisee of PepsiCo globally producing carbonated soft drinks, juices, and packaged water.', 4820, 0.235, 125, 0.065, 0.24, 0.75, 68.5, 14.8, 34.8, 0.4, 580, 188400, 683, 360, 0.05, 0.225, 0.295, 0.012),
  makeCompany('tataconsum', 'TATACONSUM', '500770', 'Tata Consumer Products Limited', 'Tata Consumer', 'Fast Moving Consumer Goods (FMCG)', 1962, 'Mumbai, Maharashtra', 'Sunil D\'Souza', 'Integrated food and beverage company combining Tata Tea, Tata Salt, Tetley, Sampann, and Soulfull.', 4120, 0.148, 65, 0.035, 0.24, 0.22, 74.2, 6.2, 38.5, 0.8, 1040, 99200, 1269, 815, 0.03, 0.125, 0.082, 0.025),
  makeCompany('colpal', 'COLPAL', '500830', 'Colgate-Palmolive (India) Limited', 'Colgate', 'Fast Moving Consumer Goods (FMCG)', 1937, 'Mumbai, Maharashtra', 'Prabha Narasimhan', 'Market leader in oral care with over 50% toothpaste market share in India.', 1580, 0.335, 8, 0.028, 0.25, 0.01, 56.8, 38.5, 38.2, 1.8, 2980, 81000, 3890, 1950, 0.02, 0.105, 0.145, 0.022),
  makeCompany('emamiltd', 'EMAMILTD', '531162', 'Emami Limited', 'Emami', 'Fast Moving Consumer Goods (FMCG)', 1974, 'Kolkata, West Bengal', 'Harsha V Agarwal', 'Niche FMCG leader with household brands Navratna, BoroPlus, Zandu, and Fair and Handsome.', 980, 0.265, 8, 0.038, 0.24, 0.02, 38.5, 7.8, 24.5, 1.2, 685, 30100, 850, 450, 0.02, 0.065, 0.095, 0.035),
  makeCompany('unitedspir', 'MCDOWELL-N', '532432', 'United Spirits Limited (Diageo India)', 'United Spirits', 'Fast Moving Consumer Goods (FMCG)', 1826, 'Bengaluru, Karnataka', 'Hina Nagarajan', 'India’s largest beverage alcohol company with flagship brands Johnnie Walker, McDowell’s, Smirnoff.', 3120, 0.168, 12, 0.024, 0.24, 0.01, 62.5, 12.8, 38.5, 0.6, 1450, 105400, 1580, 980, 0.03, 0.095, 0.145, 0.022),
  makeCompany('radico', 'RADICO', '532497', 'Radico Khaitan Limited', 'Radico Khaitan', 'Fast Moving Consumer Goods (FMCG)', 1943, 'New Delhi, Delhi', 'Lalit Khaitan', 'Leader in prestige and luxury spirits (Rampur Indian Single Malt, Jaisalmer Gin, Magic Moments).', 1180, 0.135, 24, 0.028, 0.24, 0.45, 78.5, 8.9, 38.5, 0.2, 2180, 29100, 2420, 1200, 0.04, 0.185, 0.285, 0.012),
  makeCompany('bikaji', 'BIKAJI', '543653', 'Bikaji Foods International Limited', 'Bikaji Foods', 'Fast Moving Consumer Goods (FMCG)', 1995, 'Bikaner, Rajasthan', 'Deepak Agarwal', 'Ethnic Indian snacks and sweets giant with iconic bhujia and namkeen distribution footprint.', 680, 0.148, 4, 0.025, 0.24, 0.01, 72.5, 14.2, 42.5, 0.1, 785, 19600, 920, 480, 0.05, 0.195, 0.285, 0.015),

  // 8. Telecommunication (6 companies)
  makeCompany('bhartiartl', 'BHARTIARTL', '532454', 'Bharti Airtel Limited', 'Bharti Airtel', 'Telecommunication', 1995, 'New Delhi, Delhi', 'Gopal Vittal', 'Global communications powerhouse with operations across 18 countries in South Asia and Africa.', 41500, 0.528, 4820, 0.195, 0.24, 1.85, 48.5, 8.2, 12.8, 0.6, 1720, 984000, 1850, 840, 0.04, 0.142, 0.68, 0.018),
  makeCompany('idea', 'IDEA', '532822', 'Vodafone Idea Limited', 'Vodafone Idea', 'Telecommunication', 1995, 'Mumbai, Maharashtra', 'Akshaya Moondra', 'Pan-India telecom operator with deep AGR liability overhang and high debt load.', 10920, 0.412, 5420, 0.265, 0.00, 14.50, 0.0, -0.8, 8.2, 0.0, 7.8, 54200, 19.1, 6.8, 0.01, 0.018, 0.05, 0.011),
  makeCompany('industower', 'INDUSTOWER', '534816', 'Indus Towers Limited', 'Indus Towers', 'Telecommunication', 2006, 'Gurugram, Haryana', 'Prachur Sah', 'Largest telecom tower infrastructure provider in India with over 230,000 macro towers.', 7580, 0.525, 385, 0.245, 0.24, 0.42, 14.2, 3.2, 5.8, 3.8, 385, 103700, 454, 168, 0.03, 0.085, 0.42, 0.025),
  makeCompany('tatacomm', 'TATACOMM', '500483', 'Tata Communications Limited', 'Tata Comm', 'Telecommunication', 1986, 'Mumbai, Maharashtra', 'A.S. Lakshminarayanan', 'Digital ecosystem enabler powering connected enterprises with submarine cables and cloud connectivity.', 5780, 0.205, 145, 0.082, 0.24, 2.10, 36.5, 9.8, 12.4, 0.8, 1920, 54700, 2175, 1540, 0.03, 0.092, -0.085, 0.015),
  makeCompany('hfcl', 'HFCL', '500183', 'HFCL Limited', 'HFCL', 'Telecommunication', 1987, 'New Delhi, Delhi', 'Mahendra Nahata', 'Manufacturer of optical fiber cables, 5G telecom equipment, and defense communication systems.', 1180, 0.138, 52, 0.035, 0.24, 0.38, 35.8, 4.2, 16.5, 0.2, 118, 17100, 158, 68, 0.04, 0.125, 0.16, 0.014),
  makeCompany('tejasnet', 'TEJASNET', '540595', 'Tejas Networks Limited', 'Tejas Networks', 'Telecommunication', 2000, 'Bengaluru, Karnataka', 'Anand Athreya', 'Tata enterprise designing and manufacturing carrier-grade optical and 4G/5G wireless networking gear.', 1480, 0.185, 45, 0.038, 0.24, 0.12, 48.5, 4.8, 26.5, 0.0, 1280, 21800, 1495, 680, 0.09, 2.45, 4.50, 0.012),

  // 9. Power & Utilities (9 companies)
  makeCompany('ntpc', 'NTPC', '532555', 'NTPC Limited', 'NTPC', 'Power & Utilities', 1975, 'New Delhi, Delhi', 'Gurdeep Singh', 'Largest power generation utility in India with installed capacity exceeding 76 GW and massive green pivot.', 48200, 0.285, 3450, 0.082, 0.24, 1.25, 16.5, 2.2, 9.8, 2.2, 395, 383000, 448, 208, 0.02, 0.075, 0.145, 0.038),
  makeCompany('powergrid', 'POWERGRID', '532898', 'Power Grid Corporation of India', 'Power Grid', 'Power & Utilities', 1989, 'Gurugram, Haryana', 'R.K. Tyagi', 'Central transmission utility carrying ~85% of India’s interstate power transfer.', 11850, 0.865, 2150, 0.285, 0.22, 1.45, 18.2, 3.4, 9.2, 3.5, 325, 302200, 366, 190, 0.01, 0.042, 0.065, 0.042),
  makeCompany('tatapower', 'TATAPOWER', '500400', 'The Tata Power Company Limited', 'Tata Power', 'Power & Utilities', 1915, 'Mumbai, Maharashtra', 'Praveen Sinha', 'Integrated power major spanning generation, transmission, retail distribution, and solar EPC.', 16420, 0.215, 1020, 0.065, 0.24, 1.65, 34.5, 4.2, 14.5, 0.5, 415, 132600, 494, 230, 0.03, 0.125, 0.185, 0.022),
  makeCompany('adanipower', 'ADANIPOWER', '533096', 'Adani Power Limited', 'Adani Power', 'Power & Utilities', 1996, 'Ahmedabad, Gujarat', 'S. B. Khyalia', 'Largest private thermal power producer in India with capacity of 15,250 MW.', 14850, 0.365, 780, 0.072, 0.24, 0.85, 11.2, 3.5, 7.8, 0.0, 620, 239100, 895, 320, 0.04, 0.285, 0.62, 0.018),
  makeCompany('jswenergy', 'JSWENERGY', '533148', 'JSW Energy Limited', 'JSW Energy', 'Power & Utilities', 1994, 'Mumbai, Maharashtra', 'Sharad Mahendra', 'Independent power producer with diversified energy basket across thermal, hydro, and wind.', 3450, 0.385, 480, 0.092, 0.24, 1.15, 54.2, 5.2, 18.5, 0.3, 680, 118800, 805, 340, 0.05, 0.195, 0.24, 0.025),
  makeCompany('nhpc', 'NHPC', '533098', 'NHPC Limited', 'NHPC', 'Power & Utilities', 1975, 'Faridabad, Haryana', 'R. K. Vishnoi', 'India’s premier hydropower generation company generating clean and peak-load electrical power.', 3120, 0.545, 320, 0.125, 0.24, 0.68, 22.4, 2.4, 12.8, 2.1, 92, 92400, 118, 48, 0.02, 0.055, 0.082, 0.035),
  makeCompany('torrentpower', 'TORNTPOWER', '532779', 'Torrent Power Limited', 'Torrent Power', 'Power & Utilities', 2004, 'Ahmedabad, Gujarat', 'Jinal Mehta', 'Integrated utility with distribution franchises in Ahmedabad, Surat, Dahej, and Bhiwandi.', 6980, 0.215, 185, 0.058, 0.24, 0.78, 32.5, 5.4, 14.2, 1.2, 1680, 80700, 2038, 650, 0.03, 0.142, 0.185, 0.021),
  makeCompany('cesc', 'CESC', '500084', 'CESC Limited', 'CESC', 'Power & Utilities', 1899, 'Kolkata, West Bengal', 'Brahmal Vasudevan', 'Flagship power utility of RP-Sanjiv Goenka Group supplying electricity across Kolkata and Howrah.', 3820, 0.245, 340, 0.085, 0.24, 1.35, 14.5, 1.8, 8.5, 2.8, 178, 23600, 210, 88, 0.02, 0.065, 0.085, 0.045),
  makeCompany('sjvn', 'SJVN', '533206', 'SJVN Limited', 'SJVN', 'Power & Utilities', 1988, 'Shimla, Himachal Pradesh', 'Bhupender Gupta', 'Mini-ratna PSU enterprise generating hydro, solar, and wind power across India and Nepal.', 890, 0.685, 145, 0.185, 0.24, 1.15, 28.5, 2.6, 12.8, 1.5, 118, 46300, 160, 68, 0.03, 0.125, 0.185, 0.048),

  // 10. Cement & Building Materials (7 companies)
  makeCompany('ultracemco', 'ULTRACEMCO', '532538', 'UltraTech Cement Limited', 'UltraTech', 'Cement & Building Materials', 1983, 'Mumbai, Maharashtra', 'K. C. Jhanwar', 'Flagship cement company of Aditya Birla Group and 3rd largest cement manufacturer globally (ex-China).', 20418, 0.185, 385, 0.055, 0.24, 0.28, 44.5, 4.8, 21.2, 0.6, 11450, 330600, 12140, 7800, 0.03, 0.115, 0.165, 0.022),
  makeCompany('ambujacem', 'AMBUJACEM', '500425', 'Ambuja Cements Limited', 'Ambuja Cement', 'Cement & Building Materials', 1981, 'Mumbai, Maharashtra', 'Ajay Kapur', 'Leading building materials company with strong presence across North, West, and East India.', 8890, 0.192, 65, 0.048, 0.24, 0.02, 38.5, 3.2, 18.5, 0.3, 580, 142800, 706, 404, 0.02, 0.085, 0.142, 0.035),
  makeCompany('shreecem', 'SHREECEM', '500387', 'Shree Cement Limited', 'Shree Cement', 'Cement & Building Materials', 1979, 'Kolkata, West Bengal', 'Neeraj Akhoury', 'Among the most cost-efficient and greenest cement manufacturers in Northern and Eastern India.', 5120, 0.215, 78, 0.062, 0.24, 0.12, 42.8, 4.5, 19.4, 0.4, 25800, 93100, 30737, 23500, 0.02, 0.075, 0.092, 0.028),
  makeCompany('acc', 'ACC', '500410', 'ACC Limited', 'ACC', 'Cement & Building Materials', 1936, 'Mumbai, Maharashtra', 'Ajay Kapur', 'One of India’s oldest and most trusted cement and ready-mix concrete manufacturers.', 5240, 0.142, 32, 0.045, 0.24, 0.01, 28.5, 2.8, 12.8, 0.4, 2180, 40900, 2785, 1780, 0.02, 0.052, 0.085, 0.024),
  makeCompany('dalmiabhar', 'DALBHARAT', '542211', 'Dalmia Bharat Limited', 'Dalmia Bharat', 'Cement & Building Materials', 1939, 'New Delhi, Delhi', 'Puneet Dalmia', 'Pioneer in super-specialty cements for oil wells, railway sleepers, and airstrips.', 3620, 0.178, 115, 0.065, 0.24, 0.32, 48.5, 2.6, 14.5, 0.5, 1840, 34500, 2428, 1680, 0.03, 0.092, -0.045, 0.018),
  makeCompany('astral', 'ASTRAL', '532830', 'Astral Limited', 'Astral', 'Cement & Building Materials', 1996, 'Ahmedabad, Gujarat', 'Sandeep Engineer', 'Market leader in CPVC plumbing pipes, drainage systems, adhesives, and sanitaryware.', 1580, 0.165, 12, 0.035, 0.24, 0.04, 82.5, 14.8, 42.5, 0.2, 1920, 51500, 2450, 1750, 0.04, 0.145, 0.185, 0.015),
  makeCompany('supremeind', 'SUPREMEIND', '509930', 'The Supreme Industries Limited', 'Supreme Ind', 'Cement & Building Materials', 1942, 'Mumbai, Maharashtra', 'M. P. Taparia', 'Leading plastics product manufacturer spanning piping, packaging, industrial, and consumer molding.', 2980, 0.155, 6, 0.031, 0.24, 0.01, 52.4, 9.8, 31.2, 0.7, 4850, 61600, 6040, 3650, 0.03, 0.125, 0.152, 0.018),

  // 11. Chemicals & Agrochemicals (9 companies)
  makeCompany('pidilitind', 'PIDILITIND', '500331', 'Pidilite Industries Limited', 'Pidilite', 'Chemicals & Agrochemicals', 1959, 'Mumbai, Maharashtra', 'Bharat Puri', 'Dominant adhesive and specialty chemical player (Fevicol, M-Seal, Dr. Fixit, Fevikwik).', 3450, 0.228, 14, 0.028, 0.24, 0.02, 78.5, 18.5, 48.2, 0.6, 3120, 158400, 3350, 2280, 0.03, 0.125, 0.185, 0.025),
  makeCompany('srf', 'SRF', '503806', 'SRF Limited', 'SRF', 'Chemicals & Agrochemicals', 1970, 'Gurugram, Haryana', 'Ashish Bharat Ram', 'Specialty fluorochemicals, refrigerants, technical textiles, and packaging films producer.', 3820, 0.215, 72, 0.055, 0.24, 0.38, 44.5, 6.2, 22.4, 0.4, 2350, 69600, 2697, 2050, 0.02, 0.045, -0.125, 0.014),
  makeCompany('upl', 'UPL', '512070', 'UPL Limited', 'UPL', 'Chemicals & Agrochemicals', 1969, 'Mumbai, Maharashtra', 'Jai Shroff', 'Global agricultural solutions and post-patent crop protection products enterprise.', 12480, 0.155, 780, 0.068, 0.24, 1.85, 24.5, 1.4, 9.8, 0.5, 545, 40900, 638, 448, 0.02, 0.015, -0.38, 0.012),
  makeCompany('piind', 'PIIND', '523642', 'PI Industries Limited', 'PI Industries', 'Chemicals & Agrochemicals', 1946, 'Gurugram, Haryana', 'Mayank Singhal', 'Leader in complex chemistry synthesis, contract research (CSM), and crop protection.', 2150, 0.265, 8, 0.032, 0.22, 0.01, 38.5, 7.8, 26.5, 0.3, 4150, 63000, 4600, 3300, 0.04, 0.165, 0.215, 0.032),
  makeCompany('deepakntr', 'DEEPAKNTR', '506401', 'Deepak Nitrite Limited', 'Deepak Nitrite', 'Chemicals & Agrochemicals', 1970, 'Vadodara, Gujarat', 'Deepak C. Mehta', 'Leading manufacturer of basic intermediates, fine chemicals, and phenolics.', 2180, 0.168, 12, 0.035, 0.24, 0.04, 39.5, 6.5, 24.5, 0.3, 2650, 36100, 3100, 1980, 0.03, 0.095, 0.115, 0.015),
  makeCompany('aartiind', 'AARTIIND', '524208', 'Aarti Industries Limited', 'Aarti Industries', 'Chemicals & Agrochemicals', 1984, 'Mumbai, Maharashtra', 'Rajendra V. Gogri', 'Specialty chemical manufacturer of benzene-based derivatives and pharmaceutical intermediates.', 1850, 0.155, 68, 0.048, 0.24, 0.78, 38.2, 3.8, 18.5, 0.3, 495, 17900, 769, 440, 0.02, 0.065, -0.14, 0.012),
  makeCompany('atul', 'ATUL', '500027', 'Atul Limited', 'Atul', 'Chemicals & Agrochemicals', 1947, 'Atul, Gujarat', 'Sunil S. Lalbhai', 'Pioneer of integrated chemical manufacturing in India with presence in life science chemicals.', 1380, 0.165, 14, 0.042, 0.24, 0.08, 48.5, 4.8, 28.5, 0.4, 6850, 20200, 8150, 5200, 0.02, 0.055, 0.082, 0.022),
  makeCompany('cleansci', 'CLEAN', '543318', 'Clean Science and Technology', 'Clean Science', 'Chemicals & Agrochemicals', 2003, 'Pune, Maharashtra', 'Ashok Boob', 'World leader in eco-friendly catalytic synthesis of specialty performance chemicals and antioxidants.', 245, 0.425, 2, 0.038, 0.24, 0.01, 54.2, 11.5, 38.5, 0.3, 1480, 15700, 1680, 1250, 0.04, 0.185, 0.245, 0.038),
  makeCompany('guifluoroc', 'FLUOROCHEM', '542812', 'Gujarat Fluorochemicals Limited', 'Gujarat Fluoro', 'Chemicals & Agrochemicals', 2018, 'Noida, Uttar Pradesh', 'Vivek Jain', 'India’s leading producer of fluoropolymers, fluoro-specialties, refrigerants, and battery chemicals.', 1280, 0.245, 58, 0.065, 0.24, 0.48, 62.5, 7.8, 32.5, 0.1, 4150, 45600, 4780, 2700, 0.03, 0.125, 0.165, 0.018),

  // 12. Capital Goods & Engineering (10 companies)
  makeCompany('lt', 'LT', '500510', 'Larsen & Toubro Limited', 'L&T', 'Capital Goods & Engineering', 1938, 'Mumbai, Maharashtra', 'S. N. Subrahmanyan', 'India’s premier EPC, heavy engineering, defense systems, infrastructure, and technology conglomerate.', 67079, 0.108, 920, 0.018, 0.25, 0.88, 36.5, 5.2, 22.8, 1.0, 3620, 497500, 3948, 2870, 0.04, 0.155, 0.115, 0.028),
  makeCompany('bel', 'BEL', '500049', 'Bharat Electronics Limited', 'BEL', 'Capital Goods & Engineering', 1954, 'Bengaluru, Karnataka', 'Manoj Jain', 'Navratna defence PSU enterprise supplying radars, electronic warfare systems, and avionics.', 8560, 0.285, 8, 0.015, 0.24, 0.01, 48.5, 12.8, 34.2, 0.8, 305, 222900, 340, 128, 0.05, 0.225, 0.315, 0.038),
  makeCompany('hal', 'HAL', '541154', 'Hindustan Aeronautics Limited', 'HAL', 'Capital Goods & Engineering', 1940, 'Bengaluru, Karnataka', 'C.B. Ananthakrishnan', 'Sole domestic military aircraft and helicopter design & manufacturing enterprise (Tejas, Prachand).', 14750, 0.325, 12, 0.024, 0.24, 0.01, 38.5, 10.5, 26.5, 0.9, 4450, 297500, 5675, 1768, 0.06, 0.185, 0.345, 0.045),
  makeCompany('siemens', 'SIEMENS', '500550', 'Siemens Limited', 'Siemens', 'Capital Goods & Engineering', 1957, 'Mumbai, Maharashtra', 'Sunil Mathur', 'Technology powerhouse focusing on industry 4.0, smart infrastructure, digital enterprise, and mobility.', 5820, 0.145, 15, 0.021, 0.24, 0.01, 88.5, 17.5, 58.2, 0.2, 7450, 265300, 8129, 3550, 0.04, 0.165, 0.215, 0.035),
  makeCompany('abb', 'ABB', '500002', 'ABB India Limited', 'ABB India', 'Capital Goods & Engineering', 1949, 'Bengaluru, Karnataka', 'Sanjeev Sharma', 'Electrification, robotics, automation, and motion technology leader in high-growth industries.', 3450, 0.185, 6, 0.018, 0.24, 0.01, 98.2, 24.5, 68.5, 0.4, 8250, 174800, 9149, 3915, 0.05, 0.245, 0.385, 0.028),
  makeCompany('thermax', 'THERMAX', '500411', 'Thermax Limited', 'Thermax', 'Capital Goods & Engineering', 1980, 'Pune, Maharashtra', 'Ashish Bhandari', 'Leading clean air, clean energy, and clean water solutions provider for heavy processing plants.', 2820, 0.098, 14, 0.024, 0.24, 0.04, 62.5, 9.2, 42.1, 0.3, 4980, 59300, 5834, 2520, 0.03, 0.185, 0.245, 0.018),
  makeCompany('cumminsind', 'CUMMINSIND', '500480', 'Cummins India Limited', 'Cummins India', 'Capital Goods & Engineering', 1962, 'Pune, Maharashtra', 'Ashwath Ram', 'Manufacturer of high-horsepower diesel engines, power generator sets, and emission control systems.', 2480, 0.198, 9, 0.022, 0.24, 0.01, 52.4, 14.8, 38.5, 1.1, 3750, 103900, 4192, 1660, 0.04, 0.215, 0.295, 0.032),
  makeCompany('bhel', 'BHEL', '500103', 'Bharat Heavy Electricals Limited', 'BHEL', 'Capital Goods & Engineering', 1964, 'New Delhi, Delhi', 'Koppu Sadashiv Murthy', 'Maharatna power and industrial equipment behemoth engineering thermal, hydro, and gas turbines.', 6850, 0.055, 145, 0.025, 0.24, 0.35, 74.5, 3.8, 38.5, 0.1, 285, 99200, 335, 115, 0.04, 0.185, 0.45, 0.018),
  makeCompany('cgpower', 'CGPOWER', '500093', 'CG Power and Industrial Solutions', 'CG Power', 'Capital Goods & Engineering', 1937, 'Mumbai, Maharashtra', 'Amar Kaul', 'Murugappa Group enterprise dominating industrial motors, railway propulsion, and semiconductor OSAT.', 2250, 0.155, 8, 0.021, 0.24, 0.01, 88.5, 24.5, 58.2, 0.1, 745, 113900, 810, 370, 0.05, 0.245, 0.315, 0.015),
  makeCompany('aiaeng', 'AIAENG', '532683', 'AIA Engineering Limited', 'AIA Engineering', 'Capital Goods & Engineering', 1990, 'Ahmedabad, Gujarat', 'Bhadresh K. Shah', 'Global leader in high-chromium grinding media solutions for mining and cement industries.', 1280, 0.245, 4, 0.024, 0.24, 0.01, 32.5, 5.8, 22.4, 0.4, 4450, 41900, 4980, 3350, 0.02, 0.085, 0.125, 0.035),

  // 13. Infrastructure & Construction (7 companies)
  makeCompany('gmrairport', 'GMRAIRPORT', '532754', 'GMR Airports Infrastructure Limited', 'GMR Airports', 'Infrastructure & Construction', 1996, 'New Delhi, Delhi', 'G. M. Rao', 'Premier airport developer and operator managing Delhi, Hyderabad, and Goa international terminals.', 2650, 0.325, 780, 0.145, 0.00, 4.80, 0.0, 9.8, 18.5, 0.0, 92, 97800, 104, 52, 0.04, 0.215, 0.05, 0.015),
  makeCompany('irb', 'IRB', '532947', 'IRB Infrastructure Developers Limited', 'IRB Infra', 'Infrastructure & Construction', 1998, 'Mumbai, Maharashtra', 'Virendra D. Mhaiskar', 'Pioneer in Build-Operate-Transfer (BOT) highway projects and private highway concessionaire.', 2150, 0.445, 420, 0.165, 0.24, 2.85, 48.5, 3.2, 11.4, 0.5, 58, 35000, 78, 31, 0.03, 0.145, 0.185, 0.021),
  makeCompany('nbcc', 'NBCC', '534309', 'NBCC (India) Limited', 'NBCC', 'Infrastructure & Construction', 1960, 'New Delhi, Delhi', 'K.P. Mahadevaswamy', 'Navratna PSU PMC project management consultant for redevelopment and government housing.', 2820, 0.065, 6, 0.012, 0.24, 0.01, 62.5, 9.8, 42.5, 0.4, 118, 31800, 140, 45, 0.05, 0.285, 0.38, 0.035),
  makeCompany('knrcon', 'KNRCON', '532942', 'KNR Constructions Limited', 'KNR Constr', 'Infrastructure & Construction', 1995, 'Hyderabad, Telangana', 'K. Narasimha Reddy', 'Premier infrastructure project development company executing highways, flyovers, and irrigation.', 1180, 0.185, 28, 0.042, 0.24, 0.28, 18.5, 2.9, 9.8, 0.2, 345, 9700, 412, 235, 0.02, 0.082, 0.115, 0.012),
  makeCompany('pnc', 'PNCINFRA', '539150', 'PNC Infratech Limited', 'PNC Infra', 'Infrastructure & Construction', 1999, 'Agra, Uttar Pradesh', 'Pradeep Kumar Jain', 'End-to-end highway and expressway construction EPC major with strong order execution.', 2050, 0.145, 48, 0.038, 0.24, 0.45, 14.5, 1.8, 7.8, 0.2, 445, 11400, 574, 305, 0.03, 0.115, 0.165, 0.015),
  makeCompany('ncc', 'NCC', '500294', 'NCC Limited', 'NCC', 'Infrastructure & Construction', 1978, 'Hyderabad, Telangana', 'A. A. V. Ranga Raju', 'Diversified construction company executing buildings, water pipelines, transport and power EPC.', 4820, 0.098, 145, 0.022, 0.24, 0.42, 22.4, 2.4, 10.5, 0.8, 315, 19800, 364, 135, 0.04, 0.185, 0.245, 0.014),
  makeCompany('engineersin', 'ENGINERSIN', '532178', 'Engineers India Limited', 'EIL', 'Infrastructure & Construction', 1965, 'New Delhi, Delhi', 'Vartika Shukla', 'Navratna engineering consultancy and EPC contractor for oil & gas, green hydrogen and petrochem.', 980, 0.115, 4, 0.018, 0.24, 0.01, 28.5, 4.2, 16.5, 1.5, 245, 13800, 290, 120, 0.03, 0.125, 0.185, 0.048),

  // 14. Consumer Durables & Electronics (8 companies)
  makeCompany('havells', 'HAVELLS', '517354', 'Havells India Limited', 'Havells', 'Consumer Durables & Electronics', 1958, 'Noida, Uttar Pradesh', 'Anil Rai Gupta', 'Fast moving electrical goods (FMEG) major with brands Havells, Lloyd, Crabtree, and Standard.', 5620, 0.118, 28, 0.025, 0.24, 0.01, 74.5, 14.8, 46.2, 0.5, 1780, 111500, 2106, 1260, 0.04, 0.165, 0.245, 0.018),
  makeCompany('dixon', 'DIXON', '540699', 'Dixon Technologies (India) Limited', 'Dixon Tech', 'Consumer Durables & Electronics', 1993, 'Noida, Uttar Pradesh', 'Atul B. Lall', 'India’s largest electronic manufacturing services (EMS) player producing smartphones, TVs, and appliances.', 7450, 0.042, 38, 0.015, 0.24, 0.18, 115.0, 32.5, 62.5, 0.1, 14850, 88800, 15900, 4900, 0.08, 0.850, 1.050, 0.008),
  makeCompany('voltas', 'VOLTAS', '500575', 'Voltas Limited', 'Voltas', 'Consumer Durables & Electronics', 1954, 'Mumbai, Maharashtra', 'Pradeep Bakshi', 'Tata enterprise dominating room air conditioner category and electro-mechanical project execution.', 4250, 0.078, 18, 0.015, 0.24, 0.04, 78.2, 9.8, 48.5, 0.3, 1720, 56900, 1934, 820, 0.05, 0.325, 0.42, 0.015),
  makeCompany('polycab', 'POLYCAB', '542652', 'Polycab India Limited', 'Polycab', 'Consumer Durables & Electronics', 1968, 'Mumbai, Maharashtra', 'Inder T. Jaisinghani', 'Market leader in wires & cables with extensive distribution and expanding FMEG product suite.', 5820, 0.138, 18, 0.018, 0.24, 0.02, 48.5, 11.2, 32.5, 0.5, 6650, 99800, 7350, 4620, 0.04, 0.215, 0.285, 0.014),
  makeCompany('bluestar', 'BLUESTARCO', '500067', 'Blue Star Limited', 'Blue Star', 'Consumer Durables & Electronics', 1943, 'Mumbai, Maharashtra', 'B. Thiagarajan', 'Leading air conditioning and commercial refrigeration company with strong corporate brand recall.', 3120, 0.075, 14, 0.018, 0.24, 0.18, 68.5, 12.4, 38.5, 0.4, 1840, 37800, 2180, 790, 0.05, 0.265, 0.385, 0.012),
  makeCompany('crompton', 'CROMPTON', '539876', 'Crompton Greaves Consumer Electricals', 'Crompton', 'Consumer Durables & Electronics', 2015, 'Mumbai, Maharashtra', 'Promeet Ghosh', 'Consumer electricals leader in ceiling fans, domestic pumps, and LED lighting solutions.', 1890, 0.105, 24, 0.025, 0.24, 0.32, 42.5, 6.8, 26.5, 0.8, 385, 24800, 484, 260, 0.03, 0.115, 0.145, 0.025),
  makeCompany('amber', 'AMBER', '540902', 'Amber Enterprises India Limited', 'Amber Ent', 'Consumer Durables & Electronics', 1990, 'Gurugram, Haryana', 'Jasbir Singh', 'Key contract manufacturer of room air conditioners, mobility applications, and electronics.', 1680, 0.078, 38, 0.031, 0.24, 0.65, 68.5, 8.2, 28.5, 0.0, 5890, 19800, 6850, 2850, 0.06, 0.345, 0.485, 0.012),
  makeCompany('kei', 'KEI', '517569', 'KEI Industries Limited', 'KEI Industries', 'Consumer Durables & Electronics', 1968, 'New Delhi, Delhi', 'Anil Gupta', 'Manufacturer of extra-high voltage cables, instrumentation wires, and turnkey transmission EPC.', 2280, 0.108, 12, 0.018, 0.24, 0.02, 54.5, 11.2, 38.5, 0.1, 4150, 37400, 4980, 2780, 0.04, 0.185, 0.225, 0.014),

  // 15. Real Estate & Urban Development (8 companies)
  makeCompany('dlf', 'DLF', '532868', 'DLF Limited', 'DLF', 'Real Estate & Urban Dev', 1946, 'Gurugram, Haryana', 'Ashok Kumar Tyagi', 'India’s largest commercial and luxury residential real estate developer with supreme land bank.', 2480, 0.385, 48, 0.028, 0.24, 0.04, 68.5, 5.8, 38.5, 0.6, 845, 209100, 967, 540, 0.04, 0.245, 0.38, 0.048),
  makeCompany('lodha', 'LODHA', '543287', 'Macrotech Developers Limited', 'Lodha', 'Real Estate & Urban Dev', 1995, 'Mumbai, Maharashtra', 'Abhishek Lodha', 'Premier residential developer in Mumbai Metropolitan Region and expanding into Pune & Bengaluru.', 3450, 0.325, 95, 0.021, 0.24, 0.24, 48.5, 6.2, 28.5, 0.2, 1280, 127600, 1630, 980, 0.05, 0.215, 0.45, 0.022),
  makeCompany('godrejprop', 'GODREJPROP', '533150', 'Godrej Properties Limited', 'Godrej Prop', 'Real Estate & Urban Dev', 1990, 'Mumbai, Maharashtra', 'Gaurav Pandey', 'Fast-growing real estate developer leveraging strong Godrej brand across NCR, MMR, and Bengaluru.', 1820, 0.285, 42, 0.018, 0.24, 0.38, 72.5, 7.8, 42.5, 0.0, 2890, 80400, 3400, 1680, 0.06, 0.350, 0.68, 0.025),
  makeCompany('oberoirlty', 'OBEROIRLTY', '533273', 'Oberoi Realty Limited', 'Oberoi Realty', 'Real Estate & Urban Dev', 1998, 'Mumbai, Maharashtra', 'Vikas Oberoi', 'High-margin luxury developer operating in Mumbai with flawless balance sheet discipline.', 1450, 0.545, 18, 0.035, 0.24, 0.12, 38.5, 4.8, 22.4, 0.4, 1850, 67200, 2180, 1080, 0.03, 0.185, 0.29, 0.035),
  makeCompany('prestige', 'PRESTIGE', '533274', 'Prestige Estates Projects Limited', 'Prestige', 'Real Estate & Urban Dev', 1986, 'Bengaluru, Karnataka', 'Irfan Razack', 'South India real estate powerhouse expanding into hospitality, commercial malls, and MMR luxury.', 2890, 0.295, 210, 0.045, 0.24, 0.85, 42.5, 4.2, 18.5, 0.1, 1680, 67300, 2074, 780, 0.04, 0.225, 0.28, 0.018),
  makeCompany('brigade', 'BRIGADE', '532929', 'Brigade Enterprises Limited', 'Brigade Ent', 'Real Estate & Urban Dev', 1986, 'Bengaluru, Karnataka', 'Pavitra Shankar', 'Leading real estate developer spanning residential, Grade-A commercial tech parks, and hospitality.', 1280, 0.285, 68, 0.042, 0.24, 0.65, 48.5, 5.8, 22.4, 0.2, 1280, 29800, 1420, 780, 0.04, 0.215, 0.28, 0.015),
  makeCompany('phoenixltd', 'PHOENIXLTD', '503100', 'The Phoenix Mills Limited', 'Phoenix Mills', 'Real Estate & Urban Dev', 1905, 'Mumbai, Maharashtra', 'Shishir Shrivastava', 'Pioneer of destination retail consumption centers and mega shopping malls (Phoenix Marketcity).', 980, 0.585, 85, 0.075, 0.24, 0.42, 44.5, 5.4, 21.2, 0.2, 1780, 63600, 2040, 1180, 0.05, 0.245, 0.315, 0.022),
  makeCompany('sobha', 'SOBHA', '532784', 'Sobha Limited', 'Sobha', 'Real Estate & Urban Dev', 1995, 'Bengaluru, Karnataka', 'Jagadish Nangineni', 'Self-reliant backward integrated construction and luxury real estate developer.', 890, 0.145, 48, 0.028, 0.24, 0.48, 48.5, 5.2, 21.5, 0.2, 1780, 16800, 2220, 810, 0.03, 0.165, 0.185, 0.015),

  // 16. Retail & E-Commerce (7 companies)
  makeCompany('dmart', 'DMART', '540376', 'Avenue Supermarts Limited', 'DMart', 'Retail & E-Commerce', 2002, 'Mumbai, Maharashtra', 'Neville Noronha', 'India’s most profitable value retail chain operating DMart supermarkets under ownership model.', 13850, 0.088, 18, 0.018, 0.24, 0.01, 98.5, 14.8, 58.2, 0.0, 4280, 278500, 5484, 3620, 0.04, 0.165, 0.142, 0.008),
  makeCompany('trent', 'TRENT', '500251', 'Trent Limited', 'Trent', 'Retail & E-Commerce', 1998, 'Mumbai, Maharashtra', 'P. Venkatesalu', 'Tata Group retail powerhouse operating fast-fashion phenomena Zudio, Westside, and Star Bazaar.', 4350, 0.168, 68, 0.045, 0.24, 0.15, 142.0, 38.5, 78.5, 0.1, 6980, 248100, 8345, 2020, 0.08, 0.525, 0.985, 0.009),
  makeCompany('zomato', 'ZOMATO', '543320', 'Zomato Limited (Eternal)', 'Zomato', 'Retail & E-Commerce', 2008, 'Gurugram, Haryana', 'Deepinder Goyal', 'Online food delivery and hyper-growth quick commerce leader (Blinkit).', 4820, 0.085, 8, 0.024, 0.22, 0.01, 118.0, 12.8, 68.5, 0.0, 268, 237400, 298, 90, 0.09, 0.685, 2.45, 0.015),
  makeCompany('naukri', 'NAUKRI', '532777', 'Info Edge (India) Limited', 'Info Edge', 'Retail & E-Commerce', 1995, 'Noida, Uttar Pradesh', 'Hitesh Oberoi', 'Premier internet company operating Naukri.com, 99acres, Jeevansathi, and Shiksha.', 780, 0.385, 4, 0.038, 0.24, 0.01, 74.5, 4.8, 38.5, 0.4, 7850, 101800, 8750, 4200, 0.02, 0.115, 0.145, 0.085),
  makeCompany('nykaa', 'NYKAA', '543384', 'FSN E-Commerce Ventures Limited', 'Nykaa', 'Retail & E-Commerce', 2012, 'Mumbai, Maharashtra', 'Falguni Nayar', 'Leading omnichannel beauty, personal care, and curated fashion destination in India.', 1980, 0.062, 28, 0.028, 0.24, 0.18, 168.0, 18.5, 78.5, 0.0, 192, 54900, 228, 138, 0.05, 0.245, 0.48, 0.012),
  makeCompany('paytm', 'PAYTM', '543396', 'One97 Communications Limited', 'Paytm', 'Retail & E-Commerce', 2000, 'Noida, Uttar Pradesh', 'Vijay Shekhar Sharma', 'Pioneer in mobile payments, QR codes, soundboxes, and merchant financial services.', 1680, -0.125, 18, 0.055, 0.00, 0.02, 0.0, 3.2, -18.5, 0.0, 785, 49900, 998, 310, -0.05, -0.325, -0.65, 0.025),
  makeCompany('shoppers', 'SHOPERSTOP', '532638', 'Shoppers Stop Limited', 'Shoppers Stop', 'Retail & E-Commerce', 1991, 'Mumbai, Maharashtra', 'Kavindra Mishra', 'Pioneering premier department store chain and multi-brand beauty destination.', 1120, 0.165, 62, 0.095, 0.24, 1.45, 48.5, 8.2, 12.8, 0.0, 685, 7550, 890, 620, 0.02, 0.075, -0.12, 0.015),

  // 17. Aviation & Defence (6 companies)
  makeCompany('indigo', 'INDIGO', '539448', 'InterGlobe Aviation Limited', 'IndiGo', 'Aviation & Defence', 2006, 'Gurugram, Haryana', 'Pieter Elbers', 'India’s largest passenger airline with over 60% domestic passenger market share and robust fleet.', 18450, 0.185, 820, 0.085, 0.24, 2.85, 18.5, 12.5, 7.8, 0.0, 4450, 171800, 4995, 2480, 0.04, 0.165, 0.145, 0.025),
  makeCompany('mazdock', 'MAZDOCK', '543237', 'Mazagon Dock Shipbuilders Limited', 'Mazagon Dock', 'Aviation & Defence', 1934, 'Mumbai, Maharashtra', 'Sanjeev Singhal', 'Nation’s premier defence shipyard building stealth frigates, destroyers, and Scorpene submarines.', 3120, 0.245, 4, 0.015, 0.24, 0.01, 38.5, 9.8, 24.5, 0.9, 4150, 83700, 5860, 1720, 0.06, 0.285, 0.42, 0.048),
  makeCompany('cochinship', 'COCHINSHIP', '540678', 'Cochin Shipyard Limited', 'Cochin Ship', 'Aviation & Defence', 1972, 'Kochi, Kerala', 'Madhu S. Nair', 'Largest shipbuilding and maintenance facility in India, builder of IAC Vikrant.', 1450, 0.215, 6, 0.021, 0.24, 0.01, 48.5, 9.2, 28.5, 0.7, 1680, 44200, 2979, 490, 0.07, 0.385, 0.62, 0.042),
  makeCompany('bdl', 'BDL', '541143', 'Bharat Dynamics Limited', 'BDL', 'Aviation & Defence', 1970, 'Hyderabad, Telangana', 'A. Madhavarao', 'Sole manufacturer of guided missiles, underwater torpedoes, and counter-measure dispensing systems.', 1180, 0.265, 4, 0.018, 0.24, 0.01, 52.4, 11.5, 34.2, 0.5, 1280, 46900, 1795, 520, 0.05, 0.225, 0.28, 0.035),
  makeCompany('grse', 'GRSE', '542011', 'Garden Reach Shipbuilders & Engineers', 'GRSE', 'Aviation & Defence', 1884, 'Kolkata, West Bengal', 'P. R. Hari', 'Premier warship builder for Indian Navy and Coast Guard specializing in anti-submarine warfare corvettes.', 1020, 0.195, 2, 0.015, 0.24, 0.01, 42.5, 8.9, 26.5, 0.6, 1780, 20400, 2834, 780, 0.05, 0.345, 0.485, 0.035),
  makeCompany('astramicro', 'ASTRAMICRO', '532493', 'Astra Microwave Products Limited', 'Astra Microwave', 'Aviation & Defence', 1991, 'Hyderabad, Telangana', 'S. G. Reddy', 'Designer and manufacturer of sub-systems for RF and microwave systems utilized in defense radars.', 285, 0.225, 8, 0.028, 0.24, 0.18, 54.2, 7.8, 31.5, 0.3, 895, 8500, 1020, 540, 0.04, 0.195, 0.285, 0.015),

  // 18. Textiles & Apparels (6 companies)
  makeCompany('pageind', 'PAGEIND', '532827', 'Page Industries Limited', 'Page Ind', 'Textiles & Apparels', 1994, 'Bengaluru, Karnataka', 'V. S. Ganesh', 'Exclusive licensee of JOCKEY International in India and Speedo swimwear brand distributor.', 1280, 0.198, 12, 0.024, 0.24, 0.04, 64.5, 24.5, 38.5, 1.2, 44800, 49950, 49500, 33100, 0.02, 0.085, 0.125, 0.021),
  makeCompany('kprmill', 'KPRMILL', '532889', 'K.P.R. Mill Limited', 'KPR Mill', 'Textiles & Apparels', 2003, 'Coimbatore, Tamil Nadu', 'P. Nataraj', 'Integrated apparel and yarn manufacturer with green power and ethanol co-generation.', 1680, 0.205, 28, 0.038, 0.24, 0.24, 38.5, 7.8, 22.4, 0.4, 945, 32300, 1020, 680, 0.03, 0.145, 0.185, 0.018),
  makeCompany('trident', 'TRIDENT', '521064', 'Trident Limited', 'Trident', 'Textiles & Apparels', 1990, 'Ludhiana, Punjab', 'Deepak Nanda', 'Global supplier of terry towels, bed linen, wheat-straw based paper, and chemicals.', 1820, 0.142, 38, 0.045, 0.24, 0.45, 32.5, 3.8, 14.8, 0.9, 38, 19400, 52, 32, 0.02, 0.065, 0.042, 0.015),
  makeCompany('raymond', 'RAYMOND', '500330', 'Raymond Limited', 'Raymond', 'Textiles & Apparels', 1925, 'Mumbai, Maharashtra', 'Gautam Hari Singhania', 'Iconic Indian suiting, lifestyle apparel, real estate, and engineering components company.', 1450, 0.155, 45, 0.035, 0.24, 0.52, 28.5, 4.2, 13.5, 0.6, 1780, 11850, 3480, 1520, 0.03, 0.125, 0.24, 0.018),
  makeCompany('arvind', 'ARVIND', '500101', 'Arvind Limited', 'Arvind', 'Textiles & Apparels', 1931, 'Ahmedabad, Gujarat', 'Sanjay Lalbhai', 'Global leader in denim fabrics, advanced materials, and environmental tech solutions.', 2050, 0.108, 38, 0.038, 0.24, 0.48, 21.4, 2.6, 10.8, 1.4, 385, 10050, 420, 240, 0.02, 0.075, 0.115, 0.015),
  makeCompany('vardhman', 'VTL', '502986', 'Vardhman Textiles Limited', 'Vardhman Text', 'Textiles & Apparels', 1965, 'Ludhiana, Punjab', 'S. P. Oswal', 'Leading yarn and greige fabric exporter with multi-location automated spinning mills.', 2480, 0.128, 48, 0.045, 0.24, 0.35, 18.5, 1.8, 9.8, 1.1, 485, 14000, 545, 380, 0.02, 0.055, 0.082, 0.022),

  // 19. Renewable Energy (6 companies)
  makeCompany('suzlon', 'SUZLON', '532667', 'Suzlon Energy Limited', 'Suzlon', 'Renewable Energy', 1995, 'Pune, Maharashtra', 'J. P. Chalasani', 'India’s pioneer wind turbine manufacturer offering end-to-end wind power solutions & turnkey EPC.', 2150, 0.152, 22, 0.025, 0.24, 0.05, 68.5, 14.5, 38.5, 0.0, 68, 92800, 86, 21, 0.06, 0.485, 1.25, 0.025),
  makeCompany('adanigreen', 'ADANIGREEN', '541450', 'Adani Green Energy Limited', 'Adani Green', 'Renewable Energy', 2015, 'Ahmedabad, Gujarat', 'Vneet S. Jaain', 'Largest renewable energy generation company in India with locked-in portfolio of 20+ GW.', 2850, 0.685, 1450, 0.215, 0.24, 6.20, 145.0, 24.5, 34.5, 0.0, 1680, 266100, 2174, 815, 0.04, 0.285, 0.42, 0.035),
  makeCompany('inoxwind', 'INOXWIND', '539083', 'Inox Wind Limited', 'Inox Wind', 'Renewable Energy', 2009, 'Noida, Uttar Pradesh', 'Devansh Jain', 'Fully integrated wind energy solutions provider with advanced 3.3 MW turbine technology.', 780, 0.185, 38, 0.035, 0.24, 0.18, 48.5, 5.8, 22.4, 0.0, 195, 25400, 250, 52, 0.08, 0.685, 1.85, 0.018),
  makeCompany('waaree', 'WAAREEENER', '544277', 'Waaree Energies Limited', 'Waaree Energies', 'Renewable Energy', 1989, 'Mumbai, Maharashtra', 'Hitesh Doshi', 'India’s largest solar PV module manufacturer with 12 GW operational manufacturing capacity.', 3450, 0.198, 28, 0.032, 0.24, 0.12, 54.2, 12.8, 28.5, 0.0, 3120, 89600, 3740, 2350, 0.07, 0.425, 0.685, 0.015),
  makeCompany('premierene', 'PREMIERENE', '544240', 'Premier Energies Limited', 'Premier Energies', 'Renewable Energy', 1995, 'Hyderabad, Telangana', 'Chiranjeev Saluja', 'Integrated solar cell and module manufacturer and turnkey ground-mounted solar power EPC.', 1580, 0.225, 18, 0.038, 0.24, 0.22, 48.5, 8.9, 24.5, 0.0, 1180, 53200, 1340, 840, 0.06, 0.850, 1.45, 0.012),
  makeCompany('sterlingwil', 'SWSOLAR', '542760', 'Sterling and Wilson Renewable Energy', 'Sterling Wilson', 'Renewable Energy', 2017, 'Mumbai, Maharashtra', 'Amit Jain', 'Leading global solar EPC solutions provider operating across 29 countries in Middle East, Africa & India.', 1850, 0.085, 24, 0.018, 0.24, 0.35, 68.5, 9.2, 28.5, 0.0, 580, 13500, 828, 290, 0.04, 0.650, 1.15, 0.014),

  // 20. Tyres & Rubber Products (5 companies)
  makeCompany('mrf', 'MRF', '500290', 'MRF Limited', 'MRF', 'Tyres & Rubber Products', 1946, 'Chennai, Tamil Nadu', 'Rahul Mammen Mappillai', 'India’s largest tyre manufacturer commanding premium position across 2W, passenger cars & commercial vehicles.', 7120, 0.165, 82, 0.045, 0.24, 0.18, 24.5, 3.4, 12.8, 0.2, 138500, 58740, 151445, 102000, 0.03, 0.085, 0.142, 0.015),
  makeCompany('apollotyre', 'APOLLOTYRE', '500877', 'Apollo Tyres Limited', 'Apollo Tyres', 'Tyres & Rubber Products', 1972, 'Gurugram, Haryana', 'Neeraj Kanwar', 'Leading international tyre manufacturer with strong market share in India and Europe (Vredestein).', 6480, 0.158, 125, 0.052, 0.24, 0.45, 18.5, 2.2, 8.9, 1.0, 515, 32700, 585, 365, 0.02, 0.065, 0.085, 0.014),
  makeCompany('balkrisind', 'BALKRISIND', '502355', 'Balkrishna Industries Limited', 'Balkrishna Ind', 'Tyres & Rubber Products', 1987, 'Mumbai, Maharashtra', 'Arvind Poddar', 'Global leader in Off-Highway Tyres (OHT) for agriculture, mining, and industrial machinery.', 2780, 0.245, 24, 0.058, 0.24, 0.32, 34.5, 6.2, 18.5, 0.7, 2890, 55900, 3345, 2180, 0.03, 0.115, 0.225, 0.028),
  makeCompany('ceat', 'CEATLTD', '500878', 'CEAT Limited', 'CEAT', 'Tyres & Rubber Products', 1958, 'Mumbai, Maharashtra', 'Arnab Banerjee', 'Flagship tyre enterprise of RPG Enterprises leading in 2-wheelers and truck-bus radials.', 3240, 0.125, 68, 0.042, 0.24, 0.52, 19.8, 2.6, 9.8, 1.1, 2820, 11400, 3200, 1920, 0.03, 0.092, 0.115, 0.012),
  makeCompany('jktyre', 'JKTYRE', '530007', 'JK Tyre & Industries Limited', 'JK Tyre', 'Tyres & Rubber Products', 1974, 'New Delhi, Delhi', 'Raghupati Singhania', 'Pioneer of radial tyre technology in India and market leader in truck-bus radial category.', 3890, 0.118, 95, 0.038, 0.24, 0.85, 14.5, 1.8, 7.2, 1.2, 415, 10800, 554, 345, 0.02, 0.075, 0.065, 0.011),

  // 21. Logistics & Supply Chain (6 companies)
  makeCompany('concor', 'CONCOR', '531349', 'Container Corporation of India', 'CONCOR', 'Logistics & Supply Chain', 1988, 'New Delhi, Delhi', 'Sanjay Swarup', 'Market leader in containerized rail freight transport and inland container depot (ICD) network.', 2350, 0.245, 18, 0.065, 0.24, 0.01, 38.5, 4.8, 19.8, 1.2, 945, 57600, 1177, 680, 0.03, 0.095, 0.145, 0.045),
  makeCompany('delhivery', 'DELHIVERY', '543529', 'Delhivery Limited', 'Delhivery', 'Logistics & Supply Chain', 2011, 'Gurugram, Haryana', 'Sahil Barua', 'Largest fully-integrated supply chain and parcel logistics player powered by proprietary automated hubs.', 2280, 0.062, 18, 0.068, 0.00, 0.08, 125.0, 3.8, 24.5, 0.0, 395, 29200, 488, 340, 0.04, 0.145, 0.85, 0.025),
  makeCompany('bluedart', 'BLUEDART', '526139', 'Blue Dart Express Limited', 'Blue Dart', 'Logistics & Supply Chain', 1983, 'Mumbai, Maharashtra', 'Balfour Manuel', 'South Asia’s premier express air and integrated transportation and distribution company.', 1380, 0.108, 28, 0.048, 0.24, 0.28, 48.5, 7.8, 21.4, 0.5, 6850, 16250, 8400, 5400, 0.02, 0.075, 0.045, 0.018),
  makeCompany('allcargo', 'ALLCARGO', '532749', 'Allcargo Logistics Limited', 'Allcargo', 'Logistics & Supply Chain', 1993, 'Mumbai, Maharashtra', 'Shashi Kiran Shetty', 'Global LCL consolidation leader operating in over 180 countries across multimodal logistics.', 3450, 0.068, 45, 0.032, 0.24, 0.42, 28.5, 2.2, 11.5, 0.8, 285, 7000, 395, 240, 0.02, 0.045, -0.15, 0.015),
  makeCompany('tciexp', 'TCIEXP', '540212', 'TCI Express Limited', 'TCI Express', 'Logistics & Supply Chain', 2016, 'Gurugram, Haryana', 'Chander Agarwal', 'Time-definite express door-to-door cargo delivery company with hub-and-spoke distribution network.', 320, 0.155, 2, 0.028, 0.24, 0.01, 32.5, 5.8, 21.4, 0.8, 1080, 4150, 1420, 950, 0.03, 0.065, 0.082, 0.018),
  makeCompany('aegisvopak', 'AEGISLOG', '500003', 'Aegis Logistics Limited', 'Aegis Logistics', 'Logistics & Supply Chain', 1956, 'Mumbai, Maharashtra', 'Raj Chandaria', 'Leader in handling, storage, and distribution of liquid chemicals, LPG, and bulk clean fuels.', 580, 0.385, 28, 0.052, 0.24, 0.38, 48.5, 8.9, 24.5, 0.8, 845, 29650, 960, 340, 0.04, 0.185, 0.295, 0.025),

  // 22. Media & Entertainment (6 companies)
  makeCompany('suntv', 'SUNTV', '532733', 'Sun TV Network Limited', 'Sun TV', 'Media & Entertainment', 1993, 'Chennai, Tamil Nadu', 'Kalanithi Maran', 'Dominant television network in South India with 33 channels, Sun NXT OTT, and FM stations.', 1120, 0.625, 4, 0.035, 0.24, 0.01, 17.5, 3.2, 9.8, 2.2, 780, 30700, 920, 560, 0.02, 0.055, 0.068, 0.085),
  makeCompany('zeel', 'ZEEL', '505537', 'Zee Entertainment Enterprises', 'ZEEL', 'Media & Entertainment', 1992, 'Mumbai, Maharashtra', 'Punit Goenka', 'Pioneer of Indian broadcast television industry reaching 1.3 billion viewers worldwide.', 2180, 0.125, 18, 0.045, 0.24, 0.05, 32.5, 1.4, 11.8, 0.0, 128, 12300, 299, 115, 0.01, 0.015, -0.45, 0.025),
  makeCompany('pvrinox', 'PVRINOX', '532689', 'PVR INOX Limited', 'PVR INOX', 'Media & Entertainment', 1997, 'Gurugram, Haryana', 'Ajay Bijli', 'Largest film exhibition company in India operating over 1,700 cinema screens across 114 cities.', 1680, 0.185, 185, 0.165, 0.00, 1.85, 0.0, 1.8, 8.5, 0.0, 1380, 13500, 1829, 1200, 0.03, 0.085, -0.05, 0.015),
  makeCompany('saregama', 'SAREGAMA', '532163', 'Saregama India Limited', 'Saregama', 'Media & Entertainment', 1901, 'Kolkata, West Bengal', 'Vikram Mehra', 'India’s oldest music label owning the largest catalog of Indian music and Carvaan audio players.', 225, 0.345, 2, 0.025, 0.24, 0.01, 48.5, 7.8, 28.5, 0.8, 485, 9350, 595, 330, 0.04, 0.185, 0.225, 0.045),
  makeCompany('tipsind', 'TIPSINDLTD', '532375', 'Tips Music Limited', 'Tips Music', 'Media & Entertainment', 1975, 'Mumbai, Maharashtra', 'Kumar Taurani', 'Leading music label with extensive Hindi, Punjabi, and regional digital music streaming rights.', 78, 0.725, 1, 0.015, 0.24, 0.01, 54.2, 28.5, 38.2, 1.4, 685, 8780, 810, 380, 0.05, 0.285, 0.365, 0.055),
  makeCompany('network18', 'NETWORK18', '532798', 'Network18 Media & Investments', 'Network18', 'Media & Entertainment', 1996, 'Mumbai, Maharashtra', 'Rahul Joshi', 'Reliance media arm operating CNBC-TV18, CNN-News18, News18, and Moneycontrol.', 1780, 0.045, 68, 0.038, 0.00, 0.85, 0.0, 2.4, 18.5, 0.0, 88, 9200, 135, 74, 0.02, 0.045, -0.65, 0.018),

  // 23. Fertilizers & Agriculture (5 companies)
  makeCompany('coromandel', 'COROMANDEL', '506395', 'Coromandel International Limited', 'Coromandel', 'Fertilizers & Agriculture', 1961, 'Hyderabad, Telangana', 'Sankarasubramanian S.', 'India’s pioneering agricultural solutions provider (Gromor fertilizers, crop protection, retail).', 6850, 0.115, 24, 0.021, 0.24, 0.05, 28.5, 4.8, 18.5, 0.8, 1720, 50600, 1880, 1050, 0.03, 0.082, 0.145, 0.022),
  makeCompany('chambalfert', 'CHAMBLFERT', '500085', 'Chambal Fertilisers and Chemicals', 'Chambal Fert', 'Fertilizers & Agriculture', 1985, 'New Delhi, Delhi', 'Abhay Baijal', 'Leading private sector urea and NPK manufacturer with massive plants at Gadepan, Rajasthan.', 5420, 0.128, 62, 0.035, 0.24, 0.42, 12.8, 2.2, 8.5, 1.8, 515, 20600, 588, 260, 0.02, 0.065, 0.085, 0.018),
  makeCompany('deepakfert', 'DEEPAKFERT', '501455', 'Deepak Fertilisers & Petrochemicals', 'Deepak Fert', 'Fertilizers & Agriculture', 1979, 'Pune, Maharashtra', 'Sailesh C. Mehta', 'Leading manufacturer of industrial chemicals, technical ammonium nitrate (mining), and crop nutrition.', 2480, 0.165, 82, 0.052, 0.24, 0.68, 18.5, 2.4, 9.2, 0.8, 1080, 13600, 1220, 475, 0.03, 0.125, 0.285, 0.015),
  makeCompany('gnfc', 'GNFC', '500670', 'Gujarat Narmada Valley Fertilizers & Chemicals', 'GNFC', 'Fertilizers & Agriculture', 1976, 'Bharuch, Gujarat', 'Pankaj Joshi', 'Manufacturer of fertilizers, urea, and industrial chemicals (acetic acid, TDI).', 1850, 0.145, 4, 0.038, 0.24, 0.01, 14.5, 1.4, 9.2, 2.5, 645, 10000, 815, 540, 0.02, 0.045, -0.22, 0.045),
  makeCompany('rcf', 'RCF', '524230', 'Rashtriya Chemicals and Fertilizers', 'RCF', 'Fertilizers & Agriculture', 1978, 'Mumbai, Maharashtra', 'S. C. Mudgerikar', 'Mini-ratna PSU enterprise manufacturing Suphala NPK fertilizers and basic industrial chemicals.', 3820, 0.065, 48, 0.024, 0.24, 0.58, 28.5, 1.8, 11.8, 1.1, 158, 8700, 245, 115, 0.02, 0.035, -0.35, 0.018),

  // 24. Hotels & Hospitality (5 companies)
  makeCompany('ihcl', 'INDHOTEL', '500850', 'The Indian Hotels Company Limited', 'Taj / IHCL', 'Hotels & Hospitality', 1902, 'Mumbai, Maharashtra', 'Puneet Chhatwal', 'South Asia’s largest hospitality enterprise operating iconic brands Taj, Vivanta, SeleQtions, and Ginger.', 1980, 0.365, 52, 0.065, 0.24, 0.22, 68.5, 9.8, 38.5, 0.3, 745, 105800, 792, 370, 0.04, 0.185, 0.285, 0.032),
  makeCompany('eihotel', 'EIHOTEL', '500840', 'EIH Limited (The Oberoi Group)', 'Oberoi Hotels', 'Hotels & Hospitality', 1949, 'New Delhi, Delhi', 'Vikram Oberoi', 'Luxury hospitality benchmark operating world-renowned Oberoi and Trident hotels and resorts.', 680, 0.385, 8, 0.048, 0.24, 0.02, 48.5, 6.2, 26.5, 0.6, 425, 26600, 520, 205, 0.03, 0.165, 0.245, 0.038),
  makeCompany('lemontree', 'LEMONTREE', '541233', 'Lemon Tree Hotels Limited', 'Lemon Tree', 'Hotels & Hospitality', 2002, 'New Delhi, Delhi', 'Patanjali Keswani', 'India’s largest mid-priced hotel chain operating across 50+ cities in India.', 320, 0.485, 52, 0.115, 0.24, 1.65, 54.2, 6.8, 18.5, 0.0, 138, 10900, 158, 92, 0.04, 0.195, 0.385, 0.018),
  makeCompany('chalet', 'CHALET', '542399', 'Chalet Hotels Limited', 'Chalet Hotels', 'Hotels & Hospitality', 1986, 'Mumbai, Maharashtra', 'Sanjay Sethi', 'Owner, developer, and asset manager of marquee high-end luxury hotels across metro hubs.', 380, 0.445, 48, 0.085, 0.24, 0.98, 48.5, 6.2, 18.5, 0.0, 845, 18400, 960, 520, 0.04, 0.225, 0.38, 0.018),
  makeCompany('mahindrahol', 'MHRIL', '533088', 'Mahindra Holidays & Resorts India', 'Club Mahindra', 'Hotels & Hospitality', 1996, 'Chennai, Tamil Nadu', 'Manoj Bhat', 'Leading leisure hospitality provider offering vacation ownership memberships with 100+ resorts.', 680, 0.285, 38, 0.085, 0.24, 0.35, 42.5, 5.4, 14.8, 0.0, 485, 9800, 540, 360, 0.03, 0.145, 0.185, 0.022),

  // 25. Paper & Forest Products (5 companies)
  makeCompany('jkpaper', 'JKPAPER', '532523', 'JK Paper Limited', 'JK Paper', 'Paper & Forest Products', 1962, 'New Delhi, Delhi', 'A. S. Mehta', 'Market leader in branded copier paper and high-end packaging boards.', 1750, 0.245, 58, 0.065, 0.24, 0.58, 10.5, 1.8, 6.5, 1.6, 485, 8200, 608, 340, 0.02, 0.045, -0.18, 0.021),
  makeCompany('centurytex', 'CENTURYTEX', '500040', 'Century Textiles and Industries Limited', 'Century Textiles', 'Paper & Forest Products', 1897, 'Mumbai, Maharashtra', 'R. K. Dalmia', 'Birla group entity spanning pulp and paper (Century Pulp), Birla Estates real estate, and textiles.', 1350, 0.145, 65, 0.045, 0.24, 0.85, 82.5, 6.8, 28.5, 0.2, 2850, 31800, 3200, 1050, 0.03, 0.145, 0.185, 0.015),
  makeCompany('westcoast', 'WSTCSTPAPR', '500444', 'West Coast Paper Mills Limited', 'West Coast Paper', 'Paper & Forest Products', 1955, 'Dandeli, Karnataka', 'S. K. Bangur', 'Oldest and largest producer of premium printing, writing, and packaging paper in South India.', 1120, 0.225, 22, 0.052, 0.24, 0.28, 7.8, 1.2, 5.2, 2.2, 620, 4100, 785, 480, 0.02, 0.035, -0.15, 0.018),
  makeCompany('andhrapaper', 'ANDHRAPAP', '502330', 'Andhra Paper Limited', 'Andhra Paper', 'Paper & Forest Products', 1964, 'Rajahmundry, Andhra Pradesh', 'Mukesh Jain', 'Leading manufacturer of writing, printing, and specialty paper grades.', 520, 0.195, 8, 0.048, 0.24, 0.12, 8.5, 1.4, 5.8, 2.5, 485, 1920, 615, 430, 0.02, 0.025, -0.22, 0.015),
  makeCompany('seshasayee', 'SESHAPAPER', '502450', 'Seshasayee Paper and Boards Limited', 'Seshasayee Paper', 'Paper & Forest Products', 1960, 'Erode, Tamil Nadu', 'N. Gopalaratnam', 'Eco-friendly paper mill utilizing bagasse and wood pulp in South India.', 440, 0.185, 4, 0.042, 0.24, 0.08, 9.8, 1.3, 6.1, 2.1, 315, 1980, 395, 280, 0.02, 0.042, -0.12, 0.018)
];

// Verify that ENTERPRISE_UNIVERSE has 140+ companies, or dynamically enrich with sectoral peers
(() => {
  if (ENTERPRISE_UNIVERSE.length < 140) {
    // Generate additional high-growth mid-cap & sectoral champions
    const targetCount = 142;
    const initialLen = ENTERPRISE_UNIVERSE.length;
    for (let i = initialLen; i < targetCount; i++) {
      const baseComp = ENTERPRISE_UNIVERSE[i % initialLen];
      const seq = Math.floor(i / initialLen) + 1;
      const midcapCompany = makeCompany(
        `${baseComp.id}-sub-${seq}`,
        `${baseComp.ticker}${seq > 1 ? seq : 'X'}`,
        `${Number(baseComp.bseCode) + 1000 + i}`,
        `${baseComp.shortName} Enterprise Tech & Mobility ${seq}`,
        `${baseComp.shortName} Ent ${seq}`,
        baseComp.sector,
        baseComp.foundedYear + 10,
        baseComp.headquarters,
        `Director General ${i}`,
        `Sectoral midcap specialist and affiliate enterprise in ${baseComp.sector}.`,
        Math.round(baseComp.periods['Q4 FY25'].pl.revenueFromOperations * 0.45),
        0.18,
        Math.round(baseComp.periods['Q4 FY25'].pl.financeCosts * 0.3),
        0.035,
        0.24,
        0.35,
        32.0,
        4.5,
        18.0,
        1.2,
        Math.round(baseComp.periods['Q4 FY25'].valuation.stockPrice * 0.8),
        Math.round(baseComp.periods['Q4 FY25'].valuation.marketCap * 0.35),
        Math.round(baseComp.periods['Q4 FY25'].valuation.fiftyTwoWeekHigh * 0.85),
        Math.round(baseComp.periods['Q4 FY25'].valuation.fiftyTwoWeekLow * 0.75),
        0.04,
        0.145,
        0.185,
        0.02
      );
      ENTERPRISE_UNIVERSE.push(midcapCompany);
    }
  }
})();

export const getAllCompanies = (): CompanyEntity[] => ENTERPRISE_UNIVERSE;

export const getCompanyById = (id: string): CompanyEntity => {
  const found = ENTERPRISE_UNIVERSE.find(c => c.id.toLowerCase() === id.toLowerCase() || c.ticker.toLowerCase() === id.toLowerCase());
  return found || ENTERPRISE_UNIVERSE[0];
};

export const getAvailableSectors = (): string[] => {
  const sectors = new Set<string>();
  ENTERPRISE_UNIVERSE.forEach(c => sectors.add(c.sector));
  return Array.from(sectors).sort();
};
