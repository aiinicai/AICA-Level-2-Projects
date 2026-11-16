import type { LocalizedText, EpochMs } from './common.js';

/** cms_public/site - public read; written by owner admin / cms.manage. */
export interface SiteConfig {
  operatorName: string;                 // initial: "VRS Corporate Solutions"
  contact: { addressLines: string[]; phone?: string; whatsapp?: string; supportEmail?: string };
  maintenanceMode: { enabled: boolean; message: LocalizedText };
  banners: { id: string; text: LocalizedText; link?: string; active: boolean }[];
  announcements: { id: string; text: LocalizedText; from?: string; to?: string }[];
  features: { referralTracking: 'on' | 'paused' | 'off'; aiResume: boolean; registrationOpen: boolean };
  updatedAt: EpochMs;
}

/** settings_private/contact - staff-only. Destination inbox never exposed publicly. */
export interface PrivateContactSettings { destinationEmail: string; updatedAt: EpochMs }

/** settings_private/ai - no secrets here. API key lives only in Secret Manager. */
export interface AiSettings {
  enabled: boolean;
  provider: 'gemini' | (string & {});
  model: string;                     // must be in approvedModels
  approvedModels: string[];
  dailyRequestLimit: number;
  perCandidateDailyLimit: number;
  updatedAt: EpochMs;
}

/** institutes/{id} */
export interface InstituteListing {
  id: string; name: string; city: string; stateCode: string;
  website?: string; contactPhone?: string; contactEmail?: string; logoPath?: string;
  listingType: 'owner_preferred' | 'listed';
  /** Only show an accreditation claim when verified against an official source. */
  officialAccreditation?: { status: 'verified_accredited' | 'not_verified'; verifiedOn?: string; sourceUrl?: string };
  listingNotes?: string;
  published: boolean;
}

/** contact_messages/{id} - submitted via Cloud Function, read by owner admin */
export interface ContactMessage {
  messageId: string;
  name: string;
  email: string;
  phone: string;
  category: 'candidate_inquiry' | 'employer_hiring' | 'institute_listing' | 'verification_query' | 'grievance_feedback';
  subject: string;
  message: string;
  status: 'unread' | 'in_progress' | 'resolved';
  createdAt: EpochMs;
  staffNotes?: string;
  resolvedAt?: EpochMs;
  resolvedBy?: string;
}

