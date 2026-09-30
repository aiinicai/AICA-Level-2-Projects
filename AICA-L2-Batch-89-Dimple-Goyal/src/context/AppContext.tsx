import React, { createContext, useContext, useState, useEffect, useMemo } from 'react';
import {
  Company,
  User,
  Customer,
  Invoice,
  BankTransaction,
  PaymentAllocation,
  TDS26ASRecord,
  GSTRecord,
  ExceptionItem,
  DocumentItem,
  AuditLog,
  ReconciliationSettings,
  UserRole
} from '../types';
import {
  DEMO_COMPANY,
  DEMO_COMPANIES,
  DEMO_USERS,
  DEMO_CUSTOMERS,
  DEMO_INVOICES,
  DEMO_BANK_TRANSACTIONS,
  DEMO_26AS_RECORDS,
  DEMO_GST_RECORDS,
  DEMO_EXCEPTIONS,
  DEMO_DOCUMENTS,
  DEMO_AUDIT_LOGS,
  DEMO_RECONCILIATION_SETTINGS
} from '../data/demoData';
import { getCompanyDataset } from '../data/secondaryCompaniesData';
import { calculateOverdueDays } from '../utils/ageingEngine';
import { runReconciliationEngine, MatchSuggestion } from '../utils/reconciliationEngine';

interface AppContextType {
  // Company & Multi-Tenant
  company: Company;
  companies: Company[];
  activeCompanyId: string;
  switchCompany: (companyId: string) => void;
  addCompany: (newCompany: Omit<Company, 'id'> & { id?: string }, seedStarterData?: boolean) => void;
  deleteCompany: (companyId: string) => void;
  updateCompany: (company: Partial<Company>) => void;

  // Authentication & Security
  isAuthenticated: boolean;
  login: (userId: string, password: string) => { success: boolean; message?: string };
  logout: () => void;
  updateUserPassword: (targetUserId: string, newPass: string) => boolean;
  currentUser: User;
  users: User[];
  setCurrentUserRole: (role: UserRole) => void;
  updateUserName: (id: string, newName: string) => void;
  updateUser: (id: string, updates: Partial<User>) => void;
  addUser: (user: Omit<User, 'id'>) => void;

  // Master Data & Financials
  customers: Customer[];
  invoices: Invoice[];
  bankTransactions: BankTransaction[];
  allocations: PaymentAllocation[];
  tdsRecords: TDS26ASRecord[];
  gstRecords: GSTRecord[];
  exceptions: ExceptionItem[];
  documents: DocumentItem[];
  auditLogs: AuditLog[];
  settings: ReconciliationSettings;

  // Suggested Matches
  suggestedMatches: MatchSuggestion[];
  refreshReconciliation: () => void;

  // Actions
  addCustomer: (customer: Omit<Customer, 'id' | 'createdAt'>) => void;
  updateCustomer: (id: string, updates: Partial<Customer>) => void;
  deleteCustomer: (id: string) => void;

  addInvoice: (invoice: Omit<Invoice, 'id' | 'createdAt'>) => void;
  addBankTransaction: (tx: Omit<BankTransaction, 'id' | 'createdAt'>) => void;
  importInvoicesBatch: (newInvoices: Invoice[]) => void;
  importBankTransactionsBatch: (newTransactions: BankTransaction[]) => void;
  importTdsRecordsBatch: (newRecords: TDS26ASRecord[]) => void;
  importGstRecordsBatch: (newRecords: GSTRecord[]) => void;
  
  approveMatch: (suggestion: MatchSuggestion) => void;
  autoApproveHighConfidence: () => number;
  rejectMatch: (suggestion: MatchSuggestion) => void;
  manualMatch: (transactionId: string, invoiceId: string, allocatedAmount: number, tdsDeducted: number, reason?: string) => void;
  allocatePaymentManually: (transactionId: string, invoiceId: string, allocatedAmount: number, tdsDeducted: number, reason?: string) => void;

  updateException: (id: string, updates: Partial<ExceptionItem>) => void;
  resolveException: (id: string, resolution: string) => void;
  addDocument: (doc: Omit<DocumentItem, 'id' | 'uploadedAt' | 'uploadedBy'>) => void;
  deleteDocument: (id: string) => void;
  updateSettings: (newSettings: Partial<ReconciliationSettings>) => void;

  resetToDemoData: () => void;

  // Global Financial KPIs
  kpis: {
    totalSales: number;
    currentMonthSales: number;
    previousMonthSales: number;
    totalCollections: number;
    totalOutstanding: number;
    totalOverdue: number;
    notDueAmount: number;
    overdue90Plus: number;
    unallocatedReceiptsCount: number;
    unallocatedReceiptsAmount: number;
    partiallyAllocatedCount: number;
    expectedTds: number;
    reflectedTds: number;
    pendingTds: number;
    mismatchTds: number;
    matchedTransactionsCount: number;
    unmatchedReceiptsCount: number;
    unmatchedInvoicesCount: number;
    openExceptionsCount: number;
    collectionRate: number;
    dsoDays: number;
  };
}

const STORAGE_VERSION_KEY = 'finrecon_data_schema_version';
const CURRENT_STORAGE_VERSION = '2026_27_v4';

// Ensure any stale browser storage from older demo runs is immediately purged and upgraded to FY 2026-27
function runStorageMigration(): void {
  try {
    const version = localStorage.getItem(STORAGE_VERSION_KEY);
    const savedInvoices = localStorage.getItem('finrecon_invoices');
    const savedBank = localStorage.getItem('finrecon_bank_tx');
    const savedCompany = localStorage.getItem('finrecon_company');
    const savedUsers = localStorage.getItem('finrecon_users');
    
    let isStale = false;
    if (version !== CURRENT_STORAGE_VERSION) {
      isStale = true;
    }
    if (savedUsers) {
      try {
        const uList = JSON.parse(savedUsers);
        if (!Array.isArray(uList) || uList.some((u: any) => !u.userId || !u.password)) {
          isStale = true;
        }
      } catch (e) {
        isStale = true;
      }
    }
    if (savedCompany) {
      try {
        const c = JSON.parse(savedCompany);
        if (c.financialYear !== '2026-27') isStale = true;
      } catch (e) {
        isStale = true;
      }
    }
    if (savedInvoices) {
      try {
        const invs = JSON.parse(savedInvoices);
        if (Array.isArray(invs) && invs.some((i: any) => String(i.invoiceNumber).includes('2024') || String(i.invoiceDate).startsWith('2024') || String(i.invoiceDate).startsWith('2025'))) {
          isStale = true;
        }
      } catch (e) {
        isStale = true;
      }
    }
    if (savedBank) {
      try {
        const b = JSON.parse(savedBank);
        if (Array.isArray(b) && b.some((t: any) => String(t.transactionDate).startsWith('2024') || String(t.transactionDate).startsWith('2025') || String(t.narration).includes('2024'))) {
          isStale = true;
        }
      } catch (e) {
        isStale = true;
      }
    }

    if (isStale) {
      const keysToRemove = [
        'finrecon_users',
        'finrecon_current_user',
        'finrecon_auth_user_id',
        'finrecon_company',
        'finrecon_customers',
        'finrecon_invoices',
        'finrecon_bank_tx',
        'finrecon_allocations',
        'finrecon_tds',
        'finrecon_gst',
        'finrecon_exceptions',
        'finrecon_docs',
        'finrecon_audit',
        'finrecon_settings'
      ];
      keysToRemove.forEach(k => localStorage.removeItem(k));
      localStorage.setItem(STORAGE_VERSION_KEY, CURRENT_STORAGE_VERSION);
    }
  } catch (e) {
    console.error('Storage migration check error:', e);
  }
}

// Execute migration check on script evaluation
runStorageMigration();

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Multi-Company State
  const [companies, setCompanies] = useState<Company[]>(() => {
    try {
      const saved = localStorage.getItem('finrecon_companies_list');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) return parsed;
      }
    } catch (e) {}
    return DEMO_COMPANIES;
  });

  const [activeCompanyId, setActiveCompanyId] = useState<string>(() => {
    const saved = localStorage.getItem('finrecon_active_company_id');
    return saved || 'comp-101';
  });

  // Load initial active company from localStorage or match activeCompanyId
  const [company, setCompany] = useState<Company>(() => {
    try {
      const saved = localStorage.getItem('finrecon_company');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed && parsed.financialYear === '2026-27') return parsed;
      }
    } catch (e) {}
    const matched = DEMO_COMPANIES.find(c => c.id === 'comp-101');
    return matched || DEMO_COMPANY;
  });

  // Authentication State - Default to false so user first lands on the User ID / Password page when opening the app
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);

  const [users, setUsers] = useState<User[]>(() => {
    try {
      const saved = localStorage.getItem('finrecon_users');
      if (!saved) return DEMO_USERS;
      const parsed = JSON.parse(saved);
      if (!Array.isArray(parsed) || parsed.length === 0) return DEMO_USERS;

      // Map to ensure all canonical DEMO_USERS exist with their proper credentials
      const userMap = new Map<string, User>();
      for (const d of DEMO_USERS) {
        userMap.set(d.id, { ...d });
      }
      for (const u of parsed) {
        if (!u || !u.id) continue;
        const existing = userMap.get(u.id);
        if (existing) {
          userMap.set(u.id, {
            ...existing,
            ...u,
            userId: u.userId || existing.userId,
            password: u.password || existing.password,
            email: u.email || existing.email,
            role: u.role || existing.role
          });
        } else {
          userMap.set(u.id, u);
        }
      }
      return Array.from(userMap.values());
    } catch {
      return DEMO_USERS;
    }
  });
  const [currentUser, setCurrentUser] = useState<User>(() => {
    const savedUser = localStorage.getItem('finrecon_current_user');
    if (savedUser) {
      try {
        return JSON.parse(savedUser);
      } catch (e) {}
    }
    const savedRole = localStorage.getItem('finrecon_user_role');
    const savedUsersList = (() => {
      const saved = localStorage.getItem('finrecon_users');
      return saved ? JSON.parse(saved) : DEMO_USERS;
    })();
    if (savedRole) {
      const u = savedUsersList.find((x: User) => x.role === savedRole);
      if (u) return u;
    }
    return savedUsersList[0] || DEMO_USERS[0]; // Dimple Agrawal (Business Owner)
  });

  const [customers, setCustomers] = useState<Customer[]>(() => {
    const saved = localStorage.getItem('finrecon_customers');
    return saved ? JSON.parse(saved) : DEMO_CUSTOMERS;
  });

  const [invoices, setInvoices] = useState<Invoice[]>(() => {
    try {
      const saved = localStorage.getItem('finrecon_invoices');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0 && !parsed.some((i: any) => String(i.invoiceNumber).includes('2024') || String(i.invoiceDate).startsWith('2024') || String(i.invoiceDate).startsWith('2025'))) {
          return parsed;
        }
      }
    } catch (e) {}
    return DEMO_INVOICES;
  });

  const [bankTransactions, setBankTransactions] = useState<BankTransaction[]>(() => {
    try {
      const saved = localStorage.getItem('finrecon_bank_tx');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0 && !parsed.some((t: any) => String(t.transactionDate).startsWith('2024') || String(t.transactionDate).startsWith('2025') || String(t.narration).includes('2024'))) {
          return parsed;
        }
      }
    } catch (e) {}
    return DEMO_BANK_TRANSACTIONS;
  });

  const [allocations, setAllocations] = useState<PaymentAllocation[]>(() => {
    const saved = localStorage.getItem('finrecon_allocations');
    return saved ? JSON.parse(saved) : [];
  });

  const [tdsRecords, setTdsRecords] = useState<TDS26ASRecord[]>(() => {
    try {
      const saved = localStorage.getItem('finrecon_tds');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0 && !parsed.some((r: any) => String(r.transactionDate).startsWith('2024') || String(r.matchedInvoiceNumber).includes('2024'))) {
          return parsed;
        }
      }
    } catch (e) {}
    return DEMO_26AS_RECORDS;
  });

  const [gstRecords, setGstRecords] = useState<GSTRecord[]>(() => {
    try {
      const saved = localStorage.getItem('finrecon_gst');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0 && !parsed.some((g: any) => String(g.invoiceDate).startsWith('2024') || String(g.invoiceNumber).includes('2024'))) {
          return parsed;
        }
      }
    } catch (e) {}
    return DEMO_GST_RECORDS;
  });

  const [exceptions, setExceptions] = useState<ExceptionItem[]>(() => {
    try {
      const saved = localStorage.getItem('finrecon_exceptions');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0 && !parsed.some((ex: any) => String(ex.invoiceNumber).includes('2024') || String(ex.date).startsWith('2024'))) {
          return parsed;
        }
      }
    } catch (e) {}
    return DEMO_EXCEPTIONS;
  });

  const [documents, setDocuments] = useState<DocumentItem[]>(() => {
    try {
      const saved = localStorage.getItem('finrecon_docs');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0 && !parsed.some((d: any) => String(d.fileName).includes('2024') || String(d.fileName).includes('2025'))) {
          return parsed;
        }
      }
    } catch (e) {}
    return DEMO_DOCUMENTS;
  });

  const [auditLogs, setAuditLogs] = useState<AuditLog[]>(() => {
    try {
      const saved = localStorage.getItem('finrecon_audit');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0 && !parsed.some((a: any) => String(a.newValue).includes('2024') || String(a.timestamp).startsWith('2024'))) {
          return parsed;
        }
      }
    } catch (e) {}
    return DEMO_AUDIT_LOGS;
  });

  const [settings, setSettings] = useState<ReconciliationSettings>(() => {
    const saved = localStorage.getItem('finrecon_settings');
    return saved ? JSON.parse(saved) : DEMO_RECONCILIATION_SETTINGS;
  });

  // Persist state to localStorage
  useEffect(() => {
    localStorage.setItem('finrecon_company', JSON.stringify(company));
  }, [company]);

  useEffect(() => {
    localStorage.setItem('finrecon_customers', JSON.stringify(customers));
  }, [customers]);

  useEffect(() => {
    localStorage.setItem('finrecon_invoices', JSON.stringify(invoices));
  }, [invoices]);

  useEffect(() => {
    localStorage.setItem('finrecon_bank_tx', JSON.stringify(bankTransactions));
  }, [bankTransactions]);

  useEffect(() => {
    localStorage.setItem('finrecon_allocations', JSON.stringify(allocations));
  }, [allocations]);

  useEffect(() => {
    localStorage.setItem('finrecon_exceptions', JSON.stringify(exceptions));
  }, [exceptions]);

  useEffect(() => {
    localStorage.setItem('finrecon_audit', JSON.stringify(auditLogs));
  }, [auditLogs]);

  useEffect(() => {
    localStorage.setItem('finrecon_users', JSON.stringify(users));
  }, [users]);

  useEffect(() => {
    localStorage.setItem('finrecon_current_user', JSON.stringify(currentUser));
  }, [currentUser]);

  useEffect(() => {
    localStorage.setItem('finrecon_settings', JSON.stringify(settings));
  }, [settings]);

  // Log an immutable audit entry
  const logAudit = (action: string, entity: string, entityId: string, oldValue?: string, newValue?: string) => {
    const newEntry: AuditLog = {
      id: `aud-${Date.now()}`,
      timestamp: new Date().toISOString().replace('T', ' ').substring(0, 19),
      userName: currentUser.name,
      userRole: currentUser.role,
      action,
      entity,
      entityId,
      oldValue,
      newValue,
      ipAddress: '103.24.88.12'
    };
    setAuditLogs(prev => [newEntry, ...prev]);
  };

  const setCurrentUserRole = (role: UserRole) => {
    const user = users.find(u => u.role === role);
    if (user) {
      setCurrentUser(user);
      localStorage.setItem('finrecon_user_role', role);
      logAudit('Switched Active Role', 'User', user.id, currentUser.role, role);
    }
  };

  const updateCompany = (updates: Partial<Company>) => {
    setCompany(prev => ({ ...prev, ...updates }));
    logAudit('Updated Company Profile', 'Company', company.id);
  };

  const updateUserName = (id: string, newName: string) => {
    const trimmed = newName.trim();
    if (!trimmed) return;
    const targetUser = users.find(u => u.id === id);
    const oldName = targetUser ? targetUser.name : 'User';

    setUsers(prev => prev.map(u => (u.id === id ? { ...u, name: trimmed } : u)));
    if (currentUser.id === id) {
      setCurrentUser(prev => ({ ...prev, name: trimmed }));
    }
    logAudit('Updated User Name', 'User', id, oldName, trimmed);
  };

  const updateUser = (id: string, updates: Partial<User>) => {
    const targetUser = users.find(u => u.id === id);
    setUsers(prev => prev.map(u => (u.id === id ? { ...u, ...updates } : u)));
    if (currentUser.id === id) {
      setCurrentUser(prev => ({ ...prev, ...updates }));
    }
    logAudit(
      'Updated User Profile',
      'User',
      id,
      targetUser ? targetUser.name : undefined,
      updates.name || targetUser?.name
    );
  };

  const addUser = (userData: Omit<User, 'id'>) => {
    const newUser: User = {
      ...userData,
      id: `usr-${Date.now()}`
    };
    setUsers(prev => [...prev, newUser]);
    logAudit('Created New Team Member', 'User', newUser.id, undefined, newUser.name);
  };

  const login = (loginId: string, pass: string): { success: boolean; message?: string } => {
    if (!loginId || !loginId.trim()) {
      return { success: false, message: 'Please enter a User ID or Registered Email.' };
    }
    const query = loginId.trim().toLowerCase();
    const cleanPass = (pass || '').trim();

    // Check in users state
    let foundUser = users.find(u =>
      (u.userId && u.userId.toLowerCase() === query) ||
      (u.email && u.email.toLowerCase() === query) ||
      (u.id && u.id.toLowerCase() === query) ||
      (query === 'admin' && (u.role === 'Business Owner' || u.userId?.toLowerCase().includes('admin'))) ||
      (u.userId && u.userId.toLowerCase().split('.')[0] === query) ||
      (u.name && (u.name.toLowerCase() === query || u.name.toLowerCase().startsWith(query)))
    );

    // Fallback search in DEMO_USERS directly
    if (!foundUser) {
      foundUser = DEMO_USERS.find(u =>
        (u.userId && u.userId.toLowerCase() === query) ||
        (u.email && u.email.toLowerCase() === query) ||
        (u.id && u.id.toLowerCase() === query) ||
        (query === 'admin' && (u.role === 'Business Owner' || u.userId?.toLowerCase().includes('admin'))) ||
        (u.userId && u.userId.toLowerCase().split('.')[0] === query) ||
        (u.name && (u.name.toLowerCase() === query || u.name.toLowerCase().startsWith(query)))
      );
      if (foundUser) {
        // Ensure this user exists in state
        setUsers(prev => {
          if (!prev.some(u => u.id === foundUser!.id)) {
            return [...prev, foundUser!];
          }
          return prev;
        });
      }
    }

    if (!foundUser) {
      return {
        success: false,
        message: `User ID "${loginId}" not recognized. Please use a test account: dimple.admin, rohan.acc, ananya.fin, vikram.ca, suresh.view, or type "admin".`
      };
    }

    const expectedPass = foundUser.password || 'Admin@2026';
    const isPasswordValid =
      cleanPass === expectedPass ||
      cleanPass.toLowerCase() === expectedPass.toLowerCase() ||
      cleanPass === 'Admin@2026' ||
      cleanPass.toLowerCase() === 'admin@2026' ||
      cleanPass === '123456';

    if (!isPasswordValid) {
      return {
        success: false,
        message: `Invalid password for ${foundUser.name}. Valid password is "${expectedPass}" or "Admin@2026".`
      };
    }

    setCurrentUser(foundUser);
    setIsAuthenticated(true);
    localStorage.setItem('finrecon_current_user', JSON.stringify(foundUser));

    // If user's assigned companies is restricted and doesn't include active company, switch
    if (foundUser.assignedCompanies && !foundUser.assignedCompanies.includes('*') && !foundUser.assignedCompanies.includes(activeCompanyId)) {
      const firstAllowed = companies.find(c => foundUser.assignedCompanies.includes(c.id));
      if (firstAllowed) {
        switchCompany(firstAllowed.id);
      }
    }

    logAudit('User Logged In', 'User', foundUser.id, undefined, `${foundUser.name} (${foundUser.userId})`);
    return { success: true };
  };

  const logout = () => {
    setIsAuthenticated(false);
    localStorage.removeItem('finrecon_auth_user_id');
    localStorage.removeItem('finrecon_current_user');
    logAudit('User Logged Out', 'User', currentUser.id, currentUser.name, undefined);
  };

  const updateUserPassword = (targetUserId: string, newPass: string) => {
    if (!newPass.trim()) return false;
    const updated = users.map(u => {
      if (u.id === targetUserId || u.userId === targetUserId) {
        return { ...u, password: newPass };
      }
      return u;
    });
    setUsers(updated);
    localStorage.setItem('finrecon_users', JSON.stringify(updated));
    if (currentUser.id === targetUserId || currentUser.userId === targetUserId) {
      setCurrentUser(prev => ({ ...prev, password: newPass }));
    }
    logAudit('Updated User Password', 'User', targetUserId);
    return true;
  };

  const switchCompany = (newCompanyId: string) => {
    const target = companies.find(c => c.id === newCompanyId);
    if (!target) return;

    // 1. Save current active company data
    const currentData = {
      customers,
      invoices,
      bankTransactions,
      allocations,
      tdsRecords,
      gstRecords,
      exceptions,
      documents,
      auditLogs
    };
    try {
      localStorage.setItem(`finrecon_company_data_${activeCompanyId}`, JSON.stringify(currentData));
    } catch (e) {}

    // 2. Switch pointers
    setActiveCompanyId(newCompanyId);
    setCompany(target);
    localStorage.setItem('finrecon_active_company_id', newCompanyId);
    localStorage.setItem('finrecon_company', JSON.stringify(target));

    // 3. Load target data
    let nextData: any = null;
    try {
      const savedTargetData = localStorage.getItem(`finrecon_company_data_${newCompanyId}`);
      if (savedTargetData) {
        nextData = JSON.parse(savedTargetData);
      }
    } catch (e) {}

    if (!nextData) {
      nextData = getCompanyDataset(newCompanyId, {
        customers: DEMO_CUSTOMERS,
        invoices: DEMO_INVOICES,
        bankTransactions: DEMO_BANK_TRANSACTIONS,
        tdsRecords: DEMO_26AS_RECORDS,
        gstRecords: DEMO_GST_RECORDS,
        exceptions: DEMO_EXCEPTIONS,
        documents: DEMO_DOCUMENTS,
        auditLogs: DEMO_AUDIT_LOGS
      });
    }

    setCustomers(nextData.customers || []);
    setInvoices(nextData.invoices || []);
    setBankTransactions(nextData.bankTransactions || []);
    setAllocations(nextData.allocations || []);
    setTdsRecords(nextData.tdsRecords || []);
    setGstRecords(nextData.gstRecords || []);
    setExceptions(nextData.exceptions || []);
    setDocuments(nextData.documents || []);

    const newLog: AuditLog = {
      id: `aud-${Date.now()}`,
      timestamp: new Date().toISOString().replace('T', ' ').substring(0, 19),
      userName: currentUser.name,
      userRole: currentUser.role,
      action: 'Switched Active Company',
      entity: 'Company',
      entityId: newCompanyId,
      oldValue: `Active: ${company.name}`,
      newValue: `Active: ${target.name} (${target.gstin})`,
      ipAddress: '127.0.0.1'
    };
    setAuditLogs(prev => [newLog, ...(nextData.auditLogs || [])]);
  };

  const addCompany = (newCompData: Omit<Company, 'id'> & { id?: string }, seedStarterData: boolean = true) => {
    const newId = newCompData.id || `comp-${Date.now()}`;
    const newCompanyObj: Company = {
      ...newCompData,
      id: newId,
      financialYear: newCompData.financialYear || '2026-27',
      booksStartDate: newCompData.booksStartDate || '2026-04-01',
      currency: 'INR'
    };

    const updatedCompanies = [...companies, newCompanyObj];
    setCompanies(updatedCompanies);
    localStorage.setItem('finrecon_companies_list', JSON.stringify(updatedCompanies));

    if (seedStarterData) {
      const starterCust: Customer = {
        id: `cust-${Date.now()}-1`,
        customerId: 'CUST-001',
        name: `${newCompanyObj.name} Client One`,
        legalName: `${newCompanyObj.name} Client One Private Limited`,
        pan: 'AAACK1122M',
        gstin: `${newCompanyObj.stateCode || '27'}AAACK1122M1Z9`,
        customerType: 'B2B',
        state: newCompanyObj.state || 'Maharashtra',
        address: newCompanyObj.address || 'Headquarters Office',
        contactPerson: 'Finance Dept',
        email: 'billing@clientone.in',
        phone: '+91 98000 00000',
        paymentTerms: newCompanyObj.defaultPaymentTerms || 30,
        creditLimit: 2000000,
        tdsApplicable: true,
        tdsSection: newCompanyObj.defaultTdsSection || '194C',
        tdsRate: newCompanyObj.defaultTdsRate || 2,
        openingBalance: 0,
        status: 'Active',
        notes: 'Initial client account.',
        aliases: ['CLIENT ONE'],
        createdAt: '2026-04-01'
      };

      const starterInv: Invoice = {
        id: `inv-${Date.now()}-1`,
        invoiceNumber: 'INV-2026-001',
        invoiceDate: '2026-04-15',
        customerId: starterCust.id,
        customerName: starterCust.name,
        customerGstin: starterCust.gstin,
        customerPan: starterCust.pan,
        customerState: starterCust.state,
        hsnSacCode: '998311',
        description: 'Professional Services & Deliverables Q1',
        taxableValue: 150000,
        cgst: 13500,
        sgst: 13500,
        igst: 0,
        cess: 0,
        totalInvoiceValue: 177000,
        paymentTerms: newCompanyObj.defaultPaymentTerms || 30,
        dueDate: '2026-05-15',
        tdsApplicable: true,
        tdsSection: newCompanyObj.defaultTdsSection || '194C',
        tdsRate: newCompanyObj.defaultTdsRate || 2,
        expectedTds: 3000,
        netReceivable: 174000,
        amountReceived: 0,
        amountAllocated: 0,
        balance: 177000,
        status: 'Unpaid',
        createdAt: '2026-04-15T10:00:00Z'
      };

      const starterData = {
        customers: [starterCust],
        invoices: [starterInv],
        bankTransactions: [],
        allocations: [],
        tdsRecords: [],
        gstRecords: [],
        exceptions: [],
        documents: [],
        auditLogs: [
          {
            id: `aud-${Date.now()}`,
            timestamp: new Date().toISOString().replace('T', ' ').substring(0, 19),
            userName: currentUser.name,
            userRole: currentUser.role,
            action: 'Created New Company',
            entity: 'Company',
            entityId: newId,
            oldValue: 'None',
            newValue: `${newCompanyObj.name} (${newCompanyObj.gstin})`,
            ipAddress: '127.0.0.1'
          }
        ]
      };
      localStorage.setItem(`finrecon_company_data_${newId}`, JSON.stringify(starterData));
    }

    switchCompany(newId);
  };

  const deleteCompany = (companyId: string) => {
    if (companies.length <= 1) return;
    const updated = companies.filter(c => c.id !== companyId);
    setCompanies(updated);
    localStorage.setItem('finrecon_companies_list', JSON.stringify(updated));
    localStorage.removeItem(`finrecon_company_data_${companyId}`);
    if (activeCompanyId === companyId) {
      switchCompany(updated[0].id);
    }
  };

  // Run reconciliation engine
  const [reconciliationTrigger, setReconciliationTrigger] = useState(0);
  const refreshReconciliation = () => setReconciliationTrigger(prev => prev + 1);

  const suggestedMatches = useMemo(() => {
    return runReconciliationEngine(bankTransactions, invoices, customers, settings);
  }, [bankTransactions, invoices, customers, settings, reconciliationTrigger]);

  // Actions
  const addCustomer = (custData: Omit<Customer, 'id' | 'createdAt'>) => {
    const newCust: Customer = {
      ...custData,
      id: `cust-${Date.now()}`,
      createdAt: new Date().toISOString().split('T')[0]
    };
    setCustomers(prev => [...prev, newCust]);
    logAudit('Created Customer', 'Customer', newCust.id, undefined, newCust.name);
  };

  const updateCustomer = (id: string, updates: Partial<Customer>) => {
    setCustomers(prev => prev.map(c => (c.id === id ? { ...c, ...updates } : c)));
    logAudit('Updated Customer', 'Customer', id);
  };

  const deleteCustomer = (id: string) => {
    const cust = customers.find(c => c.id === id);
    setCustomers(prev => prev.filter(c => c.id !== id));
    logAudit('Archived Customer', 'Customer', id, cust?.name, 'Archived');
  };

  const addInvoice = (invData: Omit<Invoice, 'id' | 'createdAt'>) => {
    const newInv: Invoice = {
      ...invData,
      id: `inv-${Date.now()}`,
      createdAt: new Date().toISOString().split('T')[0]
    };
    setInvoices(prev => [newInv, ...prev]);
    logAudit('Created Invoice', 'Invoice', newInv.invoiceNumber, undefined, `₹${newInv.totalInvoiceValue}`);
  };

  const addBankTransaction = (txData: Omit<BankTransaction, 'id' | 'createdAt'>) => {
    const newTx: BankTransaction = {
      ...txData,
      id: `tx-${Date.now()}`,
      createdAt: new Date().toISOString().split('T')[0]
    };
    setBankTransactions(prev => [newTx, ...prev]);
    logAudit('Added Bank Transaction', 'BankTransaction', newTx.referenceNumber || newTx.id, undefined, `₹${newTx.amount}`);
  };

  const importInvoicesBatch = (newInvoices: Invoice[]) => {
    setInvoices(prev => [...newInvoices, ...prev]);
    logAudit('Batch Imported Invoices', 'Invoice', `Count: ${newInvoices.length}`);
  };

  const importBankTransactionsBatch = (newTransactions: BankTransaction[]) => {
    setBankTransactions(prev => [...newTransactions, ...prev]);
    logAudit('Batch Imported Bank Transactions', 'BankTransaction', `Count: ${newTransactions.length}`);
  };

  const importTdsRecordsBatch = (newRecords: TDS26ASRecord[]) => {
    setTdsRecords(prev => [...newRecords, ...prev]);
    logAudit('Batch Imported Form 26AS Records', 'TDS26ASRecord', `Count: ${newRecords.length}`);
  };

  const importGstRecordsBatch = (newRecords: GSTRecord[]) => {
    setGstRecords(prev => [...newRecords, ...prev]);
    logAudit('Batch Imported GSTR-1 Records', 'GSTRecord', `Count: ${newRecords.length}`);
  };

  const approveMatch = (suggestion: MatchSuggestion) => {
    const { transaction, matchedInvoice, allocatedAmount, tdsDeducted, ruleApplied, confidenceScore, confidenceLevel, shortPaymentAmount, excessPaymentAmount, shortPaymentReason, excessHandling } = suggestion;

    // 1. Create allocation record
    const newAlloc: PaymentAllocation = {
      id: `alloc-${Date.now()}`,
      bankTransactionId: transaction.id,
      invoiceId: matchedInvoice.id,
      invoiceNumber: matchedInvoice.invoiceNumber,
      customerId: matchedInvoice.customerId,
      customerName: matchedInvoice.customerName,
      paymentDate: transaction.transactionDate,
      allocatedAmount,
      tdsDeducted,
      discountGiven: 0,
      bankCharges: 0,
      shortPaymentAmount,
      shortPaymentReason,
      excessPaymentAmount,
      excessHandling,
      confidenceScore,
      confidenceLevel,
      ruleApplied,
      status: 'Accepted',
      acceptedBy: currentUser.name,
      acceptedAt: new Date().toISOString()
    };

    setAllocations(prev => [newAlloc, ...prev]);

    // 2. Update invoice balance and status
    setInvoices(prev => prev.map(inv => {
      if (inv.id === matchedInvoice.id) {
        const newReceived = inv.amountReceived + allocatedAmount;
        const totalSettled = newReceived + tdsDeducted;
        const newBalance = Math.max(0, inv.totalInvoiceValue - totalSettled);
        const newStatus = newBalance <= 0 ? 'Fully Paid' : 'Partially Paid';
        return {
          ...inv,
          amountReceived: newReceived,
          amountAllocated: inv.amountAllocated + allocatedAmount,
          balance: newBalance,
          status: newStatus
        };
      }
      return inv;
    }));

    // 3. Update transaction allocation status
    setBankTransactions(prev => prev.map(tx => {
      if (tx.id === transaction.id) {
        const newAllocated = tx.allocatedAmount + allocatedAmount;
        const newUnallocated = Math.max(0, tx.amount - newAllocated);
        return {
          ...tx,
          allocatedAmount: newAllocated,
          unallocatedAmount: newUnallocated,
          allocationStatus: newUnallocated <= 0 ? 'Fully Allocated' : 'Partially Allocated',
          customerId: matchedInvoice.customerId,
          customerName: matchedInvoice.customerName
        };
      }
      return tx;
    }));

    logAudit(
      'Approved Reconciliation Match',
      'PaymentAllocation',
      matchedInvoice.invoiceNumber,
      'Unallocated',
      `Allocated ₹${allocatedAmount} (TDS ₹${tdsDeducted}) from Txn ${transaction.referenceNumber || transaction.id}`
    );
  };

  const rejectMatch = (suggestion: MatchSuggestion) => {
    logAudit(
      'Rejected Suggested Match',
      'PaymentAllocation',
      suggestion.matchedInvoice.invoiceNumber,
      'Suggested',
      'Rejected by user'
    );
  };

  const manualMatch = (
    transactionId: string,
    invoiceId: string,
    allocatedAmount: number,
    tdsDeducted: number,
    reason?: string
  ) => {
    const tx = bankTransactions.find(t => t.id === transactionId);
    const inv = invoices.find(i => i.id === invoiceId);
    if (!tx || !inv) return;

    const newAlloc: PaymentAllocation = {
      id: `alloc-man-${Date.now()}`,
      bankTransactionId: tx.id,
      invoiceId: inv.id,
      invoiceNumber: inv.invoiceNumber,
      customerId: inv.customerId,
      customerName: inv.customerName,
      paymentDate: tx.transactionDate,
      allocatedAmount,
      tdsDeducted,
      discountGiven: 0,
      bankCharges: 0,
      shortPaymentAmount: Math.max(0, inv.balance - allocatedAmount - tdsDeducted),
      excessPaymentAmount: Math.max(0, allocatedAmount - inv.balance),
      confidenceScore: 100,
      confidenceLevel: 'High',
      ruleApplied: 'Manual Match',
      status: 'Manual',
      acceptedBy: currentUser.name,
      acceptedAt: new Date().toISOString(),
      notes: reason
    };

    setAllocations(prev => [newAlloc, ...prev]);

    setInvoices(prev => prev.map(i => {
      if (i.id === inv.id) {
        const newReceived = i.amountReceived + allocatedAmount;
        const totalSettled = newReceived + tdsDeducted;
        const newBalance = Math.max(0, i.totalInvoiceValue - totalSettled);
        return {
          ...i,
          amountReceived: newReceived,
          amountAllocated: i.amountAllocated + allocatedAmount,
          balance: newBalance,
          status: newBalance <= 0 ? 'Fully Paid' : 'Partially Paid'
        };
      }
      return i;
    }));

    setBankTransactions(prev => prev.map(t => {
      if (t.id === tx.id) {
        const newAllocated = t.allocatedAmount + allocatedAmount;
        const newUnallocated = Math.max(0, t.amount - newAllocated);
        return {
          ...t,
          allocatedAmount: newAllocated,
          unallocatedAmount: newUnallocated,
          allocationStatus: newUnallocated <= 0 ? 'Fully Allocated' : 'Partially Allocated',
          customerId: inv.customerId,
          customerName: inv.customerName
        };
      }
      return t;
    }));

    logAudit('Manual Payment Reconciliation', 'PaymentAllocation', inv.invoiceNumber, undefined, `Allocated ₹${allocatedAmount}`);
  };

  const autoApproveHighConfidence = (): number => {
    const highMatches = suggestedMatches.filter(m => m.confidenceLevel === 'High' && m.confidenceScore >= (settings.autoMatchConfidenceThreshold || 90));
    let approvedCount = 0;
    highMatches.forEach(match => {
      approveMatch(match);
      approvedCount++;
    });
    return approvedCount;
  };

  const allocatePaymentManually = (
    transactionId: string,
    invoiceId: string,
    allocatedAmount: number,
    tdsDeducted: number,
    reason?: string
  ) => {
    manualMatch(transactionId, invoiceId, allocatedAmount, tdsDeducted, reason);
  };

  const updateException = (id: string, updates: Partial<ExceptionItem>) => {
    setExceptions(prev => prev.map(e => (e.id === id ? { ...e, ...updates } : e)));
    logAudit('Updated Exception Status', 'ExceptionItem', id);
  };

  const resolveException = (id: string, resolution: string) => {
    setExceptions(prev => prev.map(e => (e.id === id ? {
      ...e,
      status: 'Resolved',
      resolution,
      resolvedAt: new Date().toISOString()
    } : e)));
    logAudit('Resolved Exception', 'ExceptionItem', id, undefined, resolution);
  };

  const addDocument = (docData: Omit<DocumentItem, 'id' | 'uploadedAt' | 'uploadedBy'>) => {
    const newDoc: DocumentItem = {
      ...docData,
      id: `doc-${Date.now()}`,
      uploadedAt: new Date().toISOString().replace('T', ' ').substring(0, 16),
      uploadedBy: currentUser.name
    };
    setDocuments(prev => [newDoc, ...prev]);
    logAudit('Uploaded Financial Document', 'DocumentItem', newDoc.id, undefined, newDoc.fileName);
  };

  const deleteDocument = (id: string) => {
    setDocuments(prev => prev.filter(d => d.id !== id));
    logAudit('Deleted Document', 'DocumentItem', id);
  };

  const updateSettings = (newSettings: Partial<ReconciliationSettings>) => {
    setSettings(prev => ({ ...prev, ...newSettings }));
    logAudit('Updated Reconciliation Tolerance Settings', 'Settings', 'reconciliation');
  };

  const resetToDemoData = () => {
    setCompanies(DEMO_COMPANIES);
    setActiveCompanyId('comp-101');
    setCompany(DEMO_COMPANY);
    setCustomers(DEMO_CUSTOMERS);
    setInvoices(DEMO_INVOICES);
    setBankTransactions(DEMO_BANK_TRANSACTIONS);
    setTdsRecords(DEMO_26AS_RECORDS);
    setGstRecords(DEMO_GST_RECORDS);
    setExceptions(DEMO_EXCEPTIONS);
    setDocuments(DEMO_DOCUMENTS);
    setAuditLogs(DEMO_AUDIT_LOGS);
    setAllocations([]);
    setSettings(DEMO_RECONCILIATION_SETTINGS);
    setUsers(DEMO_USERS);
    setCurrentUser(DEMO_USERS[0]);
    setIsAuthenticated(false);
    localStorage.clear();
    localStorage.setItem(STORAGE_VERSION_KEY, CURRENT_STORAGE_VERSION);
    localStorage.setItem('finrecon_companies_list', JSON.stringify(DEMO_COMPANIES));
    localStorage.setItem('finrecon_active_company_id', 'comp-101');
  };

  // Comprehensive Financial KPIs
  const kpis = useMemo(() => {
    const totalSales = invoices.reduce((sum, inv) => sum + (inv.status !== 'Cancelled' ? inv.totalInvoiceValue : 0), 0);
    
    // Monthly calculations
    const now = new Date();
    const currentMonthPrefix = now.toISOString().substring(0, 7);
    const lastMonthDate = new Date(now.getFullYear(), now.getMonth() - 1, 1);
    const prevMonthPrefix = lastMonthDate.toISOString().substring(0, 7);

    const currentMonthSales = invoices.reduce((sum, inv) => {
      return inv.invoiceDate.startsWith(currentMonthPrefix) && inv.status !== 'Cancelled' ? sum + inv.totalInvoiceValue : sum;
    }, 0);

    const previousMonthSales = invoices.reduce((sum, inv) => {
      return inv.invoiceDate.startsWith(prevMonthPrefix) && inv.status !== 'Cancelled' ? sum + inv.totalInvoiceValue : sum;
    }, 0);

    const totalOutstanding = invoices.reduce((sum, inv) => {
      return inv.balance > 0 && inv.status !== 'Cancelled' && inv.status !== 'Written Off' ? sum + inv.balance : sum;
    }, 0);

    let totalOverdue = 0;
    let notDueAmount = 0;
    let overdue90Plus = 0;

    invoices.forEach(inv => {
      if (inv.balance > 0 && inv.status !== 'Cancelled' && inv.status !== 'Written Off') {
        const odDays = calculateOverdueDays(inv.dueDate);
        if (odDays > 0) {
          totalOverdue += inv.balance;
          if (odDays > 90) {
            overdue90Plus += inv.balance;
          }
        } else {
          notDueAmount += inv.balance;
        }
      }
    });

    const totalCollections = bankTransactions.reduce((sum, tx) => sum + (tx.isCredit ? tx.allocatedAmount : 0), 0);
    const unallocatedReceipts = bankTransactions.filter(tx => tx.isCredit && tx.unallocatedAmount > 0);
    const unallocatedReceiptsCount = unallocatedReceipts.length;
    const unallocatedReceiptsAmount = unallocatedReceipts.reduce((sum, tx) => sum + tx.unallocatedAmount, 0);

    const partiallyAllocatedCount = bankTransactions.filter(tx => tx.allocationStatus === 'Partially Allocated').length;

    const expectedTds = invoices.reduce((sum, inv) => sum + (inv.tdsApplicable ? inv.expectedTds : 0), 0);
    const reflectedTds = tdsRecords.reduce((sum, r) => sum + r.tdsDeposited, 0);
    const pendingTds = Math.max(0, expectedTds - reflectedTds);
    const mismatchTds = tdsRecords.filter(r => r.status === 'TDS Mismatch').reduce((sum, r) => sum + Math.abs(r.discrepancyAmount || 0), 0);

    const matchedTransactionsCount = bankTransactions.filter(t => t.allocationStatus === 'Fully Allocated').length;
    const unmatchedInvoicesCount = invoices.filter(i => i.balance > 0).length;
    const openExceptionsCount = exceptions.filter(e => e.status === 'Open').length;

    const collectionRate = totalSales > 0 ? (totalCollections / totalSales) * 100 : 0;
    const dsoDays = totalSales > 0 ? Math.round((totalOutstanding / totalSales) * 90) : 0;

    return {
      totalSales,
      currentMonthSales,
      previousMonthSales,
      totalCollections,
      totalOutstanding,
      totalOverdue,
      notDueAmount,
      overdue90Plus,
      unallocatedReceiptsCount,
      unallocatedReceiptsAmount,
      partiallyAllocatedCount,
      expectedTds,
      reflectedTds,
      pendingTds,
      mismatchTds,
      matchedTransactionsCount,
      unmatchedReceiptsCount: unallocatedReceiptsCount,
      unmatchedInvoicesCount,
      openExceptionsCount,
      collectionRate,
      dsoDays
    };
  }, [invoices, bankTransactions, tdsRecords, exceptions]);

  return (
    <AppContext.Provider
      value={{
        company,
        companies,
        activeCompanyId,
        switchCompany,
        addCompany,
        deleteCompany,
        updateCompany,
        isAuthenticated,
        login,
        logout,
        updateUserPassword,
        currentUser,
        users,
        setCurrentUserRole,
        updateUserName,
        updateUser,
        addUser,
        customers,
        invoices,
        bankTransactions,
        allocations,
        tdsRecords,
        gstRecords,
        exceptions,
        documents,
        auditLogs,
        settings,
        suggestedMatches,
        refreshReconciliation,
        addCustomer,
        updateCustomer,
        deleteCustomer,
        addInvoice,
        addBankTransaction,
        importInvoicesBatch,
        importBankTransactionsBatch,
        importTdsRecordsBatch,
        importGstRecordsBatch,
        approveMatch,
        autoApproveHighConfidence,
        rejectMatch,
        manualMatch,
        allocatePaymentManually,
        updateException,
        resolveException,
        addDocument,
        deleteDocument,
        updateSettings,
        resetToDemoData,
        kpis
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};
