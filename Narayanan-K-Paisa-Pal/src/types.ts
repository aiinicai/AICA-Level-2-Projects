export type Kind = 'due' | 'inv' | 'rec' | 'util';

export type DueCategory =
  | 'fd'
  | 'insurance'
  | 'mediclaim'
  | 'vehicle'
  | 'lpg'
  | 'utility'
  | 'emi';

export type UtilityType =
  | 'electricity'
  | 'water'
  | 'landline'
  | 'mobile'
  | 'broadband'
  | 'gas'
  | 'lpg'
  | 'piped_gas'
  | 'dth'
  | 'maintenance'
  | 'other';

export type Frequency =
  | 'once'
  | 'monthly'
  | 'bimonthly'
  | 'quarterly'
  | 'halfyearly'
  | 'annual'
  | 'days';

export type InvType =
  | 'fd'
  | 'rd'
  | 'bond'
  | 'mf'
  | 'stocks'
  | 'gold'
  | 'ppf'
  | 'nps'
  | 'property'
  | 'insurance'
  | 'other';

export type RecType =
  | 'id'
  | 'licence'
  | 'passport'
  | 'pan'
  | 'aadhaar'
  | 'voter'
  | 'ration'
  | 'vehicle'
  | 'bank'
  | 'policy'
  | 'insurance'
  | 'nominee'
  | 'contact'
  | 'other';

export interface UtilityPaymentRecord {
  id: string;
  date: string; // YYYY-MM-DD
  amount: number;
  receiptRef?: string;
  notes?: string;
}

export interface UtilityRowData {
  name: string; // Service / Provider description (e.g. "Adani Electricity Mumbai")
  utilityType?: UtilityType | string;
  category?: string;
  provider?: string; // Provider / Biller (e.g. "Adani Electricity", "BESCOM")
  accountNumber?: string; // Consumer # / Meter # / CA # / Account # (text, preserves leading zeros)
  consumerNumber?: string;
  holder?: string; // Family member name / Property (e.g. "Arun Menon - Apartment 4B")
  person?: string;
  property?: string;
  billingPeriod?: string; // e.g. "Oct 2026" or "01-09-2026 to 30-09-2026"
  billAmount?: number | '';
  amount?: number | '';
  dueDate?: string; // YYYY-MM-DD (IST)
  due?: string;
  status: 'pending' | 'partially_paid' | 'paid' | string;
  paidAmount?: number | '';
  balanceOutstanding?: number | ''; // billAmount - (paidAmount || 0)
  lastPaymentDate?: string;
  receiptAttachment?: string;
  paymentHistory?: UtilityPaymentRecord[];
  freq?: Frequency | string;
  nextDueDate?: string;
  alerts?: number[]; // e.g. [7, 3, 0, -3] (7d before, 3d before, due date, 3d overdue)
  anchor?: number; // anchor day of month
  notes?: string;
  attachmentName?: string;
}

export interface DueRowData {
  name: string;
  category: DueCategory | string;
  provider?: string;
  holder?: string;
  ref?: string;
  amount?: number | '';
  due: string; // YYYY-MM-DD
  freq: Frequency | string;
  interval?: number | '';
  alerts?: number[];
  status?: 'pending' | 'paid';
  anchor?: number;
  notes?: string;
  attachmentName?: string;
}

export interface InvRowData {
  name: string;
  holder?: string;
  type: InvType | string;
  institution?: string;
  ref?: string;
  invested?: number | '';
  current?: number | '';
  rate?: number | '';
  start?: string;
  maturity?: string;
  nextint?: string;
  alerts?: number[];
  notes?: string;
  attachmentName?: string;
}

export interface RecRowData {
  title: string;
  type: RecType | string;
  category?: 'identity' | 'insurance' | 'financial' | 'other';
  holder?: string;
  number?: string;
  issued?: string;
  expires?: string; // Optional/nullable for permanent IDs like PAN & Aadhaar
  issuingAuthority?: string;
  alerts?: number[];
  notes?: string;
  attachmentName?: string;

  // Specific fields for insurance policies
  insurer?: string;
  policyNumber?: string;
  policyholder?: string;
  insuredPersons?: string; // Person(s) covered or vehicle model/reg number
  insuranceType?: 'medical' | 'vehicle' | 'term' | 'accident' | 'home' | 'other';
  sumInsured?: number | ''; // DOES NOT count towards investment net worth
  premium?: number | ''; // DOES NOT count towards investment net worth
  paymentFrequency?: Frequency | string;
  commencementDate?: string;
  renewalDate?: string; // Policy renewal date
  premiumDueDate?: string; // Premium payment due date
  nominee?: string;
  linkedInvestmentValue?: number | ''; // For ULIP/endowment, tracked separately without double-counting
}

export interface AppRow {
  id: string;
  kind: Kind;
  data: Record<string, any>;
}

export interface UserProfile {
  whatsapp?: string;
  showUpload?: boolean;
  theme?: 'system' | 'light' | 'dark';
  pinEnabled?: boolean;
  pinHash?: string;
  pinSalt?: string;
  biometricEnabled?: boolean;
  emergencyNotes?: string;
  emergencyContacts?: { name: string; relation: string; phone: string }[];
  primaryBank?: string;
  nomineeNotes?: string;
  // Vault-level cryptographic encryption
  vaultEncrypted?: boolean;
  vaultSalt?: string;
  vaultVerification?: string; // AES-GCM ciphertext of known canary string
  vaultIv?: string;
  recoveryKeyHash?: string; // SHA-256 hash of 16-character recovery key
  recoveryKeySalt?: string;
  lastBackupAt?: string;
}

export interface StorageResult {
  success: boolean;
  error?: string;
}

export interface EncryptedVaultData {
  encrypted: true;
  version: number;
  iv: string;
  ciphertext: string;
  salt: string;
}

export interface NormalizedAlert {
  row: AppRow;
  vk: 'due' | 'mat' | 'exp';
  label: string;
  name: string;
  sub: string;
  who: string;
  amount: number;
  due: string;
  alerts: number[];
  paid: boolean;
}

export type AlertState = 'overdue' | 'today' | 'soon' | 'later' | 'paid';
