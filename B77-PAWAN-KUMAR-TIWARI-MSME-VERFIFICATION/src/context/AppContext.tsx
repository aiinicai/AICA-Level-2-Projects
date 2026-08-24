import React, { createContext, useContext, useState, useEffect, useMemo } from 'react';
import {
  Vendor,
  Invoice,
  PartPayment,
  RateMasterEntry,
  StatutoryRuleConfig,
  AuditLogEntry,
  UserRole,
  ExceptionAlert,
  InvoiceInterestResult,
  AgeingBucketSummary,
  MSMEStatus,
  MSMECategory,
  VerificationStatus,
} from '../types';
import {
  initialVendors,
  initialInvoices,
  initialRateMaster,
  initialStatutoryRules,
  initialAuditLogs,
} from '../data/initialData';
import {
  calculateMSMEDueDate,
  calculateInvoiceInterest,
  calculateAgeingBuckets,
} from '../utils/calculator';
import { checkPanGstinMatch, isValidPAN, isValidGSTIN, isValidUdyam, getDaysDifference } from '../utils/formatters';

interface AppContextType {
  vendors: Vendor[];
  invoices: Invoice[];
  rateMaster: RateMasterEntry[];
  statutoryRules: StatutoryRuleConfig;
  auditLogs: AuditLogEntry[];
  currentUserRole: UserRole;
  currentUserName: string;
  selectedFinancialYear: string;
  asOfDate: string;
  activeTab: string;
  exceptionAlerts: ExceptionAlert[];
  invoiceCalculations: InvoiceInterestResult[];
  ageingSummary: {
    buckets: AgeingBucketSummary[];
    totalPrincipal: number;
    totalInterest: number;
    totalPayable: number;
  };
  metrics: {
    totalVendors: number;
    msmeVendors: number;
    microCount: number;
    smallCount: number;
    mediumCount: number;
    verifiedMSMECount: number;
    pendingVerificationCount: number;
    totalMSMEOutstanding: number;
    overdueOutstanding: number;
    overdueInvoicesCount: number;
    estimatedInterestLiability: number;
    interestAlreadyProvided: number;
    interestYetToBeProvided: number;
    section43BHTaxExposure: number;
  };
  setCurrentUserRole: (role: UserRole) => void;
  setCurrentUserName: (name: string) => void;
  setSelectedFinancialYear: (fy: string) => void;
  setAsOfDate: (date: string) => void;
  setActiveTab: (tab: string) => void;
  addVendor: (vendor: Omit<Vendor, 'id' | 'createdDate' | 'updatedDate' | 'verificationHistory'>) => void;
  updateVendor: (id: string, updates: Partial<Vendor>, reason?: string) => void;
  deleteVendor: (id: string) => void;
  verifyVendorPortal: (vendorId: string, customStatus?: VerificationStatus, notes?: string) => Promise<boolean>;
  addInvoice: (invoice: Omit<Invoice, 'id' | 'createdAt' | 'updatedAt' | 'payments' | 'amountPaid' | 'outstandingAmount' | 'status' | 'finalDueDate' | 'statutoryLimitDays'>) => { success: boolean; message?: string };
  updateInvoice: (id: string, updates: Partial<Invoice>, reason?: string) => void;
  deleteInvoice: (id: string) => void;
  bulkAddInvoices: (invoices: Invoice[]) => void;
  bulkAddVendors: (vendors: Partial<Vendor>[]) => void;
  bulkAddPayments: (payments: {
    invoiceId: string;
    invoiceNumber: string;
    amount: number;
    paymentDate: string;
    paymentReference: string;
    paymentMode?: 'NEFT' | 'RTGS' | 'Cheque' | 'UPI' | 'Direct Debit';
    bankReferenceNo?: string;
    remarks?: string;
  }[]) => void;
  addPartPayment: (invoiceId: string, payment: Omit<PartPayment, 'id' | 'invoiceId' | 'recordedBy' | 'recordedAt'>) => void;
  deletePartPayment: (invoiceId: string, paymentId: string) => void;
  addRateEntry: (entry: Omit<RateMasterEntry, 'id' | 'updatedBy' | 'updatedAt'>) => void;
  updateRateEntry: (id: string, updates: Partial<RateMasterEntry>, reason?: string) => void;
  updateStatutoryRules: (rules: Partial<StatutoryRuleConfig>, reason: string) => void;
  overrideInvoiceDueDate: (invoiceId: string, newDueDate: string, reason: string) => void;
  approveAuditLog: (logId: string) => void;
  rejectAuditLog: (logId: string) => void;
  resetToDemoData: () => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Load from localStorage or defaults
  const [vendors, setVendors] = useState<Vendor[]>(() => {
    try {
      const stored = localStorage.getItem('msme_vendors');
      return stored ? JSON.parse(stored) : initialVendors;
    } catch {
      return initialVendors;
    }
  });

  const [invoices, setInvoices] = useState<Invoice[]>(() => {
    try {
      const stored = localStorage.getItem('msme_invoices');
      return stored ? JSON.parse(stored) : initialInvoices;
    } catch {
      return initialInvoices;
    }
  });

  const [rateMaster, setRateMaster] = useState<RateMasterEntry[]>(() => {
    try {
      const stored = localStorage.getItem('msme_rate_master');
      return stored ? JSON.parse(stored) : initialRateMaster;
    } catch {
      return initialRateMaster;
    }
  });

  const [statutoryRules, setStatutoryRules] = useState<StatutoryRuleConfig>(() => {
    try {
      const stored = localStorage.getItem('msme_statutory_rules');
      return stored ? JSON.parse(stored) : initialStatutoryRules;
    } catch {
      return initialStatutoryRules;
    }
  });

  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>(() => {
    try {
      const stored = localStorage.getItem('msme_audit_logs');
      return stored ? JSON.parse(stored) : initialAuditLogs;
    } catch {
      return initialAuditLogs;
    }
  });

  const [currentUserRole, setCurrentUserRole] = useState<UserRole>('Finance Manager');
  const [currentUserName, setCurrentUserName] = useState<string>('Pawan Kumar (Finance Manager)');
  const [selectedFinancialYear, setSelectedFinancialYear] = useState<string>('All');
  const [asOfDate, setAsOfDate] = useState<string>(() => new Date().toISOString().split('T')[0]);
  const [activeTab, setActiveTab] = useState<string>('dashboard');

  // Persist to local storage
  useEffect(() => {
    try {
      localStorage.setItem('msme_vendors', JSON.stringify(vendors));
    } catch (e) {
      console.error(e);
    }
  }, [vendors]);

  useEffect(() => {
    try {
      localStorage.setItem('msme_invoices', JSON.stringify(invoices));
    } catch (e) {
      console.error(e);
    }
  }, [invoices]);

  useEffect(() => {
    try {
      localStorage.setItem('msme_rate_master', JSON.stringify(rateMaster));
    } catch (e) {
      console.error(e);
    }
  }, [rateMaster]);

  useEffect(() => {
    try {
      localStorage.setItem('msme_statutory_rules', JSON.stringify(statutoryRules));
    } catch (e) {
      console.error(e);
    }
  }, [statutoryRules]);

  useEffect(() => {
    try {
      localStorage.setItem('msme_audit_logs', JSON.stringify(auditLogs));
    } catch (e) {
      console.error(e);
    }
  }, [auditLogs]);

  // Filter invoices by Financial Year if selected
  const filteredInvoices = useMemo(() => {
    if (selectedFinancialYear === 'All') return invoices;
    return invoices.filter((inv) => inv.financialYear === selectedFinancialYear);
  }, [invoices, selectedFinancialYear]);

  // Compute interest results for all filtered invoices
  const invoiceCalculations = useMemo(() => {
    return filteredInvoices.map((inv) => calculateInvoiceInterest(inv, rateMaster, statutoryRules, asOfDate));
  }, [filteredInvoices, rateMaster, statutoryRules, asOfDate]);

  // Compute Ageing summary
  const ageingSummary = useMemo(() => {
    return calculateAgeingBuckets(filteredInvoices, rateMaster, statutoryRules, asOfDate);
  }, [filteredInvoices, rateMaster, statutoryRules, asOfDate]);

  // Compute Exception Alerts
  const exceptionAlerts = useMemo(() => {
    const alerts: ExceptionAlert[] = [];

    // 1. Vendor alerts
    vendors.forEach((v) => {
      if (v.isMSME && (!v.certificateFileName || v.certificateFileName.trim() === '')) {
        alerts.push({
          id: `alert-cert-${v.id}`,
          type: 'CERTIFICATE_MISSING',
          severity: 'HIGH',
          title: 'MSME Certificate Missing',
          description: `Vendor "${v.vendorName}" (${v.vendorCode}) is classified as ${v.msmeCategory} but does not have an uploaded Udyam certificate.`,
          entityId: v.id,
          entityName: v.vendorName,
          vendorId: v.id,
          date: v.updatedDate || v.createdDate,
          actionRequired: 'Upload and verify Udyam certificate.',
          targetModule: 'Vendor Master',
        });
      }

      if (v.isMSME && v.verificationStatus === 'Pending') {
        alerts.push({
          id: `alert-ver-pend-${v.id}`,
          type: 'VERIFICATION_PENDING',
          severity: 'MEDIUM',
          title: 'Udyam Verification Pending',
          description: `Vendor "${v.vendorName}" Udyam registration verification on official portal is pending.`,
          entityId: v.id,
          entityName: v.vendorName,
          vendorId: v.id,
          date: v.createdDate,
          actionRequired: 'Verify on Udyam Portal.',
          targetModule: 'MSME Verification',
        });
      }

      if (v.pan && v.gstin && !checkPanGstinMatch(v.pan, v.gstin)) {
        alerts.push({
          id: `alert-mismatch-${v.id}`,
          type: 'PAN_GSTIN_MISMATCH',
          severity: 'HIGH',
          title: 'PAN & GSTIN Mismatch',
          description: `PAN (${v.pan}) does not match the embedded PAN in GSTIN (${v.gstin}) for vendor "${v.vendorName}".`,
          entityId: v.id,
          entityName: v.vendorName,
          vendorId: v.id,
          date: v.updatedDate,
          actionRequired: 'Rectify vendor PAN or GSTIN credentials.',
          targetModule: 'Vendor Master',
        });
      }

      if (v.verificationStatus === 'Mismatch') {
        alerts.push({
          id: `alert-udyam-mismatch-${v.id}`,
          type: 'UDYAM_MISMATCH',
          severity: 'HIGH',
          title: 'Udyam Registration Mismatch',
          description: `Portal verification detected discrepancies in enterprise category or name for "${v.vendorName}".`,
          entityId: v.id,
          entityName: v.vendorName,
          vendorId: v.id,
          date: v.updatedDate,
          actionRequired: 'Request fresh Udyam Certificate from vendor.',
          targetModule: 'MSME Verification',
        });
      }
    });

    // 2. Invoice alerts
    invoiceCalculations.forEach((calc) => {
      const inv = invoices.find((i) => i.id === calc.invoiceId);
      if (!inv) return;

      if (calc.isOverdue) {
        alerts.push({
          id: `alert-overdue-${inv.id}`,
          type: 'OVERDUE_INVOICE',
          severity: 'HIGH',
          title: `Overdue Invoice: ${inv.invoiceNumber}`,
          description: `Payment of ${inv.outstandingAmount} to "${inv.vendorName}" is overdue by ${calc.totalDelayDays} days beyond statutory due date (${inv.finalDueDate}).`,
          entityId: inv.id,
          entityName: inv.invoiceNumber,
          vendorId: inv.vendorId,
          invoiceId: inv.id,
          amount: inv.outstandingAmount,
          date: inv.finalDueDate,
          actionRequired: 'Release payment immediately to arrest mounting compound interest.',
          targetModule: 'Payment Register',
        });
      }

      if (calc.totalInterestPayable > 25000) {
        alerts.push({
          id: `alert-interest-exp-${inv.id}`,
          type: 'HIGH_INTEREST_EXPOSURE',
          severity: 'HIGH',
          title: `High Interest Liability: ${inv.invoiceNumber}`,
          description: `Estimated accrued statutory interest on invoice ${inv.invoiceNumber} has reached ₹${calc.totalInterestPayable.toLocaleString('en-IN')}.`,
          entityId: inv.id,
          entityName: inv.invoiceNumber,
          vendorId: inv.vendorId,
          invoiceId: inv.id,
          amount: calc.totalInterestPayable,
          date: asOfDate,
          actionRequired: 'Prioritise settlement to prevent non-deductible interest expense.',
          targetModule: 'Interest Calculator',
        });
      }

      if (calc.section43BHRisk) {
        alerts.push({
          id: `alert-43bh-${inv.id}`,
          type: '43BH_TAX_RISK',
          severity: 'HIGH',
          title: `Sec 43B(h) Tax Disallowance Risk: ${inv.invoiceNumber}`,
          description: `Overdue payment to ${inv.msmeCategory} vendor "${inv.vendorName}" risks income tax expense disallowance under Section 43B(h).`,
          entityId: inv.id,
          entityName: inv.invoiceNumber,
          vendorId: inv.vendorId,
          invoiceId: inv.id,
          amount: inv.outstandingAmount,
          date: inv.finalDueDate,
          actionRequired: 'Discharge liability before FY closing to claim tax deduction.',
          targetModule: 'Invoice Register',
        });
      }

      if (calc.status === 'Approaching Due') {
        const daysLeft = getDaysDifference(asOfDate, inv.finalDueDate);
        alerts.push({
          id: `alert-due-soon-${inv.id}`,
          type: 'DUE_SOON',
          severity: 'MEDIUM',
          title: `Invoice Approaching Due Date (${daysLeft} days remaining)`,
          description: `Invoice ${inv.invoiceNumber} for ₹${inv.outstandingAmount.toLocaleString('en-IN')} is due on ${inv.finalDueDate}.`,
          entityId: inv.id,
          entityName: inv.invoiceNumber,
          vendorId: inv.vendorId,
          invoiceId: inv.id,
          amount: inv.outstandingAmount,
          date: inv.finalDueDate,
          actionRequired: 'Process payment voucher in accounts.',
          targetModule: 'Payment Register',
        });
      }
    });

    return alerts;
  }, [vendors, invoiceCalculations, invoices, asOfDate]);

  // Overall Dashboard Metrics
  const metrics = useMemo(() => {
    const totalVendors = vendors.length;
    const msmeVendors = vendors.filter((v) => v.isMSME).length;
    const microCount = vendors.filter((v) => v.isMSME && v.msmeCategory === 'Micro').length;
    const smallCount = vendors.filter((v) => v.isMSME && v.msmeCategory === 'Small').length;
    const mediumCount = vendors.filter((v) => v.isMSME && v.msmeCategory === 'Medium').length;
    const verifiedMSMECount = vendors.filter((v) => v.isMSME && v.verificationStatus === 'Verified').length;
    const pendingVerificationCount = vendors.filter((v) => v.isMSME && v.verificationStatus === 'Pending').length;

    let totalMSMEOutstanding = 0;
    let overdueOutstanding = 0;
    let overdueInvoicesCount = 0;
    let estimatedInterestLiability = 0;
    let section43BHTaxExposure = 0;

    invoiceCalculations.forEach((calc) => {
      const isMSME = calc.msmeCategory !== 'Not Applicable';
      if (isMSME) {
        totalMSMEOutstanding += calc.outstandingPrincipal;
        if (calc.isOverdue) {
          overdueOutstanding += calc.outstandingPrincipal;
          overdueInvoicesCount += 1;
        }
        estimatedInterestLiability += calc.totalInterestPayable;
        if (calc.section43BHRisk) {
          section43BHTaxExposure += calc.outstandingPrincipal;
        }
      }
    });

    // Assume 30% of calculated interest has been accrued/provided in books
    const interestAlreadyProvided = Math.round(estimatedInterestLiability * 0.35);
    const interestYetToBeProvided = Math.max(0, estimatedInterestLiability - interestAlreadyProvided);

    return {
      totalVendors,
      msmeVendors,
      microCount,
      smallCount,
      mediumCount,
      verifiedMSMECount,
      pendingVerificationCount,
      totalMSMEOutstanding: Math.round(totalMSMEOutstanding * 100) / 100,
      overdueOutstanding: Math.round(overdueOutstanding * 100) / 100,
      overdueInvoicesCount,
      estimatedInterestLiability: Math.round(estimatedInterestLiability * 100) / 100,
      interestAlreadyProvided,
      interestYetToBeProvided,
      section43BHTaxExposure,
    };
  }, [vendors, invoiceCalculations]);

  // Audit log helper
  const logAction = (
    module: AuditLogEntry['module'],
    entityId: string,
    action: AuditLogEntry['action'],
    reason: string,
    fieldName?: string,
    originalValue?: string,
    revisedValue?: string,
    requiresApproval: boolean = false
  ) => {
    const newLog: AuditLogEntry = {
      id: `audit-${Date.now()}-${Math.floor(Math.random() * 1000)}`,
      timestamp: new Date().toISOString(),
      user: currentUserName,
      userRole: currentUserRole,
      module,
      entityId,
      action,
      fieldName,
      originalValue,
      revisedValue,
      reason,
      requiresApproval,
      approvalStatus: requiresApproval ? 'Pending' : 'Approved',
      approvedBy: requiresApproval ? undefined : currentUserName,
      approvedAt: requiresApproval ? undefined : new Date().toISOString(),
    };

    setAuditLogs((prev) => [newLog, ...prev]);
  };

  // Vendor Methods
  const addVendor = (vendorData: Omit<Vendor, 'id' | 'createdDate' | 'updatedDate' | 'verificationHistory'>) => {
    const newId = `VEND-${String(vendors.length + 1).padStart(3, '0')}`;
    const today = new Date().toISOString().split('T')[0];

    const newVendor: Vendor = {
      ...vendorData,
      id: newId,
      createdDate: today,
      updatedDate: today,
      verificationHistory: [],
    };

    setVendors((prev) => [...prev, newVendor]);
    logAction('Vendor Master', newId, 'CREATE', `Added vendor ${newVendor.vendorName} (${newVendor.vendorCode})`);
  };

  const updateVendor = (id: string, updates: Partial<Vendor>, reason: string = 'Updated vendor details') => {
    const existing = vendors.find((v) => v.id === id);
    if (!existing) return;

    const today = new Date().toISOString().split('T')[0];
    const updatedVendor = { ...existing, ...updates, updatedDate: today };

    setVendors((prev) => prev.map((v) => (v.id === id ? updatedVendor : v)));
    logAction('Vendor Master', id, 'UPDATE', reason, 'vendorProfile', JSON.stringify(existing), JSON.stringify(updatedVendor));
  };

  const deleteVendor = (id: string) => {
    const existing = vendors.find((v) => v.id === id);
    if (!existing) return;

    setVendors((prev) => prev.filter((v) => v.id !== id));
    logAction('Vendor Master', id, 'DELETE', `Deleted vendor ${existing.vendorName} (${existing.vendorCode})`);
  };

  const verifyVendorPortal = async (vendorId: string, customStatus?: VerificationStatus, notes?: string): Promise<boolean> => {
    const vendor = vendors.find((v) => v.id === vendorId);
    if (!vendor) return false;

    // Simulate verification delay
    await new Promise((resolve) => setTimeout(resolve, 800));

    let finalStatus: VerificationStatus = customStatus || 'Verified';
    let portalResponse = 'Active. Major Activity: ' + vendor.majorActivity + '. Category: ' + vendor.msmeCategory;

    if (!customStatus) {
      if (!vendor.udyamNumber || !isValidUdyam(vendor.udyamNumber)) {
        finalStatus = 'Not Found';
        portalResponse = 'Invalid Udyam Registration format or not registered in MSME database.';
      } else if (vendor.pan && vendor.gstin && !checkPanGstinMatch(vendor.pan, vendor.gstin)) {
        finalStatus = 'Mismatch';
        portalResponse = 'Mismatch detected between declared PAN and GSTIN records.';
      } else {
        finalStatus = 'Verified';
      }
    }

    const today = new Date().toISOString().split('T')[0];
    const timestamp = new Date().toISOString();

    const verificationLog = {
      id: `vh-${Date.now()}`,
      timestamp,
      verifiedBy: currentUserName,
      previousStatus: vendor.verificationStatus,
      newStatus: finalStatus,
      previousCategory: vendor.msmeCategory,
      newCategory: vendor.msmeCategory,
      udyamChecked: vendor.udyamNumber || 'N/A',
      portalResponse,
      remarks: notes || `Portal verification executed by ${currentUserName}`,
    };

    const updatedVendor: Vendor = {
      ...vendor,
      verificationStatus: finalStatus,
      verificationDate: today,
      verifiedBy: currentUserName,
      updatedDate: today,
      verificationHistory: [verificationLog, ...vendor.verificationHistory],
    };

    setVendors((prev) => prev.map((v) => (v.id === vendorId ? updatedVendor : v)));
    logAction(
      'Verification',
      vendorId,
      'VERIFY',
      notes || `Status changed from ${vendor.verificationStatus} to ${finalStatus}`,
      'verificationStatus',
      vendor.verificationStatus,
      finalStatus
    );

    return true;
  };

  // Invoice Methods
  const addInvoice = (
    invoiceData: Omit<Invoice, 'id' | 'createdAt' | 'updatedAt' | 'payments' | 'amountPaid' | 'outstandingAmount' | 'status' | 'finalDueDate' | 'statutoryLimitDays'>
  ): { success: boolean; message?: string } => {
    // Check for duplicate invoice number for the same vendor
    const isDuplicate = invoices.some(
      (inv) =>
        inv.vendorId === invoiceData.vendorId &&
        inv.invoiceNumber.trim().toLowerCase() === invoiceData.invoiceNumber.trim().toLowerCase()
    );

    if (isDuplicate) {
      return {
        success: false,
        message: `Duplicate Invoice: Invoice number "${invoiceData.invoiceNumber}" already exists for this vendor.`,
      };
    }

    const newId = `INV-${Date.now()}`;
    const totalInvoiceAmount = invoiceData.invoiceAmount + invoiceData.gstAmount;

    const dueDateCalc = calculateMSMEDueDate(
      invoiceData.mrnDate,
      invoiceData.acceptanceDate,
      invoiceData.hasWrittenAgreement,
      invoiceData.creditDays,
      invoiceData.isMSME,
      statutoryRules
    );

    const newInvoice: Invoice = {
      ...invoiceData,
      id: newId,
      totalInvoiceAmount,
      statutoryLimitDays: dueDateCalc.statutoryLimitDays,
      creditDays: dueDateCalc.effectiveCreditDays,
      acceptanceDate: dueDateCalc.effectiveAcceptanceDate,
      deemedAcceptanceDate: dueDateCalc.deemedAcceptanceDate,
      finalDueDate: dueDateCalc.finalDueDate,
      payments: [],
      amountPaid: 0,
      outstandingAmount: totalInvoiceAmount,
      status: 'Unpaid',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    setInvoices((prev) => [newInvoice, ...prev]);
    logAction(
      'Invoice Register',
      newId,
      'CREATE',
      `Registered invoice ${newInvoice.invoiceNumber} for ₹${totalInvoiceAmount.toLocaleString('en-IN')} (${newInvoice.vendorName})`
    );

    return { success: true };
  };

  const updateInvoice = (id: string, updates: Partial<Invoice>, reason: string = 'Updated invoice details') => {
    const existing = invoices.find((i) => i.id === id);
    if (!existing) return;

    const requiresApproval = Boolean(updates.finalDueDate && updates.finalDueDate !== existing.finalDueDate);

    const merged = { ...existing, ...updates, updatedAt: new Date().toISOString() };
    const totalAmount = merged.invoiceAmount + merged.gstAmount;
    merged.totalInvoiceAmount = totalAmount;
    merged.outstandingAmount = Math.max(0, totalAmount - merged.amountPaid);
    merged.status = merged.outstandingAmount === 0 ? 'Paid' : merged.amountPaid > 0 ? 'Partially Paid' : 'Unpaid';

    setInvoices((prev) => prev.map((inv) => (inv.id === id ? merged : inv)));
    logAction(
      'Invoice Register',
      id,
      'UPDATE',
      reason,
      'invoiceData',
      JSON.stringify(existing),
      JSON.stringify(merged),
      requiresApproval
    );
  };

  const deleteInvoice = (id: string) => {
    const existing = invoices.find((i) => i.id === id);
    if (!existing) return;

    setInvoices((prev) => prev.filter((i) => i.id !== id));
    logAction('Invoice Register', id, 'DELETE', `Deleted invoice ${existing.invoiceNumber} (${existing.vendorName})`);
  };

  const bulkAddInvoices = (newInvoices: Invoice[]) => {
    setInvoices((prev) => [...newInvoices, ...prev]);
    logAction('Invoice Register', 'BULK_IMPORT', 'BULK_IMPORT', `Imported ${newInvoices.length} invoices via Excel template.`);
  };

  const bulkAddVendors = (newVendors: Partial<Vendor>[]) => {
    const formatted: Vendor[] = newVendors.map((v, i) => ({
      id: v.id || `VEND-IMP-${Date.now()}-${i}`,
      vendorCode: v.vendorCode || `V-${1000 + i}`,
      vendorName: v.vendorName || 'Unknown Vendor',
      pan: v.pan || '',
      gstin: v.gstin || '',
      udyamNumber: v.udyamNumber || '',
      isMSME: v.isMSME ?? true,
      msmeStatus: v.msmeStatus || 'MSME',
      msmeCategory: v.msmeCategory || 'Micro',
      majorActivity: v.majorActivity || 'Manufacturing',
      udyamRegistrationDate: v.udyamRegistrationDate,
      verificationDate: v.verificationDate,
      verificationStatus: v.verificationStatus || 'Pending',
      hasWrittenAgreement: v.hasWrittenAgreement ?? true,
      agreedCreditDays: v.agreedCreditDays || 30,
      contactPerson: v.contactPerson,
      email: v.email,
      phone: v.phone,
      remarks: v.remarks || 'Imported via Excel',
      verificationHistory: [],
      createdDate: new Date().toISOString().split('T')[0],
      updatedDate: new Date().toISOString().split('T')[0],
    }));

    setVendors((prev) => [...prev, ...formatted]);
    logAction('Vendor Master', 'BULK_IMPORT', 'BULK_IMPORT', `Imported ${formatted.length} vendors via Excel.`);
  };

  const bulkAddPayments = (
    newPayments: {
      invoiceId: string;
      invoiceNumber: string;
      amount: number;
      paymentDate: string;
      paymentReference: string;
      paymentMode?: 'NEFT' | 'RTGS' | 'Cheque' | 'UPI' | 'Direct Debit';
      bankReferenceNo?: string;
      remarks?: string;
    }[]
  ) => {
    setInvoices((prev) => {
      const updated = prev.map((inv) => {
        const matchingPayments = newPayments.filter((p) => p.invoiceId === inv.id || p.invoiceNumber === inv.invoiceNumber);
        if (matchingPayments.length === 0) return inv;

        const additionalPartPayments: PartPayment[] = matchingPayments.map((p, idx) => ({
          id: `pmt-bulk-${Date.now()}-${idx}`,
          invoiceId: inv.id,
          paymentReference: p.paymentReference,
          paymentDate: p.paymentDate,
          amount: p.amount,
          paymentMode: p.paymentMode || 'NEFT',
          bankReferenceNo: p.bankReferenceNo,
          remarks: p.remarks || 'Imported via Excel payment clearing file',
          recordedBy: currentUserName,
          recordedAt: new Date().toISOString(),
        }));

        const combinedPayments = [...inv.payments, ...additionalPartPayments];
        const amountPaid = combinedPayments.reduce((sum, p) => sum + p.amount, 0);
        const outstandingAmount = Math.max(0, inv.totalInvoiceAmount - amountPaid);
        const status: Invoice['status'] = outstandingAmount === 0 ? 'Paid' : amountPaid > 0 ? 'Partially Paid' : 'Unpaid';

        return {
          ...inv,
          payments: combinedPayments,
          amountPaid,
          outstandingAmount,
          status,
          updatedAt: new Date().toISOString(),
        };
      });
      return updated;
    });

    logAction(
      'Payment Register',
      'BULK_IMPORT',
      'BULK_IMPORT',
      `Imported and matched ${newPayments.length} payment tranche(s) via Excel clearing file.`
    );
  };

  // Payment Methods
  const addPartPayment = (
    invoiceId: string,
    paymentData: Omit<PartPayment, 'id' | 'invoiceId' | 'recordedBy' | 'recordedAt'>
  ) => {
    const invoice = invoices.find((i) => i.id === invoiceId);
    if (!invoice) return;

    const newPayment: PartPayment = {
      ...paymentData,
      id: `pmt-${Date.now()}`,
      invoiceId,
      recordedBy: currentUserName,
      recordedAt: new Date().toISOString(),
    };

    const updatedPayments = [...invoice.payments, newPayment];
    const amountPaid = updatedPayments.reduce((sum, p) => sum + p.amount, 0);
    const outstandingAmount = Math.max(0, invoice.totalInvoiceAmount - amountPaid);
    const status = outstandingAmount === 0 ? 'Paid' : amountPaid > 0 ? 'Partially Paid' : 'Unpaid';

    const updatedInvoice: Invoice = {
      ...invoice,
      payments: updatedPayments,
      amountPaid,
      outstandingAmount,
      status,
      updatedAt: new Date().toISOString(),
    };

    setInvoices((prev) => prev.map((inv) => (inv.id === invoiceId ? updatedInvoice : inv)));
    logAction(
      'Payment Register',
      invoiceId,
      'CREATE',
      `Recorded part payment of ₹${paymentData.amount.toLocaleString('en-IN')} (Ref: ${paymentData.paymentReference}) against invoice ${invoice.invoiceNumber}`
    );
  };

  const deletePartPayment = (invoiceId: string, paymentId: string) => {
    const invoice = invoices.find((i) => i.id === invoiceId);
    if (!invoice) return;

    const paymentToDelete = invoice.payments.find((p) => p.id === paymentId);
    const updatedPayments = invoice.payments.filter((p) => p.id !== paymentId);
    const amountPaid = updatedPayments.reduce((sum, p) => sum + p.amount, 0);
    const outstandingAmount = Math.max(0, invoice.totalInvoiceAmount - amountPaid);
    const status = outstandingAmount === 0 ? 'Paid' : amountPaid > 0 ? 'Partially Paid' : 'Unpaid';

    const updatedInvoice: Invoice = {
      ...invoice,
      payments: updatedPayments,
      amountPaid,
      outstandingAmount,
      status,
      updatedAt: new Date().toISOString(),
    };

    setInvoices((prev) => prev.map((inv) => (inv.id === invoiceId ? updatedInvoice : inv)));
    logAction(
      'Payment Register',
      invoiceId,
      'DELETE',
      `Deleted payment tranche of ₹${paymentToDelete?.amount || 0} from invoice ${invoice.invoiceNumber}`
    );
  };

  // Masters
  const addRateEntry = (entry: Omit<RateMasterEntry, 'id' | 'updatedBy' | 'updatedAt'>) => {
    const newEntry: RateMasterEntry = {
      ...entry,
      id: `rate-${Date.now()}`,
      updatedBy: currentUserName,
      updatedAt: new Date().toISOString(),
    };

    setRateMaster((prev) => [newEntry, ...prev]);
    logAction(
      'Interest Rate Master',
      newEntry.id,
      'CREATE',
      `Added new rate rule: ${newEntry.referenceRateType} ${newEntry.referenceRate}% × ${newEntry.multiplier} = ${newEntry.applicableMSMERate}% effective from ${newEntry.effectiveFrom}`,
      'applicableMSMERate',
      undefined,
      `${newEntry.applicableMSMERate}%`,
      true
    );
  };

  const updateRateEntry = (id: string, updates: Partial<RateMasterEntry>, reason: string = 'Updated Rate Master') => {
    const existing = rateMaster.find((r) => r.id === id);
    if (!existing) return;

    const merged: RateMasterEntry = {
      ...existing,
      ...updates,
      updatedBy: currentUserName,
      updatedAt: new Date().toISOString(),
    };

    setRateMaster((prev) => prev.map((r) => (r.id === id ? merged : r)));
    logAction(
      'Interest Rate Master',
      id,
      'UPDATE',
      reason,
      'applicableMSMERate',
      `${existing.applicableMSMERate}%`,
      `${merged.applicableMSMERate}%`,
      true
    );
  };

  const updateStatutoryRules = (rulesUpdates: Partial<StatutoryRuleConfig>, reason: string) => {
    const merged: StatutoryRuleConfig = {
      ...statutoryRules,
      ...rulesUpdates,
      lastUpdated: new Date().toISOString(),
      updatedBy: currentUserName,
    };

    setStatutoryRules(merged);
    logAction(
      'Statutory Rules',
      statutoryRules.id,
      'UPDATE',
      reason,
      'statutoryRules',
      JSON.stringify(statutoryRules),
      JSON.stringify(merged),
      true
    );
  };

  const overrideInvoiceDueDate = (invoiceId: string, newDueDate: string, reason: string) => {
    const inv = invoices.find((i) => i.id === invoiceId);
    if (!inv) return;

    const updatedInvoice: Invoice = {
      ...inv,
      finalDueDate: newDueDate,
      isDueDateManuallyOverridden: true,
      overrideReason: reason,
      overrideApprovedBy: currentUserName,
      updatedAt: new Date().toISOString(),
    };

    setInvoices((prev) => prev.map((i) => (i.id === invoiceId ? updatedInvoice : i)));
    logAction(
      'Manual Override',
      invoiceId,
      'OVERRIDE',
      `Manual Due Date Override from ${inv.finalDueDate} to ${newDueDate}. Reason: ${reason}`,
      'finalDueDate',
      inv.finalDueDate,
      newDueDate,
      true
    );
  };

  const approveAuditLog = (logId: string) => {
    setAuditLogs((prev) =>
      prev.map((log) =>
        log.id === logId
          ? {
              ...log,
              approvalStatus: 'Approved',
              approvedBy: currentUserName,
              approvedAt: new Date().toISOString(),
            }
          : log
      )
    );
  };

  const rejectAuditLog = (logId: string) => {
    setAuditLogs((prev) =>
      prev.map((log) =>
        log.id === logId
          ? {
              ...log,
              approvalStatus: 'Rejected',
              approvedBy: currentUserName,
              approvedAt: new Date().toISOString(),
            }
          : log
      )
    );
  };

  const resetToDemoData = () => {
    setVendors(initialVendors);
    setInvoices(initialInvoices);
    setRateMaster(initialRateMaster);
    setStatutoryRules(initialStatutoryRules);
    setAuditLogs(initialAuditLogs);
    localStorage.removeItem('msme_vendors');
    localStorage.removeItem('msme_invoices');
    localStorage.removeItem('msme_rate_master');
    localStorage.removeItem('msme_statutory_rules');
    localStorage.removeItem('msme_audit_logs');
  };

  return (
    <AppContext.Provider
      value={{
        vendors,
        invoices: filteredInvoices,
        rateMaster,
        statutoryRules,
        auditLogs,
        currentUserRole,
        currentUserName,
        selectedFinancialYear,
        asOfDate,
        activeTab,
        exceptionAlerts,
        invoiceCalculations,
        ageingSummary,
        metrics,
        setCurrentUserRole,
        setCurrentUserName,
        setSelectedFinancialYear,
        setAsOfDate,
        setActiveTab,
        addVendor,
        updateVendor,
        deleteVendor,
        verifyVendorPortal,
        addInvoice,
        updateInvoice,
        deleteInvoice,
        bulkAddInvoices,
        bulkAddVendors,
        bulkAddPayments,
        addPartPayment,
        deletePartPayment,
        addRateEntry,
        updateRateEntry,
        updateStatutoryRules,
        overrideInvoiceDueDate,
        approveAuditLog,
        rejectAuditLog,
        resetToDemoData,
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
