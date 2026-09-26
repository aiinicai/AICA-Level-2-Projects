import { Transaction } from '../types';

const STORAGE_KEY = 'smart_expense_tracker_transactions_v2';
const INSIGHTS_CACHE_KEY = 'smart_expense_tracker_insights_v2';

// Realistic sample transactions for current month (September 2026) and previous month (August 2026)
const INITIAL_SAMPLE_TRANSACTIONS: Transaction[] = [
  // Current month (Sep 2026)
  {
    id: 'tx-sep-1',
    date: '2026-09-25',
    amount: 1450,
    category: 'Food',
    description: 'Swiggy Gourmet Dinner with friends',
    merchantName: 'Swiggy',
    paymentMode: 'UPI',
    source: 'image',
    lineItems: [
      { item: 'Paneer Butter Masala', amount: 480 },
      { item: 'Garlic Naan (4 pcs)', amount: 260 },
      { item: 'Dal Makhani', amount: 390 },
      { item: 'Taxes & Delivery', amount: 320 },
    ],
    createdAt: '2026-09-25T20:30:00.000Z',
  },
  {
    id: 'tx-sep-2',
    date: '2026-09-23',
    amount: 25000,
    category: 'Investment',
    description: 'Nifty 50 Index Fund Monthly SIP',
    merchantName: 'HDFC Mutual Fund',
    paymentMode: 'Bank Transfer',
    source: 'image',
    createdAt: '2026-09-23T09:15:00.000Z',
  },
  {
    id: 'tx-sep-3',
    date: '2026-09-21',
    amount: 4200,
    category: 'Bills',
    description: 'Electricity bill payment',
    merchantName: 'Tata Power',
    paymentMode: 'UPI',
    source: 'manual',
    createdAt: '2026-09-21T11:00:00.000Z',
  },
  {
    id: 'tx-sep-4',
    date: '2026-09-18',
    amount: 3850,
    category: 'Shopping',
    description: 'Weekend grocery haul & home essentials',
    merchantName: 'D-Mart Supermarket',
    paymentMode: 'Card',
    source: 'image',
    lineItems: [
      { item: 'Cold-pressed Cooking Oil (5L)', amount: 980 },
      { item: 'Basmati Rice & Pulses', amount: 1450 },
      { item: 'Dry Fruits & Nuts pack', amount: 820 },
      { item: 'Cleaning essentials', amount: 600 },
    ],
    createdAt: '2026-09-18T18:45:00.000Z',
  },
  {
    id: 'tx-sep-5',
    date: '2026-09-15',
    amount: 850,
    category: 'Travel',
    description: 'Cab fare to tech park meeting',
    merchantName: 'Uber',
    paymentMode: 'UPI',
    source: 'manual',
    createdAt: '2026-09-15T08:30:00.000Z',
  },
  {
    id: 'tx-sep-6',
    date: '2026-09-12',
    amount: 10000,
    category: 'Investment',
    description: 'Gold ETF accumulation',
    merchantName: 'Nippon India Gold ETF',
    paymentMode: 'Bank Transfer',
    source: 'manual',
    createdAt: '2026-09-12T14:10:00.000Z',
  },
  {
    id: 'tx-sep-7',
    date: '2026-09-10',
    amount: 1199,
    category: 'Entertainment',
    description: 'Monthly streaming subscriptions',
    merchantName: 'Netflix & Spotify',
    paymentMode: 'Card',
    source: 'manual',
    createdAt: '2026-09-10T10:00:00.000Z',
  },
  {
    id: 'tx-sep-8',
    date: '2026-09-08',
    amount: 2450,
    category: 'Healthcare',
    description: 'Prescription medicines and vitamins',
    merchantName: 'Apollo Pharmacy',
    paymentMode: 'UPI',
    source: 'image',
    lineItems: [
      { item: 'Multivitamin supplements', amount: 1150 },
      { item: 'First aid & allergy medication', amount: 1300 },
    ],
    createdAt: '2026-09-08T16:20:00.000Z',
  },
  {
    id: 'tx-sep-9',
    date: '2026-09-04',
    amount: 1650,
    category: 'Food',
    description: 'Artisanal Cafe brunch and coffee',
    merchantName: 'Third Wave Coffee',
    paymentMode: 'Card',
    source: 'manual',
    createdAt: '2026-09-04T12:30:00.000Z',
  },
  {
    id: 'tx-sep-10',
    date: '2026-09-02',
    amount: 2800,
    category: 'Travel',
    description: 'Car fuel refill (Petrol)',
    merchantName: 'Indian Oil Petrol Pump',
    paymentMode: 'Card',
    source: 'manual',
    createdAt: '2026-09-02T19:00:00.000Z',
  },

  // Previous month (August 2026) for trend & comparison
  {
    id: 'tx-aug-1',
    date: '2026-08-28',
    amount: 25000,
    category: 'Investment',
    description: 'Nifty 50 Index Fund Monthly SIP',
    merchantName: 'HDFC Mutual Fund',
    paymentMode: 'Bank Transfer',
    source: 'manual',
    createdAt: '2026-08-28T10:00:00.000Z',
  },
  {
    id: 'tx-aug-2',
    date: '2026-08-22',
    amount: 5400,
    category: 'Shopping',
    description: 'Independence Day festive sale clothes',
    merchantName: 'Myntra',
    paymentMode: 'Card',
    source: 'manual',
    createdAt: '2026-08-22T15:20:00.000Z',
  },
  {
    id: 'tx-aug-3',
    date: '2026-08-18',
    amount: 3900,
    category: 'Bills',
    description: 'Broadband and mobile family pack',
    merchantName: 'Airtel Broadband',
    paymentMode: 'UPI',
    source: 'manual',
    createdAt: '2026-08-18T11:45:00.000Z',
  },
  {
    id: 'tx-aug-4',
    date: '2026-08-14',
    amount: 2200,
    category: 'Food',
    description: 'Weekend family dining',
    merchantName: 'Barbeque Nation',
    paymentMode: 'Card',
    source: 'manual',
    createdAt: '2026-08-14T21:00:00.000Z',
  },
  {
    id: 'tx-aug-5',
    date: '2026-08-08',
    amount: 3200,
    category: 'Travel',
    description: 'Intercity train ticket booking',
    merchantName: 'IRCTC',
    paymentMode: 'UPI',
    source: 'manual',
    createdAt: '2026-08-08T09:30:00.000Z',
  },
];

export function getStoredTransactions(): Transaction[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(INITIAL_SAMPLE_TRANSACTIONS));
      return INITIAL_SAMPLE_TRANSACTIONS;
    }
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) {
      return parsed;
    }
    return INITIAL_SAMPLE_TRANSACTIONS;
  } catch (err) {
    console.error('Error reading localStorage transactions:', err);
    return INITIAL_SAMPLE_TRANSACTIONS;
  }
}

export function saveTransactions(transactions: Transaction[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(transactions));
  } catch (err) {
    console.error('Error saving transactions to localStorage:', err);
  }
}

export function addTransaction(data: Omit<Transaction, 'id' | 'createdAt'>): Transaction {
  const current = getStoredTransactions();
  const newTx: Transaction = {
    ...data,
    id: 'tx-' + Date.now() + '-' + Math.random().toString(36).substring(2, 7),
    createdAt: new Date().toISOString(),
  };
  const updated = [newTx, ...current];
  saveTransactions(updated);
  return newTx;
}

export function updateTransaction(updatedTx: Transaction): void {
  const current = getStoredTransactions();
  const next = current.map((tx) => (tx.id === updatedTx.id ? updatedTx : tx));
  saveTransactions(next);
}

export function deleteTransaction(id: string): void {
  const current = getStoredTransactions();
  const next = current.filter((tx) => tx.id !== id);
  saveTransactions(next);
}

/**
 * Checks for duplicates (same date and same amount)
 * Returns array of matching existing transactions
 */
export function checkDuplicateTransaction(
  date: string,
  amount: number,
  excludeId?: string
): Transaction[] {
  if (!date || !amount) return [];
  const transactions = getStoredTransactions();
  return transactions.filter(
    (tx) =>
      tx.id !== excludeId &&
      tx.date === date &&
      Math.abs(Number(tx.amount) - Number(amount)) < 0.01
  );
}

export function resetToSampleTransactions(): Transaction[] {
  saveTransactions(INITIAL_SAMPLE_TRANSACTIONS);
  localStorage.removeItem(INSIGHTS_CACHE_KEY);
  return INITIAL_SAMPLE_TRANSACTIONS;
}

export function clearAllTransactions(): void {
  saveTransactions([]);
  localStorage.removeItem(INSIGHTS_CACHE_KEY);
}

export function getCachedInsights(): any | null {
  try {
    const raw = localStorage.getItem(INSIGHTS_CACHE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function saveCachedInsights(insights: any): void {
  try {
    localStorage.setItem(INSIGHTS_CACHE_KEY, JSON.stringify(insights));
  } catch (e) {
    console.warn('Could not cache insights:', e);
  }
}
