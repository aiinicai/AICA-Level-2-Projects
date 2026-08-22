export type ModuleId =
  | 'dashboard'
  | 'vouchers'
  | 'pdf-toolkit'
  | 'clientele'
  | 'intelligence'
  | 'products'
  | 'payment-trends'
  | 'signups'
  | 'branding'
  | 'guide';

export type UserRole =
  | 'admin'
  | 'finance'
  | 'operations'
  | 'procurement'
  | 'client_portal';

export type UserStatus = 'pending' | 'approved' | 'rejected';

export type CurrencyCode = 'TZS' | 'USD' | 'INR' | 'CNY' | 'ZAR' | 'GBP' | 'EUR';

export interface User {
  id: string;
  companyId: string;
  name: string;
  email: string;
  role: UserRole;
  status: UserStatus;
  linkedClientId?: string; // present when role === 'client_portal'
  mobile?: string;
  avatarUrl?: string;
  createdAt: string;
}

export interface SignupRequest {
  id: string;
  companyId: string;
  name: string;
  email: string;
  mobile: string;
  requestedRole: UserRole;
  status: UserStatus;
  linkedClientId?: string;
  linkedClientName?: string;
  decidedBy?: string;
  decidedAt?: string;
  createdAt: string;
  notes?: string;
}

export interface EmailNotificationLog {
  id: string;
  companyId: string;
  recipientEmail: string;
  recipientName: string;
  subject: string;
  bodyText: string;
  sentAt: string;
  type: 'signup_pending_approval' | 'signup_approved' | 'signup_rejected' | 'invoice_issued';
}

export type VoucherType = 'PO' | 'LPO' | 'PROFORMA' | 'SALES' | 'DELIVERY' | 'GATE_PASS';

export type VoucherStatus = 'draft' | 'finalized' | 'paid' | 'expired';

export type VatRule = 'exempt' | 'standard' | 'optional';

export type OcrProviderType = 'none' | 'anthropic' | 'other';

export interface OcrConfig {
  provider: OcrProviderType;
  apiKeyMasked?: string;
  apiKeyEncrypted?: string;
  baseUrl?: string;
}

export interface CompanyBankDetails {
  bankName: string;
  accountName: string;
  accountNumber: string;
  swiftCode: string;
  branchName?: string;
}

export interface ThemeConfig {
  primaryColor: string;
  secondaryColor: string;
  accentColor: string;
  fontFamily: string;
}

export interface CompanyProfile {
  id: string;
  name: string;
  companyCode: string; // Unique alphanumeric code, e.g. KILI-2026
  tin: string; // 9 digits, e.g. 104-582-931
  vrn?: string; // VAT Registration Number
  address: string;
  phone: string;
  email: string;
  website: string;
  bankDetails: CompanyBankDetails;
  logoUrl?: string;
  stampUrl?: string;
  signatureUrl?: string;
  theme: ThemeConfig;
  ocrConfig?: OcrConfig;
  createdAt: string;
  updatedAt: string;
}

export interface ClientContact {
  id: string;
  name: string;
  role?: string;
  phone: string;
  email: string;
  isPrimary: boolean;
}

export type ClientDocType =
  | 'tin_certificate'
  | 'bank_account_letter'
  | 'shareholder_id'
  | 'brela_search'
  | 'business_license'
  | 'ewura_license'
  | 'incorporation_certificate'
  | 'ubo_certificate'
  | 'vrn_certificate'
  | 'tax_clearance'
  | 'other';

export interface ClientDocument {
  id: string;
  companyId: string;
  clientId: string;
  docType: ClientDocType;
  title: string;
  fileName: string;
  fileSize: number;
  dataUrl: string;
  uploadedAt: string;
  notes?: string;
}

export interface ClientRequirement {
  id: string;
  companyId: string;
  clientId: string;
  productName: string;
  expectedQuantity: number;
  unit: 'MT' | 'Liters' | 'Drums' | 'Bags' | 'Trips' | 'Units' | 'Days' | 'Hours';
  period: 'monthly' | 'quarterly' | 'annual';
  notes?: string;
}

export interface Client {
  id: string;
  companyId: string;
  name: string;
  contactPerson: string;
  mobile: string;
  email: string;
  additionalEmails?: string[];
  contacts?: ClientContact[];
  address: string;
  tin: string; // 9 digits formatted XXX-XXX-XXX
  licenseNo: string;
  isVatRegistered: boolean;
  vrn?: string;
  tags: string[];
  paymentTermsType: 'prepaid' | 'credit';
  creditDays?: number; // e.g. 14, 30, 45, 60 days
  creditLimit?: number; // in TZS
  requirements?: ClientRequirement[];
  notes?: string;
  createdAt: string;
  updatedAt: string;
}

export interface ItemMaster {
  id: string;
  companyId: string;
  name: string;
  category: 'Bitumen' | 'Fuel' | 'Logistics & Transport' | 'Construction' | 'Custom';
  unit: string;
  standardRate: number; // in TZS or base currency
  vatRule: VatRule; // 'exempt' (0% locked), 'standard' (18% editable), 'optional' (18% or 0% toggleable)
  defaultVatPercent: number;
  description?: string;
  isActive?: boolean;
}

export interface VoucherItem {
  id: string;
  itemName: string;
  description?: string;
  quantity: number;
  unit?: string;
  rate: number;
  vatRule?: VatRule;
  vatApplied: boolean;
  vatPercent: number; // 0 or 18
  amount: number; // qty * rate
  vatAmount: number; // amount * (vatPercent / 100)
  lineTotal: number; // amount + vatAmount
}

export interface Voucher {
  id: string;
  companyId: string;
  type: VoucherType;
  docNumber: string; // e.g., PI-2026-0001, INV-2026-0001
  docDate: string; // YYYY-MM-DD
  dueDate?: string;
  requestedDeliveryDate?: string;
  paymentTerms?: string;
  clientId: string;
  clientName: string;
  clientAddress: string;
  clientMobile: string;
  clientTin: string;
  currency: CurrencyCode;
  exchangeRate?: number; // Rate per 1 foreign currency unit vs TZS
  items: VoucherItem[];
  subtotal: number;
  totalVat: number;
  grandTotal: number;
  roundOffEnabled: boolean;
  roundOffAdjustment: number;
  finalGrandTotal: number;
  amountInWords?: string;
  proformaValidityDays?: 3 | 5 | 7 | 10;
  expiresOn?: string; // YYYY-MM-DD for Proformas
  // Gate Pass specific fields (No VAT/pricing on this type)
  direction?: 'inward' | 'outward';
  vehicleRegistration?: string;
  driverName?: string;
  driverLicenseNumber?: string;
  goodsDescription?: string;
  quantityUnit?: string;
  linkedVoucherId?: string;
  linkedVoucherNumber?: string;
  authorizedBy?: string;
  gatePassTime?: string;
  notes?: string;
  status: VoucherStatus;
  paidAmount?: number;
  paidDate?: string;
  createdBy?: string;
  createdAt: string;
  updatedAt: string;
}

export interface PaymentRecord {
  id: string;
  companyId: string;
  clientId: string;
  voucherId: string;
  docNumber: string;
  amount: number;
  paymentDate: string;
  paymentMethod: 'bank_transfer' | 'cheque' | 'cash' | 'mobile_money';
  referenceNumber: string;
  notes?: string;
  createdAt: string;
}

export interface ClientPaymentMetric {
  clientId: string;
  clientName: string;
  paymentTermsType: 'prepaid' | 'credit';
  creditDays: number;
  approvedCreditLimit: number;
  currentOutstanding: number;
  creditUtilizationPercent: number;
  totalInvoiced: number;
  totalPaid: number;
  averageDaysToPay: number;
  overdueInvoicesCount: number;
  overdueAmount: number;
  paymentStatus: 'healthy' | 'warning' | 'critical';
  lastPaymentDate?: string;
}

export interface PaymentTrendAnalyticsData {
  companyId: string;
  averageDaysToPay: number;
  totalOutstandingAmount: number;
  totalOverdueAmount: number;
  totalPaidAmount: number;
  overdueInvoicesCount: number;
  totalCreditLimit: number;
  averageCreditUtilization: number;
  clientMetrics: ClientPaymentMetric[];
}

export interface DemandGapAnalysis {
  client: Client;
  requirement: ClientRequirement;
  actualQuantitySupplied: number;
  gapQuantity: number;
  fulfillmentPercent: number;
  isUnderSupplied: boolean;
  estimatedLostRevenueTZS: number;
  aiSalesAdvisory?: string;
}

export interface CRMClientAnalytics {
  client: Client;
  totalSpent: number;
  orderCount: number;
  averageDaysBetweenOrders: number;
  daysSinceLastOrder?: number;
  lastOrderDate?: string;
  isOverdueForOrder: boolean;
}

export interface MarketNewsItem {
  id: string;
  category: string;
  title: string;
  summary: string;
  source: string;
  timestamp: string;
}

export interface MarketData {
  lastUpdated: string;
  forex: {
    usd_tzs: {
      rate: number;
      bid: number;
      ask: number;
      change24h: string;
      summary: string;
    };
  };
  commodities: {
    brent_crude_usd: {
      price: number;
      change24h: string;
      summary: string;
    };
    bitumen_60_70_usd_ton: {
      price: number;
      change24h: string;
      summary: string;
    };
  };
  dar_port_corridor: {
    waiting_time_days: number;
    customs_clearance_dwell_days: number;
    fuel_price_dar_tzs_liter: number;
    corridor_status: string;
  };
  marketNews: MarketNewsItem[];
}

export interface SavedIntelligenceItem {
  id: string;
  title: string;
  category: string;
  summary: string;
  timestamp: string;
}

export interface NewsCacheItem {
  id: string;
  category: 'fx' | 'oil' | 'logistics';
  headline: string;
  summary: string;
  source: string;
  sourceUrl?: string;
  publishedAt: string;
  fetchedAt: string;
  isSaved?: boolean;
  isDismissed?: boolean;
  impactScore?: 'High' | 'Medium' | 'Low';
  tags?: string[];
}

export interface MultiTenantDatabaseState {
  currentCompanyId: string;
  currentUserId: string;
  companies: CompanyProfile[];
  users: User[];
  signupRequests: SignupRequest[];
  emailLogs: EmailNotificationLog[];
  clients: Client[];
  clientDocuments: ClientDocument[];
  clientRequirements: ClientRequirement[];
  itemCatalog: ItemMaster[];
  vouchers: Voucher[];
  payments: PaymentRecord[];
  newsItems?: NewsCacheItem[];
  marketDataCache?: MarketData;
  savedIntelligence?: SavedIntelligenceItem[];
  version: number;
  lastBackupAt?: string;
}

export interface PDFWatermarkConfig {
  text: string;
  color: string;
  opacity: number;
  fontSize: number;
  rotation: number;
}
