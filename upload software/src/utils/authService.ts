import { AppUser, UserRegistrationInput, UserRole, UserStatus } from '../types/accounting';

const AUTH_USER_STORAGE_KEY = 'non_corp_auth_current_user';
const USERS_BACKUP_STORAGE_KEY = 'non_corp_auth_users_vault';

const DEFAULT_USERS: (AppUser & { password: string })[] = [
  {
    id: 'admin',
    name: 'Priyanka Garg (CA / Partner)',
    email: 'capriyankagarg61@gmail.com',
    password: 'Admin@123',
    role: 'ADMIN',
    status: 'APPROVED',
    createdAt: '2025-04-01T09:00:00.000Z',
    approvedAt: '2025-04-01T09:00:00.000Z',
    approvedBy: 'SYSTEM',
    lastLoginAt: new Date().toISOString(),
  },
  {
    id: 'auditor',
    name: 'Senior Audit Reviewer',
    email: 'audit.team@firm.in',
    password: 'Audit@123',
    role: 'AUDITOR',
    status: 'APPROVED',
    createdAt: '2025-04-01T09:30:00.000Z',
    approvedAt: '2025-04-01T09:30:00.000Z',
    approvedBy: 'admin',
    lastLoginAt: new Date().toISOString(),
  },
];

// Local fallback store
function getLocalUsers(): (AppUser & { password: string })[] {
  try {
    const raw = localStorage.getItem(USERS_BACKUP_STORAGE_KEY);
    if (raw) {
      return JSON.parse(raw);
    }
  } catch (e) {
    console.error('Failed to parse local users:', e);
  }
  localStorage.setItem(USERS_BACKUP_STORAGE_KEY, JSON.stringify(DEFAULT_USERS));
  return DEFAULT_USERS;
}

function saveLocalUsers(users: (AppUser & { password: string })[]) {
  try {
    localStorage.setItem(USERS_BACKUP_STORAGE_KEY, JSON.stringify(users));
  } catch (e) {
    console.error('Failed to save local users:', e);
  }
}

export const authService = {
  getCurrentUser(): AppUser | null {
    try {
      const raw = localStorage.getItem(AUTH_USER_STORAGE_KEY);
      if (raw) {
        return JSON.parse(raw);
      }
    } catch (e) {
      console.error('Error reading current user:', e);
    }
    return null;
  },

  setCurrentUser(user: AppUser | null): void {
    if (user) {
      localStorage.setItem(AUTH_USER_STORAGE_KEY, JSON.stringify(user));
    } else {
      localStorage.removeItem(AUTH_USER_STORAGE_KEY);
    }
  },

  async login(id: string, password: string): Promise<{ success: boolean; user?: AppUser; error?: string; isPending?: boolean }> {
    const cleanId = id.trim().toLowerCase();
    
    // Try server API first
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: cleanId, password }),
      });
      const data = await res.json();
      if (res.ok && data.success && data.user) {
        this.setCurrentUser(data.user);
        return { success: true, user: data.user };
      }
      if (data.isPending) {
        return { success: false, error: data.error, isPending: true };
      }
      return { success: false, error: data.error || 'Login failed' };
    } catch (apiErr) {
      console.warn('Backend auth unreachable, checking local fallback...', apiErr);
    }

    // Local fallback for client reliability
    const users = getLocalUsers();
    const found = users.find(u => u.id.toLowerCase() === cleanId);
    if (!found || found.password !== password) {
      return { success: false, error: 'Invalid User ID or Password' };
    }
    if (found.status === 'PENDING') {
      return { success: false, error: 'Your User ID is pending approval by the Admin.', isPending: true };
    }
    if (found.status === 'SUSPENDED') {
      return { success: false, error: 'Your account has been suspended by the Admin.' };
    }

    const { password: _, ...safeUser } = found;
    safeUser.lastLoginAt = new Date().toISOString();
    this.setCurrentUser(safeUser);
    return { success: true, user: safeUser };
  },

  async register(input: UserRegistrationInput): Promise<{ success: boolean; message?: string; error?: string }> {
    const cleanId = input.id.trim().toLowerCase();

    // Try server API first
    try {
      const res = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...input, id: cleanId }),
      });
      const data = await res.json();
      if (res.ok && data.success) {
        return { success: true, message: data.message };
      }
      return { success: false, error: data.error || 'Registration failed' };
    } catch (apiErr) {
      console.warn('Backend auth unreachable, using local fallback...', apiErr);
    }

    // Local fallback
    const users = getLocalUsers();
    if (users.some(u => u.id.toLowerCase() === cleanId)) {
      return { success: false, error: 'This User ID is already taken.' };
    }

    const newUser: AppUser & { password: string } = {
      id: cleanId,
      name: input.name.trim(),
      email: input.email.trim(),
      password: input.password,
      role: input.role || 'AUDITOR',
      status: 'PENDING', // Needs admin approval!
      createdAt: new Date().toISOString(),
    };

    users.push(newUser);
    saveLocalUsers(users);

    return {
      success: true,
      message: 'Registration request submitted! Your account is pending Admin approval before you can sign in.',
    };
  },

  async getAllUsers(): Promise<AppUser[]> {
    try {
      const res = await fetch('/api/auth/users');
      const data = await res.json();
      if (res.ok && data.success && Array.isArray(data.users)) {
        return data.users;
      }
    } catch (e) {
      console.warn('Failed to fetch users from server, using local fallback:', e);
    }
    const local = getLocalUsers();
    return local.map(({ password, ...u }) => u);
  },

  async updateUserStatus(userId: string, status: UserStatus, role?: UserRole, adminId?: string): Promise<{ success: boolean; user?: AppUser; error?: string }> {
    const cleanId = userId.toLowerCase();
    try {
      const res = await fetch(`/api/auth/users/${cleanId}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status, role, adminUserId: adminId }),
      });
      const data = await res.json();
      if (res.ok && data.success) {
        return { success: true, user: data.user };
      }
      return { success: false, error: data.error };
    } catch (e) {
      console.warn('Server patch failed, updating local fallback:', e);
    }

    // Local update
    const users = getLocalUsers();
    const user = users.find(u => u.id.toLowerCase() === cleanId);
    if (!user) return { success: false, error: 'User not found' };
    user.status = status;
    if (role) user.role = role;
    if (status === 'APPROVED' && !user.approvedAt) {
      user.approvedAt = new Date().toISOString();
      user.approvedBy = adminId || 'admin';
    }
    saveLocalUsers(users);
    const { password, ...safe } = user;
    return { success: true, user: safe };
  },

  async adminCreateUser(input: UserRegistrationInput, adminId: string): Promise<{ success: boolean; user?: AppUser; error?: string }> {
    const cleanId = input.id.trim().toLowerCase();
    try {
      const res = await fetch('/api/auth/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...input, id: cleanId, adminUserId: adminId }),
      });
      const data = await res.json();
      if (res.ok && data.success) {
        return { success: true, user: data.user };
      }
      return { success: false, error: data.error };
    } catch (e) {
      console.warn('Server create user failed, updating local fallback:', e);
    }

    // Local create
    const users = getLocalUsers();
    if (users.some(u => u.id.toLowerCase() === cleanId)) {
      return { success: false, error: 'User ID already exists' };
    }
    const newUser: AppUser & { password: string } = {
      id: cleanId,
      name: input.name.trim(),
      email: input.email.trim(),
      password: input.password,
      role: input.role || 'AUDITOR',
      status: 'APPROVED',
      createdAt: new Date().toISOString(),
      approvedAt: new Date().toISOString(),
      approvedBy: adminId || 'admin',
    };
    users.push(newUser);
    saveLocalUsers(users);
    const { password, ...safe } = newUser;
    return { success: true, user: safe };
  },

  async deleteUser(userId: string): Promise<{ success: boolean; error?: string }> {
    const cleanId = userId.toLowerCase();
    try {
      const res = await fetch(`/api/auth/users/${cleanId}`, {
        method: 'DELETE',
      });
      const data = await res.json();
      if (res.ok && data.success) {
        return { success: true };
      }
      return { success: false, error: data.error };
    } catch (e) {
      console.warn('Server delete failed, updating local fallback:', e);
    }

    const users = getLocalUsers();
    const idx = users.findIndex(u => u.id.toLowerCase() === cleanId);
    if (idx === -1) return { success: false, error: 'User not found' };
    users.splice(idx, 1);
    saveLocalUsers(users);
    return { success: true };
  },

  logout(): void {
    this.setCurrentUser(null);
  },
};
