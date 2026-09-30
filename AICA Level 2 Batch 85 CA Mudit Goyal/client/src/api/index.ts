import axios from 'axios';

// In development CRA's proxy forwards /api → localhost:5100. In a deployment
// the API lives on its own origin, named by REACT_APP_API_URL.
const BASE_URL = process.env.REACT_APP_API_URL ? `${process.env.REACT_APP_API_URL}/api` : '/api';

export const api = axios.create({ baseURL: BASE_URL });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// A 401 means the token is gone or expired — clear it and go back to the login
// screen rather than leaving the user on a page that cannot load anything.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      if (window.location.pathname !== '/login') window.location.replace('/login');
    }
    return Promise.reject(error);
  },
);

// ── Types ───────────────────────────────────────────────────────────────────

export type TaxType = 'CGST_SGST' | 'IGST' | 'NONE';
export type InvoiceStatus = 'DRAFT' | 'SENT' | 'PARTIALLY_PAID' | 'PAID' | 'CANCELLED';
export type PaymentMode = 'CASH' | 'BANK' | 'CHEQUE' | 'UPI' | 'OTHER';
export type AttendanceStatus = 'PRESENT' | 'ABSENT' | 'HALF_DAY' | 'WFH' | 'ON_LEAVE';

export interface LineItem {
  id?: number;
  slNo?: number;
  description: string;
  hsnSac?: string | null;
  quantity: number | string;
  rate: number | string;
  amount?: number | string;
}

export interface Payment {
  id: number;
  paymentDate: string;
  amount: string;
  mode: PaymentMode;
  reference: string | null;
  notes: string | null;
}

export interface Invoice {
  id: number;
  invoiceNumber: string;
  clientName: string;
  clientGstin: string | null;
  clientAddress: string | null;
  clientState: string | null;
  clientEmail: string | null;
  invoiceDate: string;
  dueDate: string | null;
  amount: string;
  taxType: TaxType;
  cgstRate: string | null;
  sgstRate: string | null;
  igstRate: string | null;
  cgstAmount: string | null;
  sgstAmount: string | null;
  igstAmount: string | null;
  totalAmount: string;
  paidAmount: string;
  status: InvoiceStatus;
  notes: string | null;
  lineItems: LineItem[];
  payments: Payment[];
  createdBy?: { id: number; staffName: string } | null;
}

export interface InvoiceListResponse {
  invoices: Invoice[];
  summary: { count: number; billed: number; collected: number; outstanding: number };
}

export interface Staff {
  id: number;
  staffName: string;
  email: string;
  phone: string | null;
  designation: string | null;
  joiningDate: string | null;
  isActive: boolean;
  user?: { id: number; email: string; role: string } | null;
}

export interface Punch {
  id: number;
  direction: 'IN' | 'OUT';
  punchedAt: string;
  latitude: string | null;
  longitude: string | null;
  locationAccuracy: string | null;
  notes: string | null;
}

export interface PunchDay {
  date: string;
  punches: Punch[];
  firstIn: string | null;
  lastOut: string | null;
  workedMinutes: number;
  nextDirection: 'IN' | 'OUT';
}

export interface RegisterRow {
  staffId: number;
  staffName: string;
  designation: string | null;
  status: AttendanceStatus;
  checkedInAt: string | null;
  checkOutAt: string | null;
  workedMinutes: number;
  punchCount: number;
  notes: string | null;
}

export interface MonthlyAttendance {
  year: number;
  month: number;
  staffId: number;
  days: Array<{
    date: string;
    status: AttendanceStatus;
    checkedInAt: string | null;
    checkOutAt: string | null;
    workedMinutes: number;
    punches: Punch[];
    notes: string | null;
  }>;
  summary: {
    daysPresent: number;
    daysRecorded: number;
    onLeave: number;
    workedMinutes: number;
    workedHours: number;
  };
}

export interface Settings {
  id: number;
  firmName: string;
  firmAddress: string;
  firmGstin: string;
  firmEmail: string;
  firmPhone: string;
  invoicePrefix: string;
  defaultTaxType: TaxType;
  defaultGstRate: string;
  defaultPaymentTermDays: number;
  updatedAt: string;
}

export interface DashboardData {
  date: string;
  invoicing: {
    billedThisMonth: number;
    collectedThisMonth: number;
    outstanding: number;
    overdue: number;
    openCount: number;
  };
  attendance: { activeStaff: number; presentToday: number; absentToday: number; hoursToday: number };
  recentInvoices: Array<{
    id: number;
    invoiceNumber: string;
    clientName: string;
    totalAmount: string;
    paidAmount: string;
    status: InvoiceStatus;
    invoiceDate: string;
  }>;
}

// ── Endpoints ───────────────────────────────────────────────────────────────

export const login = (email: string, password: string) => api.post('/auth/login', { email, password });
export const getProfile = () => api.get('/auth/profile');
export const changePassword = (currentPassword: string, newPassword: string) =>
  api.post('/auth/change-password', { currentPassword, newPassword });

export const getStaff = () => api.get<Staff[]>('/staff');
export const createStaff = (data: Record<string, unknown>) => api.post<Staff>('/staff', data);
export const updateStaff = (id: number, data: Record<string, unknown>) => api.put<Staff>(`/staff/${id}`, data);
export const toggleStaffActive = (id: number) => api.put<Staff>(`/staff/${id}/toggle-active`);
export const resetStaffPassword = (id: number, newPassword: string) =>
  api.post(`/staff/${id}/reset-password`, { newPassword });

export const getInvoices = (params?: Record<string, string | undefined>) =>
  api.get<InvoiceListResponse>('/invoices', { params });
export const getInvoice = (id: number) => api.get<Invoice>(`/invoices/${id}`);
export const createInvoice = (data: Record<string, unknown>) => api.post<Invoice>('/invoices', data);
export const updateInvoice = (id: number, data: Record<string, unknown>) => api.put<Invoice>(`/invoices/${id}`, data);
export const issueInvoice = (id: number) => api.post<Invoice>(`/invoices/${id}/issue`);
export const cancelInvoice = (id: number) => api.post<Invoice>(`/invoices/${id}/cancel`);
export const deleteInvoice = (id: number) => api.delete(`/invoices/${id}`);
export const addPayment = (id: number, data: Record<string, unknown>) =>
  api.post<Invoice>(`/invoices/${id}/payments`, data);
export const deletePayment = (paymentId: number) => api.delete<Invoice>(`/invoices/payments/${paymentId}`);

export const getPunches = (params?: { staffId?: number; date?: string }) =>
  api.get<PunchDay>('/attendance/punches', { params });
export const recordPunch = (data: Record<string, unknown>) => api.post<PunchDay & { direction: 'IN' | 'OUT' }>('/attendance/punch', data);
export const getRegister = (date: string) =>
  api.get<{ date: string; rows: RegisterRow[]; summary: Record<string, number> }>('/attendance/register', {
    params: { date },
  });
export const getMonthlyAttendance = (params: { year: number; month: number; staffId?: number }) =>
  api.get<MonthlyAttendance>('/attendance/monthly', { params });
export const markAttendance = (data: Record<string, unknown>) => api.post('/attendance/mark', data);

export const getDashboard = () => api.get<DashboardData>('/dashboard');

export const getSettings = () => api.get<Settings>('/settings');
export const updateSettings = (data: Record<string, unknown>) => api.put<Settings>('/settings', data);
