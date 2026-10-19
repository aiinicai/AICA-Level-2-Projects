export type Role = 'super_admin' | 'hr_manager' | 'department_manager' | 'employee';
export type EmployeeStatus = 'Active' | 'Under_Review' | 'PIP' | 'Terminated';
export type CompletionStatus = 'On-Time' | 'Delayed' | 'Quality_Exceeded' | 'Needs_Revision';
export type AttendanceStatus = 'On-Time' | 'Late_Grace_Period' | 'Late_Unexcused' | 'Absent';
export type PerformanceTier = 'Exceeds' | 'Meets' | 'Needs_Support' | 'Underperforming';
export type ActionPlanStatus = 'Standard' | 'Coaching' | 'PIP_Level_1' | 'PIP_Level_2' | 'Escalation_Review';

export interface User {
  id: string;
  employeeIdCode: string; // e.g. "EMP-0142"
  fullName: string;
  email: string;
  avatarUrl?: string;
  role: Role;
  departmentId: string;
  departmentName: string;
  managerId?: string;
  managerName?: string;
  joiningDate: string; // YYYY-MM-DD
  tenureYears: number;
  currentDesignation: string;
  payGradeLevel: string; // e.g. "Grade L5 - Senior Specialist"
  status: EmployeeStatus;
  officeLocation: string; // e.g. "Al Maryah Tower, Abu Dhabi"
  baseSalaryAED: number;
}

export interface Department {
  id: string;
  name: string;
  headOfDepartmentId: string;
  headName: string;
  annualTDBudgetAED: number;
  allocatedTDBudgetAED: number;
  employeeCount: number;
  code: string;
}

export interface ServiceDeliverableCatalog {
  id: string;
  departmentId: string;
  deliverableName: string;
  category: string;
  basePointValue: number;
  slaHoursExpected: number;
  qualityWeightage: number; // e.g. 1.0 to 1.5
  description: string;
}

export interface TaskEvaluation {
  id: string;
  employeeId: string;
  employeeName: string;
  deliverableId: string;
  deliverableName: string;
  departmentId: string;
  evaluatorId: string;
  evaluatorName: string;
  completionStatus: CompletionStatus;
  pointsAwarded: number;
  taskDeadline: string;
  actualCompletionTimestamp: string;
  slaHoursTurnaround: number;
  feedbackNotes: string;
  evaluatedDate: string;
}

export interface AttendanceRecord {
  id: string;
  employeeId: string;
  date: string; // YYYY-MM-DD
  checkInTime: string; // HH:MM
  status: AttendanceStatus;
  punctualityScore: number; // 0 - 100
}

export interface AppraisalRecord {
  id: string;
  cycleId: string;
  cycleName: string;
  employeeId: string;
  employeeName: string;
  departmentId: string;
  grossServicePoints: number; // 0-100
  punctualityIndex: number; // 0-100
  taskSLAIndex: number; // 0-100
  growthDeltaPct: number; // % change vs previous appraisal, e.g. +8.5%
  tenureYears: number;
  tenureLoyaltyMultiplier: number; // 1.0, 1.05, 1.10, 1.15
  baseScore: number;
  finalWeightedScore: number;
  performanceTier: PerformanceTier;
  actionPlanStatus: ActionPlanStatus;
  consecutiveUnderperformingCycles: number;
  coachingNotes: string[];
  hrApprovalStatus: 'Approved' | 'Pending Review' | 'Flagged';
  lastEvaluationDate: string;
}

export interface SkillItem {
  id: string;
  skillName: string;
  category: string;
  departmentId: string;
  benchmarkScore: number; // 1 - 5
  companyAverage: number; // 1 - 5
}

export interface TrainingCourse {
  id: string;
  title: string;
  provider: string; // e.g. "ADGM Academy", "Abu Dhabi School of Management"
  costPerEmployeeAED: number;
  targetSkillId: string;
  targetSkillName: string;
  durationWeeks: number;
  competencyGain: string;
}

export interface TrainingRecommendation {
  id: string;
  employeeId: string;
  employeeName: string;
  courseId: string;
  courseTitle: string;
  costAED: number;
  recommendedByHR: boolean;
  status: 'Recommended' | 'Enrolled' | 'Completed' | 'Budget_Pending';
  priority: 'High' | 'Medium' | 'Routine';
  reason: string;
  approvedByManager?: boolean;
  escalatedHierarchyApproval?: 'Pending' | 'Approved' | 'Not_Required';
  institutionName?: string;
}

export interface CoachingNote {
  id: string;
  employeeId: string;
  authorId: string;
  authorName: string;
  date: string;
  objective: string;
  constructiveGuidance: string;
  followUpDate: string;
  status: 'In Progress' | 'Accomplished' | 'Follow-up Scheduled';
  skillArea?: string;
  noteText?: string;
}

export interface StatutoryNotice {
  id: string;
  employeeId: string;
  employeeName: string;
  tier: 1 | 2 | 3 | 4;
  noticeTitle: string;
  dateIssued: string;
  statutoryReference: string; // UAE Federal Decree-Law No. 33 of 2021
  summaryText: string;
  actionRequirements: string[];
  mentorshipSupervisor: string;
  timelineDays: number;
  officialRefCode: string;
  status: 'Active' | 'Review_Scheduled' | 'Completed';
}

/**
 * Annual Performance Matrix Setup & Achievement Workflow
 */
export interface AnnualGoalItem {
  id: string;
  title: string;
  category: string;
  weightagePct: number;
  targetDeliverableCount: number;
  actualAchievedCount: number;
  targetSlaHours: number;
  actualAvgSlaHours: number;
  targetQualityScore: number;
  actualQualityScore: number;
  achievementNarrative: string;
  managerAssessmentScore: number; // 0-100
}

export interface AnnualPerformancePlan {
  id: string;
  employeeId: string;
  employeeName: string;
  year: number;
  planStatus: 'Draft' | 'Submitted_To_Manager' | 'Manager_Approved' | 'Achievement_Submitted' | 'Final_Assessed';
  goals: AnnualGoalItem[];
  managerApprovalNotes?: string;
  managerApprovedBy?: string;
  managerApprovedAt?: string;
  assessedScore?: number;
  lastUpdated: string;
}

/**
 * Professional Certification with AED 15,000 Special Bonus
 */
export interface ProfessionalCertification {
  id: string;
  employeeId: string;
  employeeName: string;
  certificationName: string;
  issuingBody: string;
  status: 'Proposed' | 'Manager_Approved' | 'In_Study' | 'Completed_Verified' | 'Bonus_Disbursed';
  bonusAmountAED: number; // 15,000
  bonusPaidDate?: string;
  managerApprovalNotes?: string;
  completionDate?: string;
}

/**
 * Two-Tier 90-Day Improvement Plan System (Under-par annual review)
 */
export interface TwoTierPIPRecord {
  id: string;
  employeeId: string;
  employeeName: string;
  tier: 'Tier_1_90_Day' | 'Tier_2_90_Day_Extended' | 'Statutory_Action';
  startDate: string;
  endDate: string;
  daysRemaining: number;
  supervisorName: string;
  deficiencies: string[];
  milestones: {
    day30Notes: string;
    day30Status: 'Met' | 'In_Progress' | 'Unmet';
    day60Notes: string;
    day60Status: 'Met' | 'In_Progress' | 'Unmet';
    day90Notes: string;
    day90Status: 'Met' | 'In_Progress' | 'Unmet';
  };
  finalOutcome?: 'Successful_Turnaround' | 'Escalate_To_Tier_2' | 'Demotion_Notice' | 'Termination_Notice';
  statutoryReference: string; // UAE Federal Decree-Law No. 33 of 2021
}

/**
 * Enterprise Audit Trail Log Entry for Regulatory Compliance & Accountability
 * Adheres to ADGM FSRA Governance & UAE Federal Decree-Law No. 33/2021 standards
 */
export type AuditActionType = 
  | 'MATRIX_PLAN_SAVED'
  | 'MATRIX_PLAN_APPROVED'
  | 'MATRIX_FINAL_ASSESSED'
  | 'CERTIFICATION_PROPOSED'
  | 'CERTIFICATION_APPROVED'
  | 'BONUS_DISBURSED'
  | 'DELIVERABLE_POINTS_AWARDED'
  | 'APPRAISAL_OVERRIDE_SAVED'
  | 'COACHING_NOTE_LOGGED'
  | 'TRAINING_ENROLLED'
  | 'STATUTORY_PIP_ISSUED'
  | 'PERSONA_SECURITY_LOGIN';

export type AuditCategory = 
  | 'PERFORMANCE_GOVERNANCE'
  | 'FINANCIAL_DISBURSEMENT'
  | 'STATUTORY_COMPLIANCE'
  | 'TRAINING_BUDGET'
  | 'SECURITY_AUTHENTICATION';

export type AuditSeverity = 'INFO' | 'ACTION' | 'CRITICAL' | 'FINANCIAL';

export interface AuditLogEntry {
  id: string; // e.g. "AUD-2026-0812"
  timestamp: string; // ISO 8601 string
  actionType: AuditActionType;
  actionTitle: string;
  category: AuditCategory;
  severity: AuditSeverity;
  actorId: string;
  actorName: string;
  actorRole: Role;
  actorDesignation: string;
  targetEmployeeId?: string;
  targetEmployeeName?: string;
  targetDepartment?: string;
  details: string;
  previousValue?: string;
  newValue?: string;
  ipAddress: string;
  verificationHash: string; // SHA-256 tamper-evident check
  authorizedUnderPolicy: string;
}
