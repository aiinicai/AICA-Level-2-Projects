export type TransactionCategory =
  | 'Food'
  | 'Travel'
  | 'Shopping'
  | 'Bills'
  | 'Investment'
  | 'Healthcare'
  | 'Entertainment'
  | 'Other';

export type PaymentMode = 'Cash' | 'Card' | 'UPI' | 'Bank Transfer';

export type TransactionSource = 'manual' | 'image';

export interface LineItem {
  item: string;
  amount: number;
}

export interface Transaction {
  id: string;
  date: string; // YYYY-MM-DD
  amount: number;
  category: TransactionCategory;
  description: string;
  merchantName?: string;
  paymentMode: PaymentMode;
  source: TransactionSource;
  lineItems?: LineItem[];
  createdAt: string;
  notes?: string;
}

export interface ExtractedInvoiceData {
  confidence: 'high' | 'medium' | 'low' | 'unreadable';
  unreadableReason?: string;
  isHandwrittenOrNonEnglish?: boolean;
  merchantName?: string;
  date?: string;
  totalAmount?: number;
  category?: TransactionCategory;
  paymentMode?: PaymentMode;
  description?: string;
  lineItems?: LineItem[];
}

export interface SpendingInsight {
  monthlySummary: string;
  topCategories: Array<{
    category: string;
    amount: number;
    percentage: number;
    observation: string;
  }>;
  unusualSpikes: Array<{
    category: string;
    note: string;
  }>;
  savingsSuggestions: Array<{
    title: string;
    actionableTip: string;
    estimatedPotentialSavings?: string;
  }>;
  investmentSummary: string;
  generatedAt: string;
}
