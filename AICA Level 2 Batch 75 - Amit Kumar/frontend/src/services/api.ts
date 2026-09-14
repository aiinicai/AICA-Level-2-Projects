import type { Client, User, AuthResponse } from "../types";

const rawApiUrl = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const cleanBaseUrl = rawApiUrl.replace(/\/$/, "");
export const API_BASE = cleanBaseUrl.endsWith("/api") ? cleanBaseUrl : `${cleanBaseUrl}/api`;



export function getAuthToken(): string | null {
  return localStorage.getItem("sw_auth_token");
}

export function setAuthToken(token: string) {
  localStorage.setItem("sw_auth_token", token);
}

export function clearAuthToken() {
  localStorage.removeItem("sw_auth_token");
  localStorage.removeItem("sw_auth_user");
}

export function getAuthHeaders(): HeadersInit {
  const token = getAuthToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

export async function login(login_id: string, password: string): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ login_id, password }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Login failed");
  }
  const data: AuthResponse = await res.json();
  setAuthToken(data.access_token);
  localStorage.setItem("sw_auth_user", JSON.stringify(data.user));
  return data;
}

export async function logout(): Promise<void> {
  try {
    await fetch(`${API_BASE}/auth/logout`, {
      method: "POST",
      headers: getAuthHeaders(),
    });
  } catch (e) {
    console.error("Logout API call error:", e);
  } finally {
    clearAuthToken();
  }
}

export async function fetchCurrentUser(): Promise<User> {
  const res = await fetch(`${API_BASE}/auth/me`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error("Unauthorized");
  return res.json();
}

export async function changePassword(old_password: string, new_password: string) {
  const res = await fetch(`${API_BASE}/auth/change-password`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ old_password, new_password }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Password change failed");
  }
  return res.json();
}

export async function resetPassword(user_id: number, new_password: string) {
  const res = await fetch(`${API_BASE}/auth/reset-password`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ user_id, new_password }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Password reset failed");
  }
  return res.json();
}

export async function fetchUsers(): Promise<User[]> {
  const res = await fetch(`${API_BASE}/users`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch user list");
  return res.json();
}

export async function createUser(data: Partial<User> & { password: string }): Promise<User> {
  const res = await fetch(`${API_BASE}/users`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "User creation failed");
  }
  return res.json();
}

export async function updateUser(user_id: number, data: Partial<User>): Promise<User> {
  const res = await fetch(`${API_BASE}/users/${user_id}`, {
    method: "PUT",
    headers: getAuthHeaders(),
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "User update failed");
  }
  return res.json();
}

export async function deleteUser(user_id: number) {
  const res = await fetch(`${API_BASE}/users/${user_id}`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "User deletion failed");
  }
  return res.json();
}

export async function fetchClients(): Promise<Client[]> {
  const res = await fetch(`${API_BASE}/clients`, { headers: getAuthHeaders() });
  return res.json();
}

export async function createClient(data: Partial<Client>): Promise<Client> {
  const res = await fetch(`${API_BASE}/clients`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(data),
  });
  return res.json();
}

export async function updateClient(_clientId: number, data: Partial<Client>): Promise<Client> {
  return createClient(data);
}


export async function loadSampleData(clientId: number) {
  const res = await fetch(`${API_BASE}/clients/${clientId}/load-sample-data`, {
    method: "POST",
  });
  return res.json();
}

export async function uploadExcelFile(
  type: string,
  clientId: number,
  file: File
) {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/upload/${type}/${clientId}`, {
    method: "POST",
    body: formData,
  });
  return res.json();
}

export const uploadScheduleFile = uploadExcelFile;

export function getSampleTemplateUrl(type: string) {
  return `${API_BASE}/sample-templates/${type}`;
}

export async function fetchMapping(clientId: number) {
  const res = await fetch(`${API_BASE}/mapping/${clientId}`);
  return res.json();
}

export async function autoMap(clientId: number) {
  const res = await fetch(`${API_BASE}/mapping/auto-map/${clientId}`, {
    method: "POST",
  });
  return res.json();
}

export async function updateMappingItem(data: {
  id: number;
  final_classification: string;
  financial_statement: string;
  note_number: string;
  current_non_current: string;
}) {
  const res = await fetch(`${API_BASE}/mapping/update`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return res.json();
}

export async function suggestMapping(ledgerName: string, originalGroup: string = "") {
  return testRule(ledgerName, originalGroup);
}

export async function createMappingRule(data: any) {
  const res = await fetch(`${API_BASE}/rules`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return res.json();
}

export async function fetchRules() {
  const res = await fetch(`${API_BASE}/rules`);
  return res.json();
}

export async function testRule(ledgerName: string, originalGroup: string = "") {
  const formData = new FormData();
  formData.append("ledger_name", ledgerName);
  formData.append("original_group", originalGroup);
  const res = await fetch(`${API_BASE}/rules/test`, {
    method: "POST",
    body: formData,
  });
  return res.json();
}

export async function fetchFinancialStatements(clientId: number) {
  const res = await fetch(`${API_BASE}/financial-statements/${clientId}`);
  return res.json();
}

export async function fetchNotes(clientId: number) {
  const res = await fetch(`${API_BASE}/notes/${clientId}`);
  return res.json();
}

export async function updateNote(noteId: number, content: string) {
  const res = await fetch(`${API_BASE}/notes/${noteId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
  return res.json();
}

export async function resetNote(noteId: number) {
  const res = await fetch(`${API_BASE}/notes/${noteId}/reset`, {
    method: "POST",
  });
  return res.json();
}

export async function regenerateNotes(clientId: number) {
  const res = await fetch(`${API_BASE}/notes/${clientId}/regenerate`, {
    method: "POST",
  });
  return res.json();
}

export async function refreshFinancialStatements(clientId: number) {
  const res = await fetch(`${API_BASE}/financial-statements/${clientId}/refresh`, {
    method: "POST",
  });
  return res.json();
}


export async function fetchAccountingPolicies(clientId: number) {
  const res = await fetch(`${API_BASE}/accounting-policies/${clientId}`);
  return res.json();
}

export async function updateAccountingPolicy(policyId: number, content: string) {
  const res = await fetch(`${API_BASE}/accounting-policies/${policyId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
  return res.json();
}

export async function resetAccountingPolicy(policyId: number) {
  const res = await fetch(`${API_BASE}/accounting-policies/${policyId}/reset`, {
    method: "POST",
  });
  return res.json();
}

export async function toggleAccountingPolicyApplicability(policyId: number, isApplicable: boolean) {
  const res = await fetch(`${API_BASE}/accounting-policies/${policyId}/toggle-applicability`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ is_applicable: isApplicable }),
  });
  return res.json();
}

export async function fetchCashFlow(clientId: number) {
  const res = await fetch(`${API_BASE}/cash-flow/${clientId}`);
  return res.json();
}

export async function fetchCashFlowAdjustments(clientId: number) {
  const res = await fetch(`${API_BASE}/cash-flow/adjustments/${clientId}`);
  return res.json();
}

export async function createCashFlowAdjustment(clientId: number, data: any) {
  const res = await fetch(`${API_BASE}/cash-flow/adjustments/${clientId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return res.json();
}

export async function fetchCashFlowValidations(clientId: number) {
  const res = await fetch(`${API_BASE}/cash-flow/validations/${clientId}`);
  return res.json();
}

export async function fetchSchedules(clientId: number) {
  const res = await fetch(`${API_BASE}/schedules/${clientId}`);
  return res.json();
}

export async function fetchRatios(clientId: number) {
  const res = await fetch(`${API_BASE}/ratios/${clientId}`);
  return res.json();
}

export async function fetchValidations(clientId: number) {
  const res = await fetch(`${API_BASE}/validations/${clientId}`);
  return res.json();
}

export function getExportExcelUrl(clientId: number) {
  return `${API_BASE}/export/excel/${clientId}`;
}

export function getExportPdfUrl(clientId: number) {
  return `${API_BASE}/export/pdf/${clientId}`;
}

export function getExportWordUrl(clientId: number) {
  return `${API_BASE}/export/word/${clientId}`;
}

export const SCHEDULE_III_CLASSIFICATIONS = [
  // Balance Sheet
  { name: "Share Capital", statement: "Balance Sheet", note: "1.1", type: "Shareholders' Funds" },
  { name: "Reserves and Surplus", statement: "Balance Sheet", note: "1.2", type: "Shareholders' Funds" },
  { name: "Long-term Borrowings", statement: "Balance Sheet", note: "2.1", type: "Non-Current" },
  { name: "Long-term Provisions", statement: "Balance Sheet", note: "2.2", type: "Non-Current" },
  { name: "Short-term Borrowings", statement: "Balance Sheet", note: "3.1", type: "Current" },
  { name: "Trade Payables", statement: "Balance Sheet", note: "3.2", type: "Current" },
  { name: "Other Current Liabilities", statement: "Balance Sheet", note: "3.3", type: "Current" },
  { name: "Short-term Provisions", statement: "Balance Sheet", note: "3.4", type: "Current" },
  { name: "Property, Plant and Equipment", statement: "Balance Sheet", note: "4.1", type: "Non-Current" },
  { name: "Capital Work-in-Progress", statement: "Balance Sheet", note: "4.2", type: "Non-Current" },
  { name: "Non-current Investments", statement: "Balance Sheet", note: "4.3", type: "Non-Current" },
  { name: "Long-term Loans and Advances", statement: "Balance Sheet", note: "4.4", type: "Non-Current" },
  { name: "Inventories", statement: "Balance Sheet", note: "5.1", type: "Current" },
  { name: "Trade Receivables", statement: "Balance Sheet", note: "5.2", type: "Current" },
  { name: "Cash and Bank Balances", statement: "Balance Sheet", note: "5.3", type: "Current" },
  { name: "Short-term Loans and Advances", statement: "Balance Sheet", note: "5.4", type: "Current" },
  
  // Profit & Loss
  { name: "Revenue from Operations", statement: "Profit & Loss", note: "6.1", type: "P&L Income" },
  { name: "Other Income", statement: "Profit & Loss", note: "6.2", type: "P&L Income" },
  { name: "Cost of Materials Consumed", statement: "Profit & Loss", note: "7.1", type: "P&L Expense" },
  { name: "Purchases of Stock-in-Trade", statement: "Profit & Loss", note: "7.1", type: "P&L Expense" },
  { name: "Changes in Inventories", statement: "Profit & Loss", note: "7.1", type: "P&L Expense" },
  { name: "Employee Benefit Expenses", statement: "Profit & Loss", note: "7.2", type: "P&L Expense" },
  { name: "Finance Costs", statement: "Profit & Loss", note: "7.3", type: "P&L Expense" },
  { name: "Depreciation and Amortisation Expense", statement: "Profit & Loss", note: "7.4", type: "P&L Expense" },
  { name: "Other Expenses", statement: "Profit & Loss", note: "7.5", type: "P&L Expense" },
  { name: "Tax Expense", statement: "Profit & Loss", note: "7.6", type: "P&L Tax" },
];

export const api = {
  login,
  logout,
  fetchCurrentUser,
  changePassword,
  resetPassword,
  fetchUsers,
  createUser,
  updateUser,
  deleteUser,
  fetchClients,
  createClient,
  updateClient,
  loadSampleData,
  uploadExcelFile,
  uploadScheduleFile,
  getSampleTemplateUrl,
  fetchMapping,
  autoMap,
  updateMappingItem,
  suggestMapping,
  createMappingRule,
  fetchRules,
  testRule,
  saveRule: createMappingRule,
  fetchFinancialStatements,
  getFinancialStatements: fetchFinancialStatements,
  fetchNotes,
  updateNote,
  resetNote,
  regenerateNotes,
  refreshFinancialStatements,
  fetchAccountingPolicies,
  updateAccountingPolicy,
  resetAccountingPolicy,
  toggleAccountingPolicyApplicability,
  fetchCashFlow,
  fetchCashFlowAdjustments,
  createCashFlowAdjustment,
  fetchCashFlowValidations,
  fetchSchedules,
  fetchRatios,
  getRatios: fetchRatios,
  fetchValidations,
  getValidations: fetchValidations,
  getTrialBalance: fetchMapping,
  getClassifications: async () => ({ classifications: SCHEDULE_III_CLASSIFICATIONS.map(c => c.name) }),
  saveMapping: async (id: number, mapping: any) => updateMappingItem({ id, ...mapping }),
  getExportExcelUrl,
  getExportPdfUrl,
  getExportWordUrl,
};

export default api;

