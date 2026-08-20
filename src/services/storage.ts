import {
  MultiTenantDatabaseState,
  CompanyProfile,
  Client,
  Voucher,
  VoucherType,
  VoucherStatus,
  ClientDocument,
  ClientRequirement,
  ItemMaster,
  User,
  UserRole,
  SignupRequest,
  EmailNotificationLog,
  PaymentRecord,
  PaymentTrendAnalyticsData,
  ClientPaymentMetric,
  MarketData,
  SavedIntelligenceItem,
  CRMClientAnalytics,
  DemandGapAnalysis,
  NewsCacheItem,
} from '../types';
import {
  initialDatabaseState,
  demoCompanies,
  demoUsers,
  demoSignupRequests,
  demoEmailLogs,
  demoItemCatalog,
  demoClients,
  demoClientRequirements,
  demoClientDocuments,
  demoVouchers,
  demoPayments,
  demoMarketNews
} from '../data/seedData';
import { convertNumberToWords } from '../utils/numberToWords';

const STORAGE_KEY = 'kilitrade_multitenant_saas_v3';

export function formatTIN(val: string): string {
  const digits = val.replace(/\D/g, '').slice(0, 9);
  if (digits.length <= 3) return digits;
  if (digits.length <= 6) return `${digits.slice(0, 3)}-${digits.slice(3)}`;
  return `${digits.slice(0, 3)}-${digits.slice(3, 6)}-${digits.slice(6, 9)}`;
}

export function validateTIN(val: string): boolean {
  const digits = val.replace(/\D/g, '');
  return digits.length === 9;
}

export class StorageService {
  private static instance: StorageService;
  private state: MultiTenantDatabaseState;
  private listeners: (() => void)[] = [];

  private constructor() {
    this.state = this.loadFromDisk();
    const currentCompany = this.getCompanyProfile();
    if (currentCompany) {
      this.applyTheme(currentCompany.theme);
    }
  }

  public static getInstance(): StorageService {
    if (!StorageService.instance) {
      StorageService.instance = new StorageService();
    }
    return StorageService.instance;
  }

  private loadFromDisk(): MultiTenantDatabaseState {
    try {
      const data = localStorage.getItem(STORAGE_KEY);
      if (data) {
        const parsed = JSON.parse(data) as Partial<MultiTenantDatabaseState>;
        return {
          ...initialDatabaseState,
          ...parsed,
          companies: parsed.companies && parsed.companies.length > 0 ? parsed.companies : demoCompanies,
          users: parsed.users && parsed.users.length > 0 ? parsed.users : demoUsers,
          signupRequests: parsed.signupRequests || demoSignupRequests,
          emailLogs: parsed.emailLogs || demoEmailLogs,
          clients: parsed.clients || demoClients,
          clientDocuments: parsed.clientDocuments || demoClientDocuments,
          clientRequirements: parsed.clientRequirements || demoClientRequirements,
          itemCatalog: parsed.itemCatalog || demoItemCatalog,
          vouchers: parsed.vouchers || demoVouchers,
          payments: parsed.payments || demoPayments,
          newsItems: parsed.newsItems || demoMarketNews,
        };
      }
    } catch (e) {
      console.warn('Failed to load multi-tenant DB state from storage, loading defaults', e);
    }
    return initialDatabaseState;
  }

  private saveToDisk(): void {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this.state));
      this.notifyListeners();
    } catch (e) {
      console.error('Failed to write multi-tenant DB state to storage', e);
    }
  }

  public subscribe(listener: () => void): () => void {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter((l) => l !== listener);
    };
  }

  private notifyListeners(): void {
    this.listeners.forEach((l) => {
      try {
        l();
      } catch (err) {
        console.error('Listener callback error', err);
      }
    });
  }

  public getState(): MultiTenantDatabaseState {
    return this.state;
  }

  // --- Company / Multi-Tenant Operations ---
  public getCompanies(): CompanyProfile[] {
    return this.state.companies;
  }

  public getCurrentCompanyId(): string {
    return this.state.currentCompanyId;
  }

  public getCompanyProfile(companyId?: string): CompanyProfile {
    const targetId = companyId || this.state.currentCompanyId;
    const found = this.state.companies.find((c) => c.id === targetId);
    return found || this.state.companies[0] || demoCompanies[0];
  }

  public getCompanyByCode(code: string): CompanyProfile | undefined {
    const clean = code.trim().toUpperCase();
    return this.state.companies.find((c) => c.companyCode.toUpperCase() === clean);
  }

  public switchCompany(companyId: string, preferredUserId?: string): void {
    const company = this.state.companies.find((c) => c.id === companyId);
    if (!company) return;

    this.state.currentCompanyId = companyId;

    // Pick first active user of that company or specified user
    if (preferredUserId) {
      const u = this.state.users.find((user) => user.id === preferredUserId && user.companyId === companyId);
      if (u) {
        this.state.currentUserId = u.id;
      }
    } else {
      const companyUser = this.state.users.find((u) => u.companyId === companyId && u.status === 'approved');
      if (companyUser) {
        this.state.currentUserId = companyUser.id;
      }
    }

    this.applyTheme(company.theme);
    this.saveToDisk();
  }

  public registerNewCompany(
    companyData: Omit<CompanyProfile, 'id' | 'companyCode' | 'createdAt' | 'updatedAt'>,
    adminUserData: { name: string; email: string; mobile?: string }
  ): { company: CompanyProfile; adminUser: User } {
    const newCompanyId = `comp_${Date.now()}`;
    const cleanPrefix = companyData.name
      .replace(/[^a-zA-Z]/g, '')
      .slice(0, 4)
      .toUpperCase() || 'CORP';
    const randSuffix = Math.floor(1000 + Math.random() * 9000);
    const companyCode = `${cleanPrefix}-${randSuffix}`;

    const newCompany: CompanyProfile = {
      ...companyData,
      id: newCompanyId,
      companyCode,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    const newUserId = `usr_${Date.now()}`;
    const newAdminUser: User = {
      id: newUserId,
      companyId: newCompanyId,
      name: adminUserData.name,
      email: adminUserData.email,
      mobile: adminUserData.mobile,
      role: 'admin',
      status: 'approved',
      createdAt: new Date().toISOString(),
    };

    // Seed initial standard items for this new company
    const starterItems: ItemMaster[] = [
      {
        id: `itm_${newCompanyId}_bit6070`,
        companyId: newCompanyId,
        name: 'Bitumen Grade 60/70 (Steel Drums 200L / Bulk MT)',
        category: 'Bitumen',
        unit: 'MT',
        standardRate: 1180000,
        vatRule: 'optional',
        defaultVatPercent: 18,
        description: 'Standard penetration grade paving asphalt for road construction.',
      },
      {
        id: `itm_${newCompanyId}_bit80100`,
        companyId: newCompanyId,
        name: 'Bitumen Grade 80/100 (Steel Drums 200L)',
        category: 'Bitumen',
        unit: 'MT',
        standardRate: 1220000,
        vatRule: 'optional',
        defaultVatPercent: 18,
        description: 'Medium penetration asphalt for highland & cold region projects.',
      },
      {
        id: `itm_${newCompanyId}_mc30`,
        companyId: newCompanyId,
        name: 'Cutback Bitumen MC-30 (Prime Coat)',
        category: 'Bitumen',
        unit: 'Drums',
        standardRate: 750000,
        vatRule: 'optional',
        defaultVatPercent: 18,
        description: 'Medium curing cutback liquid asphalt for aggregate base priming.',
      },
      {
        id: `itm_${newCompanyId}_diesel`,
        companyId: newCompanyId,
        name: 'Automotive Gas Oil (AGO Diesel - 50ppm)',
        category: 'Fuel',
        unit: 'Liters',
        standardRate: 3140,
        vatRule: 'exempt',
        defaultVatPercent: 0,
        description: 'Commercial fleet bulk diesel (Non-Vatable under fuel excise rules).',
      },
      {
        id: `itm_${newCompanyId}_petrol`,
        companyId: newCompanyId,
        name: 'MOGAS Unleaded Petrol (Premium Motor Spirit)',
        category: 'Fuel',
        unit: 'Liters',
        standardRate: 3080,
        vatRule: 'exempt',
        defaultVatPercent: 0,
        description: 'Motor spirit (Non-Vatable under fuel tax code).',
      },
      {
        id: `itm_${newCompanyId}_transport`,
        companyId: newCompanyId,
        name: 'Corridor Freight Transport & Logistics Dispatch',
        category: 'Logistics & Transport',
        unit: 'Trips',
        standardRate: 3800000,
        vatRule: 'standard',
        defaultVatPercent: 18,
        description: 'Containerized heavy truck haulage.',
      },
    ];

    this.state.companies.push(newCompany);
    this.state.users.push(newAdminUser);
    this.state.itemCatalog.push(...starterItems);

    this.state.currentCompanyId = newCompanyId;
    this.state.currentUserId = newUserId;

    this.applyTheme(newCompany.theme);
    this.saveToDisk();

    return { company: newCompany, adminUser: newAdminUser };
  }

  public saveCompanyProfile(updated: CompanyProfile): void {
    const idx = this.state.companies.findIndex((c) => c.id === updated.id);
    if (idx >= 0) {
      this.state.companies[idx] = { ...updated, updatedAt: new Date().toISOString() };
    } else {
      this.state.companies.push(updated);
    }
    if (updated.id === this.state.currentCompanyId) {
      this.applyTheme(updated.theme);
    }
    this.saveToDisk();
  }

  // --- Users & Authentication ---
  public isSessionActive(): boolean {
    try {
      const activeId = localStorage.getItem('kilitrade_active_session_user_id');
      if (!activeId) return false;
      const user = this.state.users.find((u) => u.id === activeId && u.status === 'approved');
      return Boolean(user);
    } catch {
      return false;
    }
  }

  public login(user: User): void {
    localStorage.setItem('kilitrade_active_session_user_id', user.id);
    this.setCurrentUser(user);
  }

  public logout(): void {
    localStorage.removeItem('kilitrade_active_session_user_id');
    this.saveToDisk();
  }

  public getCurrentUser(): User {
    const activeId = localStorage.getItem('kilitrade_active_session_user_id');
    if (activeId) {
      const found = this.state.users.find((u) => u.id === activeId && u.status === 'approved');
      if (found) return found;
    }

    const found = this.state.users.find((u) => u.id === this.state.currentUserId);
    if (found) return found;

    const companyUser = this.state.users.find(
      (u) => u.companyId === this.state.currentCompanyId && u.status === 'approved'
    );
    return companyUser || this.state.users[0] || demoUsers[0];
  }

  public setCurrentUser(user: User): void {
    this.state.currentUserId = user.id;
    if (user.companyId && user.companyId !== this.state.currentCompanyId) {
      this.state.currentCompanyId = user.companyId;
      const comp = this.getCompanyProfile(user.companyId);
      if (comp) this.applyTheme(comp.theme);
    }
    this.saveToDisk();
  }

  public getUsers(companyId?: string): User[] {
    const cId = companyId || this.state.currentCompanyId;
    return this.state.users.filter((u) => u.companyId === cId && u.status === 'approved');
  }

  public getAllUsersAcrossCompanies(): User[] {
    return this.state.users;
  }

  // --- Sign-up & Approval Workflows ---
  public getSignupRequests(companyId?: string): SignupRequest[] {
    const cId = companyId || this.state.currentCompanyId;
    return this.state.signupRequests.filter((r) => r.companyId === cId);
  }

  public submitSignupRequest(data: {
    companyCode: string;
    name: string;
    email: string;
    mobile: string;
    requestedRole: UserRole;
    linkedClientName?: string;
    notes?: string;
  }): { success: boolean; message: string; request?: SignupRequest } {
    const targetCompany = this.getCompanyByCode(data.companyCode);
    if (!targetCompany) {
      return { success: false, message: `Invalid Company Code "${data.companyCode}". Please verify with your corporate administrator.` };
    }

    // Check if user already exists
    const existingUser = this.state.users.find(
      (u) => u.companyId === targetCompany.id && u.email.toLowerCase() === data.email.toLowerCase()
    );
    if (existingUser) {
      return { success: false, message: `An account with email ${data.email} already exists in ${targetCompany.name}.` };
    }

    const newReq: SignupRequest = {
      id: `req_${Date.now()}`,
      companyId: targetCompany.id,
      name: data.name,
      email: data.email,
      mobile: data.mobile,
      requestedRole: data.requestedRole,
      status: 'pending',
      linkedClientName: data.linkedClientName,
      createdAt: new Date().toISOString(),
      notes: data.notes,
    };

    this.state.signupRequests.unshift(newReq);

    // Send transactional email notification to company admins
    const companyAdmins = this.state.users.filter(
      (u) => u.companyId === targetCompany.id && u.role === 'admin' && u.status === 'approved'
    );

    companyAdmins.forEach((admin) => {
      const emailLog: EmailNotificationLog = {
        id: `email_${Date.now()}_${Math.floor(Math.random() * 1000)}`,
        companyId: targetCompany.id,
        recipientEmail: admin.email,
        recipientName: admin.name,
        subject: `Action Required: New ${data.requestedRole === 'client_portal' ? 'Client' : 'Staff'} Sign-up Request (${data.name})`,
        bodyText: `Hello ${admin.name},\n\n${data.name} (${data.email}) has submitted a sign-up request for role "${data.requestedRole}" using company code ${targetCompany.companyCode}.\n\nPlease review and approve this request in your Pending Sign-ups queue.\n\nBest regards,\nPlatform Security Bot`,
        sentAt: new Date().toISOString(),
        type: 'signup_pending_approval',
      };
      this.state.emailLogs.unshift(emailLog);
    });

    this.saveToDisk();
    return {
      success: true,
      message: `Sign-up request submitted for approval. Notification email dispatched to ${targetCompany.name} administrators.`,
      request: newReq,
    };
  }

  public approveSignupRequest(
    requestId: string,
    decidedByUserId: string,
    linkedClientId?: string
  ): { success: boolean; user?: User } {
    const req = this.state.signupRequests.find((r) => r.id === requestId);
    if (!req) return { success: false };

    req.status = 'approved';
    req.decidedBy = decidedByUserId;
    req.decidedAt = new Date().toISOString();
    req.linkedClientId = linkedClientId;

    const newUser: User = {
      id: `usr_${Date.now()}`,
      companyId: req.companyId,
      name: req.name,
      email: req.email,
      mobile: req.mobile,
      role: req.requestedRole,
      status: 'approved',
      linkedClientId: linkedClientId,
      createdAt: new Date().toISOString(),
    };

    this.state.users.push(newUser);

    // Add confirmation email log
    const emailLog: EmailNotificationLog = {
      id: `email_${Date.now()}`,
      companyId: req.companyId,
      recipientEmail: req.email,
      recipientName: req.name,
      subject: `Account Approved: Welcome to ${this.getCompanyProfile(req.companyId).name}`,
      bodyText: `Hello ${req.name},\n\nYour sign-up request for "${req.requestedRole}" access has been approved by administrator.\n\nYou can now log in to the portal.\n\nBest regards,\nPlatform Administrator`,
      sentAt: new Date().toISOString(),
      type: 'signup_approved',
    };
    this.state.emailLogs.unshift(emailLog);

    this.saveToDisk();
    return { success: true, user: newUser };
  }

  public rejectSignupRequest(requestId: string, decidedByUserId: string, reason?: string): boolean {
    const req = this.state.signupRequests.find((r) => r.id === requestId);
    if (!req) return false;

    req.status = 'rejected';
    req.decidedBy = decidedByUserId;
    req.decidedAt = new Date().toISOString();
    if (reason) req.notes = `${req.notes || ''} [Rejected reason: ${reason}]`;

    // Add rejection email log
    const emailLog: EmailNotificationLog = {
      id: `email_${Date.now()}`,
      companyId: req.companyId,
      recipientEmail: req.email,
      recipientName: req.name,
      subject: `Account Status Update: ${this.getCompanyProfile(req.companyId).name}`,
      bodyText: `Hello ${req.name},\n\nYour sign-up request has been declined.\nReason: ${reason || 'Application not verified.'}\n\nContact your corporate administrator if you believe this is an error.`,
      sentAt: new Date().toISOString(),
      type: 'signup_rejected',
    };
    this.state.emailLogs.unshift(emailLog);

    this.saveToDisk();
    return true;
  }

  public getEmailLogs(companyId?: string): EmailNotificationLog[] {
    const cId = companyId || this.state.currentCompanyId;
    return this.state.emailLogs.filter((e) => e.companyId === cId);
  }

  // --- Clientele (CRM) Scoped to Current Company ---
  public getClients(): Client[] {
    return this.state.clients.filter((c) => c.companyId === this.state.currentCompanyId);
  }

  public getClientById(id: string): Client | undefined {
    return this.state.clients.find((c) => c.id === id && c.companyId === this.state.currentCompanyId);
  }

  public saveClient(client: Client): void {
    const scopedClient = { ...client, companyId: this.state.currentCompanyId };
    const index = this.state.clients.findIndex((c) => c.id === client.id);
    if (index >= 0) {
      this.state.clients[index] = { ...scopedClient, updatedAt: new Date().toISOString() };
    } else {
      this.state.clients.push({
        ...scopedClient,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      });
    }
    this.saveToDisk();
  }

  public deleteClient(id: string): void {
    this.state.clients = this.state.clients.filter((c) => c.id !== id);
    this.state.clientDocuments = this.state.clientDocuments.filter((d) => d.clientId !== id);
    this.state.clientRequirements = this.state.clientRequirements.filter((r) => r.clientId !== id);
    this.saveToDisk();
  }

  // --- KYC Documents ---
  public getClientDocuments(clientId: string): ClientDocument[] {
    return this.state.clientDocuments.filter(
      (d) => d.clientId === clientId && d.companyId === this.state.currentCompanyId
    );
  }

  public saveClientDocument(doc: ClientDocument): void {
    const scopedDoc = { ...doc, companyId: this.state.currentCompanyId };
    const index = this.state.clientDocuments.findIndex((d) => d.id === doc.id);
    if (index >= 0) {
      this.state.clientDocuments[index] = scopedDoc;
    } else {
      this.state.clientDocuments.push(scopedDoc);
    }
    this.saveToDisk();
  }

  public deleteClientDocument(id: string): void {
    this.state.clientDocuments = this.state.clientDocuments.filter((d) => d.id !== id);
    this.saveToDisk();
  }

  // --- Client Requirements ---
  public getClientRequirements(clientId: string): ClientRequirement[] {
    return this.state.clientRequirements.filter(
      (r) => r.clientId === clientId && r.companyId === this.state.currentCompanyId
    );
  }

  public saveClientRequirement(req: ClientRequirement): void {
    const scopedReq = { ...req, companyId: this.state.currentCompanyId };
    const index = this.state.clientRequirements.findIndex((r) => r.id === req.id);
    if (index >= 0) {
      this.state.clientRequirements[index] = scopedReq;
    } else {
      this.state.clientRequirements.push(scopedReq);
    }
    this.saveToDisk();
  }

  public deleteClientRequirement(id: string): void {
    this.state.clientRequirements = this.state.clientRequirements.filter((r) => r.id !== id);
    this.saveToDisk();
  }

  // --- Item Catalog ---
  public getItemCatalog(): ItemMaster[] {
    return this.state.itemCatalog.filter((i) => i.companyId === this.state.currentCompanyId);
  }

  public saveItem(item: ItemMaster): void {
    const scopedItem = { ...item, companyId: this.state.currentCompanyId };
    const index = this.state.itemCatalog.findIndex((i) => i.id === item.id);
    if (index >= 0) {
      this.state.itemCatalog[index] = scopedItem;
    } else {
      this.state.itemCatalog.push(scopedItem);
    }
    this.saveToDisk();
  }

  public deleteItem(id: string): void {
    this.state.itemCatalog = this.state.itemCatalog.filter((i) => i.id !== id);
    this.saveToDisk();
  }

  // --- Vouchers & Invoices (With Multi-Tenant & Role Scoping) ---
  public getVouchers(): Voucher[] {
    const currentUser = this.getCurrentUser();
    let list = this.state.vouchers.filter((v) => v.companyId === this.state.currentCompanyId);

    // Auto check expired proformas
    const todayStr = new Date().toISOString().slice(0, 10);
    list = list.map((v) => {
      if (v.type === 'PROFORMA' && v.expiresOn && v.expiresOn < todayStr && v.status !== 'paid') {
        return { ...v, status: 'expired' };
      }
      return v;
    });

    // Client Portal Row-Level Isolation
    if (currentUser.role === 'client_portal') {
      if (!currentUser.linkedClientId) return [];
      return list.filter(
        (v) =>
          v.clientId === currentUser.linkedClientId &&
          (v.status === 'finalized' || v.status === 'paid' || v.status === 'expired') &&
          (v.type === 'SALES' || v.type === 'PROFORMA' || v.type === 'DELIVERY')
      );
    }

    // Procurement Role: Only LPO
    if (currentUser.role === 'procurement') {
      return list.filter((v) => v.type === 'LPO');
    }

    return list;
  }

  public getVoucherById(id: string): Voucher | undefined {
    return this.getVouchers().find((v) => v.id === id);
  }

  public saveVoucher(voucher: Voucher): void {
    const amountInWords = convertNumberToWords(
      voucher.finalGrandTotal || voucher.grandTotal,
      voucher.currency
    );

    // Compute proforma validity
    let expiresOn = voucher.expiresOn;
    if (voucher.type === 'PROFORMA' && voucher.proformaValidityDays) {
      const baseDate = new Date(voucher.docDate || Date.now());
      baseDate.setDate(baseDate.getDate() + voucher.proformaValidityDays);
      expiresOn = baseDate.toISOString().slice(0, 10);
    }

    const scopedVoucher: Voucher = {
      ...voucher,
      companyId: this.state.currentCompanyId,
      amountInWords,
      expiresOn,
      createdBy: voucher.createdBy || this.state.currentUserId,
      updatedAt: new Date().toISOString(),
    };

    const index = this.state.vouchers.findIndex((v) => v.id === voucher.id);
    if (index >= 0) {
      this.state.vouchers[index] = scopedVoucher;
    } else {
      this.state.vouchers.unshift({
        ...scopedVoucher,
        createdAt: new Date().toISOString(),
      });
    }
    this.saveToDisk();
  }

  public updateVoucherStatus(id: string, newStatus: VoucherStatus): void {
    const voucher = this.state.vouchers.find((v) => v.id === id && v.companyId === this.state.currentCompanyId);
    if (voucher) {
      voucher.status = newStatus;
      voucher.updatedAt = new Date().toISOString();
      this.saveToDisk();
    }
  }

  public deleteVoucher(id: string): void {
    this.state.vouchers = this.state.vouchers.filter((v) => v.id !== id);
    this.saveToDisk();
  }

  public getNextDocNumber(type: VoucherType): string {
    const prefixMap: Record<VoucherType, string> = {
      PO: 'PO',
      LPO: 'LPO',
      PROFORMA: 'PI',
      SALES: 'INV',
      DELIVERY: 'DN',
      GATE_PASS: 'GP',
    };
    const prefix = prefixMap[type] || 'DOC';
    const year = new Date().getFullYear();

    const existingOfType = this.state.vouchers.filter(
      (v) => v.companyId === this.state.currentCompanyId && v.type === type
    );
    const nextSeq = existingOfType.length + 1;
    const padded = String(nextSeq).padStart(4, '0');
    return `${prefix}-${year}-${padded}`;
  }

  // --- Payments & Payment Trend Analytics (Finance / Admin) ---
  public getPayments(): PaymentRecord[] {
    return this.state.payments.filter((p) => p.companyId === this.state.currentCompanyId);
  }

  public recordPayment(data: {
    voucherId: string;
    clientId: string;
    amount: number;
    paymentDate: string;
    paymentMethod: 'bank_transfer' | 'cheque' | 'cash' | 'mobile_money';
    referenceNumber: string;
    notes?: string;
  }): PaymentRecord {
    const voucher = this.state.vouchers.find((v) => v.id === data.voucherId);
    const docNumber = voucher ? voucher.docNumber : 'INV-GEN';

    const newPayment: PaymentRecord = {
      id: `pay_${Date.now()}`,
      companyId: this.state.currentCompanyId,
      clientId: data.clientId,
      voucherId: data.voucherId,
      docNumber,
      amount: data.amount,
      paymentDate: data.paymentDate,
      paymentMethod: data.paymentMethod,
      referenceNumber: data.referenceNumber,
      notes: data.notes,
      createdAt: new Date().toISOString(),
    };

    this.state.payments.push(newPayment);

    // Update voucher paid amount and status
    if (voucher) {
      const currentPaid = (voucher.paidAmount || 0) + data.amount;
      voucher.paidAmount = currentPaid;
      voucher.paidDate = data.paymentDate;
      if (currentPaid >= (voucher.finalGrandTotal || voucher.grandTotal)) {
        voucher.status = 'paid';
      }
      voucher.updatedAt = new Date().toISOString();
    }

    this.saveToDisk();
    return newPayment;
  }

  public getPaymentTrendAnalytics(): PaymentTrendAnalyticsData {
    const cId = this.state.currentCompanyId;
    const clients = this.getClients();
    const vouchers = this.state.vouchers.filter((v) => v.companyId === cId && v.type === 'SALES');
    const payments = this.state.payments.filter((p) => p.companyId === cId);

    const today = new Date();

    let totalOutstanding = 0;
    let totalOverdue = 0;
    let totalPaid = 0;
    let overdueCount = 0;
    let totalCreditLimit = 0;

    const allDaysToPay: number[] = [];

    const clientMetrics: ClientPaymentMetric[] = clients.map((client) => {
      const clientVouchers = vouchers.filter((v) => v.clientId === client.id);
      const clientPayments = payments.filter((p) => p.clientId === client.id);

      const clientInvoiced = clientVouchers.reduce((sum, v) => sum + (v.finalGrandTotal || v.grandTotal), 0);
      const clientPaid = clientPayments.reduce((sum, p) => sum + p.amount, 0);
      const clientOutstanding = Math.max(0, clientInvoiced - clientPaid);

      totalOutstanding += clientOutstanding;
      totalPaid += clientPaid;
      totalCreditLimit += client.creditLimit || 0;

      // Overdue invoices calculation
      let clientOverdueAmount = 0;
      let clientOverdueCount = 0;

      clientVouchers.forEach((v) => {
        const vRemaining = Math.max(0, (v.finalGrandTotal || v.grandTotal) - (v.paidAmount || 0));
        if (vRemaining > 0 && v.dueDate) {
          const due = new Date(v.dueDate);
          if (due < today) {
            clientOverdueAmount += vRemaining;
            clientOverdueCount++;
          }
        }
      });

      totalOverdue += clientOverdueAmount;
      overdueCount += clientOverdueCount;

      // Calculate days to pay for settled invoices
      const clientDaysToPayList: number[] = [];
      clientVouchers.forEach((v) => {
        if (v.paidDate && v.docDate) {
          const docD = new Date(v.docDate).getTime();
          const paidD = new Date(v.paidDate).getTime();
          const diffDays = Math.max(1, Math.round((paidD - docD) / (1000 * 3600 * 24)));
          clientDaysToPayList.push(diffDays);
          allDaysToPay.push(diffDays);
        }
      });

      const avgDays = clientDaysToPayList.length > 0
        ? Math.round(clientDaysToPayList.reduce((a, b) => a + b, 0) / clientDaysToPayList.length)
        : (client.creditDays || 14);

      const creditLimit = client.creditLimit || 0;
      const creditUtilization = creditLimit > 0 ? Math.min(100, Math.round((clientOutstanding / creditLimit) * 100)) : 0;

      let paymentStatus: 'healthy' | 'warning' | 'critical' = 'healthy';
      if (clientOverdueCount > 0 || creditUtilization > 90) {
        paymentStatus = clientOverdueCount >= 2 || creditUtilization >= 100 ? 'critical' : 'warning';
      }

      const lastPay = clientPayments.sort((a, b) => new Date(b.paymentDate).getTime() - new Date(a.paymentDate).getTime())[0];

      return {
        clientId: client.id,
        clientName: client.name,
        paymentTermsType: client.paymentTermsType,
        creditDays: client.creditDays || 0,
        approvedCreditLimit: creditLimit,
        currentOutstanding: clientOutstanding,
        creditUtilizationPercent: creditUtilization,
        totalInvoiced: clientInvoiced,
        totalPaid: clientPaid,
        averageDaysToPay: avgDays,
        overdueInvoicesCount: clientOverdueCount,
        overdueAmount: clientOverdueAmount,
        paymentStatus,
        lastPaymentDate: lastPay ? lastPay.paymentDate : undefined,
      };
    });

    const averageDaysToPay = allDaysToPay.length > 0
      ? Math.round(allDaysToPay.reduce((a, b) => a + b, 0) / allDaysToPay.length)
      : 21;

    const averageCreditUtilization = totalCreditLimit > 0
      ? Math.round((totalOutstanding / totalCreditLimit) * 100)
      : 0;

    return {
      companyId: cId,
      averageDaysToPay,
      totalOutstandingAmount: totalOutstanding,
      totalOverdueAmount: totalOverdue,
      totalPaidAmount: totalPaid,
      overdueInvoicesCount: overdueCount,
      totalCreditLimit,
      averageCreditUtilization,
      clientMetrics,
    };
  }

  // --- Demand Gap & CRM Analytics ---
  public getDemandGapAnalysis(): DemandGapAnalysis[] {
    const clients = this.getClients();
    const requirements = this.state.clientRequirements.filter(
      (r) => r.companyId === this.state.currentCompanyId
    );
    const vouchers = this.getVouchers().filter((v) => v.type === 'SALES' || v.type === 'DELIVERY');

    const result: DemandGapAnalysis[] = [];

    requirements.forEach((req) => {
      const client = clients.find((c) => c.id === req.clientId);
      if (!client) return;

      let actualSupplied = 0;
      vouchers
        .filter((v) => v.clientId === req.clientId)
        .forEach((v) => {
          v.items.forEach((item) => {
            const isMatch =
              item.itemName.toLowerCase().includes('bitumen') &&
              req.productName.toLowerCase().includes('bitumen');
            const isDieselMatch =
              item.itemName.toLowerCase().includes('diesel') &&
              req.productName.toLowerCase().includes('diesel');

            if (isMatch || isDieselMatch || item.itemName.toLowerCase() === req.productName.toLowerCase()) {
              actualSupplied += item.quantity;
            }
          });
        });

      const gap = Math.max(0, req.expectedQuantity - actualSupplied);
      const fulfillmentPercent =
        req.expectedQuantity > 0 ? Math.min(100, Math.round((actualSupplied / req.expectedQuantity) * 100)) : 0;
      const isUnderSupplied = gap > 0;
      const estimatedLostRevenue = gap * 1180000;

      result.push({
        client,
        requirement: req,
        actualQuantitySupplied: actualSupplied,
        gapQuantity: gap,
        fulfillmentPercent,
        isUnderSupplied,
        estimatedLostRevenueTZS: estimatedLostRevenue,
      });
    });

    return result;
  }

  public getRepeatOrderAlerts(): CRMClientAnalytics[] {
    const clients = this.getClients();
    const vouchers = this.getVouchers().filter((v) => v.type === 'SALES');
    const now = new Date();

    const results: CRMClientAnalytics[] = [];

    clients.forEach((client) => {
      const clientVouchers = vouchers
        .filter((v) => v.clientId === client.id)
        .sort((a, b) => new Date(b.docDate).getTime() - new Date(a.docDate).getTime());

      const totalSpent = clientVouchers.reduce((acc, v) => acc + (v.finalGrandTotal || v.grandTotal), 0);
      const orderCount = clientVouchers.length;

      let avgDays = 14;
      if (orderCount >= 2) {
        let totalInterval = 0;
        for (let i = 0; i < clientVouchers.length - 1; i++) {
          const d1 = new Date(clientVouchers[i].docDate).getTime();
          const d2 = new Date(clientVouchers[i + 1].docDate).getTime();
          totalInterval += Math.abs(d1 - d2) / (1000 * 3600 * 24);
        }
        avgDays = Math.round(totalInterval / (orderCount - 1)) || 14;
      }

      const lastOrderDate = clientVouchers[0]?.docDate;
      let daysSinceLastOrder = 0;
      let isOverdue = false;

      if (lastOrderDate) {
        daysSinceLastOrder = Math.floor(
          (now.getTime() - new Date(lastOrderDate).getTime()) / (1000 * 3600 * 24)
        );
        isOverdue = daysSinceLastOrder > avgDays * 1.3 && daysSinceLastOrder > 10;
      }

      results.push({
        client,
        totalSpent,
        orderCount,
        averageDaysBetweenOrders: avgDays,
        daysSinceLastOrder,
        lastOrderDate,
        isOverdueForOrder: isOverdue,
      });
    });

    return results;
  }

  // --- Intelligence & News Cache ---
  public getCachedMarketData(): MarketData | null {
    return this.state.marketDataCache || null;
  }

  public setCachedMarketData(data: MarketData): void {
    this.state.marketDataCache = data;
    this.saveToDisk();
  }

  public getNewsItems(): NewsCacheItem[] {
    return this.state.newsItems || demoMarketNews;
  }

  public toggleStarNewsItem(id: string): void {
    if (!this.state.newsItems) this.state.newsItems = [...demoMarketNews];
    const found = this.state.newsItems.find((n) => n.id === id);
    if (found) {
      found.isSaved = !found.isSaved;
      this.saveToDisk();
    }
  }

  public dismissNewsItem(id: string): void {
    if (!this.state.newsItems) this.state.newsItems = [...demoMarketNews];
    const found = this.state.newsItems.find((n) => n.id === id);
    if (found) {
      found.isDismissed = true;
      this.saveToDisk();
    }
  }

  // --- Compatibility & Backup Methods ---
  public updateCompanyProfile(profile: CompanyProfile): void {
    this.saveCompanyProfile(profile);
  }

  public saveClients(clientsList: Client[]): void {
    const currentCompId = this.getCurrentCompanyId();
    // Replace all clients for this company with the provided list
    const otherClients = this.state.clients.filter((c) => c.companyId !== currentCompId);
    this.state.clients = [...otherClients, ...clientsList];
    this.saveToDisk();
  }

  public getCRMAnalytics(): CRMClientAnalytics[] {
    return this.getRepeatOrderAlerts();
  }

  public addClientDocument(doc: ClientDocument): void {
    this.saveClientDocument(doc);
  }

  public exportDatabaseJson(): string {
    return JSON.stringify(this.state, null, 2);
  }

  public importDatabaseJson(jsonString: string): { success: boolean; message: string } {
    try {
      const parsed = JSON.parse(jsonString) as MultiTenantDatabaseState;
      if (parsed && parsed.companies && parsed.users) {
        this.state = parsed;
        this.saveToDisk();
        const comp = this.getCompanyProfile();
        if (comp) this.applyTheme(comp.theme);
        return { success: true, message: 'Cloud database snapshot imported successfully.' };
      }
      return { success: false, message: 'JSON format invalid: missing companies or users records.' };
    } catch (e: any) {
      return { success: false, message: `Failed to import JSON: ${e.message}` };
    }
  }

  public resetToSeedData(): void {
    this.state = JSON.parse(JSON.stringify(initialDatabaseState));
    this.saveToDisk();
    const comp = this.getCompanyProfile();
    if (comp) this.applyTheme(comp.theme);
  }

  public saveCachedMarketData(data: MarketData): void {
    this.setCachedMarketData(data);
  }

  public getSavedIntelligence(): SavedIntelligenceItem[] {
    return this.state.savedIntelligence || [];
  }

  public saveIntelligenceItems(items: SavedIntelligenceItem[]): void {
    this.state.savedIntelligence = items;
    this.saveToDisk();
  }

  // --- Theme Application ---
  public applyTheme(theme: CompanyProfile['theme']): void {
    if (!theme) return;
    const root = document.documentElement;

    root.style.setProperty('--primary-color', theme.primaryColor);
    root.style.setProperty('--secondary-color', theme.secondaryColor);
    root.style.setProperty('--accent-color', theme.accentColor);
    root.style.setProperty('--font-family', theme.fontFamily || 'Inter, system-ui, sans-serif');

    // Extract RGB for tailwind alpha blending
    const hexToRgb = (hex: string) => {
      let c = hex.replace('#', '');
      if (c.length === 3) c = c.split('').map((x) => x + x).join('');
      const n = parseInt(c, 16);
      return `${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}`;
    };

    try {
      root.style.setProperty('--primary-rgb', hexToRgb(theme.primaryColor));
      root.style.setProperty('--secondary-rgb', hexToRgb(theme.secondaryColor));
      root.style.setProperty('--accent-rgb', hexToRgb(theme.accentColor));
    } catch {
      // Fallback
    }
  }
}
