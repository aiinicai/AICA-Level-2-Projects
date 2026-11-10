import type { Row } from '../types';

/** Section 17(5) categories offered when an invoice is blocked. */
export const BLOCK_CATEGORIES = [
  { id: 'mv', lbl: 'Motor vehicles & passenger conveyances', sec: '17(5)(a)' },
  { id: 'fb', lbl: 'Food, beverages & outdoor catering', sec: '17(5)(b)(i)' },
  { id: 'bt', lbl: 'Beauty treatment, health & cosmetic services', sec: '17(5)(b)(i)' },
  { id: 'mc', lbl: 'Club, health and fitness membership', sec: '17(5)(b)(ii)' },
  { id: 'rc', lbl: 'Rent-a-cab, life and health insurance', sec: '17(5)(b)(i)' },
  { id: 'tb', lbl: 'Travel benefits to employees (leave / holiday)', sec: '17(5)(b)(iii)' },
  { id: 'wc', lbl: 'Works contract for immovable property', sec: '17(5)(c)' },
  { id: 'cp', lbl: 'Construction of immovable property on own account', sec: '17(5)(d)' },
  { id: 'pu', lbl: 'Personal use / gifts / free samples', sec: '17(5)(g)/(h)' },
  { id: 'ot', lbl: 'Other ineligible credit', sec: '17(5)' },
] as const;

export const categoryById = (id: string) => BLOCK_CATEGORIES.find((c) => c.id === id) ?? BLOCK_CATEGORIES[BLOCK_CATEGORIES.length - 1];

const has = (name: string, words: string[]) => words.some((w) => name.includes(w));

/** Reverse-charge detection: the register's RCM column first, then supplier-name keywords. */
export function detectRcm(row: Row, rcmCell: unknown): { rcm: boolean; reason: string } {
  if (rcmCell !== undefined && rcmCell !== null && rcmCell !== '') {
    const v = String(rcmCell).trim().toLowerCase();
    if (['y', 'yes', 'true', '1', 'rcm'].includes(v)) return { rcm: true, reason: 'Marked as reverse charge in the file' };
  }
  const n = ` ${row.name.toUpperCase()} `;
  if (has(n, ['LOGISTICS', 'TRANSPORT', 'ROADWAYS', 'ROADLINES', 'CARRIER', 'FREIGHT', 'CARGO', 'TRUCKING', ' GTA ', 'GOODS TRANSPORT']))
    return { rcm: true, reason: 'Name suggests a goods transport agency (GTA)' };
  if (has(n, ['ADVOCATE', 'SOLICITOR', 'LAWYER', 'LAW ASSOCIATES', 'LAW CHAMBERS', 'LAW FIRM', 'LEGAL ']))
    return { rcm: true, reason: 'Name suggests an advocate / legal firm' };
  if (has(n, ['SECURITY SERVICE', 'SECURITY AGENCY', 'GUARD', 'VIGILANCE', 'DETECTIVE']))
    return { rcm: true, reason: 'Name suggests security / guard services' };
  if (has(n, ['INSURANCE AGENT', 'INSURANCE AGENCY', 'INSURANCE COMMISSION']))
    return { rcm: true, reason: 'Name suggests insurance agent commission' };
  return { rcm: false, reason: '' };
}

/** Section 17(5) detection from supplier-name keywords. */
export function detectBlocked(row: Row): { blocked: false } | { blocked: true; catId: string; reason: string } {
  const n = ` ${row.name.toUpperCase()} `;
  const transport = n.includes('LOGISTICS') || n.includes('TRANSPORT');
  const hit = (catId: string, reason: string) => ({ blocked: true as const, catId, reason });

  if (
    !transport &&
    has(n, [' MOTORS', ' MOTOR ', 'AUTOMOBILE', 'VEHICLE', 'HYUNDAI', 'TOYOTA', 'MARUTI', 'TATA MOTORS', ' BMW', 'MERCEDES', ' CARS ', 'HONDA CARS', ' AUDI', 'KIA ', 'SKODA', 'AUTOMOTIVE'])
  )
    return hit('mv', 'Name suggests motor vehicles');
  if (has(n, ['CATERING', 'CATERERS', 'RESTAURANT', ' FOOD', 'DINING', 'BANQUET', ' CAFE', 'CAFETERIA', 'BAKERY', 'SWEETS', 'PIZZ', 'COFFEE']))
    return hit('fb', 'Name suggests food / catering');
  if (has(n, ['SALON', ' SPA ', 'BEAUTY', 'COSMETIC', 'PARLOUR', 'PARLOR']))
    return hit('bt', 'Name suggests beauty / cosmetic services');
  if (has(n, [' GYM', 'FITNESS', 'HEALTH CLUB', 'COUNTRY CLUB', 'SPORTS CLUB', 'GYMKHANA']))
    return hit('mc', 'Name suggests club / fitness membership');
  if (has(n, [' CAB ', ' CABS ', 'RENT A CAB', 'CAR RENTAL', 'TAXI', 'LIFE INSURANCE', 'HEALTH INSURANCE', 'MEDICLAIM', 'STAR HEALTH']))
    return hit('rc', 'Name suggests rent-a-cab or life / health insurance');
  if (!transport && has(n, ['HOLIDAY', 'RESORT', 'TOUR OPERATOR', 'TOURS AND TRAVEL', 'TOURS & TRAVEL']))
    return hit('tb', 'Name suggests holiday / travel benefits');
  if (has(n, ['CONSTRUCTION', 'BUILDERS', 'DEVELOPERS', 'CIVIL WORKS', 'CIVIL CONTRACTOR']))
    return hit('wc', 'Name suggests works contract / construction');
  return { blocked: false };
}
