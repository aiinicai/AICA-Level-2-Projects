import React, { useState, useMemo, useEffect } from 'react';
import { Navbar, NavigationTab } from './components/Navbar';
import { SalaryRegisterTab } from './components/SalaryRegisterTab';
import { EmployeeMasterTab } from './components/EmployeeMasterTab';
import { DeclarationsTab } from './components/DeclarationsTab';
import { TaxSimulatorTab } from './components/TaxSimulatorTab';
import { TaxGovernanceTab } from './components/TaxGovernanceTab';
import { EmployeePortalTab } from './components/EmployeePortalTab';
import { LoginModal } from './components/LoginModal';
import { PayslipModal } from './components/PayslipModal';
import { EmployeeModal } from './components/EmployeeModal';
import { DeclarationModal } from './components/DeclarationModal';
import { ExcelUploadModal } from './components/ExcelUploadModal';
import { FloatingTaxCopilot } from './components/FloatingTaxCopilot';
import { CapstoneDeckModal } from './components/CapstoneDeckModal';

import {
  EmployeeMaster,
  EmployeeDeclaration,
  TaxConfig,
  MonthlySalaryRecord,
} from './types/payroll';
import { UserSession } from './types/auth';
import {
  INITIAL_EMPLOYEES as SAMPLE_EMPLOYEES,
  INITIAL_DECLARATIONS as SAMPLE_DECLARATIONS,
  TAX_CONFIG_2026_27 as AY2026_27_TAX_CONFIG,
} from './data/seedData';
import { runPayrollMonth, createDefaultDeclaration, FY_MONTHS } from './utils/payrollEngine';
import { RotateCcw, CheckCircle, ShieldAlert, UserCheck, ShieldCheck, LogOut } from 'lucide-react';

export default function App() {
  // Authentication & Role Session
  const [currentUser, setCurrentUser] = useState<UserSession | null>(() => {
    const saved = localStorage.getItem('payroll_user_session_v1');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch (e) {
        console.error('Failed to parse saved user session', e);
      }
    }
    // Secure by default: unauthenticated visitors must log in through the Security Gateway
    return null;
  });

  // Persistence state for employees & declarations
  const [employees, setEmployees] = useState<EmployeeMaster[]>(() => {
    const saved = localStorage.getItem('payroll_employees_v1');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        // Merge in any new seed employees that aren't in local storage yet
        const existingCodes = new Set(parsed.map((e: EmployeeMaster) => e.employeeCode));
        const missingFromSeed = SAMPLE_EMPLOYEES.filter((e) => !existingCodes.has(e.employeeCode));
        return [...parsed, ...missingFromSeed];
      } catch (e) {
        console.error('Failed to parse saved employees', e);
      }
    }
    return SAMPLE_EMPLOYEES;
  });

  const [declarations, setDeclarations] = useState<EmployeeDeclaration[]>(() => {
    const saved = localStorage.getItem('payroll_declarations_v1');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        // Merge in any new seed declarations that aren't in local storage yet
        const existingCodes = new Set(parsed.map((d: EmployeeDeclaration) => d.employeeCode));
        const missingFromSeed = SAMPLE_DECLARATIONS.filter((d) => !existingCodes.has(d.employeeCode));
        return [...parsed, ...missingFromSeed];
      } catch (e) {
        console.error('Failed to parse saved declarations', e);
      }
    }
    return SAMPLE_DECLARATIONS;
  });

  const [taxConfig, setTaxConfig] = useState<TaxConfig>(AY2026_27_TAX_CONFIG);
  const [activeTab, setActiveTab] = useState<NavigationTab>(() => {
    return currentUser?.role === 'employee' ? 'my-portal' : 'payroll';
  });
  const [selectedMonth, setSelectedMonth] = useState<number>(5); // August 2026 (Month 5 of FY)
  const [selectedFy, setSelectedFy] = useState<string>('2026-27');

  // Save changes to localStorage
  useEffect(() => {
    localStorage.setItem('payroll_employees_v1', JSON.stringify(employees));
  }, [employees]);

  useEffect(() => {
    localStorage.setItem('payroll_declarations_v1', JSON.stringify(declarations));
  }, [declarations]);

  useEffect(() => {
    if (currentUser) {
      localStorage.setItem('payroll_user_session_v1', JSON.stringify(currentUser));
      if (currentUser.role === 'employee') {
        setActiveTab('my-portal');
      }
    } else {
      localStorage.removeItem('payroll_user_session_v1');
    }
  }, [currentUser]);

  // Modals state
  const [payslipRecord, setPayslipRecord] = useState<MonthlySalaryRecord | null>(null);
  const [employeeModal, setEmployeeModal] = useState<{ isOpen: boolean; employee: EmployeeMaster | null }>({
    isOpen: false,
    employee: null,
  });
  const [declarationModal, setDeclarationModal] = useState<{
    isOpen: boolean;
    declaration: EmployeeDeclaration | null;
  }>({
    isOpen: false,
    declaration: null,
  });
  const [isExcelUploadOpen, setIsExcelUploadOpen] = useState(false);
  const [isCapstoneDeckOpen, setIsCapstoneDeckOpen] = useState(false);
  const [simulatorSelectedEmp, setSimulatorSelectedEmp] = useState<string>(
    employees.length > 0 ? employees[0].employeeCode : ''
  );
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  // Run calculation engine dynamically
  const payrollSummary = useMemo(() => {
    return runPayrollMonth(employees, declarations, taxConfig, selectedMonth);
  }, [employees, declarations, taxConfig, selectedMonth]);

  // Handlers
  const handleSaveEmployee = (updatedEmp: EmployeeMaster) => {
    setEmployees((prev) => {
      const idx = prev.findIndex((e) => e.employeeCode === updatedEmp.employeeCode);
      if (idx >= 0) {
        const next = [...prev];
        next[idx] = updatedEmp;
        return next;
      }
      return [...prev, updatedEmp];
    });

    setDeclarations((prev) => {
      const exists = prev.find((d) => d.employeeCode === updatedEmp.employeeCode);
      if (!exists) {
        return [...prev, createDefaultDeclaration(updatedEmp, selectedFy)];
      }
      return prev;
    });

    showToast(`Employee ${updatedEmp.employeeCode} (${updatedEmp.employeeName}) saved.`);
  };

  const handleSaveDeclaration = (updatedDecl: EmployeeDeclaration) => {
    setDeclarations((prev) => {
      const idx = prev.findIndex((d) => d.employeeCode === updatedDecl.employeeCode);
      if (idx >= 0) {
        const next = [...prev];
        next[idx] = updatedDecl;
        return next;
      }
      return [...prev, updatedDecl];
    });
    showToast(`Tax Declaration for ${updatedDecl.employeeCode} updated.`);
  };

  const handleImportMaster = (imported: EmployeeMaster[]) => {
    setEmployees((prev) => {
      const map = new Map<string, EmployeeMaster>();
      prev.forEach((e) => map.set(e.employeeCode, e));
      imported.forEach((e) => map.set(e.employeeCode, e));
      return Array.from(map.values());
    });
    showToast(`Imported ${imported.length} employee records from Excel.`);
  };

  const handleImportDeclarations = (imported: EmployeeDeclaration[]) => {
    setDeclarations((prev) => {
      const map = new Map<string, EmployeeDeclaration>();
      prev.forEach((d) => map.set(d.employeeCode, d));
      imported.forEach((d) => map.set(d.employeeCode, d));
      return Array.from(map.values());
    });
    showToast(`Imported ${imported.length} tax declarations from Excel.`);
  };

  const handleResetToSeed = () => {
    if (window.confirm('Reset data back to the 14 initial sample employees? Any custom edits will be cleared.')) {
      setEmployees(SAMPLE_EMPLOYEES);
      setDeclarations(SAMPLE_DECLARATIONS);
      localStorage.removeItem('payroll_employees_v1');
      localStorage.removeItem('payroll_declarations_v1');
      showToast('Reset back to standard 14 employee sample test suite.');
    }
  };

  // Find logged-in employee object
  const loggedInEmployee = useMemo(() => {
    if (!currentUser || currentUser.role !== 'employee') {
      // If admin viewing as employee, fallback to first employee
      return employees.find((e) => e.employeeCode === simulatorSelectedEmp) || employees[0];
    }
    return employees.find((e) => e.employeeCode === currentUser.employeeCode) || employees[0];
  }, [currentUser, employees, simulatorSelectedEmp]);

  const loggedInDeclaration = useMemo(() => {
    if (!loggedInEmployee) return undefined;
    return declarations.find((d) => d.employeeCode === loggedInEmployee.employeeCode);
  }, [loggedInEmployee, declarations]);

  // If not logged in, render the secure corporate login gateway page
  if (!currentUser) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans antialiased">
        {toastMessage && (
          <div className="fixed top-4 right-4 z-50 flex items-center gap-2 bg-slate-900 text-white px-4 py-2.5 rounded-xl shadow-lg text-xs animate-in fade-in slide-in-from-top-2 border border-slate-700">
            <CheckCircle className="h-4 w-4 text-emerald-400" />
            <span>{toastMessage}</span>
          </div>
        )}
        <LoginModal
          employees={employees}
          onLogin={(session) => {
            setCurrentUser(session);
            if (session.role === 'employee') {
              setActiveTab('my-portal');
              showToast(`Authenticated as ${session.name} (${session.email})`);
            } else {
              setActiveTab('payroll');
              showToast('Authenticated as Administrator (admin@xyz.com)');
            }
          }}
          onOpenCapstoneDeck={() => setIsCapstoneDeckOpen(true)}
          isModal={false}
        />
        <CapstoneDeckModal
          isOpen={isCapstoneDeckOpen}
          onClose={() => setIsCapstoneDeckOpen(false)}
        />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-100/70 text-slate-800 flex flex-col font-sans antialiased">
      {/* Toast alert */}
      {toastMessage && (
        <div className="fixed top-4 right-4 z-50 flex items-center gap-2 bg-slate-900 text-white px-4 py-2.5 rounded-xl shadow-lg text-xs animate-in fade-in slide-in-from-top-2 border border-slate-700">
          <CheckCircle className="h-4 w-4 text-emerald-400" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Global Top Navbar */}
      <div className="print:hidden">
        <Navbar
          activeTab={activeTab}
          onTabChange={setActiveTab}
          selectedMonth={selectedMonth}
          onMonthChange={setSelectedMonth}
          selectedFy={selectedFy}
          onFyChange={setSelectedFy}
          taxConfig={taxConfig}
          employeeCount={employees.length}
          userSession={currentUser}
          onLogout={() => {
            setCurrentUser(null);
            showToast('Signed out from corporate session.');
          }}
          onOpenLogin={() => setCurrentUser(null)}
          onOpenCapstoneDeck={() => setIsCapstoneDeckOpen(true)}
        />

        {/* Security Role & Session Status Banner */}
        <div className="bg-slate-950 text-white border-b border-slate-800 py-2 px-4 text-xs">
          <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <span className="text-slate-400 font-bold uppercase tracking-wider text-[10px]">
                Security Perimeter:
              </span>
              {currentUser.role === 'employee' ? (
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-bold text-emerald-400 flex items-center gap-1.5 text-xs">
                    <ShieldCheck className="h-4 w-4 text-emerald-400" />
                    Employee Portal: <span className="text-white">{currentUser.name}</span> ({currentUser.email})
                  </span>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-950/80 border border-emerald-600/40 text-emerald-300 font-semibold">
                    Scoped to {currentUser.employeeCode}
                  </span>
                  <span className="text-slate-400 text-[11px] hidden md:inline">
                    (Confidential: Isolated strictly to personal salary & tax declarations)
                  </span>
                </div>
              ) : (
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-bold text-indigo-400 flex items-center gap-1.5 text-xs">
                    <ShieldCheck className="h-4 w-4 text-indigo-400" />
                    Administrator Session: <span className="text-white">admin@xyz.com</span>
                  </span>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-indigo-950/80 border border-indigo-600/40 text-indigo-300 font-semibold">
                    Full Superuser Access
                  </span>
                  <span className="text-slate-400 text-[11px] hidden md:inline">
                    (Company Salary Register, Attendance & Tax Governance)
                  </span>
                </div>
              )}
            </div>

            <div className="flex items-center gap-2.5 text-[11px]">
              {currentUser.role === 'admin' ? (
                /* Admin can inspect employee portal for auditing */
                <div className="flex items-center gap-1.5">
                  <span className="text-slate-400 font-medium">Audit Employee Portal:</span>
                  <select
                    value={simulatorSelectedEmp}
                    onChange={(e) => {
                      setSimulatorSelectedEmp(e.target.value);
                      showToast(`Auditing Employee Portal for ${e.target.value}`);
                    }}
                    className="bg-slate-800 text-white border border-slate-700 rounded px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500 font-medium cursor-pointer"
                  >
                    {employees.map((emp) => (
                      <option key={emp.employeeCode} value={emp.employeeCode}>
                        {emp.employeeName} ({emp.email || `${emp.employeeName.split(' ')[0].toLowerCase()}@xyz.com`})
                      </option>
                    ))}
                  </select>
                </div>
              ) : (
                <span className="text-[10px] text-slate-400 font-mono hidden sm:inline">
                  RBAC Mode: Employee Self-Service
                </span>
              )}

              <button
                type="button"
                onClick={() => {
                  setCurrentUser(null);
                  showToast('Signed out from corporate session.');
                }}
                className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-rose-900/40 hover:text-rose-200 border border-slate-700 hover:border-rose-700/50 text-slate-300 flex items-center gap-1.5 text-xs font-semibold transition-all cursor-pointer"
                title="Sign out from current session"
              >
                <LogOut className="h-3.5 w-3.5 text-rose-400" />
                <span>Sign Out</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Tab View Canvas */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8 space-y-6 print:hidden">
        {/* If logged in as Employee, force Employee Portal */}
        {currentUser?.role === 'employee' || activeTab === 'my-portal' ? (
          <EmployeePortalTab
            employee={loggedInEmployee}
            declaration={loggedInDeclaration}
            taxConfig={taxConfig}
            payrollSummary={payrollSummary}
            selectedMonth={selectedMonth}
            onViewPayslip={(rec) => setPayslipRecord(rec)}
            onEditDeclaration={(decl) => setDeclarationModal({ isOpen: true, declaration: decl })}
          />
        ) : (
          /* Admin View Tabs */
          <>
            {activeTab === 'payroll' && (
              <SalaryRegisterTab
                payrollSummary={payrollSummary}
                onViewPayslip={(rec) => setPayslipRecord(rec)}
                onViewTaxBreakdown={(empCode) => {
                  setSimulatorSelectedEmp(empCode);
                  setActiveTab('simulator');
                }}
                onRerunPayroll={() => {
                  showToast('Payroll calculations refreshed with latest attendance and tax rules.');
                }}
              />
            )}

            {activeTab === 'employees' && (
              <EmployeeMasterTab
                employees={employees}
                onAddEmployee={() => setEmployeeModal({ isOpen: true, employee: null })}
                onEditEmployee={(emp) => setEmployeeModal({ isOpen: true, employee: emp })}
                onUploadExcel={() => setIsExcelUploadOpen(true)}
              />
            )}

            {activeTab === 'declarations' && (
              <DeclarationsTab
                declarations={declarations}
                employees={employees}
                selectedFy={selectedFy}
                onEditDeclaration={(decl) => setDeclarationModal({ isOpen: true, declaration: decl })}
                onUploadExcel={() => setIsExcelUploadOpen(true)}
              />
            )}

            {activeTab === 'simulator' && (
              <TaxSimulatorTab
                employees={employees}
                declarations={declarations}
                taxConfig={taxConfig}
                currentMonth={selectedMonth}
                selectedEmployeeCode={simulatorSelectedEmp}
                onSelectEmployee={(code) => setSimulatorSelectedEmp(code)}
              />
            )}

            {activeTab === 'governance' && (
              <TaxGovernanceTab
                taxConfig={taxConfig}
                onUpdateConfig={(cfg) => {
                  setTaxConfig(cfg);
                  showToast('Tax configuration updated.');
                }}
              />
            )}
          </>
        )}
      </main>

      {/* Footer Bar */}
      <footer className="bg-white border-t border-slate-200 mt-auto py-3 px-6 text-xs text-slate-500 print:hidden">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center gap-3">
            <span>
              Payroll & ESS Engine • Indian Income Tax AY 2026–27 compliance
            </span>
            <span className="hidden sm:inline text-slate-300">|</span>
            <span className="hidden sm:inline">Role: {currentUser?.role === 'employee' ? 'Employee Self-Service (Scoped)' : 'Administrator'}</span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleResetToSeed}
              className="flex items-center gap-1 text-[11px] text-slate-500 hover:text-slate-800 transition-colors cursor-pointer"
              title="Reset data back to the original test employees"
            >
              <RotateCcw className="h-3 w-3" />
              Reset Test Data ({employees.length} Employees)
            </button>
          </div>
        </div>
      </footer>

      {/* Modals */}
      {payslipRecord && (
        <PayslipModal
          record={payslipRecord}
          taxConfig={taxConfig}
          onClose={() => setPayslipRecord(null)}
        />
      )}

      {employeeModal.isOpen && (
        <EmployeeModal
          employee={employeeModal.employee}
          isOpen={employeeModal.isOpen}
          onClose={() => setEmployeeModal({ isOpen: false, employee: null })}
          onSave={handleSaveEmployee}
        />
      )}

      {declarationModal.isOpen && declarationModal.declaration && (
        <DeclarationModal
          declaration={declarationModal.declaration}
          employees={employees}
          taxConfig={taxConfig}
          isOpen={declarationModal.isOpen}
          onClose={() => setDeclarationModal({ isOpen: false, declaration: null })}
          onSave={handleSaveDeclaration}
        />
      )}

      {isExcelUploadOpen && (
        <ExcelUploadModal
          isOpen={isExcelUploadOpen}
          onClose={() => setIsExcelUploadOpen(false)}
          onImportMaster={handleImportMaster}
          onImportDeclarations={handleImportDeclarations}
          currentEmployees={employees}
          currentDeclarations={declarations}
        />
      )}

      {/* Floating AI Tax Copilot accessible from all tabs */}
      {currentUser && (
        <FloatingTaxCopilot
          employees={employees}
          declarations={declarations}
          taxConfig={taxConfig}
          currentMonth={selectedMonth}
          activeEmployeeCode={currentUser.role === 'employee' ? currentUser.employeeCode : simulatorSelectedEmp}
        />
      )}
      {/* Capstone Project Presentation Deck & Report Modal */}
      <CapstoneDeckModal
        isOpen={isCapstoneDeckOpen}
        onClose={() => setIsCapstoneDeckOpen(false)}
      />
    </div>
  );
}
