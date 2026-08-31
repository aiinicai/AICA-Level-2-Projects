import type { CSSProperties } from 'react';

export type ShipmentType = 'inward' | 'outward';

export type ShipmentStatus =
  | 'draft'
  | 'received_at_reception'
  | 'allocated_to_shelf'
  | 'handed_over_to_staff'
  | 'dispatched'
  | 'in_transit'
  | 'out_for_delivery'
  | 'delivered'
  | 'rto'
  | 'cancelled';

export type ConfidentialityLevel = 'routine' | 'confidential' | 'urgent' | 'original_certificates';

export type UserRole = 'admin_partner' | 'front_desk' | 'audit_staff';

export interface Organization {
  id: string;
  name: string;
  code: string;
  address?: string;
  city?: string;
  createdAt: string;
}

export interface UserProfile {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  department: string;
  designation: string;
  phone: string;
  firmName: string;
  organizationId: string;
  icaiNumber?: string;
}

export interface TrackingEvent {
  id: string;
  timestamp: string;
  status: ShipmentStatus;
  location: string;
  description: string;
  actorName: string;
  actorRole: UserRole;
}

export interface ProofOfDelivery {
  imageUrl?: string;
  signatureUrl?: string;
  signerName?: string;
  relationshipToConsignee?: string;
  deliveredAt: string;
  verifiedBy: string;
  deliveryNotes?: string;
}

export interface InwardShipment {
  id: string;
  organizationId?: string;
  referenceNumber: string; // Internal Serial e.g., INW-2026-0842
  trackingNumber: string;  // Carrier AWB e.g., 7839281920
  carrier: string;         // Blue Dart, DTDC, FedEx, Speed Post, etc.
  senderName: string;      // Client or Third Party
  senderOrganization?: string;
  recipientStaffId: string;
  recipientStaffName: string;
  department: string;
  category: 'Audit Documents' | 'Tax Filing Files' | 'Client Original Deeds' | 'ROC Compliance' | 'General Letter' | 'Cheque / Bank' | 'Other' | string;
  confidentiality: ConfidentialityLevel;
  shelfLocation: string;   // e.g. "Rack A-03", "Partner Vault"
  packageType: 'Envelope' | 'Pouch' | 'Legal Docket' | 'Box' | 'Sealed Envelope';
  parcelPhotoUrl?: string; // Captured parcel photo with date & time stamp
  receivedAt: string;
  status: ShipmentStatus;
  events: TrackingEvent[];
  proofOfDelivery?: ProofOfDelivery;
  notes?: string;
  internalHandoverSignedAt?: string;
  internalHandoverSignedBy?: string;
}

export interface OutwardShipment {
  id: string;
  organizationId?: string;
  referenceNumber: string; // Internal Serial e.g., OUT-2026-0419
  trackingNumber: string;  // Carrier AWB e.g., 9028172641
  carrier: string;
  clientName: string;      // Client being serviced
  clientJobCode: string;   // e.g. "AUD-2026-INFY", "IT-APPEAL-TCS" for CA Cost Allocation
  partnerInCharge: string; // CA Partner
  assignedStaffId: string;
  assignedStaffName: string;
  recipientName: string;   // Addressee Person
  recipientOrganization: string; // Company / IT Dept / ROC / Bank
  recipientAddress: string;
  recipientCity: string;
  recipientPhone?: string;
  recipientEmail?: string;
  department: string;
  contentDescription: string;
  confidentiality: ConfidentialityLevel;
  packageType: 'Envelope' | 'Legal Docket' | 'Carton' | 'Sealed Box';
  weightKg: number;
  courierCost: number;     // INR / currency
  billableToClient: boolean;
  dispatchedAt: string;
  estimatedDeliveryDate: string;
  status: ShipmentStatus;
  events: TrackingEvent[];
  proofOfDelivery?: ProofOfDelivery;
  notes?: string;
}

export type ThemeStyle = 'light' | 'navy' | 'emerald' | 'sapphire' | 'amber' | 'nordic';

export interface AppThemeConfig {
  id: ThemeStyle;
  name: string;
  description: string;
  isLight?: boolean;
  pageBg: string;
  pageStyle: CSSProperties;
  cardBg: string;
  cardBorder: string;
  cardHover: string;
  headerBg: string;
  subCardBg: string;
  inputBg: string;
  inputBorder: string;
  tableHeaderBg: string;
  tableRowHover: string;
  textPrimary: string;
  textSecondary: string;
  textMuted: string;
  textAccent: string;
  primaryColor: string;
  secondaryColor: string;
  accentColor: string;
  accentHover: string;
  primaryBtn: string;
  secondaryBtn: string;
  activeTab: string;
  badgeBg: string;
  badgeText: string;
  borderAccent: string;
  ringColor: string;
  gradientFrom: string;
  gradientTo: string;
  accentGlow: string;
}

export type IconConcept =
  | 'parceldesk_official'
  | 'dynamic_cube'
  | 'beacon_pin'
  | 'monogram_p'
  | 'flow_arrows'
  | 'shield_vault'
  | 'origami_wing';

export interface NotificationLog {
  id: string;
  organizationId?: string;
  timestamp: string;
  recipient: string;
  channel: 'WhatsApp' | 'SMS' | 'Email' | 'In-App';
  type: 'Inward Arrived' | 'Outward Dispatched' | 'POD Delivered' | 'Urgent Handover' | 'Account Created';
  referenceNumber: string;
  trackingNumber: string;
  message: string;
  status: 'Sent' | 'Delivered' | 'Read';
}
