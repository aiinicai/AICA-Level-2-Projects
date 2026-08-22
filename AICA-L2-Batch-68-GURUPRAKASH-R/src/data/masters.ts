/** Reference master values used by the Client and Engagement forms. */

export const INDUSTRIES = [
  "Auto Components",
  "Industrial Engineering",
  "Textiles",
  "Pharmaceuticals",
  "Information Technology",
  "Logistics",
  "Food Processing",
  "Construction and Infrastructure",
  "Financial Services",
  "Other",
] as const;

export const ENTITY_TYPES = [
  "Private Limited Company",
  "Public Limited Company",
  "Limited Liability Partnership",
  "Partnership Firm",
  "Proprietorship",
  "Trust",
  "Society",
  "Branch of Foreign Company",
] as const;

export const FINANCIAL_YEAR_ENDINGS = ["31 March", "30 June", "30 September", "31 December"] as const;

export const INDIAN_STATES = [
  "Tamil Nadu",
  "Karnataka",
  "Kerala",
  "Andhra Pradesh",
  "Telangana",
  "Maharashtra",
  "Gujarat",
  "Delhi",
  "West Bengal",
  "Other",
] as const;

export const PAN_PATTERN = /^[A-Z]{5}[0-9]{4}[A-Z]$/;
export const GSTIN_PATTERN = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]Z[0-9A-Z]$/;
export const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
/** Reasonable Indian or international mobile format. */
export const MOBILE_PATTERN = /^\+?[0-9][0-9\s-]{7,17}[0-9]$/;
