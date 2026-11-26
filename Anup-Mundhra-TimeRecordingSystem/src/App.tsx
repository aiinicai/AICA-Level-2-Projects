import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  BarChart3,
  Bell,
  CalendarCheck2,
  CheckCircle2,
  ClipboardCheck,
  Clock,
  FileSpreadsheet,
  FolderKanban,
  LogOut,
  Menu,
  Settings,
  Table2,
  X,
} from 'lucide-react';
import type { User } from 'firebase/auth';
import { collection, doc, onSnapshot, query, where } from './lib/fsAdapter';
import { ApplyLeavePanel } from './components/ApplyLeavePanel';
import { BalanceLedgerView } from './components/BalanceLedgerView';
import { ConfirmDialog } from './components/ConfirmDialog';
import { ErrorBoundary } from './components/ErrorBoundary';
import { ManagerApprovalModal } from './components/ManagerApprovalModal';
import { PolicySettingsView } from './components/PolicySettingsView';
import { RosterSyncView } from './components/RosterSyncView';
import { SignInScreen } from './components/SignInScreen';
import { TeamApprovalsView } from './components/TeamApprovalsView';
import { PayrollReportView } from './components/PayrollReportView';
import { TimesheetAdminView } from './components/TimesheetAdminView';
import { TimesheetApprovalsView } from './components/TimesheetApprovalsView';
import { TimesheetView } from './components/TimesheetView';
import { getCurrentYear, getTodayIsoDate, normalizeEmail } from './lib/dateUtils';
import {
  db,
  getSheetsAccessToken,
  handleFirestoreError,
  initFirebaseAuth,
  logoutUser,
  OperationType,
  requestSheetsPermission,
  signInWithGoogle,
  startDemoSession,
  testFirestoreConnection,
} from './lib/firebase';
import { getDemoRole, isDemoMode } from './lib/demoStore';
import { DEMO_ADMIN_EMAIL, DEMO_USERS } from './lib/demoData';
import {
  commitProjectsSync,
  fetchProjectsFromSheet,
  reopenTimesheetDay,
  resolveApproverEmail,
  reviewTimesheetDays,
  saveTimesheetDay,
  submitTimesheetDays,
} from './lib/timesheetService';
import type { Project, TimesheetEntry, TimesheetLine } from './types/timesheet';
import {
  adjustEmployeeBalance,
  cancelPendingLeaveRequest,
  commitRosterSync,
  ensureEmployeeBalancesForYear,
  removeHoliday,
  reviewLeaveRequest,
  runMonthlyAccrualPosting,
  saveHoliday,
  saveLeaveCategory,
  saveSingleEmployee,
  seedInitialDataIfNeeded,
  submitLeaveRequest,
} from './lib/leaveService';
import {
  BOOTSTRAPPED_ADMIN_EMAIL,
  type Employee,
  type HalfDayOption,
  type Holiday,
  type LeaveBalance,
  type LeaveCategory,
  type LeaveRequest,
  type RosterDiffSummary,
  type RosterSource,
  type RosterSyncConfig,
  type ToastMessage,
} from './types/leave';

type NavSection =
  | 'apply'
  | 'ledger'
  | 'approvals'
  | 'roster'
  | 'policy'
  | 'ts_entry'
  | 'ts_approvals'
  | 'ts_admin'
  | 'ts_payroll';

type AppSection = 'timesheet' | 'leave';

const APP_NAME = 'TimeRecordingSystem';

function WorkspaceApp() {
  const [authReady, setAuthReady] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [signingIn, setSigningIn] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);

  const [activeNav, setActiveNav] = useState<NavSection>('ts_entry');
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const [projects, setProjects] = useState<Project[]>([]);
  const [myEntries, setMyEntries] = useState<TimesheetEntry[]>([]);
  const [teamEntries, setTeamEntries] = useState<TimesheetEntry[]>([]);
  const [allEntries, setAllEntries] = useState<TimesheetEntry[]>([]);
  const [allLeaveRequests, setAllLeaveRequests] = useState<LeaveRequest[]>([]);
  const [syncingProjects, setSyncingProjects] = useState(false);
  const [projectsSyncMsg, setProjectsSyncMsg] = useState<string | null>(null);
  const [tsPromptOpen, setTsPromptOpen] = useState(false);
  const tsPromptShownForUid = useRef<string | null>(null);

  const [employees, setEmployees] = useState<Employee[]>([]);
  const [categories, setCategories] = useState<LeaveCategory[]>([]);
  const [balances, setBalances] = useState<LeaveBalance[]>([]);
  const [myRequests, setMyRequests] = useState<LeaveRequest[]>([]);
  const [teamRequests, setTeamRequests] = useState<LeaveRequest[]>([]);
  const [holidays, setHolidays] = useState<Holiday[]>([]);
  const [syncConfig, setSyncConfig] = useState<RosterSyncConfig | null>(null);
  const [dataLoaded, setDataLoaded] = useState(false);

  // Manager Login Pop-Up state: automatically opens once per sign-in if pending team leaves exist
  const [managerModalOpen, setManagerModalOpen] = useState(false);
  const autoPopupShownForUid = useRef<string | null>(null);

  const [accrualConfirmOpen, setAccrualConfirmOpen] = useState(false);
  const [runningAccrual, setRunningAccrual] = useState(false);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const year = getCurrentYear();

  const notify = useCallback(
    (type: ToastMessage['type'], title: string, detail?: string) => {
      const id = `${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
      setToasts((prev) => [...prev, { id, type, title, detail }]);
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, 4500);
    },
    []
  );

  useEffect(() => {
    testFirestoreConnection();
    const unsub = initFirebaseAuth((firebaseUser) => {
      setUser(firebaseUser);
      setAuthReady(true);
      if (!firebaseUser) {
        autoPopupShownForUid.current = null;
        setManagerModalOpen(false);
        setEmployees([]);
        setCategories([]);
        setBalances([]);
        setMyRequests([]);
        setTeamRequests([]);
        setHolidays([]);
        setSyncConfig(null);
        setProjects([]);
        setMyEntries([]);
        setTeamEntries([]);
        setAllEntries([]);
        setAllLeaveRequests([]);
        tsPromptShownForUid.current = null;
        setTsPromptOpen(false);
        setDataLoaded(false);
      }
    });
    return () => unsub();
  }, []);

  const userEmail = useMemo(
    () => (user?.email ? normalizeEmail(user.email) : ''),
    [user]
  );

  const isBootstrappedAdmin =
    userEmail === BOOTSTRAPPED_ADMIN_EMAIL ||
    (isDemoMode() && userEmail === DEMO_ADMIN_EMAIL);
  const demoRole = isDemoMode() ? getDemoRole() : null;

  // Seed default leave categories, holidays, and initial admin record on admin's first visit
  useEffect(() => {
    if (!user || !userEmail) return;
    if (isBootstrappedAdmin) {
      seedInitialDataIfNeeded(userEmail, user.displayName || 'HR Administrator').catch((err) => {
        console.error('Seed check error:', err);
      });
    }
  }, [user, userEmail, isBootstrappedAdmin]);

  // Attach real-time Firestore listeners once authenticated
  useEffect(() => {
    if (!user || !userEmail) return;

    const unsubs: Array<() => void> = [];

    // 1. Leave Categories (all verified users)
    unsubs.push(
      onSnapshot(
        collection(db, 'leaveCategories'),
        (snap) => {
          const list = snap.docs
            .map((d) => ({ id: d.id, ...(d.data() as Omit<LeaveCategory, 'id'>) }))
            .sort((a, b) => a.name.localeCompare(b.name));
          setCategories(list);
        },
        (err) => handleFirestoreError(err, OperationType.LIST, 'leaveCategories')
      )
    );

    // 2. Holidays (all verified users)
    unsubs.push(
      onSnapshot(
        collection(db, 'holidays'),
        (snap) => {
          const list = snap.docs
            .map((d) => ({ id: d.id, ...(d.data() as Omit<Holiday, 'id'>) }))
            .sort((a, b) => a.date.localeCompare(b.date));
          setHolidays(list);
        },
        (err) => handleFirestoreError(err, OperationType.LIST, 'holidays')
      )
    );

    // 3. Employees (Admin sees all; employees/managers see self & direct reports via dual-query merge)
    if (isBootstrappedAdmin) {
      unsubs.push(
        onSnapshot(
          collection(db, 'employees'),
          (snap) => {
            const list = snap.docs.map((d) => ({ id: d.id, ...(d.data() as Omit<Employee, 'id'>) }));
            setEmployees(list);
            setDataLoaded(true);
          },
          (err) => handleFirestoreError(err, OperationType.LIST, 'employees')
        )
      );
    } else {
      let selfDocs: Employee[] = [];
      let reportDocs: Employee[] = [];
      const mergeEmployees = () => {
        const map = new Map<string, Employee>();
        for (const e of [...selfDocs, ...reportDocs]) map.set(e.id, e);
        setEmployees(Array.from(map.values()));
        setDataLoaded(true);
      };

      unsubs.push(
        onSnapshot(
          query(collection(db, 'employees'), where('email', '==', userEmail)),
          (snap) => {
            selfDocs = snap.docs.map((d) => ({ id: d.id, ...(d.data() as Omit<Employee, 'id'>) }));
            mergeEmployees();
          },
          (err) => handleFirestoreError(err, OperationType.LIST, 'employees/self')
        )
      );

      unsubs.push(
        onSnapshot(
          query(collection(db, 'employees'), where('managerEmail', '==', userEmail)),
          (snap) => {
            reportDocs = snap.docs.map((d) => ({ id: d.id, ...(d.data() as Omit<Employee, 'id'>) }));
            mergeEmployees();
          },
          (err) => handleFirestoreError(err, OperationType.LIST, 'employees/reports')
        )
      );
    }

    // 4. Leave Balances
    if (isBootstrappedAdmin) {
      unsubs.push(
        onSnapshot(
          collection(db, 'leaveBalances'),
          (snap) => {
            setBalances(
              snap.docs.map((d) => ({ id: d.id, ...(d.data() as Omit<LeaveBalance, 'id'>) }))
            );
          },
          (err) => handleFirestoreError(err, OperationType.LIST, 'leaveBalances')
        )
      );
    } else {
      let myBalDocs: LeaveBalance[] = [];
      let teamBalDocs: LeaveBalance[] = [];
      const mergeBalances = () => {
        const map = new Map<string, LeaveBalance>();
        for (const b of [...myBalDocs, ...teamBalDocs]) map.set(b.id, b);
        setBalances(Array.from(map.values()));
      };

      unsubs.push(
        onSnapshot(
          query(collection(db, 'leaveBalances'), where('employeeEmail', '==', userEmail)),
          (snap) => {
            myBalDocs = snap.docs.map((d) => ({ id: d.id, ...(d.data() as Omit<LeaveBalance, 'id'>) }));
            mergeBalances();
          },
          (err) => handleFirestoreError(err, OperationType.LIST, 'leaveBalances/self')
        )
      );

      unsubs.push(
        onSnapshot(
          query(collection(db, 'leaveBalances'), where('managerEmail', '==', userEmail)),
          (snap) => {
            teamBalDocs = snap.docs.map((d) => ({ id: d.id, ...(d.data() as Omit<LeaveBalance, 'id'>) }));
            mergeBalances();
          },
          (err) => handleFirestoreError(err, OperationType.LIST, 'leaveBalances/team')
        )
      );
    }

    // 5. My Leave Requests
    unsubs.push(
      onSnapshot(
        query(collection(db, 'leaveRequests'), where('employeeEmail', '==', userEmail)),
        (snap) => {
          const list = snap.docs
            .map((d) => ({ id: d.id, ...(d.data() as Omit<LeaveRequest, 'id'>) }))
            .sort((a, b) => b.startDate.localeCompare(a.startDate));
          setMyRequests(list);
        },
        (err) => handleFirestoreError(err, OperationType.LIST, 'leaveRequests/self')
      )
    );

    // 6. Team Leave Requests (assigned to me as reporting manager)
    unsubs.push(
      onSnapshot(
        query(collection(db, 'leaveRequests'), where('managerEmail', '==', userEmail)),
        (snap) => {
          const list = snap.docs
            .map((d) => ({ id: d.id, ...(d.data() as Omit<LeaveRequest, 'id'>) }))
            .sort((a, b) => b.startDate.localeCompare(a.startDate));
          setTeamRequests(list);
        },
        (err) => handleFirestoreError(err, OperationType.LIST, 'leaveRequests/team')
      )
    );

    // 8. Projects master (all verified users)
    unsubs.push(
      onSnapshot(
        collection(db, 'projects'),
        (snap) => {
          const list = snap.docs
            .map((d) => ({ id: d.id, ...(d.data() as Omit<Project, 'id'>) }))
            .sort((a, b) => a.code.localeCompare(b.code));
          setProjects(list);
        },
        (err) => handleFirestoreError(err, OperationType.LIST, 'projects')
      )
    );

    // 9. My timesheet entries
    unsubs.push(
      onSnapshot(
        query(collection(db, 'timesheetEntries'), where('employeeEmail', '==', userEmail)),
        (snap) => {
          setMyEntries(
            snap.docs.map((d) => ({ id: d.id, ...(d.data() as Omit<TimesheetEntry, 'id'>) }))
          );
        },
        (err) => handleFirestoreError(err, OperationType.LIST, 'timesheetEntries/self')
      )
    );

    // 10. Timesheet entries assigned to me as approver
    unsubs.push(
      onSnapshot(
        query(collection(db, 'timesheetEntries'), where('managerEmail', '==', userEmail)),
        (snap) => {
          setTeamEntries(
            snap.docs.map((d) => ({ id: d.id, ...(d.data() as Omit<TimesheetEntry, 'id'>) }))
          );
        },
        (err) => handleFirestoreError(err, OperationType.LIST, 'timesheetEntries/team')
      )
    );

    // 11. Everything (bootstrapped HR admin only): payroll report, reopen, self-managed approvals
    if (isBootstrappedAdmin) {
      unsubs.push(
        onSnapshot(
          collection(db, 'timesheetEntries'),
          (snap) => {
            setAllEntries(
              snap.docs.map((d) => ({ id: d.id, ...(d.data() as Omit<TimesheetEntry, 'id'>) }))
            );
          },
          (err) => handleFirestoreError(err, OperationType.LIST, 'timesheetEntries')
        )
      );
      unsubs.push(
        onSnapshot(
          collection(db, 'leaveRequests'),
          (snap) => {
            setAllLeaveRequests(
              snap.docs.map((d) => ({ id: d.id, ...(d.data() as Omit<LeaveRequest, 'id'>) }))
            );
          },
          (err) => handleFirestoreError(err, OperationType.LIST, 'leaveRequests/all')
        )
      );
    }

    // 7. Roster Sync Config (Admin only)
    if (isBootstrappedAdmin) {
      unsubs.push(
        onSnapshot(
          doc(db, 'settings', 'rosterSync'),
          (snap) => {
            if (snap.exists()) {
              setSyncConfig(snap.data() as RosterSyncConfig);
            }
          },
          (err) => handleFirestoreError(err, OperationType.GET, 'settings/rosterSync')
        )
      );
    }

    return () => {
      for (const unsub of unsubs) unsub();
    };
  }, [user, userEmail, isBootstrappedAdmin]);

  const currentEmployee = useMemo(
    () => employees.find((e) => e.email === userEmail) || null,
    [employees, userEmail]
  );

  // Auto-seed missing leave balance docs for the active signed-in employee
  useEffect(() => {
    if (!currentEmployee || categories.length === 0) return;
    ensureEmployeeBalancesForYear(currentEmployee, categories, balances, year).catch((err) => {
      console.error('Balance auto-seed error:', err);
    });
  }, [currentEmployee, categories, balances, year]);

  const pendingTeamRequests = useMemo(
    () => teamRequests.filter((r) => r.status === 'pending'),
    [teamRequests]
  );

  // Trigger Manager Login Pop-Up automatically when a manager logs in and has pending requests
  useEffect(() => {
    if (!user || !dataLoaded) return;
    if (pendingTeamRequests.length > 0 && autoPopupShownForUid.current !== user.uid) {
      autoPopupShownForUid.current = user.uid;
      setManagerModalOpen(true);
    }
  }, [user, dataLoaded, pendingTeamRequests.length]);

  const myBalances = useMemo(
    () => balances.filter((b) => b.employeeEmail === userEmail),
    [balances, userEmail]
  );

  const directReports = useMemo(
    () => employees.filter((e) => e.managerEmail === userEmail && e.status === 'active'),
    [employees, userEmail]
  );

  const isAdmin = isBootstrappedAdmin || Boolean(currentEmployee?.isAdmin);
  const isManager =
    Boolean(currentEmployee?.isManager) ||
    directReports.length > 0 ||
    teamRequests.length > 0;

  const today = getTodayIsoDate();

  // Entries this user can approve: direct reports' days; the HR admin also approves
  // days of employees who have no reporting manager (e.g. the top partner).
  const reviewableEntries = useMemo(() => {
    const source = isBootstrappedAdmin ? allEntries : teamEntries;
    return source.filter(
      (e) =>
        e.employeeEmail !== userEmail &&
        (e.managerEmail === userEmail || (isAdmin && e.employeeEmail === e.managerEmail))
    );
  }, [isBootstrappedAdmin, allEntries, teamEntries, isAdmin, userEmail]);

  const pendingTimesheetDays = useMemo(
    () => reviewableEntries.filter((e) => e.status === 'submitted').length,
    [reviewableEntries]
  );

  const myApproverLabel = currentEmployee
    ? resolveApproverEmail(currentEmployee) === currentEmployee.email
      ? 'HR Admin'
      : currentEmployee.managerName || currentEmployee.managerEmail
    : 'your manager';

  // One-time prompt at sign-in when timesheet days are waiting for this approver
  useEffect(() => {
    if (!user || !dataLoaded) return;
    if (pendingTimesheetDays > 0 && tsPromptShownForUid.current !== user.uid) {
      tsPromptShownForUid.current = user.uid;
      setTsPromptOpen(true);
    }
  }, [user, dataLoaded, pendingTimesheetDays]);

  const handleSaveTimesheetDay = async (date: string, lines: TimesheetLine[]) => {
    if (!currentEmployee) return;
    await saveTimesheetDay({
      employee: currentEmployee,
      date,
      lines,
      existing: myEntries.find((e) => e.date === date),
    });
    notify('success', lines.length === 0 ? 'Day cleared' : 'Day saved', date);
  };

  const handleSubmitTimesheetDays = async (entries: TimesheetEntry[]) => {
    await submitTimesheetDays(entries);
    notify(
      'success',
      'Submitted for approval',
      `${entries.length} day${entries.length === 1 ? '' : 's'} sent to ${myApproverLabel}.`
    );
  };

  const handleReviewTimesheet = async (
    entries: TimesheetEntry[],
    decision: 'approved' | 'rejected',
    comment: string
  ) => {
    await reviewTimesheetDays({ entries, decision, comment, reviewerEmail: userEmail });
    notify(
      decision === 'approved' ? 'success' : 'info',
      decision === 'approved' ? 'Timesheet approved' : 'Timesheet rejected',
      `${entries.length} day${entries.length === 1 ? '' : 's'} for ${entries[0]?.employeeName || 'employee'}.`
    );
  };

  const handleReopenTimesheetDay = async (entry: TimesheetEntry, reason: string) => {
    await reopenTimesheetDay({ entry, adminEmail: userEmail, reason });
    notify('info', 'Day reopened', `${entry.employeeName} can edit ${entry.date} again.`);
  };

  const handleSyncProjects = async () => {
    if (!syncConfig?.spreadsheetId) {
      notify(
        'error',
        'Link the Google Sheet first',
        'Run a roster sync once so the app knows which sheet to read the Projects tab from.'
      );
      return;
    }
    setSyncingProjects(true);
    try {
      let token = getSheetsAccessToken() || (await requestSheetsPermission());
      let result;
      try {
        result = await fetchProjectsFromSheet(syncConfig.spreadsheetId, token);
      } catch (err) {
        if (err instanceof Error && err.message === 'TOKEN_EXPIRED') {
          token = await requestSheetsPermission();
          result = await fetchProjectsFromSheet(syncConfig.spreadsheetId, token);
        } else {
          throw err;
        }
      }
      const counts = await commitProjectsSync(result.projects, projects);
      const msg = `${counts.added} added, ${counts.updated} updated, ${counts.deactivated} deactivated${
        result.warnings.length ? ` (${result.warnings.length} warning(s): ${result.warnings[0]})` : ''
      }`;
      setProjectsSyncMsg(`Last sync: ${msg}`);
      notify('success', 'Projects synced', msg);
    } catch (err) {
      notify('error', 'Projects sync failed', err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setSyncingProjects(false);
    }
  };

  const handleSignIn = async () => {
    setSigningIn(true);
    setAuthError(null);
    try {
      await signInWithGoogle();
    } catch (err) {
      setAuthError(err instanceof Error ? err.message : 'Google Sign-In failed.');
    } finally {
      setSigningIn(false);
    }
  };

  const handleSubmitLeave = async (payload: {
    category: LeaveCategory;
    startDate: string;
    endDate: string;
    halfDay: HalfDayOption;
    workingDays: number;
    reason: string;
  }) => {
    if (!currentEmployee) return;
    await submitLeaveRequest({
      employee: currentEmployee,
      ...payload,
    });
    notify(
      'success',
      'Leave request submitted',
      `Sent to ${currentEmployee.managerName || currentEmployee.managerEmail} for approval.`
    );
  };

  const handleApproveRequest = async (req: LeaveRequest, comment: string) => {
    await reviewLeaveRequest({
      request: req,
      decision: 'approved',
      comment,
      reviewerEmail: userEmail,
      categories,
    });
    notify(
      'success',
      'Leave approved',
      `${req.employeeName}'s ${req.workingDays}-day ${req.categoryName} balance has been updated.`
    );
  };

  const handleRejectRequest = async (req: LeaveRequest, comment: string) => {
    await reviewLeaveRequest({
      request: req,
      decision: 'rejected',
      comment,
      reviewerEmail: userEmail,
      categories,
    });
    notify('info', 'Leave rejected', `${req.employeeName}'s request was declined.`);
  };

  const handleCancelRequest = async (requestId: string) => {
    await cancelPendingLeaveRequest(requestId);
    notify('info', 'Request cancelled', 'Your pending leave request was withdrawn.');
  };

  const handleAdjustBalance = async (
    balance: LeaveBalance,
    opening: number,
    accrued: number
  ) => {
    await adjustEmployeeBalance({ balance, opening, accrued });
    notify('success', 'Balance updated', `${balance.employeeName} (${balance.categoryName}) updated.`);
  };

  const handleRunMonthlyAccrual = async () => {
    setRunningAccrual(true);
    try {
      const count = await runMonthlyAccrualPosting({
        employees,
        balances,
        categories,
        year,
      });
      setAccrualConfirmOpen(false);
      notify('success', 'Monthly accrual posted', `Updated ${count} employee leave balance entries.`);
    } finally {
      setRunningAccrual(false);
    }
  };

  const handleCommitRosterSync = async (params: {
    diff: RosterDiffSummary;
    source: RosterSource;
    sheetMeta?: { spreadsheetId: string; spreadsheetTitle: string; sheetName: string };
  }) => {
    await commitRosterSync({
      ...params,
      syncedBy: userEmail,
      categories,
      existingBalances: balances,
      year,
    });
    notify(
      'success',
      'Employee roster synced',
      `${params.diff.newJoinees.length} added · ${params.diff.updated.length} updated · ${params.diff.resignees.length} marked resigned`
    );
  };

  if (!authReady) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-sm text-slate-500">Loading workspace...</div>
      </div>
    );
  }

  if (!user) {
    return <SignInScreen
        onSignIn={handleSignIn}
        onDemo={(role) => startDemoSession(role)}
        signingIn={signingIn}
        error={authError}
      />;
  }

  // Non-admin user whose email is not yet in the synced Google Sheet / Excel roster
  if (dataLoaded && !currentEmployee && !isAdmin) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
        <div className="max-w-md w-full bg-white border border-slate-200 rounded-xl p-8 space-y-5">
          <h1 className="text-lg font-semibold text-slate-900">Account Pending Directory Sync</h1>
          <p className="text-sm text-slate-600 leading-relaxed">
            You are signed in as <strong className="text-slate-900">{userEmail}</strong>, which has not been synced from the company employee sheet yet.
          </p>
          <p className="text-xs text-slate-500 leading-relaxed">
            Please ask your HR Administrator to add your email, designation, and reporting manager to the linked Google Sheet and run a sync.
          </p>
          <button
            type="button"
            onClick={logoutUser}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 cursor-pointer"
          >
            <LogOut className="w-4 h-4" />
            Sign out
          </button>
        </div>
      </div>
    );
  }

  const allNavItems: Array<{
    id: NavSection;
    section: AppSection;
    label: string;
    icon: React.ComponentType<{ className?: string }>;
    badge?: number;
    visible: boolean;
  }> = [
    {
      id: 'ts_entry',
      section: 'timesheet',
      label: 'My Timesheet',
      icon: Clock,
      visible: true,
    },
    {
      id: 'ts_approvals',
      section: 'timesheet',
      label: 'Timesheet Approvals',
      icon: ClipboardCheck,
      badge: pendingTimesheetDays,
      visible: isManager || isAdmin,
    },
    {
      id: 'ts_admin',
      section: 'timesheet',
      label: 'Projects & Reopen',
      icon: FolderKanban,
      visible: isAdmin,
    },
    {
      id: 'ts_payroll',
      section: 'timesheet',
      label: 'Payroll Report',
      icon: BarChart3,
      visible: isAdmin,
    },
    {
      id: 'apply',
      section: 'leave',
      label: 'Apply & Overview',
      icon: CalendarCheck2,
      visible: true,
    },
    {
      id: 'ledger',
      section: 'leave',
      label: 'Balance Database',
      icon: Table2,
      visible: true,
    },
    {
      id: 'approvals',
      section: 'leave',
      label: 'Team Approvals',
      icon: ClipboardCheck,
      badge: pendingTeamRequests.length,
      visible: isManager || isAdmin,
    },
    {
      id: 'roster',
      section: 'leave',
      label: 'Roster & Sheet Sync',
      icon: FileSpreadsheet,
      visible: isAdmin,
    },
    {
      id: 'policy',
      section: 'leave',
      label: 'Leave Policy',
      icon: Settings,
      visible: isAdmin,
    },
  ];

  const activeSection: AppSection = activeNav.startsWith('ts_') ? 'timesheet' : 'leave';
  const navItems = allNavItems.filter((n) => n.section === activeSection);
  const timesheetBadge = pendingTimesheetDays;
  const leaveBadge = pendingTeamRequests.length;

  const switchSection = (section: AppSection) => {
    setActiveNav(section === 'timesheet' ? 'ts_entry' : 'apply');
  };

  const sectionSwitcher = (
    <div className="grid grid-cols-2 gap-1 p-1 bg-slate-100 border border-slate-200 rounded-lg">
      {(['timesheet', 'leave'] as const).map((s) => {
        const badge = s === 'timesheet' ? timesheetBadge : leaveBadge;
        return (
          <button
            key={s}
            type="button"
            onClick={() => switchSection(s)}
            className={`px-2 py-1.5 text-xs font-semibold rounded-md whitespace-nowrap cursor-pointer ${
              activeSection === s
                ? 'bg-white text-slate-900 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            {s === 'timesheet' ? 'Timesheet' : 'Leave'}
            {badge > 0 && (
              <span className="ml-1.5 font-mono tabular-nums text-amber-700">{badge}</span>
            )}
          </button>
        );
      })}
    </div>
  );

  const activeNavTitle = allNavItems.find((n) => n.id === activeNav)?.label || 'Workspace';

  return (
    <div className="min-h-screen bg-slate-50 flex">
      {/* Desktop Sidebar */}
      <aside className="hidden lg:flex lg:w-64 lg:flex-col lg:fixed lg:inset-y-0 bg-white border-r border-slate-200">
        <div className="px-6 h-16 flex items-center border-b border-slate-200">
          <span className="text-lg font-bold tracking-tight text-slate-900 font-display whitespace-nowrap">
            {APP_NAME}
          </span>
        </div>

        <div className="px-4 pt-4">{sectionSwitcher}</div>
        <nav className="flex-1 p-4 space-y-1">
          {navItems
            .filter((item) => item.visible)
            .map((item) => {
              const Icon = item.icon;
              const isActive = activeNav === item.id;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setActiveNav(item.id)}
                  className={`w-full flex items-center justify-between px-3 py-2.5 text-sm font-medium rounded-lg transition-colors whitespace-nowrap cursor-pointer ${
                    isActive
                      ? 'bg-slate-900 text-white'
                      : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                  }`}
                >
                  <span className="flex items-center gap-2.5">
                    <Icon className="w-4 h-4 shrink-0" />
                    <span>{item.label}</span>
                  </span>
                  {typeof item.badge === 'number' && item.badge > 0 && (
                    <span
                      className={`font-mono tabular-nums text-xs font-semibold ${
                        isActive ? 'text-amber-300' : 'text-amber-700'
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
        </nav>

        <div className="p-4 border-t border-slate-200 space-y-3">
          <div className="space-y-0.5">
            <p className="text-sm font-semibold text-slate-900 truncate">
              {currentEmployee?.name || user.displayName || userEmail}
            </p>
            <p className="text-xs text-slate-500 truncate">
              {currentEmployee?.designation || (isAdmin ? 'HR Administrator' : 'Employee')}
            </p>
            <p className="text-xs text-slate-400 truncate">{userEmail}</p>
          </div>
          <button
            type="button"
            onClick={logoutUser}
            className="w-full inline-flex items-center justify-center gap-2 px-3 py-2 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors cursor-pointer"
          >
            <LogOut className="w-3.5 h-3.5" />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-40 lg:hidden flex">
          <div
            className="fixed inset-0 bg-slate-900/40"
            onClick={() => setMobileMenuOpen(false)}
          />
          <aside className="relative w-64 max-w-[80vw] bg-white border-r border-slate-200 flex flex-col z-50">
            <div className="px-5 h-16 flex items-center justify-between border-b border-slate-200">
              <span className="text-lg font-bold tracking-tight text-slate-900 font-display">
                {APP_NAME}
              </span>
              <button
                type="button"
                onClick={() => setMobileMenuOpen(false)}
                className="p-1.5 text-slate-500 cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="px-4 pt-4">{sectionSwitcher}</div>
            <nav className="flex-1 p-4 space-y-1">
              {navItems
                .filter((item) => item.visible)
                .map((item) => {
                  const Icon = item.icon;
                  const isActive = activeNav === item.id;
                  return (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => {
                        setActiveNav(item.id);
                        setMobileMenuOpen(false);
                      }}
                      className={`w-full flex items-center justify-between px-3 py-2.5 text-sm font-medium rounded-lg cursor-pointer ${
                        isActive ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-100'
                      }`}
                    >
                      <span className="flex items-center gap-2.5">
                        <Icon className="w-4 h-4 shrink-0" />
                        <span>{item.label}</span>
                      </span>
                      {typeof item.badge === 'number' && item.badge > 0 && (
                        <span className="font-mono tabular-nums text-xs font-semibold">
                          {item.badge}
                        </span>
                      )}
                    </button>
                  );
                })}
            </nav>
            <div className="p-4 border-t border-slate-200">
              <button
                type="button"
                onClick={logoutUser}
                className="w-full inline-flex items-center justify-center gap-2 px-3 py-2 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded-lg cursor-pointer"
              >
                <LogOut className="w-3.5 h-3.5" />
                Sign Out
              </button>
            </div>
          </aside>
        </div>
      )}

      {/* Main Content Area */}
      <div className="flex-1 lg:pl-64 flex flex-col min-w-0">
        {demoRole && (
          <div className="bg-amber-50 border-b border-amber-200 px-4 sm:px-8 py-2 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-amber-900">
            <span className="font-semibold">Demo mode</span>
            <span>Sample data only. Changes stay in this browser and are lost on refresh.</span>
            <span className="flex items-center gap-1.5 sm:ml-auto">
              View as:
              {(['admin', 'manager', 'employee'] as const).map((r) => (
                <button
                  key={r}
                  type="button"
                  onClick={() => {
                    setActiveNav('ts_entry');
                    startDemoSession(r);
                  }}
                  className={`px-2.5 py-1 rounded-md font-semibold cursor-pointer ${
                    demoRole === r
                      ? 'bg-amber-900 text-white'
                      : 'bg-white border border-amber-300 text-amber-900 hover:bg-amber-100'
                  }`}
                >
                  {DEMO_USERS[r].label}
                </button>
              ))}
            </span>
          </div>
        )}
        <header className="h-16 bg-white border-b border-slate-200 px-4 sm:px-8 flex items-center justify-between gap-4 sticky top-0 z-30">
          <div className="flex items-center gap-3 min-w-0">
            <button
              type="button"
              onClick={() => setMobileMenuOpen(true)}
              className="lg:hidden p-2 text-slate-600 hover:text-slate-900 rounded-lg cursor-pointer"
              aria-label="Open menu"
            >
              <Menu className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-2 text-sm truncate">
              <span className="text-slate-400">Workspace</span>
              <span className="text-slate-300">/</span>
              <span className="font-medium text-slate-900 truncate">{activeNavTitle}</span>
            </div>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            {pendingTimesheetDays > 0 && (
              <button
                type="button"
                onClick={() => setActiveNav('ts_approvals')}
                className="inline-flex items-center gap-2 px-3.5 py-1.5 text-xs font-medium text-sky-900 bg-sky-50 border border-sky-200 rounded-lg hover:bg-sky-100 transition-colors whitespace-nowrap shrink-0 cursor-pointer"
              >
                <Clock className="w-3.5 h-3.5 text-sky-700" />
                <span>
                  {pendingTimesheetDays} Timesheet {pendingTimesheetDays === 1 ? 'Day' : 'Days'} to Approve
                </span>
              </button>
            )}
            {pendingTeamRequests.length > 0 && (
              <button
                type="button"
                onClick={() => setManagerModalOpen(true)}
                className="inline-flex items-center gap-2 px-3.5 py-1.5 text-xs font-medium text-amber-900 bg-amber-50 border border-amber-200 rounded-lg hover:bg-amber-100 transition-colors whitespace-nowrap shrink-0 cursor-pointer"
              >
                <Bell className="w-3.5 h-3.5 text-amber-700" />
                <span>
                  {pendingTeamRequests.length} Pending {pendingTeamRequests.length === 1 ? 'Approval' : 'Approvals'}
                </span>
              </button>
            )}

            {isAdmin && activeNav !== 'roster' && (
              <button
                type="button"
                onClick={() => setActiveNav('roster')}
                className="hidden sm:inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-medium text-white bg-slate-900 rounded-lg hover:bg-slate-800 transition-colors whitespace-nowrap shrink-0 cursor-pointer"
              >
                <FileSpreadsheet className="w-3.5 h-3.5" />
                Sync Google Sheet
              </button>
            )}
          </div>
        </header>

        <main className="flex-1 max-w-6xl w-full mx-auto p-4 sm:p-8 space-y-6">
          {!dataLoaded ? (
            <div className="space-y-4">
              <div className="h-44 bg-white border border-slate-200 rounded-xl animate-pulse" />
              <div className="h-64 bg-white border border-slate-200 rounded-xl animate-pulse" />
            </div>
          ) : (
            <>
              {activeNav === 'ts_entry' && (
                currentEmployee ? (
                  <TimesheetView
                    employee={currentEmployee}
                    projects={projects}
                    holidays={holidays}
                    myEntries={myEntries}
                    myRequests={myRequests}
                    today={today}
                    approverName={myApproverLabel}
                    onSaveDay={handleSaveTimesheetDay}
                    onSubmitDays={handleSubmitTimesheetDays}
                  />
                ) : (
                  <div className="bg-white border border-slate-200 rounded-xl p-8 text-sm text-slate-600">
                    Initializing your profile...
                  </div>
                )
              )}

              {activeNav === 'ts_approvals' && (
                <TimesheetApprovalsView
                  reviewableEntries={reviewableEntries}
                  onReview={handleReviewTimesheet}
                />
              )}

              {activeNav === 'ts_admin' && isAdmin && (
                <TimesheetAdminView
                  projects={projects}
                  employees={employees}
                  entries={allEntries}
                  syncing={syncingProjects}
                  lastSyncMessage={projectsSyncMsg}
                  onSyncProjects={handleSyncProjects}
                  onReopen={handleReopenTimesheetDay}
                />
              )}

              {activeNav === 'ts_payroll' && isAdmin && (
                <PayrollReportView
                  employees={employees}
                  entries={allEntries}
                  leaveRequests={allLeaveRequests}
                  holidays={holidays}
                  categories={categories}
                  projects={projects}
                  today={today}
                />
              )}

              {activeNav === 'apply' && (
                currentEmployee ? (
                  <>
                    <ApplyLeavePanel
                      employee={currentEmployee}
                      categories={categories}
                      balances={myBalances}
                      myRequests={myRequests}
                      holidays={holidays}
                      onSubmit={handleSubmitLeave}
                    />
                    <BalanceLedgerView
                      currentEmployee={currentEmployee}
                      year={year}
                      categories={categories}
                      myBalances={myBalances}
                      myRequests={myRequests}
                      allEmployees={employees}
                      allBalances={balances}
                      isAdmin={isAdmin}
                      isManager={isManager}
                      onCancelRequest={handleCancelRequest}
                      onAdjustBalance={handleAdjustBalance}
                      onRunMonthlyAccrual={() => setAccrualConfirmOpen(true)}
                    />
                  </>
                ) : (
                  <div className="bg-white border border-slate-200 rounded-xl p-8 text-sm text-slate-600">
                    Initializing your HR Administrator profile and default leave policies...
                  </div>
                )
              )}

              {activeNav === 'ledger' && (
                currentEmployee ? (
                  <BalanceLedgerView
                    currentEmployee={currentEmployee}
                    year={year}
                    categories={categories}
                    myBalances={myBalances}
                    myRequests={myRequests}
                    allEmployees={employees}
                    allBalances={balances}
                    isAdmin={isAdmin}
                    isManager={isManager}
                    onCancelRequest={handleCancelRequest}
                    onAdjustBalance={handleAdjustBalance}
                    onRunMonthlyAccrual={() => setAccrualConfirmOpen(true)}
                  />
                ) : (
                  <div className="bg-white border border-slate-200 rounded-xl p-8 text-sm text-slate-600">
                    Initializing leave balance ledger...
                  </div>
                )
              )}

              {activeNav === 'approvals' && (
                <TeamApprovalsView
                  teamRequests={teamRequests}
                  teamBalances={balances}
                  onApprove={handleApproveRequest}
                  onReject={handleRejectRequest}
                />
              )}

              {activeNav === 'roster' && isAdmin && (
                <RosterSyncView
                  employees={employees}
                  syncConfig={syncConfig}
                  onCommitSync={handleCommitRosterSync}
                  onSaveSingleEmployee={(emp) =>
                    saveSingleEmployee(emp, categories, balances, year).then(() =>
                      notify('success', 'Employee saved', `${emp.name} updated in directory.`)
                    )
                  }
                  onNotify={notify}
                />
              )}

              {activeNav === 'policy' && isAdmin && (
                <PolicySettingsView
                  categories={categories}
                  holidays={holidays}
                  onSaveCategory={(cat) =>
                    saveLeaveCategory(cat).then(() =>
                      notify('success', 'Leave category saved', `${cat.name} updated.`)
                    )
                  }
                  onSaveHoliday={(date, name) =>
                    saveHoliday(date, name).then(() =>
                      notify('success', 'Holiday added', `${name} (${date}) saved.`)
                    )
                  }
                  onDeleteHoliday={(id) =>
                    removeHoliday(id).then(() =>
                      notify('info', 'Holiday removed', 'Working-day calendar updated.')
                    )
                  }
                />
              )}
            </>
          )}
        </main>
      </div>

      {/* Automatic Manager Login Pending Approvals Pop-Up */}
      <ManagerApprovalModal
        open={managerModalOpen}
        pendingRequests={pendingTeamRequests}
        teamRequests={teamRequests}
        teamBalances={balances}
        onApprove={handleApproveRequest}
        onReject={handleRejectRequest}
        onClose={() => setManagerModalOpen(false)}
      />

      {/* One-time timesheet approvals prompt at sign-in */}
      {tsPromptOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40">
          <div className="w-full max-w-md bg-white border border-slate-200 rounded-xl p-6 space-y-4">
            <h2 className="text-base font-semibold text-slate-900">Timesheets waiting for you</h2>
            <p className="text-sm text-slate-600">
              {pendingTimesheetDays} submitted timesheet {pendingTimesheetDays === 1 ? 'day is' : 'days are'} waiting
              for your approval.
            </p>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setTsPromptOpen(false)}
                className="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 cursor-pointer"
              >
                Later
              </button>
              <button
                type="button"
                onClick={() => {
                  setTsPromptOpen(false);
                  setActiveNav('ts_approvals');
                }}
                className="px-4 py-2 text-sm font-medium text-white bg-slate-900 rounded-lg hover:bg-slate-800 cursor-pointer"
              >
                Review now
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Monthly Accrual Confirmation */}
      <ConfirmDialog
        open={accrualConfirmOpen}
        title="Post Monthly Leave Accruals"
        description={`Credit monthly accrued days to all active employees for ${year} based on each category's monthly accrual rate?`}
        details={categories
          .filter((c) => c.active && c.monthlyAccrual > 0)
          .map((c) => `• ${c.name}: +${c.monthlyAccrual} days`)}
        confirmLabel="Post Monthly Accrual"
        busy={runningAccrual}
        onConfirm={handleRunMonthlyAccrual}
        onCancel={() => setAccrualConfirmOpen(false)}
      />

      {/* Toast Notifications */}
      {toasts.length > 0 && (
        <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none">
          {toasts.map((t) => (
            <div
              key={t.id}
              className={`pointer-events-auto bg-white border rounded-xl px-4 py-3 shadow-lg flex items-start gap-3 ${
                t.type === 'error'
                  ? 'border-red-200'
                  : t.type === 'success'
                    ? 'border-emerald-200'
                    : 'border-slate-200'
              }`}
            >
              <CheckCircle2
                className={`w-4 h-4 mt-0.5 shrink-0 ${
                  t.type === 'error'
                    ? 'text-red-600'
                    : t.type === 'success'
                      ? 'text-emerald-600'
                      : 'text-slate-600'
                }`}
              />
              <div className="flex-1 min-w-0">
                <p className="text-xs font-semibold text-slate-900">{t.title}</p>
                {t.detail && <p className="text-xs text-slate-600 mt-0.5">{t.detail}</p>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <WorkspaceApp />
    </ErrorBoundary>
  );
}
