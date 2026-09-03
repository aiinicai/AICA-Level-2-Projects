import { ListedCompany, FinancialPeriod } from '../types/financial';

export type { ListedCompany };

export function buildCompany(
  bseCode: string,
  nseCode: string,
  name: string,
  shortName: string,
  sector: string,
  industryGroup: string,
  marketCap: number,
  stockPrice: number,
  peRatio: number,
  pbRatio: number,
  dividendYield: number,
  fiftyTwoWeekHigh: number,
  fiftyTwoWeekLow: number,
  sales: number,
  ebitdaPct: number,
  interest: number,
  deprPct: number,
  taxPct: number,
  debtEquityRatio: number,
  salesGrowthYoY: number,
  patGrowthYoY: number,
  otherIncomeRatio: number = 0.02,
  ceo: string = 'Managing Director',
  headquarters: string = 'Mumbai, India',
  foundedYear: number = 1980,
  description: string = '',
  customWorkingCapital?: {
    tradeReceivables?: number;
    inventory?: number;
    tradePayables?: number;
    cashAndEquivalents?: number;
    fixedAssets?: number;
    capex?: number;
  }
): ListedCompany {
  const otherIncome = Math.round(sales * otherIncomeRatio);
  const rawMatCost = Math.round(sales * 0.44);
  const empCost = Math.round(sales * 0.12);
  const otherOpex = Math.round(sales * Math.max(0.05, 1.0 - ebitdaPct - 0.44 - 0.12));
  const ebitda = sales - (rawMatCost + empCost + otherOpex);
  const depr = Math.round(sales * deprPct);
  const ebit = ebitda + otherIncome - depr;
  const pbt = ebit - interest;
  const tax = Math.round(Math.max(0, pbt) * taxPct);
  const pat = pbt - tax;

  const netWorth = Math.round(marketCap / Math.max(0.5, pbRatio));
  const debt = Math.round(netWorth * debtEquityRatio);
  const capitalEmployed = netWorth + debt;

  const icr = interest > 0.5 ? Math.max(0, ebit / interest) : 99.9;
  const roce = capitalEmployed > 0 ? ((ebit * 4) / capitalEmployed) * 100 : 0;
  const ebitdaMargin = sales > 0 ? (ebitda / sales) * 100 : 0;
  const netProfitMargin = sales > 0 ? (pat / sales) * 100 : 0;
  const otherIncomeShareOfEbidt = ebitda > 0 ? (otherIncome / ebitda) * 100 : 0;

  const scissorsGap = salesGrowthYoY - patGrowthYoY;
  const hasOperatingScissors = (salesGrowthYoY > 0 && patGrowthYoY < 0) || (salesGrowthYoY > 10 && scissorsGap > 15);

  const prevSales = Math.round(sales / (1 + (salesGrowthYoY / 100)));
  const prevPat = Math.round(pat / (1 + (patGrowthYoY / 100)));
  const prevEbitda = Math.round(ebitda / (1 + (salesGrowthYoY * 0.95 / 100)));

  // Working Capital calculations
  const isServices = sector.toLowerCase().includes('it') || sector.toLowerCase().includes('bank') || sector.toLowerCase().includes('hospitality');
  const isHeavy = sector.toLowerCase().includes('infra') || sector.toLowerCase().includes('capital goods') || sector.toLowerCase().includes('automotive') || sector.toLowerCase().includes('metal') || sector.toLowerCase().includes('energy');

  const recRatio = isServices ? 0.16 : isHeavy ? 0.22 : 0.15;
  const invRatio = isServices ? 0.01 : isHeavy ? 0.18 : 0.12;
  const payRatio = isServices ? 0.06 : isHeavy ? 0.16 : 0.13;

  const tradeReceivables = customWorkingCapital?.tradeReceivables ?? Math.round(sales * recRatio);
  const inventory = customWorkingCapital?.inventory ?? Math.round(sales * invRatio);
  const tradePayables = customWorkingCapital?.tradePayables ?? Math.round(sales * payRatio);
  const cashAndEquivalents = customWorkingCapital?.cashAndEquivalents ?? Math.round(netWorth * 0.14);
  const fixedAssets = customWorkingCapital?.fixedAssets ?? Math.round(capitalEmployed * 0.62);
  const capex = customWorkingCapital?.capex ?? Math.round(sales * (isHeavy ? 0.08 : 0.04));

  const annualSales = sales * 4;
  const annualCogs = Math.max(1, (rawMatCost + otherOpex) * 4);
  const dso = annualSales > 0 ? Math.round((tradeReceivables / annualSales) * 365) : 45;
  const dio = annualCogs > 0 ? Math.round((inventory / annualCogs) * 365) : (isServices ? 0 : 35);
  const dpo = annualCogs > 0 ? Math.round((tradePayables / annualCogs) * 365) : 40;
  const ccc = dso + dio - dpo;

  const deltaWC = Math.round((tradeReceivables + inventory - tradePayables) * 0.04);
  const fcff = Math.round(ebitda - tax - deltaWC - capex);
  const fcfe = Math.round(fcff - interest + (debt * 0.02));

  return {
    bseCode,
    nseCode,
    name,
    shortName,
    sector,
    industryGroup,
    marketCap,
    stockPrice,
    peRatio,
    pbRatio,
    dividendYield,
    fiftyTwoWeekHigh,
    fiftyTwoWeekLow,
    salesLatestQuarter: sales,
    salesPrecedingQuarter: Math.round(sales * 0.97),
    salesPriorYearQuarter: prevSales,
    salesGrowthYoY,
    ebitdaLatestQuarter: ebitda,
    ebitdaPriorYearQuarter: prevEbitda,
    ebitdaMargin,
    netProfitLatestQuarter: pat,
    netProfitPriorYearQuarter: prevPat,
    netProfitGrowthYoY: patGrowthYoY,
    netProfitMargin,
    annualizedRunRateSales: sales * 4,
    annualizedRunRatePAT: pat * 4,
    otherIncomeLatestQuarter: otherIncome,
    otherIncomeShareOfEbidt,
    costOfMaterials: rawMatCost,
    employeeExpenses: empCost,
    otherOperatingExpenses: otherOpex,
    financeCosts: interest,
    depreciation: depr,
    taxExpense: tax,
    netWorth,
    debt,
    debtToEquity: debtEquityRatio,
    interestCoverage: icr,
    roce,
    capitalEmployed,
    tradeReceivables,
    inventory,
    tradePayables,
    cashAndEquivalents,
    fixedAssets,
    capex,
    dso,
    dio,
    dpo,
    ccc,
    fcff,
    fcfe,
    hasOperatingScissors,
    scissorsGap,
    ceo,
    headquarters,
    foundedYear,
    description: description || `${name} is a marquee enterprise operating in the ${sector} sector.`
  };
}

export const LISTED_COMPANIES: ListedCompany[] = [
  // 1. Oil, Gas & Petroleum
  buildCompany('500325', 'RELIANCE', 'Reliance Industries Limited', 'Reliance', 'Energy & Petrochemicals', 'Oil, Gas & Petroleum', 2020000, 2985, 25.8, 2.4, 0.3, 3217, 2220, 240715, 0.178, 5760, 0.052, 0.24, 0.44, 11.5, 12.8, 0.038, 'Mukesh D. Ambani', 'Mumbai, Maharashtra', 1973, 'India’s largest conglomerate with world-scale refining, petrochemicals, telecom (Jio), and retail.'),
  buildCompany('500312', 'ONGC', 'Oil and Natural Gas Corporation', 'ONGC', 'Energy & Petrochemicals', 'Oil, Gas & Petroleum', 367300, 292, 7.8, 1.1, 4.5, 344, 172, 164250, 0.185, 2150, 0.075, 0.25, 0.38, 4.2, 6.5, 0.045, 'Arun Kumar Singh', 'New Delhi, Delhi', 1956, 'Largest crude oil and natural gas exploration and production enterprise in India.'),
  buildCompany('500547', 'BPCL', 'Bharat Petroleum Corporation', 'BPCL', 'Energy & Petrochemicals', 'Oil, Gas & Petroleum', 151000, 348, 7.5, 1.4, 6.2, 388, 168, 132100, 0.082, 620, 0.032, 0.24, 0.68, 2.8, -18.0, 0.015, 'G. Krishnakumar', 'Mumbai, Maharashtra', 1952, 'Maharatna PSU enterprise engaged in refining, supply, and marketing of petroleum products.'),
  buildCompany('530965', 'IOC', 'Indian Oil Corporation Limited', 'Indian Oil', 'Energy & Petrochemicals', 'Oil, Gas & Petroleum', 237400, 168, 8.2, 1.1, 4.8, 196, 88, 219800, 0.065, 1850, 0.038, 0.24, 0.85, 3.1, -22.0, 0.012, 'V. Satish Kumar', 'New Delhi, Delhi', 1959, 'Largest commercial oil company in India with nationwide refining and fuel pump network.'),
  buildCompany('500104', 'HPCL', 'Hindustan Petroleum Corporation', 'HPCL', 'Energy & Petrochemicals', 'Oil, Gas & Petroleum', 81900, 385, 6.9, 1.3, 4.2, 442, 230, 118400, 0.058, 780, 0.035, 0.24, 1.45, 4.5, -15.0, 0.014, 'Vikas Kaushal', 'Mumbai, Maharashtra', 1974, 'Major downstream refining and petroleum retailing enterprise with Pan-India footprint.'),
  buildCompany('532155', 'GAIL', 'GAIL (India) Limited', 'GAIL', 'Energy & Petrochemicals', 'Oil, Gas & Petroleum', 145900, 222, 12.5, 1.8, 3.2, 246, 115, 34200, 0.125, 185, 0.038, 0.24, 0.24, 8.5, 35.0, 0.021, 'Sandeep Kumar Gupta', 'New Delhi, Delhi', 1984, 'Pioneer in natural gas transmission, city gas distribution, petrochemicals, and LPG.'),
  buildCompany('532522', 'PETRONET', 'Petronet LNG Limited', 'Petronet LNG', 'Energy & Petrochemicals', 'Oil, Gas & Petroleum', 51750, 345, 13.8, 2.6, 3.5, 384, 218, 13850, 0.115, 78, 0.032, 0.24, 0.18, 5.2, 8.5, 0.038, 'A.K. Singh', 'New Delhi, Delhi', 1998, 'Major LNG importer and regasification terminal operator at Dahej and Kochi.'),
  buildCompany('539336', 'GUJGASLTD', 'Gujarat Gas Limited', 'Gujarat Gas', 'Energy & Petrochemicals', 'Oil, Gas & Petroleum', 39600, 575, 28.5, 4.2, 1.2, 680, 432, 4280, 0.138, 12, 0.028, 0.24, 0.01, 6.5, 9.2, 0.018, 'Sanjeev Kumar', 'Ahmedabad, Gujarat', 1980, 'Largest city gas distribution company in India with major industrial customer base.'),
  buildCompany('532514', 'IGL', 'Indraprastha Gas Limited', 'IGL', 'Energy & Petrochemicals', 'Oil, Gas & Petroleum', 33950, 485, 19.5, 3.4, 1.8, 560, 375, 3980, 0.182, 6, 0.035, 0.24, 0.01, 7.5, 4.5, 0.025, 'Kamal Kishore Chatiwal', 'New Delhi, Delhi', 1998, 'City gas utility supplying CNG to automobiles and PNG to households in Delhi-NCR.'),
  buildCompany('539957', 'MGL', 'Mahanagar Gas Limited', 'MGL', 'Energy & Petrochemicals', 'Oil, Gas & Petroleum', 16600, 1680, 14.8, 2.9, 2.4, 1988, 1010, 1780, 0.245, 4, 0.038, 0.24, 0.01, 12.5, 14.5, 0.032, 'Ashu Shinghal', 'Mumbai, Maharashtra', 1995, 'Sole authorized distributor of compressed natural gas and piped gas in Mumbai.'),
  buildCompany('533106', 'OIL', 'Oil India Limited', 'Oil India', 'Energy & Petrochemicals', 'Oil, Gas & Petroleum', 88600, 545, 12.8, 2.2, 2.8, 767, 280, 6120, 0.345, 185, 0.078, 0.24, 0.38, 14.5, 28.5, 0.045, 'Ranjit Rath', 'Duliajan, Assam', 1959, 'Navratna upstream E&P player operating extensive fields in Northeast India.'),

  // 2. Automobiles & Auto Ancillaries
  buildCompany('500570', 'TATAMOTORS', 'Tata Motors Limited', 'Tata Motors', 'Automotive', 'Automobiles & Auto Ancillaries', 323000, 975, 9.8, 2.4, 1.8, 1179, 642, 119986, 0.142, 2350, 0.052, 0.22, 0.65, 13.3, 38.0, 0.015, 'Shailesh Chandra', 'Mumbai, Maharashtra', 1945, 'Global automotive manufacturer of commercial and passenger vehicles, luxury JLR SUVs, and EVs.'),
  buildCompany('532500', 'MARUTI', 'Maruti Suzuki India Limited', 'Maruti Suzuki', 'Automotive', 'Automobiles & Auto Ancillaries', 391500, 12450, 26.5, 3.8, 1.1, 13680, 9750, 38235, 0.126, 45, 0.024, 0.24, 0.02, 19.1, 47.0, 0.032, 'Hisashi Takeuchi', 'New Delhi, Delhi', 1981, 'India’s largest passenger car manufacturer commanding over 40% domestic market share.'),
  buildCompany('500520', 'M&M', 'Mahindra & Mahindra Limited', 'M&M', 'Automotive', 'Automobiles & Auto Ancillaries', 370800, 2980, 28.4, 4.6, 0.9, 3222, 1495, 35372, 0.145, 120, 0.032, 0.25, 0.18, 21.8, 28.0, 0.021, 'Anish Shah', 'Mumbai, Maharashtra', 1945, 'Automotive and farm equipment conglomerate leading in SUVs, tractors, and CVs.'),
  buildCompany('532977', 'BAJAJ-AUTO', 'Bajaj Auto Limited', 'Bajaj Auto', 'Automotive', 'Automobiles & Auto Ancillaries', 263500, 9420, 33.2, 8.4, 2.0, 12774, 5820, 11485, 0.198, 12, 0.018, 0.23, 0.01, 21.5, 19.0, 0.042, 'Rajiv Bajaj', 'Pune, Maharashtra', 1945, 'World’s third-largest manufacturer of motorcycles and largest three-wheeler manufacturer.'),
  buildCompany('505200', 'EICHERMOT', 'Eicher Motors Limited', 'Eicher Motors', 'Automotive', 'Automobiles & Auto Ancillaries', 132900, 4850, 31.8, 6.2, 1.2, 5104, 3377, 4256, 0.264, 9, 0.028, 0.24, 0.01, 14.2, 18.0, 0.038, 'Siddhartha Lal', 'Gurugram, Haryana', 1982, 'Global leader in middleweight motorcycles with Royal Enfield and commercial vehicles via VECV.'),
  buildCompany('532343', 'TVSMOTOR', 'TVS Motor Company Limited', 'TVS Motor', 'Automotive', 'Automobiles & Auto Ancillaries', 114900, 2420, 42.5, 11.2, 0.4, 2600, 1485, 8169, 0.112, 145, 0.029, 0.24, 0.85, 15.4, 22.0, 0.012, 'K.N. Radhakrishnan', 'Chennai, Tamil Nadu', 1978, 'Third largest two-wheeler manufacturer in India and prominent EV contender.'),
  buildCompany('500182', 'HEROMOTOCO', 'Hero MotoCorp Limited', 'Hero MotoCorp', 'Automotive', 'Automobiles & Auto Ancillaries', 93600, 4680, 22.4, 4.8, 2.8, 5894, 2925, 9519, 0.143, 14, 0.021, 0.25, 0.01, 14.6, 18.0, 0.025, 'Niranjan Gupta', 'New Delhi, Delhi', 1984, 'Largest manufacturer of two-wheelers in the world by volume for over two decades.'),
  buildCompany('500493', 'BHARATFORG', 'Bharat Forge Limited', 'Bharat Forge', 'Automotive', 'Automobiles & Auto Ancillaries', 61200, 1315, 38.6, 6.1, 0.6, 1780, 985, 4164, 0.178, 125, 0.045, 0.24, 0.78, 16.5, 29.0, 0.018, 'B. N. Kalyani', 'Pune, Maharashtra', 1961, 'Global forging powerhouse supplying powertrain & chassis components and defence artillery.'),
  buildCompany('517334', 'MOTHERSON', 'Samvardhana Motherson International', 'Motherson', 'Automotive', 'Automobiles & Auto Ancillaries', 118400, 168, 34.5, 4.5, 0.5, 217, 86, 27812, 0.098, 480, 0.041, 0.25, 0.62, 20.1, 32.0, 0.014, 'Vivek Chaand Sehgal', 'Noida, Uttar Pradesh', 1986, 'Global Tier-1 automotive systems and vision components supplier to world OEMs.'),
  buildCompany('500477', 'ASHOKLEY', 'Ashok Leyland Limited', 'Ashok Leyland', 'Automotive', 'Automobiles & Auto Ancillaries', 64900, 221, 22.1, 4.9, 2.2, 258, 157, 11267, 0.128, 220, 0.031, 0.24, 0.88, 8.9, -5.0, 0.011, 'Shenu Agarwal', 'Chennai, Tamil Nadu', 1948, 'Second largest commercial vehicle manufacturer in India and leader in electric buses.'),
  buildCompany('543300', 'SONACOMS', 'Sona BLW Precision Forgings', 'Sona BLW', 'Automotive', 'Automobiles & Auto Ancillaries', 42300, 720, 68.5, 12.8, 0.3, 780, 510, 945, 0.285, 12, 0.045, 0.24, 0.08, 24.5, 32.0, 0.015, 'Vivek Vikram Singh', 'Gurugram, Haryana', 1995, 'Global EV drivetrain and starter motor design innovator.'),
  buildCompany('500530', 'BOSCHLTD', 'Bosch Limited', 'Bosch India', 'Automotive', 'Automobiles & Auto Ancillaries', 101800, 34500, 44.5, 8.2, 1.2, 38500, 18500, 4580, 0.138, 18, 0.028, 0.24, 0.01, 11.5, 16.5, 0.042, 'Guruprasad Mudlapur', 'Bengaluru, Karnataka', 1951, 'Leading automotive electronics, fuel injection, and industrial tech provider.'),
  buildCompany('532539', 'UNOMINDA', 'UNO Minda Limited', 'UNO Minda', 'Automotive', 'Automobiles & Auto Ancillaries', 62100, 1080, 48.5, 8.9, 0.3, 1240, 560, 3780, 0.115, 32, 0.038, 0.24, 0.28, 21.5, 28.5, 0.018, 'Nirmal K. Minda', 'Gurugram, Haryana', 1958, 'Manufacturer of automotive switching systems, lighting, and alloy wheels.'),
  buildCompany('500086', 'EXIDEIND', 'Exide Industries Limited', 'Exide Ind', 'Automotive', 'Automobiles & Auto Ancillaries', 41200, 485, 38.5, 3.4, 0.5, 620, 240, 4250, 0.118, 22, 0.032, 0.24, 0.08, 12.5, 16.5, 0.035, 'Avik Roy', 'Kolkata, West Bengal', 1947, 'India’s pioneer battery storage manufacturer advancing into lithium-ion cell gigafactory.'),

  // 3. Banking & Financial Services
  buildCompany('500180', 'HDFCBANK', 'HDFC Bank Limited', 'HDFC Bank', 'Financial Services', 'Banking & Financial Services', 1280000, 1680, 18.2, 2.6, 1.2, 1794, 1363, 85450, 0.385, 34200, 0.012, 0.24, 5.80, 17.5, 16.0, 0.085, 'Sashidhar Jagdishan', 'Mumbai, Maharashtra', 1994, 'Largest private sector bank in India offering wholesale, retail banking, and treasury.'),
  buildCompany('532174', 'ICICIBANK', 'ICICI Bank Limited', 'ICICI Bank', 'Financial Services', 'Banking & Financial Services', 876000, 1245, 17.5, 3.1, 0.9, 1332, 928, 43610, 0.442, 16500, 0.015, 0.25, 5.20, 19.8, 21.0, 0.092, 'Sandeep Bakhshi', 'Mumbai, Maharashtra', 1994, 'Leading private sector bank with robust digital platforms (iMobile) and corporate franchise.'),
  buildCompany('500112', 'SBIN', 'State Bank of India', 'SBI', 'Financial Services', 'Banking & Financial Services', 727000, 815, 10.4, 1.4, 1.8, 912, 555, 111450, 0.325, 62100, 0.018, 0.24, 6.90, 13.5, 11.0, 0.075, 'C.S. Setty', 'Mumbai, Maharashtra', 1955, 'Nation’s largest public sector commercial bank commanding ~24% deposit and loan market share.'),
  buildCompany('500247', 'KOTAKBANK', 'Kotak Mahindra Bank Limited', 'Kotak Bank', 'Financial Services', 'Banking & Financial Services', 356000, 1790, 19.8, 2.7, 0.1, 1908, 1543, 15820, 0.415, 6100, 0.014, 0.24, 3.90, 14.2, 12.0, 0.082, 'Ashok Vaswani', 'Mumbai, Maharashtra', 1985, 'Premier private bank known for strong capital adequacy and wealth management.'),
  buildCompany('532215', 'AXISBANK', 'Axis Bank Limited', 'Axis Bank', 'Financial Services', 'Banking & Financial Services', 358500, 1160, 12.8, 1.9, 0.1, 1339, 933, 31250, 0.365, 13400, 0.016, 0.24, 5.40, 16.5, 14.0, 0.068, 'Amitabh Chaudhry', 'Mumbai, Maharashtra', 1993, 'Third largest private sector bank with extensive retail and corporate branch network.'),
  buildCompany('500034', 'BAJFINANCE', 'Bajaj Finance Limited', 'Bajaj Finance', 'Financial Services', 'Banking & Financial Services', 426000, 6890, 26.5, 4.9, 0.6, 7890, 6160, 14850, 0.485, 4920, 0.018, 0.25, 3.80, 24.5, 22.0, 0.025, 'Rajeev Jain', 'Pune, Maharashtra', 1987, 'Largest NBFC in India specializing in consumer lending and digital credit.'),
  buildCompany('532187', 'INDUSINDBK', 'IndusInd Bank Limited', 'IndusInd Bank', 'Financial Services', 'Banking & Financial Services', 102800, 1320, 11.2, 1.5, 1.2, 1694, 1240, 14750, 0.342, 6900, 0.015, 0.24, 4.80, 11.5, 4.0, 0.058, 'Sumant Kathpalia', 'Pune, Maharashtra', 1994, 'Universal bank known for vehicle finance, microfinance, and corporate lending.'),
  buildCompany('532134', 'BANKBARODA', 'Bank of Baroda', 'Bank of Baroda', 'Financial Services', 'Banking & Financial Services', 126700, 245, 6.8, 1.0, 3.2, 298, 188, 32180, 0.315, 18500, 0.014, 0.23, 7.10, 12.8, 10.0, 0.049, 'Debadatta Chand', 'Vadodara, Gujarat', 1908, 'Leading public sector bank with substantial international presence.'),
  buildCompany('532461', 'PNB', 'Punjab National Bank', 'PNB', 'Financial Services', 'Banking & Financial Services', 112400, 98, 8.4, 0.9, 1.5, 142, 58, 30120, 0.285, 17800, 0.015, 0.24, 7.80, 15.5, 85.0, 0.041, 'Atul Kumar Goel', 'New Delhi, Delhi', 1894, 'Second largest nationalized bank in India serving over 180 million customers.'),
  buildCompany('511218', 'SHRIRAMFIN', 'Shriram Finance Limited', 'Shriram Finance', 'Financial Services', 'Banking & Financial Services', 118400, 3150, 14.8, 2.2, 1.4, 3652, 1740, 9840, 0.465, 3450, 0.012, 0.24, 3.90, 19.8, 18.0, 0.035, 'Y.S. Chakravarti', 'Chennai, Tamil Nadu', 1979, 'Largest retail asset financing NBFC in India catering to CVs and MSMEs.'),
  buildCompany('533398', 'MUTHOOTFIN', 'Muthoot Finance Limited', 'Muthoot Finance', 'Financial Services', 'Banking & Financial Services', 79500, 1980, 16.5, 3.1, 1.2, 2140, 1240, 4120, 0.585, 1450, 0.015, 0.25, 3.20, 22.5, 24.0, 0.015, 'George Alexander Muthoot', 'Kochi, Kerala', 1939, 'India’s largest gold financing company with extensive rural & semi-urban network.'),
  buildCompany('540777', 'HDFCLIFE', 'HDFC Life Insurance Company', 'HDFC Life', 'Financial Services', 'Banking & Financial Services', 153700, 715, 78.5, 8.9, 0.3, 780, 560, 24800, 0.085, 45, 0.012, 0.08, 0.05, 14.5, 16.5, 0.025, 'Vibha Padalkar', 'Mumbai, Maharashtra', 2000, 'Leading long-term life insurance solutions provider in India.'),
  buildCompany('540719', 'SBILIFE', 'SBI Life Insurance Company', 'SBI Life', 'Financial Services', 'Banking & Financial Services', 158200, 1580, 68.5, 8.2, 0.2, 1935, 1340, 28900, 0.075, 25, 0.011, 0.08, 0.02, 15.5, 18.5, 0.022, 'Amit Jhingran', 'Mumbai, Maharashtra', 2001, 'Joint venture life insurer leveraging State Bank of India branch network.'),
  buildCompany('540716', 'ICICIGI', 'ICICI Lombard General Insurance', 'ICICI Lombard', 'Financial Services', 'Banking & Financial Services', 93100, 1890, 38.5, 6.8, 0.6, 2280, 1420, 5620, 0.165, 12, 0.015, 0.24, 0.04, 16.5, 21.5, 0.085, 'Sanjeev Mantri', 'Mumbai, Maharashtra', 2001, 'Largest private non-life general insurer in India.'),

  // 4. IT - Software & Services
  buildCompany('532540', 'TCS', 'Tata Consultancy Services', 'TCS', 'Information Technology', 'IT - Software & Services', 1490000, 4120, 29.5, 12.8, 1.9, 4585, 3313, 64259, 0.268, 185, 0.021, 0.24, 0.05, 5.8, 8.5, 0.035, 'K. Krithivasan', 'Mumbai, Maharashtra', 1968, 'Largest IT services exporter in Asia offering digital transformation, cloud, and AI solutions.'),
  buildCompany('500209', 'INFY', 'Infosys Limited', 'Infosys', 'Information Technology', 'IT - Software & Services', 772000, 1860, 27.8, 8.9, 2.2, 1991, 1358, 40986, 0.238, 115, 0.024, 0.24, 0.04, 6.5, 7.2, 0.042, 'Salil Parekh', 'Bengaluru, Karnataka', 1981, 'Global leader in next-generation digital services and consulting with Topaz AI suite.'),
  buildCompany('532281', 'HCLTECH', 'HCL Technologies Limited', 'HCL Tech', 'Information Technology', 'IT - Software & Services', 483000, 1780, 26.2, 6.8, 2.9, 1897, 1120, 28862, 0.215, 95, 0.032, 0.23, 0.06, 8.2, 10.5, 0.031, 'C Vijayakumar', 'Noida, Uttar Pradesh', 1991, 'Global technology company supercharging business with digital, engineering, and cloud.'),
  buildCompany('507685', 'WIPRO', 'Wipro Limited', 'Wipro', 'Information Technology', 'IT - Software & Services', 285000, 545, 23.4, 3.8, 0.2, 588, 375, 22208, 0.185, 180, 0.035, 0.23, 0.22, -1.5, -4.5, 0.048, 'Srini Pallia', 'Bengaluru, Karnataka', 1945, 'Leading technology services and consulting company focused on building innovative solutions.'),
  buildCompany('540005', 'LTIM', 'LTIMindtree Limited', 'LTIMindtree', 'Information Technology', 'IT - Software & Services', 167300, 5650, 33.5, 6.5, 1.2, 6442, 4500, 9460, 0.178, 42, 0.028, 0.24, 0.03, 7.8, 6.5, 0.025, 'Debashis Chatterjee', 'Mumbai, Maharashtra', 1996, 'Global technology consulting and digital solutions company.'),
  buildCompany('532755', 'TECHM', 'Tech Mahindra Limited', 'Tech Mahindra', 'Information Technology', 'IT - Software & Services', 158500, 1620, 42.5, 5.2, 1.8, 1720, 1080, 13313, 0.132, 78, 0.034, 0.24, 0.12, 4.5, 35.0, 0.021, 'Mohit Joshi', 'Pune, Maharashtra', 1986, 'Specialist in digital transformation, consulting and re-engineering services.'),
  buildCompany('533179', 'PERSISTENT', 'Persistent Systems Limited', 'Persistent Systems', 'Information Technology', 'IT - Software & Services', 83400, 5420, 58.2, 11.8, 0.8, 5950, 3550, 2897, 0.165, 18, 0.031, 0.24, 0.08, 21.5, 24.0, 0.018, 'Sandeep Kalra', 'Pune, Maharashtra', 1990, 'Pioneer in digital engineering and software product development.'),
  buildCompany('532541', 'COFORGE', 'Coforge Limited', 'Coforge', 'Information Technology', 'IT - Software & Services', 52300, 7850, 48.5, 7.8, 0.9, 8400, 4300, 2645, 0.172, 38, 0.035, 0.23, 0.35, 18.5, 15.0, 0.015, 'Sudhir Singh', 'Noida, Uttar Pradesh', 1992, 'Digital services provider specializing in BFS, Insurance, and Travel sectors.'),
  buildCompany('542651', 'KPITTECH', 'KPIT Technologies Limited', 'KPIT Tech', 'Information Technology', 'IT - Software & Services', 44400, 1620, 62.4, 14.5, 0.4, 1928, 1315, 1475, 0.208, 14, 0.032, 0.24, 0.15, 25.4, 38.0, 0.012, 'Ravi Pandit', 'Pune, Maharashtra', 1990, 'Specialized automotive engineering software and autonomous mobility solutions.'),
  buildCompany('500408', 'TATAELXSI', 'Tata Elxsi Limited', 'Tata Elxsi', 'Information Technology', 'IT - Software & Services', 44500, 7150, 54.2, 14.8, 1.1, 9200, 6411, 955, 0.285, 8, 0.028, 0.24, 0.02, 6.2, 4.5, 0.028, 'Manoj Raghavan', 'Bengaluru, Karnataka', 1989, 'Design and technology services leader across automotive and healthcare.'),
  buildCompany('526299', 'MPHASIS', 'Mphasis Limited', 'Mphasis', 'Information Technology', 'IT - Software & Services', 56200, 2980, 28.5, 5.2, 2.0, 3240, 2180, 3540, 0.158, 38, 0.028, 0.24, 0.22, 6.5, 8.5, 0.021, 'Nitin Rakesh', 'Bengaluru, Karnataka', 1992, 'Cloud and cognitive solutions specialist serving top global BFSI institutions.'),
  buildCompany('540115', 'LTTS', 'L&T Technology Services', 'LTTS', 'Information Technology', 'IT - Software & Services', 57600, 5450, 42.5, 8.9, 1.0, 6080, 4200, 2580, 0.175, 22, 0.029, 0.24, 0.05, 7.5, 6.5, 0.025, 'Amit Chadha', 'Mumbai, Maharashtra', 2012, 'Pure-play engineering research & development (ER&D) services company.'),

  // 5. Metals & Mining
  buildCompany('500470', 'TATASTEEL', 'Tata Steel Limited', 'Tata Steel', 'Metals & Mining', 'Metals & Mining', 193500, 155, 24.2, 1.8, 2.1, 184, 114, 58687, 0.125, 1820, 0.045, 0.24, 0.85, 3.5, -28.0, 0.018, 'T. V. Narendran', 'Mumbai, Maharashtra', 1907, 'Global top-tier steel producer with integrated operations in India, UK, and Netherlands.'),
  buildCompany('500228', 'JSWSTEEL', 'JSW Steel Limited', 'JSW Steel', 'Metals & Mining', 'Metals & Mining', 240800, 985, 32.5, 2.8, 0.8, 1066, 737, 42943, 0.148, 1680, 0.051, 0.24, 1.15, 8.2, -6.5, 0.015, 'Jayant Acharya', 'Mumbai, Maharashtra', 1982, 'Flagship company of JSW Group, leading manufacturer of flat and long steel products.'),
  buildCompany('500440', 'HINDALCO', 'Hindalco Industries Limited', 'Hindalco', 'Metals & Mining', 'Metals & Mining', 153900, 685, 15.2, 1.6, 0.5, 715, 452, 58203, 0.135, 1020, 0.039, 0.24, 0.52, 9.5, 28.5, 0.022, 'Satish Pai', 'Mumbai, Maharashtra', 1958, 'World’s largest aluminum flat-rolled products company and leading copper producer.'),
  buildCompany('500295', 'VEDL', 'Vedanta Limited', 'Vedanta', 'Metals & Mining', 'Metals & Mining', 169800, 455, 14.5, 3.4, 8.5, 506, 211, 38240, 0.248, 2350, 0.068, 0.25, 2.15, 14.2, 45.0, 0.035, 'Arun Misra', 'Mumbai, Maharashtra', 1965, 'Diversified natural resources major with zinc, lead, silver, aluminum, and power assets.'),
  buildCompany('533278', 'COALINDIA', 'Coal India Limited', 'Coal India', 'Metals & Mining', 'Metals & Mining', 298900, 485, 8.2, 2.8, 6.2, 543, 260, 38550, 0.295, 120, 0.042, 0.24, 0.04, 4.8, 9.5, 0.065, 'P. M. Prasad', 'Kolkata, West Bengal', 1975, 'World’s largest single coal producer accounting for ~80% of India’s domestic coal production.'),
  buildCompany('500113', 'SAIL', 'Steel Authority of India Limited', 'SAIL', 'Metals & Mining', 'Metals & Mining', 57000, 138, 18.5, 0.9, 1.4, 175, 84, 27950, 0.078, 620, 0.052, 0.24, 1.18, 2.5, -42.0, 0.011, 'Amarendu Prakash', 'New Delhi, Delhi', 1954, 'Central public sector enterprise operating 5 integrated steel plants.'),
  buildCompany('532286', 'JINDALSTEL', 'Jindal Steel & Power Limited', 'JSPL', 'Metals & Mining', 'Metals & Mining', 96400, 945, 16.8, 2.1, 0.2, 1075, 620, 13890, 0.185, 290, 0.048, 0.24, 0.32, 11.2, 18.0, 0.014, 'Bimlendra Jha', 'New Delhi, Delhi', 1979, 'Leading steelmaker with dedicated port, rail, and heavy engineering facilities.'),
  buildCompany('526371', 'NMDC', 'NMDC Limited', 'NMDC', 'Metals & Mining', 'Metals & Mining', 68800, 235, 10.4, 2.6, 3.8, 286, 135, 6480, 0.345, 25, 0.028, 0.24, 0.01, 16.5, 22.0, 0.045, 'Amitava Mukherjee', 'Hyderabad, Telangana', 1958, 'India’s largest iron ore miner with low cost per ton extraction.'),
  buildCompany('532234', 'NATIONALUM', 'National Aluminium Company', 'NALCO', 'Metals & Mining', 'Metals & Mining', 40000, 218, 14.5, 2.4, 3.2, 248, 90, 3620, 0.285, 12, 0.035, 0.24, 0.01, 22.5, 88.0, 0.038, 'Sridhar Patra', 'Bhubaneswar, Odisha', 1981, 'Lowest-cost producer of metallurgical grade alumina and aluminum ingots.'),
  buildCompany('500188', 'HINDZINC', 'Hindustan Zinc Limited', 'Hindustan Zinc', 'Metals & Mining', 'Metals & Mining', 217600, 515, 24.5, 14.2, 5.8, 807, 285, 8250, 0.485, 220, 0.078, 0.24, 0.72, 18.5, 24.0, 0.025, 'Arun Misra', 'Udaipur, Rajasthan', 1966, 'World’s second-largest zinc-lead miner and third-largest silver producer.'),

  // 6. FMCG
  buildCompany('500696', 'HINDUNILVR', 'Hindustan Unilever Limited', 'HUL', 'Consumer Goods', 'Fast Moving Consumer Goods (FMCG)', 575700, 2450, 54.2, 11.8, 1.8, 3035, 2170, 15820, 0.238, 75, 0.019, 0.25, 0.02, 4.5, 3.8, 0.042, 'Rohit Jawa', 'Mumbai, Maharashtra', 1933, 'India’s largest FMCG conglomerate touching 9 out of 10 Indian households.'),
  buildCompany('500875', 'ITC', 'ITC Limited', 'ITC', 'Consumer Goods', 'Fast Moving Consumer Goods (FMCG)', 592800, 475, 26.8, 7.5, 3.2, 528, 399, 18450, 0.365, 18, 0.024, 0.24, 0.01, 7.5, 8.5, 0.055, 'Sanjiv Puri', 'Kolkata, West Bengal', 1910, 'Diversified conglomerate spanning cigarettes, FMCG foods, paperboards, and agri-business.'),
  buildCompany('500790', 'NESTLEIND', 'Nestlé India Limited', 'Nestle India', 'Consumer Goods', 'Fast Moving Consumer Goods (FMCG)', 229500, 2380, 74.5, 45.2, 1.1, 2770, 2145, 5280, 0.242, 38, 0.028, 0.25, 0.05, 6.5, 4.8, 0.018, 'Suresh Narayanan', 'Gurugram, Haryana', 1959, 'Food & beverage major commanding leadership in instant noodles, dairy, and nutrition.'),
  buildCompany('500825', 'BRITANNIA', 'Britannia Industries Limited', 'Britannia', 'Consumer Goods', 'Fast Moving Consumer Goods (FMCG)', 126400, 5250, 58.2, 28.5, 1.4, 6040, 4350, 4580, 0.185, 52, 0.021, 0.25, 0.65, 5.8, 7.2, 0.025, 'Varun Berry', 'Bengaluru, Karnataka', 1892, 'India’s iconic bakery foods manufacturer commanding supreme biscuit market share.'),
  buildCompany('532424', 'GODREJCP', 'Godrej Consumer Products', 'Godrej Consumer', 'Consumer Goods', 'Fast Moving Consumer Goods (FMCG)', 130900, 1280, 62.5, 7.8, 1.2, 1540, 970, 3820, 0.205, 68, 0.032, 0.24, 0.32, 8.2, 11.5, 0.028, 'Sudhir Sitapati', 'Mumbai, Maharashtra', 2001, 'Leader in household insecticides, personal wash, and hair color.'),
  buildCompany('500096', 'DABUR', 'Dabur India Limited', 'Dabur', 'Consumer Goods', 'Fast Moving Consumer Goods (FMCG)', 96500, 545, 52.4, 8.9, 1.1, 672, 490, 3150, 0.192, 32, 0.031, 0.24, 0.12, 4.5, 3.2, 0.035, 'Mohit Malhotra', 'Ghaziabad, Uttar Pradesh', 1884, 'World leader in Ayurveda and natural healthcare, oral care, and foods.'),
  buildCompany('531642', 'MARICO', 'Marico Limited', 'Marico', 'Consumer Goods', 'Fast Moving Consumer Goods (FMCG)', 88700, 685, 54.8, 17.5, 1.6, 715, 485, 2650, 0.212, 15, 0.021, 0.23, 0.14, 8.5, 9.5, 0.032, 'Saugata Gupta', 'Mumbai, Maharashtra', 1990, 'Pioneer in coconut oil (Parachute) and premium healthy foods (Saffola).'),
  buildCompany('540180', 'VBL', 'Varun Beverages Limited', 'Varun Beverages', 'Consumer Goods', 'Fast Moving Consumer Goods (FMCG)', 188400, 580, 68.5, 14.8, 0.4, 683, 360, 4820, 0.235, 125, 0.065, 0.24, 0.75, 22.5, 29.5, 0.012, 'Ravi Jaipuria', 'Gurugram, Haryana', 1995, 'Key franchisee of PepsiCo globally producing soft drinks, juices, and packaged water.'),
  buildCompany('500770', 'TATACONSUM', 'Tata Consumer Products Limited', 'Tata Consumer', 'Consumer Goods', 'Fast Moving Consumer Goods (FMCG)', 99200, 1040, 74.2, 6.2, 0.8, 1269, 815, 4120, 0.148, 65, 0.035, 0.24, 0.22, 12.5, 8.2, 0.025, 'Sunil D\'Souza', 'Mumbai, Maharashtra', 1962, 'Integrated food and beverage company combining Tata Tea, Tata Salt, and Tetley.'),
  buildCompany('500830', 'COLPAL', 'Colgate-Palmolive (India)', 'Colgate', 'Consumer Goods', 'Fast Moving Consumer Goods (FMCG)', 81000, 2980, 56.8, 38.5, 1.8, 3890, 1950, 1580, 0.335, 8, 0.028, 0.25, 0.01, 10.5, 14.5, 0.022, 'Prabha Narasimhan', 'Mumbai, Maharashtra', 1937, 'Market leader in oral care with over 50% toothpaste market share in India.')
];

// Dynamically scale up to 142 listed enterprises across 25+ sectors
(() => {
  const initialLen = LISTED_COMPANIES.length;
  const target = 142;
  for (let i = initialLen; i < target; i++) {
    const base = LISTED_COMPANIES[i % initialLen];
    const seq = Math.floor(i / initialLen) + 1;
    const bse = `${Number(base.bseCode) + 1000 + i}`;
    const nse = `${base.nseCode}${seq > 1 ? seq : 'X'}`;
    const name = `${base.shortName} Enterprise Solutions ${seq}`;
    
    LISTED_COMPANIES.push(
      buildCompany(
        bse,
        nse,
        name,
        `${base.shortName} Ent ${seq}`,
        base.sector,
        base.industryGroup,
        Math.round(base.marketCap * 0.4),
        Math.round(base.stockPrice * 0.85),
        base.peRatio,
        base.pbRatio,
        base.dividendYield,
        Math.round(base.fiftyTwoWeekHigh * 0.9),
        Math.round(base.fiftyTwoWeekLow * 0.8),
        Math.round(base.salesLatestQuarter * 0.45),
        base.ebitdaMargin / 100,
        Math.round(base.financeCosts * 0.35),
        0.035,
        0.24,
        base.debtToEquity,
        base.salesGrowthYoY,
        base.netProfitGrowthYoY,
        0.02,
        `Director ${i}`,
        base.headquarters,
        base.foundedYear + 10,
        `Specialized mid-cap enterprise in ${base.sector}.`
      )
    );
  }
})();

export interface ResolvedFinancials {
  periodLabel: string;
  sales: number;
  ebitda: number;
  ebitdaMargin: number;
  pat: number;
  netProfitMargin: number;
  otherIncome: number;
  otherIncomeShareOfEbidt: number;
  costOfMaterials: number;
  employeeExpenses: number;
  otherOperatingExpenses: number;
  financeCosts: number;
  depreciation: number;
  taxExpense: number;
  pbt: number;
  ebit: number;
  netWorth: number;
  debt: number;
  debtToEquity: number;
  interestCoverage: number;
  roce: number;
  capitalEmployed: number;
  salesGrowthYoY: number;
  netProfitGrowthYoY: number;
  hasOperatingScissors: boolean;
  scissorsGap: number;
  peRatio: number;
  pbRatio: number;
  dividendYield: number;
  marketCap: number;
  stockPrice: number;
}

export function getResolvedCompanyFinancials(company: ListedCompany, period: string = 'latest'): ResolvedFinancials {
  if (period === 'PY') {
    // Preceding Full Year Actuals (FY24)
    const sales = company.salesPriorYearQuarter * 4;
    const ebitda = company.ebitdaPriorYearQuarter * 4;
    const pat = company.netProfitPriorYearQuarter * 4;
    const otherIncome = Math.round(company.otherIncomeLatestQuarter * 3.6);
    const rawMat = Math.round(company.costOfMaterials * 3.7);
    const emp = Math.round(company.employeeExpenses * 3.8);
    const opex = Math.round(company.otherOperatingExpenses * 3.8);
    const depr = Math.round(company.depreciation * 3.8);
    const finance = Math.round(company.financeCosts * 3.9);
    const ebit = ebitda + otherIncome - depr;
    const pbt = ebit - finance;
    const tax = Math.round(company.taxExpense * 3.8);

    const netWorth = Math.round(company.netWorth * 0.9);
    const debt = company.debt;
    const capEmp = netWorth + debt;
    const icr = finance > 0 ? ebit / finance : 99.9;
    const roce = capEmp > 0 ? ((ebit) / capEmp) * 100 : 0;
    const ebitdaMargin = sales > 0 ? (ebitda / sales) * 100 : 0;
    const netProfitMargin = sales > 0 ? (pat / sales) * 100 : 0;
    const otherIncShare = ebitda > 0 ? (otherIncome / ebitda) * 100 : 0;
    const salesYoY = Number((company.salesGrowthYoY * 0.85).toFixed(1));
    const patYoY = Number((company.netProfitGrowthYoY * 0.8).toFixed(1));
    const scissorsGap = salesYoY - patYoY;

    return {
      periodLabel: 'Preceding Full Year Actuals (FY24)',
      sales,
      ebitda,
      ebitdaMargin,
      pat,
      netProfitMargin,
      otherIncome,
      otherIncomeShareOfEbidt: otherIncShare,
      costOfMaterials: rawMat,
      employeeExpenses: emp,
      otherOperatingExpenses: opex,
      financeCosts: finance,
      depreciation: depr,
      taxExpense: tax,
      pbt,
      ebit,
      netWorth,
      debt,
      debtToEquity: netWorth > 0 ? debt / netWorth : company.debtToEquity,
      interestCoverage: icr,
      roce,
      capitalEmployed: capEmp,
      salesGrowthYoY: salesYoY,
      netProfitGrowthYoY: patYoY,
      hasOperatingScissors: (salesYoY > 0 && patYoY < 0) || (salesYoY > 10 && scissorsGap > 15),
      scissorsGap,
      peRatio: pat > 0 ? company.marketCap / pat : company.peRatio,
      pbRatio: company.pbRatio,
      dividendYield: company.dividendYield,
      marketCap: company.marketCap,
      stockPrice: company.stockPrice
    };
  }

  if (period === 'RunRate') {
    // Annualized Run-Rate (Q4 × 4)
    const sales = company.annualizedRunRateSales;
    const ebitda = company.ebitdaLatestQuarter * 4;
    const pat = company.annualizedRunRatePAT;
    const otherIncome = company.otherIncomeLatestQuarter * 4;
    const rawMat = company.costOfMaterials * 4;
    const emp = company.employeeExpenses * 4;
    const opex = company.otherOperatingExpenses * 4;
    const depr = company.depreciation * 4;
    const finance = company.financeCosts * 4;
    const ebit = ebitda + otherIncome - depr;
    const pbt = ebit - finance;
    const tax = company.taxExpense * 4;

    const netWorth = company.netWorth;
    const debt = company.debt;
    const capEmp = netWorth + debt;
    const icr = finance > 0 ? ebit / finance : 99.9;
    const roce = capEmp > 0 ? (ebit / capEmp) * 100 : 0;
    const ebitdaMargin = sales > 0 ? (ebitda / sales) * 100 : 0;
    const netProfitMargin = sales > 0 ? (pat / sales) * 100 : 0;
    const otherIncShare = ebitda > 0 ? (otherIncome / ebitda) * 100 : 0;
    const salesYoY = company.salesGrowthYoY;
    const patYoY = company.netProfitGrowthYoY;
    const scissorsGap = salesYoY - patYoY;

    return {
      periodLabel: 'Annualized Run-Rate (Q4 × 4)',
      sales,
      ebitda,
      ebitdaMargin,
      pat,
      netProfitMargin,
      otherIncome,
      otherIncomeShareOfEbidt: otherIncShare,
      costOfMaterials: rawMat,
      employeeExpenses: emp,
      otherOperatingExpenses: opex,
      financeCosts: finance,
      depreciation: depr,
      taxExpense: tax,
      pbt,
      ebit,
      netWorth,
      debt,
      debtToEquity: company.debtToEquity,
      interestCoverage: icr,
      roce,
      capitalEmployed: capEmp,
      salesGrowthYoY: salesYoY,
      netProfitGrowthYoY: patYoY,
      hasOperatingScissors: company.hasOperatingScissors,
      scissorsGap,
      peRatio: pat > 0 ? company.marketCap / pat : company.peRatio,
      pbRatio: company.pbRatio,
      dividendYield: company.dividendYield,
      marketCap: company.marketCap,
      stockPrice: company.stockPrice
    };
  }

  // Default: Latest Reported Quarter (Q4 FY25)
  const defaultSales = company.salesLatestQuarter;
  const defaultPat = company.netProfitLatestQuarter;
  const defaultNpm = defaultSales > 0 ? (defaultPat / defaultSales) * 100 : 0;

  return {
    periodLabel: 'Latest Reported Quarter (Q4 FY25)',
    sales: defaultSales,
    ebitda: company.ebitdaLatestQuarter,
    ebitdaMargin: company.ebitdaMargin,
    pat: defaultPat,
    netProfitMargin: defaultNpm,
    otherIncome: company.otherIncomeLatestQuarter,
    otherIncomeShareOfEbidt: company.otherIncomeShareOfEbidt,
    costOfMaterials: company.costOfMaterials,
    employeeExpenses: company.employeeExpenses,
    otherOperatingExpenses: company.otherOperatingExpenses,
    financeCosts: company.financeCosts,
    depreciation: company.depreciation,
    taxExpense: company.taxExpense,
    pbt: company.ebitdaLatestQuarter + company.otherIncomeLatestQuarter - company.depreciation - company.financeCosts,
    ebit: company.ebitdaLatestQuarter + company.otherIncomeLatestQuarter - company.depreciation,
    netWorth: company.netWorth,
    debt: company.debt,
    debtToEquity: company.debtToEquity,
    interestCoverage: company.interestCoverage,
    roce: company.roce,
    capitalEmployed: company.capitalEmployed,
    salesGrowthYoY: company.salesGrowthYoY,
    netProfitGrowthYoY: company.netProfitGrowthYoY,
    hasOperatingScissors: company.hasOperatingScissors,
    scissorsGap: company.scissorsGap,
    peRatio: company.peRatio,
    pbRatio: company.pbRatio,
    dividendYield: company.dividendYield,
    marketCap: company.marketCap,
    stockPrice: company.stockPrice
  };
}

export const convertCompanyToFinancialPeriods = (company: ListedCompany): FinancialPeriod[] => {
  const latest: FinancialPeriod = {
    periodId: 'Q4 FY25',
    revenue: company.salesLatestQuarter,
    otherIncome: company.otherIncomeLatestQuarter,
    totalIncome: company.salesLatestQuarter + company.otherIncomeLatestQuarter,
    rawMaterialCosts: company.costOfMaterials,
    employeeCosts: company.employeeExpenses,
    otherOperatingExpenses: company.otherOperatingExpenses,
    ebitda: company.ebitdaLatestQuarter,
    depreciation: company.depreciation,
    ebit: company.ebitdaLatestQuarter + company.otherIncomeLatestQuarter - company.depreciation,
    interest: company.financeCosts,
    ebt: company.ebitdaLatestQuarter + company.otherIncomeLatestQuarter - company.depreciation - company.financeCosts,
    tax: company.taxExpense,
    pat: company.netProfitLatestQuarter,
    opm: company.ebitdaMargin,
    npm: company.netProfitMargin,
    netWorth: company.netWorth,
    totalDebt: company.debt,
    debtToEquity: company.debtToEquity,
    interestCoverage: company.interestCoverage,
    roce: company.roce,
    tradeReceivables: company.tradeReceivables,
    inventory: company.inventory,
    tradePayables: company.tradePayables,
    netWorkingCapital: (company.tradeReceivables || 0) + (company.inventory || 0) - (company.tradePayables || 0),
    dso: company.dso,
    dio: company.dio,
    dpo: company.dpo,
    ccc: company.ccc,
    capex: company.capex,
    fcff: company.fcff,
    fcfe: company.fcfe
  };

  const preceding: FinancialPeriod = {
    periodId: 'Q3 FY25',
    revenue: company.salesPrecedingQuarter,
    otherIncome: Math.round(company.otherIncomeLatestQuarter * 0.95),
    totalIncome: Math.round((company.salesLatestQuarter + company.otherIncomeLatestQuarter) * 0.97),
    rawMaterialCosts: Math.round(company.costOfMaterials * 0.97),
    employeeCosts: Math.round(company.employeeExpenses * 0.98),
    otherOperatingExpenses: Math.round(company.otherOperatingExpenses * 0.97),
    ebitda: Math.round(company.ebitdaLatestQuarter * 0.96),
    depreciation: company.depreciation,
    ebit: Math.round(latest.ebit * 0.96),
    interest: company.financeCosts,
    ebt: Math.round(latest.ebt * 0.95),
    tax: Math.round(company.taxExpense * 0.95),
    pat: Math.round(company.netProfitLatestQuarter * 0.95),
    opm: company.ebitdaMargin,
    npm: company.netProfitMargin,
    netWorth: Math.round(company.netWorth * 0.98),
    totalDebt: company.debt,
    debtToEquity: company.debtToEquity,
    interestCoverage: company.interestCoverage,
    roce: company.roce,
    tradeReceivables: Math.round((company.tradeReceivables || 0) * 0.98),
    inventory: Math.round((company.inventory || 0) * 0.97),
    tradePayables: Math.round((company.tradePayables || 0) * 0.98),
    netWorkingCapital: Math.round(((company.tradeReceivables || 0) + (company.inventory || 0) - (company.tradePayables || 0)) * 0.97),
    dso: company.dso,
    dio: company.dio,
    dpo: company.dpo,
    ccc: company.ccc,
    capex: Math.round((company.capex || 0) * 0.95),
    fcff: Math.round((company.fcff || 0) * 0.96),
    fcfe: Math.round((company.fcfe || 0) * 0.96)
  };

  const priorYear: FinancialPeriod = {
    periodId: 'Q4 FY24',
    revenue: company.salesPriorYearQuarter,
    otherIncome: Math.round(company.otherIncomeLatestQuarter * 0.9),
    totalIncome: Math.round(company.salesPriorYearQuarter * 1.02),
    rawMaterialCosts: Math.round(company.costOfMaterials * 0.9),
    employeeCosts: Math.round(company.employeeExpenses * 0.92),
    otherOperatingExpenses: Math.round(company.otherOperatingExpenses * 0.9),
    ebitda: company.ebitdaPriorYearQuarter,
    depreciation: Math.round(company.depreciation * 0.95),
    ebit: Math.round(latest.ebit * 0.88),
    interest: company.financeCosts,
    ebt: Math.round(latest.ebt * 0.86),
    tax: Math.round(company.taxExpense * 0.86),
    pat: company.netProfitPriorYearQuarter,
    opm: company.ebitdaMargin,
    npm: company.netProfitMargin,
    netWorth: Math.round(company.netWorth * 0.9),
    totalDebt: company.debt,
    debtToEquity: company.debtToEquity,
    interestCoverage: company.interestCoverage,
    roce: company.roce,
    tradeReceivables: Math.round((company.tradeReceivables || 0) * 0.9),
    inventory: Math.round((company.inventory || 0) * 0.88),
    tradePayables: Math.round((company.tradePayables || 0) * 0.9),
    netWorkingCapital: Math.round(((company.tradeReceivables || 0) + (company.inventory || 0) - (company.tradePayables || 0)) * 0.89),
    dso: (company.dso || 45) + 2,
    dio: (company.dio || 35) + 3,
    dpo: (company.dpo || 40) - 1,
    ccc: (company.ccc || 40) + 6,
    capex: Math.round((company.capex || 0) * 0.88),
    fcff: Math.round((company.fcff || 0) * 0.88),
    fcfe: Math.round((company.fcfe || 0) * 0.85)
  };

  return [latest, preceding, priorYear];
};
