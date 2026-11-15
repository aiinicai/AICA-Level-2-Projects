import type { EpochMs, LanguageCode, AuditStamp } from './common.js';

/** Release-one occupation. New categories (e.g. chartered_accountant) are added as sub-profiles, not new collections. */
export type OccupationKey = 'collections' | 'chartered_accountant' | (string & {});

export type DraStatus = 'certified' | 'training_in_progress' | 'result_awaited' | 'not_certified';

export type CollectionRole =
  | 'field_collection'
  | 'telecalling'
  | 'backend'
  | 'team_leader'
  | 'supervisor'
  | 'manager'
  | 'regional_manager'
  | 'zonal_head'
  | 'state_head'
  | 'national_head'
  | 'other';

export type ProfileCompleteness = 'registration_only' | 'partial' | 'complete';
export type AccountStatus = 'active' | 'disabled' | 'closure_requested' | 'closed';

/**
 * candidates/{uid}
 * Core profile. Readable by the candidate and by staff with "profile.basic" access.
 * NEVER contains PAN, DOB, father's name, street address, salary - those are in restricted docs.
 */
export interface CandidateCore extends AuditStamp {
  uid: string;
  candidateId: string;                 // permanent, random, NOT derived from phone/name e.g. VRS-C-7K3M9QX2
  referralCode: string;                // stable, random e.g. R7KM3QX
  fullName: string;
  mobileE164: string;                  // verified by Firebase Auth (copied server-side from token)
  alternateMobile?: string;
  whatsappSameAsMobile: boolean;
  whatsappNumber?: string;
  email?: string;
  emailVerified: boolean;              // separate from mobile verification
  preferredLanguage: LanguageCode;
  location: CurrentLocation;
  draStatus: DraStatus;                // summary only; detail lives in DraQualification
  primaryRole: CollectionRole;
  occupations: OccupationKey[];        // ['collections'] in release one
  experienceType: 'fresher' | 'experienced' | null;
  relevantExperienceMonths: number | null;
  languagesKnown: string[];
  profilePhotoPath?: string;           // private Storage path, never a public URL
  cvPath?: string;
  completeness: ProfileCompleteness;
  accountStatus: AccountStatus;
  source?: AttributionSource;          // how the candidate found us (set once, server-side)
  availabilityConfirmedAt?: EpochMs;
  ageAttestation18Plus: { accepted: true; at: EpochMs; policyVersion: string };
  /** Lowercase search tokens built server-side (name prefixes, city, district) for indexed internal search. */
  searchTokens?: string[];
}

export interface CurrentLocation {
  stateCode: string;            // e.g. "PB"
  district?: string;
  city: string;
  locality?: string;
  pin: string;                  // 6 digits
  pinMismatchFlag?: boolean;    // set when PIN prefix does not match the state (advisory)
  otherCityPendingReview?: boolean;
}

export interface AttributionSource {
  kind: 'referral' | 'campaign' | 'direct' | 'staff_entry';
  referralCode?: string;
  campaign?: string;            // utm_campaign / staff campaign code
  medium?: string;
  firstSeenAt: EpochMs;
}

/** candidates/{uid}/restricted/identity  - candidate + staff with "identity.restricted" grant only. */
export interface RestrictedIdentity {
  fatherName?: string;
  dateOfBirth?: string;          // YYYY-MM-DD
  streetAddress?: string;
  permanentAddress?: string;
  /** Only collected when a recruitment check justifies it. Stored server-side encrypted; client sees masked value. */
  panMasked?: string;            // e.g. XXXXX1234X
  panCollectedReason?: string;
  updatedAt: EpochMs;
}

/** candidates/{uid}/restricted/compensation */
export interface RestrictedCompensation {
  currentMonthlySalaryInr?: number;
  expectedMonthlySalaryInr?: number;
  updatedAt: EpochMs;
}

/** candidates/{uid}/occupations/collections */
export interface CollectionsSubProfile {
  education: EducationEntry[];
  employmentHistory: EmploymentEntry[];
  lendersHandled: string[];
  productsHandled: string[];     // from CMS reference list: credit_card, personal_loan, two_wheeler, auto, agri, cv, ...
  bucketsHandled: string[];      // e.g. X, 1-30, 31-60, 61-90, NPA, write-off
  roleExperience: CollectionRole[];
  geographicExperience: string[]; // state codes / districts
  skills: string[];
  preferences: JobPreferences;
  updatedAt: EpochMs;
}

export interface EducationEntry {
  level: 'below_10' | 'class_10' | 'class_12' | 'diploma' | 'graduate' | 'post_graduate' | 'professional' | 'other';
  board?: string; institution?: string; yearOfPassing?: number;
}

export interface EmploymentEntry {
  id: string;
  employerOrAgency: string;
  designation: string;
  role: CollectionRole;
  startMonth: string;            // YYYY-MM
  endMonth?: string;             // undefined = current
  isCurrent: boolean;
  lenders: string[];
  products: string[];
  buckets: string[];
  locations: string[];
  /** Free text. UI warns: never enter borrower names, account numbers or customer data. */
  summary?: string;
}

export interface JobPreferences {
  preferredRoles: CollectionRole[];
  preferredLocations: { stateCode: string; district?: string; city?: string }[];
  willingToRelocate: boolean;
  workArrangement: ('field' | 'office' | 'remote' | 'hybrid')[];
  employmentTypes: ('full_time' | 'part_time' | 'contract' | 'internship')[];
  joiningAvailability: 'immediate' | '15_days' | '30_days' | '60_days_plus';
  hasTwoWheeler: boolean | null;
  hasDrivingLicence: boolean | null;
  opportunityStatus: 'actively_looking' | 'open' | 'not_looking';
  contactPreferences: { phoneCall: boolean; whatsapp: boolean; sms: boolean; email: boolean };
}
