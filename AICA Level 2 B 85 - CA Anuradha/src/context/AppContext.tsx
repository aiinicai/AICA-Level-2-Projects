import React, { createContext, useContext, useState, useEffect } from 'react';
import {
  User,
  Role,
  Department,
  MonthCycle,
  DepartmentSubmission,
  DepartmentCategory,
  AuditLogEntry,
  LineItem,
  ApprovalRecord,
} from '../types';
import {
  INITIAL_USERS,
  INITIAL_CATEGORIES,
  INITIAL_MONTHS,
  INITIAL_SUBMISSIONS,
  INITIAL_AUDIT_LOGS,
} from '../data/initialData';
import { convertInrToAud } from '../utils/formatters';

interface AppContextType {
  currentUser: User;
  setCurrentUser: (user: User) => void;
  users: User[];
  activeMonthId: string;
  setActiveMonthId: (monthId: string) => void;
  months: MonthCycle[];
  activeMonth: MonthCycle;
  submissions: Record<string, DepartmentSubmission[]>;
  currentSubmissions: DepartmentSubmission[];
  categories: DepartmentCategory[];
  auditLogs: AuditLogEntry[];
  currencyMode: 'both' | 'inr' | 'aud';
  setCurrencyMode: (mode: 'both' | 'inr' | 'aud') => void;
  
  // Actions
  saveDepartmentDraft: (monthId: string, department: Department, lineItems: LineItem[], comments?: string) => void;
  submitDepartmentRequirements: (monthId: string, department: Department, lineItems: LineItem[], comments?: string) => void;
  recallDepartmentSubmission: (monthId: string, department: Department) => void;
  updateExchangeRate: (monthId: string, rate: number, rateSource: string) => void;
  setControllerConsolidationNotes: (monthId: string, notes: string) => void;
  markPackReadyForApproval: (monthId: string) => void;
  executeApprovalDecision: (
    monthId: string,
    decision: 'Approved' | 'Approved with Adjustments' | 'Rejected' | 'Changes Requested',
    comments: string,
    adjustedLineItems?: { id: string; approvedAmountInr: number; adjustmentNote?: string }[]
  ) => void;
  openNewMonth: (monthId: string, label: string, deadline: string, initialRate: number, rateSource: string) => void;
  closeMonth: (monthId: string) => void;
  addCategory: (cat: Omit<DepartmentCategory, 'id'>) => void;
  editCategory: (id: string, updates: Partial<DepartmentCategory>) => void;
  deleteCategory: (id: string) => void;
  addUser: (user: Omit<User, 'id'>) => void;
  updateUser: (id: string, updates: Partial<User>) => void;
  resetToInitialData: () => void;
  getPriorMonthSubmission: (currentMonthId: string, department: Department) => DepartmentSubmission | undefined;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

const STORAGE_KEYS = {
  USERS: 'maropost_users_v1',
  CURRENT_USER_ID: 'maropost_current_user_id_v1',
  MONTHS: 'maropost_months_v1',
  ACTIVE_MONTH_ID: 'maropost_active_month_id_v1',
  SUBMISSIONS: 'maropost_submissions_v1',
  CATEGORIES: 'maropost_categories_v1',
  AUDIT_LOGS: 'maropost_audit_logs_v1',
  CURRENCY_MODE: 'maropost_currency_mode_v1',
};

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // 1. Users State
  const [users, setUsers] = useState<User[]>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEYS.USERS);
      return saved ? JSON.parse(saved) : INITIAL_USERS;
    } catch {
      return INITIAL_USERS;
    }
  });

  // Current User
  const [currentUser, setCurrentUserState] = useState<User>(() => {
    try {
      const savedId = localStorage.getItem(STORAGE_KEYS.CURRENT_USER_ID);
      if (savedId) {
        const found = users.find((u) => u.id === savedId);
        if (found) return found;
      }
      return INITIAL_USERS[0]; // Default to HR Head
    } catch {
      return INITIAL_USERS[0];
    }
  });

  const setCurrentUser = (user: User) => {
    setCurrentUserState(user);
    localStorage.setItem(STORAGE_KEYS.CURRENT_USER_ID, user.id);
  };

  // 2. Months State
  const [months, setMonths] = useState<MonthCycle[]>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEYS.MONTHS);
      return saved ? JSON.parse(saved) : INITIAL_MONTHS;
    } catch {
      return INITIAL_MONTHS;
    }
  });

  const [activeMonthId, setActiveMonthId] = useState<string>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEYS.ACTIVE_MONTH_ID);
      return saved || '2026-10';
    } catch {
      return '2026-10';
    }
  });

  // 3. Submissions State
  const [submissions, setSubmissions] = useState<Record<string, DepartmentSubmission[]>>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEYS.SUBMISSIONS);
      return saved ? JSON.parse(saved) : INITIAL_SUBMISSIONS;
    } catch {
      return INITIAL_SUBMISSIONS;
    }
  });

  // 4. Categories State
  const [categories, setCategories] = useState<DepartmentCategory[]>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEYS.CATEGORIES);
      return saved ? JSON.parse(saved) : INITIAL_CATEGORIES;
    } catch {
      return INITIAL_CATEGORIES;
    }
  });

  // 5. Audit Logs State
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEYS.AUDIT_LOGS);
      return saved ? JSON.parse(saved) : INITIAL_AUDIT_LOGS;
    } catch {
      return INITIAL_AUDIT_LOGS;
    }
  });

  // 6. Currency Mode State
  const [currencyMode, setCurrencyMode] = useState<'both' | 'inr' | 'aud'>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEYS.CURRENCY_MODE);
      return (saved as any) || 'both';
    } catch {
      return 'both';
    }
  });

  // Persistence Effects
  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.USERS, JSON.stringify(users));
  }, [users]);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.MONTHS, JSON.stringify(months));
  }, [months]);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.ACTIVE_MONTH_ID, activeMonthId);
  }, [activeMonthId]);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.SUBMISSIONS, JSON.stringify(submissions));
  }, [submissions]);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.CATEGORIES, JSON.stringify(categories));
  }, [categories]);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.AUDIT_LOGS, JSON.stringify(auditLogs));
  }, [auditLogs]);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.CURRENCY_MODE, currencyMode);
  }, [currencyMode]);

  // Derived Active Month
  const activeMonth = months.find((m) => m.id === activeMonthId) || months[0];
  const currentSubmissions = submissions[activeMonthId] || [];

  // Helper to log actions
  const addAuditLog = (
    action: string,
    details: string,
    monthId: string,
    department?: Department
  ) => {
    const entry: AuditLogEntry = {
      id: `log-${Date.now()}-${Math.random().toString(36).substr(2, 4)}`,
      timestamp: new Date().toISOString(),
      userId: currentUser.id,
      userName: currentUser.name,
      userRole: currentUser.role,
      action,
      details,
      monthId,
      department,
    };
    setAuditLogs((prev) => [entry, ...prev]);
  };

  // Helper to find prior month submission for comparison
  const getPriorMonthSubmission = (
    currentMonthId: string,
    department: Department
  ): DepartmentSubmission | undefined => {
    // Find chronological prior month
    const sorted = [...months].sort((a, b) => b.id.localeCompare(a.id));
    const currentIndex = sorted.findIndex((m) => m.id === currentMonthId);
    if (currentIndex >= 0 && currentIndex < sorted.length - 1) {
      const priorMonthId = sorted[currentIndex + 1].id;
      const priorSubs = submissions[priorMonthId] || [];
      return priorSubs.find((s) => s.department === department);
    }
    return undefined;
  };

  // Action: Save Draft
  const saveDepartmentDraft = (
    monthId: string,
    department: Department,
    lineItems: LineItem[],
    comments?: string
  ) => {
    setSubmissions((prev) => {
      const monthSubs = prev[monthId] ? [...prev[monthId]] : [];
      const existingIdx = monthSubs.findIndex((s) => s.department === department);
      
      const updatedSub: DepartmentSubmission = {
        id: existingIdx >= 0 ? monthSubs[existingIdx].id : `sub-${monthId}-${department.toLowerCase()}`,
        monthId,
        department,
        status: 'Draft',
        lastUpdatedBy: currentUser.name,
        lastUpdatedAt: new Date().toISOString(),
        comments: comments || (existingIdx >= 0 ? monthSubs[existingIdx].comments : ''),
        lineItems,
      };

      if (existingIdx >= 0) {
        monthSubs[existingIdx] = updatedSub;
      } else {
        monthSubs.push(updatedSub);
      }

      return { ...prev, [monthId]: monthSubs };
    });

    const totalInr = lineItems.reduce((acc, i) => acc + (Number(i.amountInr) || 0), 0);
    addAuditLog(
      'Saved Draft',
      `Saved draft requirements for ${department} department totaling ₹${totalInr.toLocaleString('en-IN')} (${lineItems.length} items).`,
      monthId,
      department
    );
  };

  // Action: Submit Department Requirements
  const submitDepartmentRequirements = (
    monthId: string,
    department: Department,
    lineItems: LineItem[],
    comments?: string
  ) => {
    const totalInr = lineItems.reduce((acc, i) => acc + (Number(i.amountInr) || 0), 0);

    setSubmissions((prev) => {
      const monthSubs = prev[monthId] ? [...prev[monthId]] : [];
      const existingIdx = monthSubs.findIndex((s) => s.department === department);
      
      const updatedSub: DepartmentSubmission = {
        id: existingIdx >= 0 ? monthSubs[existingIdx].id : `sub-${monthId}-${department.toLowerCase()}`,
        monthId,
        department,
        status: 'Submitted',
        submittedBy: currentUser.name,
        submittedAt: new Date().toISOString(),
        lastUpdatedBy: currentUser.name,
        lastUpdatedAt: new Date().toISOString(),
        comments: comments || (existingIdx >= 0 ? monthSubs[existingIdx].comments : ''),
        lineItems,
      };

      if (existingIdx >= 0) {
        monthSubs[existingIdx] = updatedSub;
      } else {
        monthSubs.push(updatedSub);
      }

      return { ...prev, [monthId]: monthSubs };
    });

    addAuditLog(
      'Submitted Cash Requirements',
      `Formally submitted ${department} cash requirements totaling ₹${totalInr.toLocaleString('en-IN')} across ${lineItems.length} line items.`,
      monthId,
      department
    );
  };

  // Action: Recall Submission
  const recallDepartmentSubmission = (monthId: string, department: Department) => {
    const month = months.find((m) => m.id === monthId);
    if (month && month.status !== 'Open') {
      alert('Cannot recall submission once the monthly pack is ready or processed by Management.');
      return;
    }

    setSubmissions((prev) => {
      const monthSubs = prev[monthId] ? [...prev[monthId]] : [];
      const existingIdx = monthSubs.findIndex((s) => s.department === department);
      if (existingIdx >= 0) {
        monthSubs[existingIdx] = {
          ...monthSubs[existingIdx],
          status: 'Draft',
          recalledAt: new Date().toISOString(),
          recalledBy: currentUser.name,
        };
      }
      return { ...prev, [monthId]: monthSubs };
    });

    addAuditLog(
      'Recalled Submission',
      `Recalled ${department} cash requirements back to Draft for revisions.`,
      monthId,
      department
    );
  };

  // Action: Update Exchange Rate (Finance Controller)
  const updateExchangeRate = (monthId: string, rate: number, rateSource: string) => {
    setMonths((prev) =>
      prev.map((m) => {
        if (m.id === monthId) {
          return {
            ...m,
            exchangeRate: rate,
            rateSource,
          };
        }
        return m;
      })
    );

    addAuditLog(
      'Updated Exchange Rate',
      `Set INR→AUD exchange rate to ${rate} (Source: ${rateSource}).`,
      monthId
    );
  };

  // Action: Set Controller Consolidation Notes
  const setControllerConsolidationNotes = (monthId: string, notes: string) => {
    setMonths((prev) =>
      prev.map((m) => (m.id === monthId ? { ...m, consolidationNotes: notes } : m))
    );
  };

  // Action: Mark Pack Ready for Approval (Locks Rate & Department Submissions)
  const markPackReadyForApproval = (monthId: string) => {
    const now = new Date().toISOString();

    // 1. Lock the month status & rate
    setMonths((prev) =>
      prev.map((m) => {
        if (m.id === monthId) {
          return {
            ...m,
            status: 'Ready for Approval',
            rateLockedAt: now,
            rateLockedBy: currentUser.name,
            controllerMarkedReadyAt: now,
            controllerMarkedReadyBy: currentUser.name,
          };
        }
        return m;
      })
    );

    // 2. Lock any submitted department forms
    setSubmissions((prev) => {
      const monthSubs = prev[monthId] ? [...prev[monthId]] : [];
      const updated = monthSubs.map((sub) => {
        if (sub.status === 'Submitted') {
          return { ...sub, status: 'Locked' as const };
        }
        return sub;
      });
      return { ...prev, [monthId]: updated };
    });

    addAuditLog(
      'Marked Ready for Approval',
      `Consolidated cash requirements pack marked ready for Management review. Exchange rate locked.`,
      monthId
    );
  };

  // Action: Management Approval / Rejection / Adjustments
  const executeApprovalDecision = (
    monthId: string,
    decision: 'Approved' | 'Approved with Adjustments' | 'Rejected' | 'Changes Requested',
    comments: string,
    adjustedLineItems?: { id: string; approvedAmountInr: number; adjustmentNote?: string }[]
  ) => {
    const month = months.find((m) => m.id === monthId);
    if (!month) return;

    const currentSubs = submissions[monthId] || [];
    let totalRequestedInr = 0;
    let totalApprovedInr = 0;

    // Apply adjustments to submissions & line items
    const updatedSubs = currentSubs.map((sub) => {
      let deptReqInr = 0;
      let deptApprInr = 0;

      const updatedItems = sub.lineItems.map((item) => {
        deptReqInr += item.amountInr;
        totalRequestedInr += item.amountInr;

        const adjustment = adjustedLineItems?.find((a) => a.id === item.id);
        if (adjustment) {
          deptApprInr += adjustment.approvedAmountInr;
          totalApprovedInr += adjustment.approvedAmountInr;
          return {
            ...item,
            approvedAmountInr: adjustment.approvedAmountInr,
            adjustmentNote: adjustment.adjustmentNote || '',
            status: (adjustment.approvedAmountInr === item.amountInr
              ? 'approved'
              : adjustment.approvedAmountInr === 0
              ? 'rejected'
              : 'adjusted') as any,
          };
        } else {
          const appr = decision === 'Rejected' ? 0 : item.amountInr;
          deptApprInr += appr;
          totalApprovedInr += appr;
          return {
            ...item,
            approvedAmountInr: appr,
            status: (decision === 'Rejected' ? 'rejected' : 'approved') as any,
          };
        }
      });

      return {
        ...sub,
        status: (decision === 'Rejected'
          ? 'Rejected'
          : decision === 'Changes Requested'
          ? 'Changes Requested'
          : 'Approved') as any,
        lineItems: updatedItems,
      };
    });

    const approvalRecord: ApprovalRecord = {
      id: `appr-${monthId}-${Date.now()}`,
      monthId,
      approverId: currentUser.id,
      approverName: currentUser.name,
      approverRole: currentUser.title || 'Management',
      decision,
      comments,
      decidedAt: new Date().toISOString(),
      totalRequestedInr,
      totalApprovedInr,
      totalRequestedAud: convertInrToAud(totalRequestedInr, month.exchangeRate),
      totalApprovedAud: convertInrToAud(totalApprovedInr, month.exchangeRate),
      exchangeRate: month.exchangeRate,
    };

    // Update months
    setMonths((prev) =>
      prev.map((m) => {
        if (m.id === monthId) {
          return {
            ...m,
            status: decision === 'Rejected' ? 'Open' : decision === 'Changes Requested' ? 'Open' : 'Approved',
            approvalRecord,
          };
        }
        return m;
      })
    );

    // Update submissions
    setSubmissions((prev) => ({
      ...prev,
      [monthId]: updatedSubs,
    }));

    addAuditLog(
      `Management Decision: ${decision}`,
      `Management (${currentUser.name}) decided: "${decision}". Notes: ${comments || 'None'}. Requested: ₹${totalRequestedInr.toLocaleString('en-IN')} | Approved: ₹${totalApprovedInr.toLocaleString('en-IN')}.`,
      monthId
    );
  };

  // Action: Open New Month Cycle (Admin)
  const openNewMonth = (
    monthId: string,
    label: string,
    deadline: string,
    initialRate: number,
    rateSource: string
  ) => {
    const newMonth: MonthCycle = {
      id: monthId,
      label,
      status: 'Open',
      exchangeRate: initialRate,
      rateSource,
      submissionDeadline: deadline,
      createdAt: new Date().toISOString(),
    };

    // Initialize 4 empty department draft shells
    const departments: Department[] = ['HR', 'Admin', 'IT', 'Finance'];
    const initialDepts: DepartmentSubmission[] = departments.map((dept) => {
      const deptCats = categories.filter((c) => c.department === dept);
      const defaultItems: LineItem[] = deptCats.slice(0, 3).map((cat, idx) => ({
        id: `li-${monthId}-${dept.toLowerCase()}-${idx + 1}`,
        submissionId: `sub-${monthId}-${dept.toLowerCase()}`,
        department: dept,
        category: cat.name,
        description: `${cat.name} estimate`,
        amountInr: 0,
        priority: 'Important',
        notes: '',
      }));

      return {
        id: `sub-${monthId}-${dept.toLowerCase()}`,
        monthId,
        department: dept,
        status: 'Draft',
        lineItems: defaultItems,
      };
    });

    setMonths((prev) => [newMonth, ...prev.filter((m) => m.id !== monthId)]);
    setSubmissions((prev) => ({ ...prev, [monthId]: initialDepts }));
    setActiveMonthId(monthId);

    addAuditLog(
      'Opened New Monthly Cycle',
      `Opened cash requirement cycle for "${label}" with submission deadline ${deadline}. Initial FX rate: ${initialRate}.`,
      monthId
    );
  };

  // Action: Close Month Cycle (Admin)
  const closeMonth = (monthId: string) => {
    setMonths((prev) =>
      prev.map((m) => (m.id === monthId ? { ...m, status: 'Closed' } : m))
    );
    addAuditLog('Closed Month Cycle', `Formally closed cash cycle ${monthId}.`, monthId);
  };

  // Category Actions
  const addCategory = (cat: Omit<DepartmentCategory, 'id'>) => {
    const newCat: DepartmentCategory = {
      ...cat,
      id: `cat-${Date.now()}`,
    };
    setCategories((prev) => [...prev, newCat]);
    addAuditLog(
      'Added Department Category',
      `Created category "${cat.name}" under ${cat.department} department.`,
      activeMonthId,
      cat.department
    );
  };

  const editCategory = (id: string, updates: Partial<DepartmentCategory>) => {
    setCategories((prev) => prev.map((c) => (c.id === id ? { ...c, ...updates } : c)));
  };

  const deleteCategory = (id: string) => {
    const cat = categories.find((c) => c.id === id);
    setCategories((prev) => prev.filter((c) => c.id !== id));
    if (cat) {
      addAuditLog(
        'Deleted Category',
        `Removed category "${cat.name}" from ${cat.department}.`,
        activeMonthId,
        cat.department
      );
    }
  };

  // User Directory Actions
  const addUser = (userData: Omit<User, 'id'>) => {
    const newUser: User = {
      ...userData,
      id: `user-${Date.now()}`,
    };
    setUsers((prev) => [...prev, newUser]);
  };

  const updateUser = (id: string, updates: Partial<User>) => {
    setUsers((prev) => prev.map((u) => (u.id === id ? { ...u, ...updates } : u)));
    if (currentUser.id === id) {
      setCurrentUserState((prev) => ({ ...prev, ...updates }));
    }
  };

  // Reset to Initial Seed Data
  const resetToInitialData = () => {
    setUsers(INITIAL_USERS);
    setCurrentUserState(INITIAL_USERS[0]);
    setMonths(INITIAL_MONTHS);
    setActiveMonthId('2026-10');
    setSubmissions(INITIAL_SUBMISSIONS);
    setCategories(INITIAL_CATEGORIES);
    setAuditLogs(INITIAL_AUDIT_LOGS);
    setCurrencyMode('both');
    localStorage.clear();
  };

  return (
    <AppContext.Provider
      value={{
        currentUser,
        setCurrentUser,
        users,
        activeMonthId,
        setActiveMonthId,
        months,
        activeMonth,
        submissions,
        currentSubmissions,
        categories,
        auditLogs,
        currencyMode,
        setCurrencyMode,
        saveDepartmentDraft,
        submitDepartmentRequirements,
        recallDepartmentSubmission,
        updateExchangeRate,
        setControllerConsolidationNotes,
        markPackReadyForApproval,
        executeApprovalDecision,
        openNewMonth,
        closeMonth,
        addCategory,
        editCategory,
        deleteCategory,
        addUser,
        updateUser,
        resetToInitialData,
        getPriorMonthSubmission,
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
