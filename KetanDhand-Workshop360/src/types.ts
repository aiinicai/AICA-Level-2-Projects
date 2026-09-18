export type UserRole = "owner" | "shopkeeper" | "mechanic";
export type UserStatus = "approved" | "pending" | "rejected" | "deactivated";

export interface User {
  id: string;
  name: string;
  phone: string;
  email?: string;
  role: UserRole;
  status: UserStatus;
  createdAt: string;
}

export interface RepairItem {
  id: string;
  name: string;
  quantity: number;
  rate: number;
  addedBy: "mechanic" | "owner";
  addedByName: string;
  timestamp: string;
}

export interface AuditLog {
  id: string;
  timestamp: string;
  userName: string;
  userRole: string;
  action: string;
  details: string;
}

export type RepairStatus = "repairing" | "ready_for_billing" | "completed";

export interface Repair {
  id: string;
  repairNo: string;
  bikeRegistration: string;
  bikeModel: string;
  customerName?: string;
  customerPhone?: string;
  mechanicId: string;
  mechanicName: string;
  startTime: string;
  completionTime?: string;
  status: RepairStatus;
  items: RepairItem[];
  labourCharges: number;
  discount: number;
  taxRate: number;
  auditTrail: AuditLog[];
  createdAt: string;
}

export interface AnalyticsData {
  returningBikes: { reg: string; count: number }[];
  topProducts: { name: string; count: number }[];
  topBrands: { brand: string; count: number }[];
  repairsByMechanic: { name: string; count: number }[];
  currentWorkload: { name: string; count: number }[];
  topModels: { model: string; count: number }[];
  avgCompletionTimeMinutes: number;
  totalRepairs: number;
}
