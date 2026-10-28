export type UserRole = 'candidate' | 'jury' | 'guest';

export interface UserSession {
  role: UserRole;
  name: string;
  membershipNo?: string;
  email: string;
  title: string;
  avatarInitials: string;
  authenticated: boolean;
  loginTime: string;
}

export interface JuryScoreDimension {
  id: string;
  title: string;
  category: string;
  maxScore: number;
  currentScore: number;
  weightage: string;
  rubricGuidelines: string[];
  notes?: string;
}

export interface JuryEvaluationData {
  evaluatorName: string;
  evaluatorDesignation: string;
  candidateName: string;
  candidateMembershipNo: string;
  projectTitle: string;
  evaluationDate: string;
  dimensions: JuryScoreDimension[];
  overallComments: string;
  verdict: 'Recommended with Distinction' | 'Recommended' | 'Conditional' | 'Under Review';
}
