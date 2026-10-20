import React from 'react';
import { 
  User, 
  TaskEvaluation, 
  CoachingNote, 
  AppraisalRecord, 
  TrainingRecommendation,
  AnnualPerformancePlan,
  ProfessionalCertification,
  AuditLogEntry
} from './types';
import { 
  MOCK_COMPANY_INFO, 
  MOCK_DEPARTMENTS, 
  MOCK_USERS, 
  MOCK_ATTENDANCE_RECORDS, 
  MOCK_SKILLS, 
  MOCK_TRAINING_COURSES, 
  MOCK_STATUTORY_NOTICES 
} from './data/mockData';
import {
  getInitialSessionUser,
  saveSessionUser,
  clearSessionUser,
  getStoredAppraisals,
  saveStoredAppraisals,
  getStoredEvaluations,
  saveStoredEvaluations,
  getStoredCoaching,
  saveStoredCoaching,
  getStoredTraining,
  saveStoredTraining,
  getStoredPlans,
  saveStoredPlans,
  getStoredCerts,
  saveStoredCerts,
  getStoredAuditLogs,
  saveStoredAuditLogs,
  resetAllSessionData
} from './utils/sessionStore';
import { Header } from './components/Header';
import { EmployeeGrowthHub } from './components/EmployeeGrowthHub';
import { ManagerDashboard } from './components/ManagerDashboard';
import { HRIntelligenceDashboard } from './components/HRIntelligenceDashboard';
import { ScoreSimulator } from './components/ScoreSimulator';
import { StatutoryComplianceModal } from './components/StatutoryComplianceModal';
import { QuickEvaluationModal } from './components/QuickEvaluationModal';
import { AddCoachingModal } from './components/AddCoachingModal';
import { LandingLoginScreen } from './components/LandingLoginScreen';
import { AnnualPerformanceMatrix } from './components/AnnualPerformanceMatrix';
import { CertificationBonusPanel } from './components/CertificationBonusPanel';
import { ReportsCenter } from './components/ReportsCenter';
import { AuditTrailView } from './components/AuditTrailView';
import { CheckCircle2, AlertCircle, RefreshCw } from 'lucide-react';

export default function App() {
  // Authentication & Session State (Landing & Login Screen presented by default)
  const [isAuthenticated, setIsAuthenticated] = React.useState<boolean>(false);
  const [currentUser, setCurrentUser] = React.useState<User>(() => getInitialSessionUser());

  // Navigation Tab State
  const [activeTab, setActiveTab] = React.useState<
    'employee' | 'manager' | 'matrix' | 'certifications' | 'hr' | 'compliance' | 'reports' | 'audit' | 'simulator'
  >('employee');

  // Application Data Records with automatic local session persistence
  const [evaluations, setEvaluations] = React.useState<TaskEvaluation[]>(() => getStoredEvaluations());
  const [coachingNotes, setCoachingNotes] = React.useState<CoachingNote[]>(() => getStoredCoaching());
  const [trainingRecs, setTrainingRecs] = React.useState<TrainingRecommendation[]>(() => getStoredTraining());
  const [appraisals, setAppraisals] = React.useState<AppraisalRecord[]>(() => getStoredAppraisals());
  const [users, setUsers] = React.useState<User[]>(MOCK_USERS);
  const [annualPlans, setAnnualPlans] = React.useState<AnnualPerformancePlan[]>(() => getStoredPlans());
  const [certifications, setCertifications] = React.useState<ProfessionalCertification[]>(() => getStoredCerts());
  const [auditLogs, setAuditLogs] = React.useState<AuditLogEntry[]>(() => getStoredAuditLogs());

  // Modals State
  const [isQuickEvalOpen, setIsQuickEvalOpen] = React.useState<boolean>(false);
  const [quickEvalEmpId, setQuickEvalEmpId] = React.useState<string | undefined>(undefined);
  const [isAddCoachingOpen, setIsAddCoachingOpen] = React.useState<boolean>(false);
  const [coachingEmpId, setCoachingEmpId] = React.useState<string | undefined>(undefined);
  const [isComplianceOpen, setIsComplianceOpen] = React.useState<boolean>(false);
  const [complianceEmpId, setComplianceEmpId] = React.useState<string | undefined>(undefined);

  // Toast Notification State
  const [toastMessage, setToastMessage] = React.useState<string | null>(null);
  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage(null);
    }, 4000);
  };

  // Sync state changes to local session storage
  React.useEffect(() => {
    saveSessionUser(currentUser);
  }, [currentUser]);

  React.useEffect(() => {
    saveStoredAppraisals(appraisals);
  }, [appraisals]);

  React.useEffect(() => {
    saveStoredEvaluations(evaluations);
  }, [evaluations]);

  React.useEffect(() => {
    saveStoredCoaching(coachingNotes);
  }, [coachingNotes]);

  React.useEffect(() => {
    saveStoredTraining(trainingRecs);
  }, [trainingRecs]);

  React.useEffect(() => {
    saveStoredPlans(annualPlans);
  }, [annualPlans]);

  React.useEffect(() => {
    saveStoredCerts(certifications);
  }, [certifications]);

  React.useEffect(() => {
    saveStoredAuditLogs(auditLogs);
  }, [auditLogs]);

  // Session reset handler
  const handleResetSession = () => {
    resetAllSessionData();
    const defaultUser = MOCK_USERS[3];
    setCurrentUser(defaultUser);
    setEvaluations(getStoredEvaluations());
    setAppraisals(getStoredAppraisals());
    setCoachingNotes(getStoredCoaching());
    setTrainingRecs(getStoredTraining());
    setAnnualPlans(getStoredPlans());
    setCertifications(getStoredCerts());
    setAuditLogs(getStoredAuditLogs());
    setActiveTab('employee');
    showToast('Session reset to default enterprise state');
  };

  // Login handler
  const handleLoginSuccess = (user: User) => {
    setCurrentUser(user);
    saveSessionUser(user);
    setIsAuthenticated(true);
    if (user.role === 'employee') {
      setActiveTab('employee');
    } else if (user.role === 'department_manager') {
      setActiveTab('manager');
    } else if (user.role === 'hr_manager' || user.role === 'super_admin') {
      setActiveTab('hr');
    }
    showToast(`Authenticated as ${user.fullName} (${user.currentDesignation})`);
  };

  // Logout handler
  const handleLogout = () => {
    clearSessionUser();
    setIsAuthenticated(false);
    showToast('Logged out to Paras Advisory portal landing screen');
  };

  // Persona switching
  const handleSelectUser = (user: User) => {
    setCurrentUser(user);
    saveSessionUser(user);
    if (user.role === 'employee') {
      setActiveTab('employee');
    } else if (user.role === 'department_manager') {
      setActiveTab('manager');
    } else if (user.role === 'hr_manager' || user.role === 'super_admin') {
      setActiveTab('hr');
    }
    showToast(`Switched persona to ${user.fullName} (${user.currentDesignation})`);
  };

  // Helper to log an immutable audit event
  const logAuditEvent = (event: Omit<AuditLogEntry, 'id' | 'timestamp' | 'verificationHash' | 'ipAddress' | 'authorizedUnderPolicy'> & {
    authorizedUnderPolicy?: string;
    ipAddress?: string;
  }) => {
    const timestamp = new Date().toISOString();
    const id = `AUD-2026-${Math.floor(1000 + Math.random() * 9000)}`;
    const hash = `sha256:${Array.from({ length: 40 }, () => Math.floor(Math.random() * 16).toString(16)).join('')}`;
    const newLog: AuditLogEntry = {
      ...event,
      id,
      timestamp,
      verificationHash: hash,
      ipAddress: event.ipAddress || '194.170.84.15 (ADGM Maryah Island HQ)',
      authorizedUnderPolicy: event.authorizedUnderPolicy || 'ADGM FSRA Supervisory Accountability Directive',
    };
    setAuditLogs((prev) => [newLog, ...prev]);
    return newLog;
  };

  // Training Enrollment Handler
  const handleEnrollTraining = (recId: string) => {
    setTrainingRecs((prev) =>
      prev.map((r) => (r.id === recId ? { ...r, status: 'Enrolled' } : r))
    );
    const rec = trainingRecs.find((r) => r.id === recId);
    showToast(`Successfully enrolled in "${rec?.courseTitle}". 100% firm-sponsored.`);
    logAuditEvent({
      actionType: 'TRAINING_ENROLLED',
      actionTitle: 'Sponsored Training Course Enrollment Approved',
      category: 'TRAINING_BUDGET',
      severity: 'ACTION',
      actorId: currentUser.id,
      actorName: currentUser.fullName,
      actorRole: currentUser.role,
      actorDesignation: currentUser.currentDesignation,
      targetEmployeeId: currentUser.id,
      targetEmployeeName: currentUser.fullName,
      targetDepartment: currentUser.departmentName,
      details: `Enrolled in firm-sponsored course: "${rec?.courseTitle}". 100% financed under firm T&D budget.`,
      newValue: 'Status: Enrolled (Firm Sponsored)',
    });
  };

  // Save New Evaluation & Update Appraisal Score
  const handleSaveEvaluation = (newEval: TaskEvaluation) => {
    setEvaluations((prev) => [newEval, ...prev]);
    setAppraisals((prev) =>
      prev.map((app) => {
        if (app.employeeId === newEval.employeeId) {
          const updatedGross = Math.min(100, Math.round(((app.grossServicePoints + newEval.pointsAwarded) / 2) * 10) / 10);
          return {
            ...app,
            grossServicePoints: updatedGross,
          };
        }
        return app;
      })
    );
    showToast(`Awarded ${newEval.pointsAwarded} deliverable points to ${newEval.employeeName}`);
    logAuditEvent({
      actionType: 'DELIVERABLE_POINTS_AWARDED',
      actionTitle: 'Deliverable Quality Points Awarded',
      category: 'PERFORMANCE_GOVERNANCE',
      severity: 'INFO',
      actorId: currentUser.id,
      actorName: currentUser.fullName,
      actorRole: currentUser.role,
      actorDesignation: currentUser.currentDesignation,
      targetEmployeeId: newEval.employeeId,
      targetEmployeeName: newEval.employeeName,
      details: `Awarded ${newEval.pointsAwarded} pts for deliverable: "${newEval.deliverableName}". Turnaround: ${newEval.slaHoursTurnaround} hrs.`,
      newValue: `Score: ${newEval.pointsAwarded} pts`,
    });
  };

  // Save New Coaching Note
  const handleSaveCoaching = (newNote: CoachingNote) => {
    setCoachingNotes((prev) => [newNote, ...prev]);
    const emp = users.find((u) => u.id === newNote.employeeId);
    showToast(`Logged constructive coaching note for ${emp?.fullName}`);
    logAuditEvent({
      actionType: 'COACHING_NOTE_LOGGED',
      actionTitle: 'Constructive Coaching Note Recorded',
      category: 'PERFORMANCE_GOVERNANCE',
      severity: 'INFO',
      actorId: currentUser.id,
      actorName: currentUser.fullName,
      actorRole: currentUser.role,
      actorDesignation: currentUser.currentDesignation,
      targetEmployeeId: newNote.employeeId,
      targetEmployeeName: emp?.fullName,
      details: `Recorded coaching note: "${newNote.constructiveGuidance?.slice(0, 100)}..."`,
      newValue: `Objective: ${newNote.objective}`,
    });
  };

  // Update Full Appraisal Record
  const handleUpdateAppraisal = (updatedAppraisal: AppraisalRecord) => {
    setAppraisals((prev) =>
      prev.map((a) => (a.employeeId === updatedAppraisal.employeeId ? updatedAppraisal : a))
    );
    showToast(`Appraisal saved for ${updatedAppraisal.employeeName} (${updatedAppraisal.finalWeightedScore} pts)`);
    logAuditEvent({
      actionType: 'APPRAISAL_OVERRIDE_SAVED',
      actionTitle: 'Appraisal Record Synchronized & Saved',
      category: 'PERFORMANCE_GOVERNANCE',
      severity: 'ACTION',
      actorId: currentUser.id,
      actorName: currentUser.fullName,
      actorRole: currentUser.role,
      actorDesignation: currentUser.currentDesignation,
      targetEmployeeId: updatedAppraisal.employeeId,
      targetEmployeeName: updatedAppraisal.employeeName,
      details: `Appraisal synchronized. Weighted score: ${updatedAppraisal.finalWeightedScore} pts.`,
      newValue: `Final Score: ${updatedAppraisal.finalWeightedScore} pts`,
    });
  };

  // Annual Performance Matrix Handlers
  const handleSaveAnnualPlan = (updatedPlan: AnnualPerformancePlan) => {
    setAnnualPlans((prev) =>
      prev.map((p) => (p.id === updatedPlan.id ? updatedPlan : p))
    );
    showToast(`Annual Performance Matrix updated for ${updatedPlan.employeeName}`);
    logAuditEvent({
      actionType: 'MATRIX_PLAN_SAVED',
      actionTitle: 'Annual Performance Matrix Plan Updated',
      category: 'PERFORMANCE_GOVERNANCE',
      severity: 'INFO',
      actorId: currentUser.id,
      actorName: currentUser.fullName,
      actorRole: currentUser.role,
      actorDesignation: currentUser.currentDesignation,
      targetEmployeeId: updatedPlan.employeeId,
      targetEmployeeName: updatedPlan.employeeName,
      details: `Annual matrix draft goals updated across ${updatedPlan.goals.length} target categories.`,
      newValue: `Status: ${updatedPlan.planStatus}`,
    });
  };

  const handleApproveAnnualPlan = (planId: string, notes: string) => {
    let targetPlan: AnnualPerformancePlan | undefined;
    setAnnualPlans((prev) =>
      prev.map((p) => {
        if (p.id === planId) {
          targetPlan = p;
          return {
            ...p,
            planStatus: 'Manager_Approved',
            managerApprovalNotes: notes,
            managerApprovedAt: new Date().toISOString().split('T')[0],
          };
        }
        return p;
      })
    );
    showToast('Annual Performance Matrix approved by Practice Partner!');
    logAuditEvent({
      actionType: 'MATRIX_PLAN_APPROVED',
      actionTitle: 'Annual Performance Matrix Plan Approved',
      category: 'PERFORMANCE_GOVERNANCE',
      severity: 'ACTION',
      actorId: currentUser.id,
      actorName: currentUser.fullName,
      actorRole: currentUser.role,
      actorDesignation: currentUser.currentDesignation,
      targetEmployeeId: targetPlan?.employeeId,
      targetEmployeeName: targetPlan?.employeeName,
      details: `Practice Partner approved 2026 Annual Performance Matrix targets. Notes: "${notes}"`,
      previousValue: 'Status: Submitted_To_Manager',
      newValue: 'Status: Manager_Approved',
    });
  };

  const handleFinalAssessAnnualPlan = (planId: string, assessedScore: number) => {
    let targetPlan: AnnualPerformancePlan | undefined;
    setAnnualPlans((prev) =>
      prev.map((p) => {
        if (p.id === planId) {
          targetPlan = p;
          return {
            ...p,
            planStatus: 'Final_Assessed',
            assessedScore,
            lastUpdated: new Date().toISOString().split('T')[0],
          };
        }
        return p;
      })
    );
    showToast(`Annual assessment finalized with score: ${assessedScore} points.`);
    logAuditEvent({
      actionType: 'MATRIX_FINAL_ASSESSED',
      actionTitle: 'Annual Performance Assessment Score Sealed',
      category: 'PERFORMANCE_GOVERNANCE',
      severity: 'CRITICAL',
      actorId: currentUser.id,
      actorName: currentUser.fullName,
      actorRole: currentUser.role,
      actorDesignation: currentUser.currentDesignation,
      targetEmployeeId: targetPlan?.employeeId,
      targetEmployeeName: targetPlan?.employeeName,
      details: `Formal annual assessment finalized. Weighted performance score: ${assessedScore}/100 pts.`,
      newValue: `Final Assessed Score: ${assessedScore} pts`,
    });
  };

  // Certification Bonus Handlers
  const handleProposeCertification = (newCert: Omit<ProfessionalCertification, 'id'>) => {
    const certItem: ProfessionalCertification = {
      ...newCert,
      id: `cert-${Date.now()}`,
    };
    setCertifications((prev) => [certItem, ...prev]);
    showToast(`Proposed ${certItem.certificationName} for manager approval.`);
    logAuditEvent({
      actionType: 'CERTIFICATION_PROPOSED',
      actionTitle: 'Chartered Certification Track Proposed',
      category: 'FINANCIAL_DISBURSEMENT',
      severity: 'INFO',
      actorId: currentUser.id,
      actorName: currentUser.fullName,
      actorRole: currentUser.role,
      actorDesignation: currentUser.currentDesignation,
      targetEmployeeId: certItem.employeeId,
      targetEmployeeName: certItem.employeeName,
      details: `Proposed study track for "${certItem.certificationName}" with ${certItem.issuingBody}. Target bonus: AED 15,000.00.`,
      newValue: 'Status: Proposed',
    });
  };

  const handleApproveCertification = (certId: string, notes: string) => {
    let targetCert: ProfessionalCertification | undefined;
    setCertifications((prev) =>
      prev.map((c) => {
        if (c.id === certId) {
          targetCert = c;
          return { ...c, status: 'Manager_Approved', managerApprovalNotes: notes };
        }
        return c;
      })
    );
    showToast('Certification study track approved. Entitled to AED 15,000 bonus upon completion.');
    logAuditEvent({
      actionType: 'CERTIFICATION_APPROVED',
      actionTitle: 'Chartered Certification Track Approved',
      category: 'FINANCIAL_DISBURSEMENT',
      severity: 'ACTION',
      actorId: currentUser.id,
      actorName: currentUser.fullName,
      actorRole: currentUser.role,
      actorDesignation: currentUser.currentDesignation,
      targetEmployeeId: targetCert?.employeeId,
      targetEmployeeName: targetCert?.employeeName,
      details: `Approved candidate enrollment for "${targetCert?.certificationName}". Verified eligibility for AED 15,000.00 bonus upon completion.`,
      previousValue: 'Status: Proposed',
      newValue: 'Status: Manager_Approved (Entitled to AED 15,000)',
    });
  };

  const handleVerifyAndDisburseBonus = (certId: string) => {
    let targetCert: ProfessionalCertification | undefined;
    setCertifications((prev) =>
      prev.map((c) => {
        if (c.id === certId) {
          targetCert = c;
          return {
            ...c,
            status: 'Bonus_Disbursed',
            bonusPaidDate: new Date().toISOString().split('T')[0],
          };
        }
        return c;
      })
    );
    showToast('Special Bonus of AED 15,000.00 authorized and disbursed to payroll!');
    logAuditEvent({
      actionType: 'BONUS_DISBURSED',
      actionTitle: 'AED 15,000 Special Certification Bonus Disbursed',
      category: 'FINANCIAL_DISBURSEMENT',
      severity: 'FINANCIAL',
      actorId: currentUser.id,
      actorName: currentUser.fullName,
      actorRole: currentUser.role,
      actorDesignation: currentUser.currentDesignation,
      targetEmployeeId: targetCert?.employeeId,
      targetEmployeeName: targetCert?.employeeName,
      details: `Formally authorized release of AED 15,000.00 special one-time bonus for completed credential: "${targetCert?.certificationName}". Disbursed via UAE WPS batch.`,
      previousValue: 'Status: Completed_Verified',
      newValue: 'Status: Bonus_Disbursed (AED 15,000.00 Authorized)',
    });
  };

  // If not authenticated, render the Landing & Login Screen
  if (!isAuthenticated) {
    return <LandingLoginScreen onLoginSuccess={handleLoginSuccess} />;
  }

  // Current Employee Appraisal & Plan
  const currentAppraisal = appraisals.find((a) => a.employeeId === currentUser.id) || appraisals[0];
  const currentPlan = annualPlans.find((p) => p.employeeId === currentUser.id) || annualPlans[0];

  // Filter records for views
  const employeeEvaluations = evaluations.filter((e) => e.employeeId === currentUser.id);
  const employeeAttendance = MOCK_ATTENDANCE_RECORDS.filter((a) => a.employeeId === currentUser.id);
  const employeeTrainingRecs = trainingRecs.filter((t) => t.employeeId === currentUser.id);
  const employeeCoachingNotes = coachingNotes.filter((c) => c.employeeId === currentUser.id);

  // Department managers list and active manager
  const departmentManagers = users.filter((u) => u.role === 'department_manager');
  const defaultManager = departmentManagers.find((u) => u.id === 'emp-tariq') || departmentManagers[0] || MOCK_USERS[2];
  const activeManager = (currentUser.role === 'department_manager' || currentUser.role === 'super_admin') 
    ? currentUser 
    : defaultManager;

  // Team users for manager view
  const teamUsers = users.filter((u) => u.role === 'employee');

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans">
      {/* Top Header */}
      <Header
        currentUser={currentUser}
        allUsers={users}
        onSelectUser={handleSelectUser}
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        onOpenQuickEval={() => {
          setQuickEvalEmpId(currentUser.role === 'employee' ? currentUser.id : undefined);
          setIsQuickEvalOpen(true);
        }}
        onOpenComplianceDoc={() => {
          setComplianceEmpId(currentUser.id);
          setIsComplianceOpen(true);
        }}
        onLogout={handleLogout}
        onResetSession={handleResetSession}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Tab 1: Employee Growth Hub */}
        {activeTab === 'employee' && (
          <EmployeeGrowthHub
            user={currentUser}
            appraisalRecord={currentAppraisal}
            evaluations={employeeEvaluations.length > 0 ? employeeEvaluations : evaluations.slice(0, 3)}
            attendanceRecords={employeeAttendance.length > 0 ? employeeAttendance : MOCK_ATTENDANCE_RECORDS}
            trainingRecommendations={employeeTrainingRecs.length > 0 ? employeeTrainingRecs : trainingRecs.slice(0, 2)}
            coachingNotes={employeeCoachingNotes.length > 0 ? employeeCoachingNotes : coachingNotes}
            annualPlan={currentPlan}
            onEnrollTraining={handleEnrollTraining}
            onOpenSimulator={() => setActiveTab('simulator')}
            onOpenCompliance={() => {
              setComplianceEmpId(currentUser.id);
              setIsComplianceOpen(true);
            }}
            onOpenMatrix={() => setActiveTab('matrix')}
          />
        )}

        {/* Tab 2: Department Manager Hub */}
        {activeTab === 'manager' && (
          <ManagerDashboard
            managerUser={activeManager}
            allManagers={departmentManagers.length > 0 ? departmentManagers : [MOCK_USERS[2]]}
            teamUsers={teamUsers.length > 0 ? teamUsers : users}
            teamAppraisals={appraisals}
            recentEvaluations={evaluations}
            coachingNotes={coachingNotes}
            onOpenQuickEval={(empId) => {
              setQuickEvalEmpId(empId);
              setIsQuickEvalOpen(true);
            }}
            onOpenAddCoaching={(empId) => {
              setCoachingEmpId(empId);
              setIsAddCoachingOpen(true);
            }}
            onSaveEvaluation={handleSaveEvaluation}
            onUpdateAppraisal={handleUpdateAppraisal}
            onOpenComplianceDoc={(empId) => {
              setComplianceEmpId(empId);
              setIsComplianceOpen(true);
            }}
            onViewAsEmployee={(member) => {
              setCurrentUser(member);
              setActiveTab('employee');
              showToast(`Viewing Growth Hub for ${member.fullName}`);
            }}
          />
        )}

        {/* Tab 3: Annual Performance Matrix */}
        {activeTab === 'matrix' && (
          <AnnualPerformanceMatrix
            currentUser={currentUser}
            employeeUser={currentUser.role === 'employee' ? currentUser : (teamUsers[0] || MOCK_USERS[3])}
            plan={currentPlan}
            attendanceRecords={MOCK_ATTENDANCE_RECORDS}
            appraisalRecord={currentAppraisal}
            onSavePlan={handleSaveAnnualPlan}
            onApprovePlan={handleApproveAnnualPlan}
            onFinalAssess={handleFinalAssessAnnualPlan}
          />
        )}

        {/* Tab 4: Professional Certification & AED 15,000 Bonus */}
        {activeTab === 'certifications' && (
          <CertificationBonusPanel
            currentUser={currentUser}
            employeeUser={currentUser.role === 'employee' ? currentUser : (teamUsers[0] || MOCK_USERS[3])}
            certifications={certifications}
            onProposeCertification={handleProposeCertification}
            onApproveCertification={handleApproveCertification}
            onVerifyAndDisburseBonus={handleVerifyAndDisburseBonus}
          />
        )}

        {/* Tab 5: HR & Executive Intelligence Dashboard */}
        {activeTab === 'hr' && (
          <HRIntelligenceDashboard
            companyInfo={MOCK_COMPANY_INFO}
            departments={MOCK_DEPARTMENTS}
            allUsers={users}
            allAppraisals={appraisals}
            skills={MOCK_SKILLS}
            courses={MOCK_TRAINING_COURSES}
            trainingRecommendations={trainingRecs}
            statutoryNotices={MOCK_STATUTORY_NOTICES}
            onOpenComplianceDoc={(empId) => {
              setComplianceEmpId(empId);
              setIsComplianceOpen(true);
            }}
            onOpenSimulator={() => setActiveTab('simulator')}
          />
        )}

        {/* Tab 6: UAE Labor Law Compliance Desk */}
        {activeTab === 'compliance' && (
          <div className="space-y-6">
            <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <h1 className="text-2xl font-bold text-slate-900">
                  UAE Labor Law Compliance & Escalation Desk
                </h1>
                <p className="text-xs text-slate-500 mt-1">
                  MOHRE Governance Standards • UAE Federal Decree-Law No. 33 of 2021
                </p>
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setActiveTab('reports')}
                  className="px-3.5 py-2.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-700 font-semibold text-xs transition-colors cursor-pointer"
                >
                  View Reports Center →
                </button>
                <button
                  onClick={() => {
                    setComplianceEmpId(undefined);
                    setIsComplianceOpen(true);
                  }}
                  className="px-4 py-2.5 rounded-lg bg-rose-700 hover:bg-rose-800 text-white font-semibold text-xs transition-colors self-start md:self-center cursor-pointer"
                >
                  Launch Document Generator
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {MOCK_STATUTORY_NOTICES.map((not) => (
                <div key={not.id} className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono text-slate-400">{not.officialRefCode}</span>
                    <span className={`text-[11px] font-bold px-2 py-0.5 rounded border ${
                      not.tier === 1 
                        ? 'bg-teal-50 text-teal-800 border-teal-200' 
                        : 'bg-amber-50 text-amber-800 border-amber-200'
                    }`}>
                      Tier {not.tier} Escalation
                    </span>
                  </div>
                  <h3 className="text-base font-bold text-slate-900 leading-snug">
                    {not.noticeTitle}
                  </h3>
                  <div className="text-xs text-slate-600">
                    Issued to: <strong>{not.employeeName}</strong> • Supervisor: {not.mentorshipSupervisor}
                  </div>
                  <p className="text-xs text-slate-600 bg-slate-50 p-3 rounded-lg border border-slate-100">
                    "{not.summaryText}"
                  </p>
                  <div className="pt-2 flex items-center justify-between text-xs border-t border-slate-100">
                    <span className="text-slate-400">Timeline: {not.timelineDays} Days</span>
                    <button
                      onClick={() => {
                        setComplianceEmpId(not.employeeId);
                        setIsComplianceOpen(true);
                      }}
                      className="text-xs font-semibold text-rose-700 hover:text-rose-900 cursor-pointer"
                    >
                      View Official Letter →
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Tab 7: Reports Center */}
        {activeTab === 'reports' && (
          <ReportsCenter
            companyInfo={MOCK_COMPANY_INFO}
            currentUser={currentUser}
            allUsers={users}
            departments={MOCK_DEPARTMENTS}
            allAppraisals={appraisals}
            allPlans={annualPlans}
            certifications={certifications}
            statutoryNotices={MOCK_STATUTORY_NOTICES}
            auditLogs={auditLogs}
          />
        )}

        {/* Tab 8: Audit Trail */}
        {activeTab === 'audit' && (
          <AuditTrailView
            auditLogs={auditLogs}
            currentUser={currentUser}
            onLogCustomEvent={(ev) => {
              setAuditLogs((prev) => [ev, ...prev]);
            }}
          />
        )}

        {/* Tab 9: Simulator */}
        {activeTab === 'simulator' && <ScoreSimulator />}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 py-6 text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div>
            <span className="font-bold text-slate-800">Paras Accounting & Auditing Advisory</span>
            <span className="mx-2">•</span>
            <span>Abu Dhabi Global Market (ADGM) & MOHRE Registered Auditing Practice</span>
          </div>
          <div className="flex items-center gap-4 text-slate-400">
            <span>UAE Decree-Law No. 33 of 2021 Compliant</span>
            <span>•</span>
            <span className="tabular-nums">Cycle: Q3-2026</span>
          </div>
        </div>
      </footer>

      {/* Modals */}
      <QuickEvaluationModal
        isOpen={isQuickEvalOpen}
        onClose={() => setIsQuickEvalOpen(false)}
        onSaveEvaluation={handleSaveEvaluation}
        defaultEmployeeId={quickEvalEmpId}
        evaluatorUser={activeManager}
      />

      <AddCoachingModal
        isOpen={isAddCoachingOpen}
        onClose={() => setIsAddCoachingOpen(false)}
        onSaveCoaching={handleSaveCoaching}
        defaultEmployeeId={coachingEmpId}
        authorUser={activeManager}
      />

      <StatutoryComplianceModal
        isOpen={isComplianceOpen}
        onClose={() => setIsComplianceOpen(false)}
        selectedEmployeeId={complianceEmpId}
      />

      {/* Toast Alert */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 bg-slate-900 text-white text-xs font-medium px-4 py-3 rounded-xl shadow-xl flex items-center gap-2.5 animate-in fade-in slide-in-from-bottom-2">
          <CheckCircle2 className="w-4 h-4 text-teal-400 shrink-0" />
          <span>{toastMessage}</span>
        </div>
      )}
    </div>
  );
}
