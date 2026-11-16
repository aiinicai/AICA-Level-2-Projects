import type { EpochMs } from './common.js';
import type { DraStatus, EducationEntry, EmploymentEntry } from './candidate.js';

export type ResumeTemplateId = 'classic' | 'modern' | 'experience' | 'compact';

export interface ResumeDoc {
  id: string;
  uid: string;
  templateId: ResumeTemplateId;
  headline: string;
  summary: string;
  fullName: string;
  phone: string;
  email?: string;
  locationCity: string;
  locationState: string;
  draStatus: DraStatus;
  draCertificateNumber?: string;
  draIssuer?: string;
  skills: string[];
  education: EducationEntry[];
  workExperience: EmploymentEntry[];
  languages: string[];
  productsHandled?: string[];
  bucketsHandled?: string[];
  updatedAt: EpochMs;
}
