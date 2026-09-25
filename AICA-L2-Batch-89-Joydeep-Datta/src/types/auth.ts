export type UserRole = 'admin' | 'employee';

export interface UserSession {
  role: UserRole;
  email: string;
  name: string;
  employeeCode?: string;
}
