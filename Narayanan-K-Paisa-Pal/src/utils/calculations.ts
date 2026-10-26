import {
  AppRow,
  DueCategory,
  Frequency,
  InvType,
  Kind,
  NormalizedAlert,
  AlertState,
  UtilityType,
} from '../types';

export const DAY = 86400000;

export const CATS: Record<DueCategory, string> = {
  fd: 'Fixed deposit',
  insurance: 'Insurance policy',
  mediclaim: 'Mediclaim',
  vehicle: 'Vehicle insurance',
  lpg: 'LPG refill',
  utility: 'Electricity / water bill',
  emi: 'EMI',
};

export const UTILITY_TYPES: Record<string, string> = {
  electricity: 'Electricity bill',
  water: 'Water bill',
  landline: 'Landline phone',
  mobile: 'Mobile bill',
  broadband: 'Broadband / WiFi',
  gas: 'Piped gas / LPG',
  lpg: 'LPG cylinder',
  piped_gas: 'Piped gas (PNG)',
  dth: 'DTH / Cable TV',
  maintenance: 'Society maintenance',
  other: 'Other utility',
};

export const FREQ: Record<Frequency, string> = {
  once: 'Once',
  monthly: 'Monthly',
  bimonthly: 'Every 2 months',
  quarterly: 'Quarterly',
  halfyearly: 'Half-yearly',
  annual: 'Yearly',
  days: 'Every N days',
};

export const FM: Record<string, number> = {
  once: 0,
  monthly: 1,
  bimonthly: 2,
  quarterly: 3,
  halfyearly: 6,
  annual: 12,
};

export const INV: Record<InvType, string> = {
  fd: 'Fixed deposit',
  rd: 'Recurring deposit',
  bond: 'Bonds / debentures',
  mf: 'Mutual fund',
  stocks: 'Shares / stocks',
  gold: 'Gold / SGB / ETF',
  ppf: 'PPF / EPF',
  nps: 'NPS',
  property: 'Property',
  insurance: 'Insurance (investment)',
  other: 'Other',
};

export const DEF_INV_ALERTS: Partial<Record<InvType, number[]>> = {
  fd: [30, 15, 7, 1],
  rd: [30, 7],
  bond: [30, 15, 7],
  gold: [30, 7],
};

export const MATLBL: Partial<Record<InvType, string>> = {
  fd: 'FD renewal',
  rd: 'RD maturity',
  bond: 'Bond maturity',
  gold: 'Gold maturity',
  ppf: 'PPF maturity',
  insurance: 'Policy maturity',
};

export const REC: Record<string, string> = {
  id: 'ID card',
  licence: 'Driving licence',
  passport: 'Passport',
  pan: 'PAN card',
  aadhaar: 'Aadhaar card',
  voter: 'Voter ID',
  ration: 'Ration card',
  vehicle: 'Vehicle papers',
  bank: 'Bank account',
  policy: 'Insurance policy',
  insurance: 'Insurance policy',
  nominee: 'Nominee record',
  contact: 'Key contact',
  other: 'Other record',
};

export const DEF_ALERTS: Record<string, number[]> = {
  fd: [30, 7],
  insurance: [30, 15, 7, 1],
  mediclaim: [30, 15, 7, 1],
  vehicle: [30, 15, 7, 1],
  lpg: [3, 1],
  utility: [7, 3, 0],
  emi: [3, 1, 0],
};

export const KIND_NAME: Record<Kind, string> = {
  due: 'due date',
  inv: 'investment',
  rec: 'record',
  util: 'utility bill',
};

export const KIND_PLURAL: Record<Kind, string> = {
  due: 'due dates',
  inv: 'investments',
  rec: 'records',
  util: 'utility bills',
};

export const uid = (): string =>
  'r' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7);

export const toDay = (s: string): number => {
  if (!s || s.length < 10) return 0;
  return Date.UTC(+s.slice(0, 4), +s.slice(5, 7) - 1, +s.slice(8, 10));
};

export const fmtD = (t: number): string => new Date(t).toISOString().slice(0, 10);

export const todayIST = (): string => fmtD(Date.now() + 5.5 * 3600e3);

export const MON = [
  'Jan',
  'Feb',
  'Mar',
  'Apr',
  'May',
  'Jun',
  'Jul',
  'Aug',
  'Sep',
  'Oct',
  'Nov',
  'Dec',
];

export const longD = (s?: string): string => {
  if (!s || s.length < 10) return '';
  const monthIdx = +s.slice(5, 7) - 1;
  return `${s.slice(8, 10)} ${MON[monthIdx] ?? ''} ${s.slice(0, 4)}`;
};

export function addMonths(s: string, n: number, anchor?: number): string {
  const y = +s.slice(0, 4);
  const m = +s.slice(5, 7) - 1;
  const d = anchor || +s.slice(8, 10);
  const idx = m + n;
  const ny = y + Math.floor(idx / 12);
  const nm = ((idx % 12) + 12) % 12;
  const last = new Date(Date.UTC(ny, nm + 1, 0)).getUTCDate();
  return fmtD(Date.UTC(ny, nm, Math.min(d, last)));
}

export function rollForward(
  d: Record<string, any>,
  today: string,
  paymentDetails?: { amountPaid?: number; paymentDate?: string; receiptRef?: string }
): Record<string, any> {
  const n = { ...d };

  // Handle explicit payment details (partial or full)
  if (paymentDetails && paymentDetails.amountPaid != null) {
    const payAmt = +paymentDetails.amountPaid;
    const currentOutstanding =
      n.balanceOutstanding != null && n.balanceOutstanding !== ''
        ? +n.balanceOutstanding
        : +(n.billAmount ?? n.amount ?? 0);

    const newOutstanding = Math.max(0, currentOutstanding - payAmt);
    n.balanceOutstanding = newOutstanding;
    n.paidAmount = (+n.paidAmount || 0) + payAmt;
    n.lastPaymentDate = paymentDetails.paymentDate || today;

    const hist = Array.isArray(n.paymentHistory) ? [...n.paymentHistory] : [];
    hist.push({
      id: uid(),
      paymentDate: paymentDetails.paymentDate || today,
      amountPaid: payAmt,
      receiptRef: paymentDetails.receiptRef || '',
      notes: newOutstanding === 0 ? 'Full payment' : 'Partial payment',
    });
    n.paymentHistory = hist;

    // A partially paid bill remains outstanding until settled!
    n.status = newOutstanding === 0 ? 'paid' : 'pending';
    return n;
  }

  const baseDueDate = d.dueDate || d.due || today;

  if (d.freq === 'once') {
    n.status = 'paid';
  } else if (d.freq === 'days') {
    const nextDate = fmtD(toDay(today) + (+d.interval || 35) * DAY);
    if (d.dueDate) n.dueDate = nextDate;
    n.due = nextDate;
    n.status = 'pending';
    if (n.billAmount) {
      n.balanceOutstanding = n.billAmount;
      n.paidAmount = 0;
    }
  } else {
    // Preserve original anchor day so Jan 31 -> Feb 28 -> March 31!
    const anchor =
      typeof d.anchor === 'number' && d.anchor > 0
        ? d.anchor
        : +String(baseDueDate).slice(8, 10) || 1;
    n.anchor = anchor;
    const nextDate = addMonths(baseDueDate, FM[d.freq] ?? 1, anchor);
    if (d.dueDate) n.dueDate = nextDate;
    n.due = nextDate;
    n.status = 'pending';
    if (n.billAmount) {
      n.balanceOutstanding = n.billAmount;
      n.paidAmount = 0;
    }
  }
  return n;
}

export function inr(a: number | string | undefined): string {
  const n = Math.round(+a! || 0);
  const formatted = new Intl.NumberFormat('en-IN', {
    maximumFractionDigits: 0,
  }).format(Math.abs(n));
  return (n < 0 ? '-' : '') + '₹' + formatted;
}

export function inrS(n: number | string | undefined): string {
  const val = +n! || 0;
  const a = Math.abs(val);
  if (a >= 1e7) {
    const cr = (val / 1e7).toFixed(2).replace(/\.?0+$/, '');
    return `₹${cr} Cr`;
  }
  if (a >= 1e5) {
    const l = (val / 1e5).toFixed(2).replace(/\.?0+$/, '');
    return `₹${l} L`;
  }
  return inr(val);
}

export const rateTxt = (v: number | string | undefined): string => {
  if (v === '' || v == null || !+v) return '–';
  return (+v).toFixed(2).replace(/\.?0+$/, '') + '%';
};

export function parseAlerts(val: any, fallback: number[]): number[] {
  if (Array.isArray(val)) {
    return val.map(Number).filter((n) => !isNaN(n));
  }
  if (typeof val === 'string' && val.trim().length > 0) {
    return val
      .split(',')
      .map((s) => Number(s.trim()))
      .filter((n) => !isNaN(n));
  }
  if (typeof val === 'number') {
    return [val];
  }
  return fallback;
}

export function normAll(row: AppRow): NormalizedAlert[] {
  if (!row || !row.kind) return [];
  const d = row.data || {};
  const out: NormalizedAlert[] = [];

  // 1. Utilities (Electricity, Water, Gas, Broadband, etc.)
  if (row.kind === 'util') {
    const dueDate = d.dueDate || d.due;
    if (dueDate) {
      const outstanding =
        d.balanceOutstanding != null && d.balanceOutstanding !== ''
          ? +d.balanceOutstanding
          : +d.billAmount || 0;
      out.push({
        row,
        vk: 'due',
        label: UTILITY_TYPES[d.utilityType] || 'Utility Bill',
        name: d.name || d.provider || 'Household Utility',
        sub: d.accountNumber ? `Consumer #${d.accountNumber}` : d.provider || '',
        who: d.holder || d.property || '',
        amount: Math.max(0, outstanding),
        due: dueDate,
        alerts: parseAlerts(d.alerts, [7, 3, 0]),
        paid: d.status === 'paid' || (d.status === 'partially_paid' && outstanding <= 0),
      });
    }
  }

  // 2. Due Dates (EMIs, Loans, Dues)
  if (row.kind === 'due' && d.due) {
    out.push({
      row,
      vk: 'due',
      label: CATS[d.category as DueCategory] || 'Due',
      name: d.name || 'Untitled',
      sub: d.provider || '',
      who: d.holder || '',
      amount: +d.amount || 0,
      due: d.due,
      alerts: parseAlerts(d.alerts, [7, 1]),
      paid: d.status === 'paid',
    });
  }

  // 3. Investments (FD, RD, Mutual Funds, Bonds)
  if (row.kind === 'inv') {
    const al = parseAlerts(d.alerts, DEF_INV_ALERTS[d.type as InvType] || [30, 7]);

    if (d.maturity) {
      out.push({
        row,
        vk: 'mat',
        label: MATLBL[d.type as InvType] || 'Maturity',
        name: d.name || 'Investment',
        sub: d.institution || '',
        who: d.holder || '',
        amount: +d.current || +d.invested || 0,
        due: d.maturity,
        alerts: al,
        paid: false,
      });
    }

    if (d.nextint) {
      out.push({
        row,
        vk: 'mat',
        label: 'Interest / coupon due',
        name: d.name || 'Investment',
        sub: d.institution || '',
        who: d.holder || '',
        amount: 0,
        due: d.nextint,
        alerts: [7, 1],
        paid: false,
      });
    }
  }

  // 4. Records (Identity Documents & Insurance Policies)
  if (row.kind === 'rec') {
    const isInsurance =
      d.category === 'insurance' ||
      d.type === 'policy' ||
      d.type === 'insurance' ||
      Boolean(d.policyNumber || d.insurer);

    if (isInsurance) {
      // Insurance policy renewal alert
      const renewalDate = d.renewalDate || d.expires;
      if (renewalDate && !/permanent|no expiry|na|n\/a/i.test(renewalDate)) {
        out.push({
          row,
          vk: 'exp',
          label: `${d.insuranceType ? `${d.insuranceType.toUpperCase()} ` : ''}Policy Renewal`,
          name: d.title || d.insurer || 'Insurance Policy',
          sub: d.policyNumber ? `Policy #${d.policyNumber}` : d.insurer || '',
          who: d.policyholder || d.holder || '',
          amount: 0,
          due: renewalDate,
          alerts: parseAlerts(d.alerts, [30, 15, 7, 1]),
          paid: false,
        });
      }

      // Premium due alert (separate from policy renewal date)
      if (d.premiumDueDate) {
        out.push({
          row,
          vk: 'due',
          label: 'Insurance Premium Due',
          name: d.title || d.insurer || 'Insurance Policy',
          sub: d.policyNumber ? `Policy #${d.policyNumber}` : '',
          who: d.policyholder || d.holder || '',
          amount: +d.premium || 0,
          due: d.premiumDueDate,
          alerts: parseAlerts(d.alerts, [30, 15, 7, 1]),
          paid: false,
        });
      }
    } else {
      // Identity document expiry alert (only for documents with valid, non-permanent expiry dates)
      const isPermanentDoc =
        d.type === 'pan' ||
        d.type === 'aadhaar' ||
        /pan|aadhaar|aadhar/i.test(d.title || '');

      if (d.expires && !isPermanentDoc && !/permanent|no expiry|na|n\/a/i.test(d.expires)) {
        out.push({
          row,
          vk: 'exp',
          label: (REC[d.type] || 'Record') + ' expiry',
          name: d.title || 'Record',
          sub: d.number ? `Doc #${d.number}` : '',
          who: d.holder || '',
          amount: 0,
          due: d.expires,
          alerts: parseAlerts(d.alerts, [60, 30, 7]),
          paid: false,
        });
      }
    }
  }

  return out;
}

export const norm = (row: AppRow): NormalizedAlert | null => normAll(row)[0] || null;

export function daysTo(a: NormalizedAlert): number {
  return Math.round((toDay(a.due) - toDay(todayIST())) / DAY);
}

export function stateOf(a: NormalizedAlert): AlertState {
  if (a.paid) return 'paid';
  const d = daysTo(a);
  if (d < 0) return 'overdue';
  if (d === 0) return 'today';
  if (d <= Math.max(0, ...a.alerts)) return 'soon';
  return 'later';
}

export function whenTxt(a: NormalizedAlert): string {
  const d = daysTo(a);
  if (d < 0) return `${-d} day${d === -1 ? '' : 's'} overdue`;
  if (d === 0) return 'due today';
  return `in ${d} day${d === 1 ? '' : 's'} (${longD(a.due)})`;
}

export interface MigrationResult {
  migratedRows: AppRow[];
  reclassifiedCount: number;
  details: { id: string; name: string; from: Kind; to: Kind; reason: string }[];
}

export function reclassifyMisplacedEntries(rows: AppRow[]): MigrationResult {
  let count = 0;
  const details: MigrationResult['details'] = [];

  const migratedRows = rows.map((r) => {
    const d = { ...r.data };
    let newKind: Kind = r.kind;
    let reason = '';

    // 1. Misplaced Utility bills (in 'due' or 'inv')
    const isUtility =
      r.kind !== 'util' &&
      (d.category === 'utility' ||
        d.category === 'utility_bill' ||
        /electricity|bescom|tata power|tneb|water|jal board|bwssb|broadband|airtel|jio|gas|cylinder|lpg|piped gas|landline/i.test(
          d.name || d.title || d.provider || ''
        ) ||
        r.id.startsWith('trial-utility'));

    if (isUtility) {
      newKind = 'util';
      const utilType: UtilityType = /water|jal board|bwssb/i.test(d.name || d.provider || '')
        ? 'water'
        : /broadband|wifi|fiber/i.test(d.name || d.provider || '')
        ? 'broadband'
        : /gas|lpg|cylinder/i.test(d.name || d.provider || '')
        ? 'gas'
        : /phone|landline|mobile/i.test(d.name || d.provider || '')
        ? 'mobile'
        : 'electricity';

      d.utilityType = d.utilityType || utilType;
      d.provider = d.provider || d.institution || d.name || 'Utility Provider';
      d.consumerNumber = d.consumerNumber || d.accountNumber || d.ref || '';
      d.person = d.person || d.holder || '';
      d.billAmount = +(d.billAmount ?? d.amount ?? 0);
      d.balanceOutstanding = +(d.balanceOutstanding ?? d.billAmount);
      d.dueDate = d.dueDate || d.due || todayIST();
      d.status = d.status || (toDay(d.dueDate) < toDay(todayIST()) ? 'overdue' : 'pending');
      reason = 'Reclassified from Due Dates to dedicated Utilities section';
    }
    // 2. Misplaced Insurance policies (in 'due' or 'inv')
    else if (
      r.kind !== 'rec' &&
      (d.category === 'insurance' ||
        d.category === 'mediclaim' ||
        d.type === 'insurance' ||
        /lic|jeevan|hdfc life|star health|care health|icici lombard|new india|insurance|mediclaim|motor insurance|policy/i.test(
          d.name || d.title || d.provider || d.institution || ''
        ) ||
        r.id.startsWith('trial-insurance'))
    ) {
      newKind = 'rec';
      d.type = 'insurance';
      d.title = d.title || d.name || 'Insurance Policy';
      d.insurer = d.insurer || d.provider || d.institution || '';
      d.provider = d.insurer;
      d.policyNumber = d.policyNumber || d.number || d.ref || '';
      d.policyholder = d.policyholder || d.holder || '';
      d.premium = +(d.premium ?? d.premiumAmount ?? d.amount ?? 0);
      d.sumInsured = +(d.sumInsured ?? d.currentValue ?? 0);
      d.renewalDate = d.renewalDate || d.expires || d.due || '';
      d.expires = d.renewalDate;
      d.alerts = d.alerts || [30, 15, 7, 1];
      reason = 'Reclassified from Due Dates/Investments to Records (Insurance)';
    }
    // 3. Misplaced Identity Documents (in 'inv' or 'due')
    else if (
      r.kind !== 'rec' &&
      (d.type === 'passport' ||
        d.type === 'aadhaar' ||
        d.type === 'pan' ||
        d.type === 'licence' ||
        /passport|aadhaar|pan card|driving licence/i.test(d.name || d.title || ''))
    ) {
      newKind = 'rec';
      d.title = d.title || d.name || 'Identity Document';
      reason = 'Reclassified from Investments to Records (Identity Documents)';
    }

    if (newKind !== r.kind) {
      count++;
      details.push({
        id: r.id,
        name: d.name || d.title || 'Entry',
        from: r.kind,
        to: newKind,
        reason,
      });
      return { ...r, kind: newKind, data: d };
    }
    return r;
  });

  return { migratedRows, reclassifiedCount: count, details };
}
