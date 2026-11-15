import React, { createContext, useContext, useState, useEffect } from 'react';
import { Task, TaskAttachment, StatutoryEvent, PartnerCredentials, MSMEFixedDefaults, UserRole } from '../types';
import { INITIAL_STATUTORY_EVENTS, OFFICE_STAFF_MEMBERS } from '../data/statutoryData';
import { db, auth as firebaseAuth, testConnection, handleFirestoreError, OperationType } from '../lib/firebase';
import { GoogleAuthProvider, signInWithPopup, signOut } from 'firebase/auth';
import { collection, doc, onSnapshot, setDoc, updateDoc, deleteDoc, getDocsFromServer } from 'firebase/firestore';

interface AuthState {
  role: UserRole | null;
  username: string;
}

interface AppContextType {
  auth: AuthState;
  login: (role: UserRole, user: string, pass: string) => { success: boolean; message: string };
  logout: () => void;
  adminCredentials: { username: string; passwordHash: string };
  staffCredentials: { username: string; passwordHash: string };
  updateCredentials: (targetRole: UserRole, newUsername: string, newPass: string) => { success: boolean; message: string };
  requestResetEmail: (email?: string, role?: UserRole) => Promise<{ success: boolean; message: string; code?: string }>;
  requestResetMobile: (mobileOrEmail?: string, role?: UserRole) => Promise<{ success: boolean; message: string; code?: string }>;
  requestAdminResetEmail: (mobileOrEmail?: string) => Promise<{ success: boolean; message: string; code?: string }>;
  requestAdminResetMobile: (mobile?: string) => Promise<{ success: boolean; message: string; code?: string }>;
  verifyAndResetPassword: (targetRole: UserRole, otp: string, newPass: string) => Promise<{ success: boolean; message: string }>;
  verifyGoogleAndResetPassword: (targetRole: UserRole, newPass: string) => Promise<{ success: boolean; message: string }>;
  verifyAndResetAdminPass: (otp: string, newPass: string) => Promise<{ success: boolean; message: string }>;

  // Staff Directory (Admin-only CRUD)
  staffMembers: string[];
  addStaffMember: (name: string) => { success: boolean; message: string };
  editStaffMember: (oldName: string, newName: string) => { success: boolean; message: string };
  deleteStaffMember: (name: string) => { success: boolean; message: string };

  // Tasks
  tasks: Task[];
  addTask: (data: { title: string; description?: string; deadline?: string; isUrgent?: boolean; assignedTo?: string; attachments?: TaskAttachment[] }) => void;
  editTask: (taskId: string, data: { title: string; description?: string; deadline?: string; isUrgent?: boolean; assignedTo?: string; attachments?: TaskAttachment[] }) => void;
  toggleTaskComplete: (taskId: string) => void;
  setTaskTruncated: (taskId: string, truncated: boolean) => void;
  deleteTask: (taskId: string) => { success: boolean; message?: string };
  addAttachmentToTask: (taskId: string, attachment: TaskAttachment) => void;
  syncTasksNow: () => Promise<void>;
  lastSyncedAt: Date | null;

  // Calendar
  calendarEvents: StatutoryEvent[];
  refreshCalendarWithAI: (year?: number, month?: number) => Promise<{ success: boolean; count: number; message: string }>;
  
  // UDIN
  udinPartners: {
    partner1: PartnerCredentials;
    partner2: PartnerCredentials;
  };
  updateUdinCredentials: (partnerKey: 'partner1' | 'partner2', data: Partial<PartnerCredentials>) => void;

  // MSME defaults
  msmeDefaults: MSMEFixedDefaults;
  updateMsmeDefaults: (data: Partial<MSMEFixedDefaults>) => void;

  // Active view tab helper
  currentTab: string;
  setCurrentTab: (tab: string) => void;

  // Firebase status
  isFirebaseConnected: boolean;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

const INITIAL_TASKS: Task[] = [
  {
    id: 'task-1',
    title: 'File GSTR-3B for M/s Aggarwal Steels & Rolling Mills',
    description: 'Verify GSTR-2B input tax credit eligibility and reverse charge liability under Section 9(3).',
    assignedTo: 'Aman Deep Singh',
    deadline: '2026-11-20',
    isUrgent: true,
    completed: false,
    attachments: [
      { name: 'Aggarwal_Sales_Purchase_Oct.pdf', url: '#', type: 'pdf', size: '1.8 MB' }
    ],
    createdAt: '2026-11-05'
  },
  {
    id: 'task-2',
    title: 'Generate UDIN for Tax Audit Report Form 3CA/3CD - Gupta Agro Mills',
    description: 'Enter audited figures in ICAI UDIN portal under Partner 1 account and generate UDIN certificate.',
    assignedTo: 'Harpreet Kaur',
    deadline: '2026-11-12',
    isUrgent: true,
    completed: false,
    attachments: [
      { name: 'Gupta_Agro_Audit_Report.pdf', url: '#', type: 'pdf', size: '3.4 MB' }
    ],
    createdAt: '2026-11-06'
  },
  {
    id: 'task-3',
    title: 'Submit MSME Udyam Application - Sharma Garments & Hosiery',
    description: 'Extract plant & machinery WDV and turnover from 2025-26 ITR acknowledgment; apply via Udyam portal.',
    assignedTo: 'Pooja Sharma',
    deadline: '2026-11-15',
    isUrgent: false,
    completed: true,
    completedAt: '2026-11-08 16:45',
    completedBy: 'Pooja Sharma',
    attachments: [
      { name: 'Sharma_PAN_Aadhaar_Electricity.pdf', url: '#', type: 'pdf', size: '2.1 MB' }
    ],
    createdAt: '2026-11-04'
  },
  {
    id: 'task-4',
    title: 'Prepare AIF (Agri Infra Fund) Project Proposal for Bathinda Cold Storage',
    description: 'Compute 3% interest subvention schedule on ₹1.8 Cr term loan and verify Jamabandi land record.',
    assignedTo: 'Rohit Kumar',
    deadline: '2026-11-25',
    isUrgent: true,
    completed: false,
    attachments: [
      { name: 'Cold_Storage_DPR_Quotation.pdf', url: '#', type: 'pdf', size: '4.8 MB' }
    ],
    createdAt: '2026-11-07'
  },
  {
    id: 'task-5',
    title: 'Reconcile 26AS & AIS for Corporate Client M/s Malwa Cotton Ginners',
    description: 'Cross-verify Section 194Q TDS vs 206C(1H) TCS deducted by buyers before filing Q3 TDS return.',
    assignedTo: 'Manpreet Singh',
    deadline: '2026-11-18',
    isUrgent: false,
    completed: false,
    attachments: [
      { name: 'Malwa_26AS_Statement.pdf', url: '#', type: 'pdf', size: '1.2 MB' }
    ],
    createdAt: '2026-11-08'
  },
  {
    id: 'task-6',
    title: 'Deposit Advance Tax 3rd Installment for Partnership Clients',
    description: 'Challan 280 tax computation for high net worth retail merchants in Punjab.',
    assignedTo: 'All Staff',
    deadline: '2026-12-15',
    isUrgent: false,
    completed: false,
    attachments: [],
    createdAt: '2026-11-09'
  }
];

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Authentication state (Fixed User IDs: ADMIN and STAFF)
  // Always start locked so every app/link open prompts for the password window
  const [auth, setAuth] = useState<AuthState>({ role: null, username: '' });

  // Admin credentials (Fixed User ID: 'ADMIN' - password reset strictly via rishugarg006@gmail.com)
  const [adminCredentials, setAdminCredentials] = useState<{ username: string; passwordHash: string }>(() => {
    const saved = localStorage.getItem('ca_office_admin_creds');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        return { username: 'ADMIN', passwordHash: parsed.passwordHash || '' };
      } catch (e) {}
    }
    return { username: 'ADMIN', passwordHash: '' };
  });

  // Staff credentials (Fixed User ID: 'STAFF' - password reset strictly via rishugarg006@gmail.com)
  const [staffCredentials, setStaffCredentials] = useState<{ username: string; passwordHash: string }>(() => {
    const saved = localStorage.getItem('ca_office_staff_creds');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        return { username: 'STAFF', passwordHash: parsed.passwordHash || '' };
      } catch (e) {}
    }
    return { username: 'STAFF', passwordHash: '' };
  });

  // Staff members directory (managed by Admin only)
  const [staffMembers, setStaffMembers] = useState<string[]>(() => {
    const defaultMembers = OFFICE_STAFF_MEMBERS.filter(m => m !== 'All Staff');
    const saved = localStorage.getItem('ca_office_staff_members');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed)) {
          return parsed.filter((item: unknown): item is string => typeof item === 'string' && item.trim().length > 0 && item !== 'All Staff');
        }
      } catch (e) {}
    }
    return defaultMembers;
  });

  // Tasks
  const [tasks, setTasks] = useState<Task[]>(() => {
    const saved = localStorage.getItem('ca_office_tasks');
    if (saved) {
      try { return JSON.parse(saved); } catch (e) {}
    }
    return INITIAL_TASKS;
  });

  // Calendar: Always merge authoritative INITIAL_STATUTORY_EVENTS with any AI-added events from localStorage
  // so updated National Holidays (e.g., Children's Day) always appear even if old events were cached
  const [calendarEvents, setCalendarEvents] = useState<StatutoryEvent[]>(() => {
    const saved = localStorage.getItem('ca_office_events');
    if (saved) {
      try {
        const parsed: StatutoryEvent[] = JSON.parse(saved);
        if (Array.isArray(parsed)) {
          const baseIds = new Set(INITIAL_STATUTORY_EVENTS.map(e => e.id));
          const baseKeys = new Set(INITIAL_STATUTORY_EVENTS.map(e => `${e.date}::${e.title.toLowerCase()}`));
          const extraEvents = parsed.filter(
            e => e && e.id && e.title && e.date && !baseIds.has(e.id) && !baseKeys.has(`${e.date}::${e.title.toLowerCase()}`)
          );
          return [...INITIAL_STATUTORY_EVENTS, ...extraEvents];
        }
      } catch (e) {}
    }
    return INITIAL_STATUTORY_EVENTS;
  });

  // UDIN Credentials for 2 Partners
  const [udinPartners, setUdinPartners] = useState<{ partner1: PartnerCredentials; partner2: PartnerCredentials }>(() => {
    const saved = localStorage.getItem('ca_office_udin_partners');
    if (saved) {
      try { return JSON.parse(saved); } catch (e) {}
    }
    return {
      partner1: {
        name: 'CA. Rishu Garg (Senior Partner)',
        membershipNo: '524981',
        userId: '524981',
        passwordHash: 'Rishu@UDIN2026!',
        mobile: '98765-43210',
        email: 'rishugargai@gmail.com'
      },
      partner2: {
        name: 'CA. Mohit Singla (Managing Partner)',
        membershipNo: '548210',
        userId: '548210',
        passwordHash: 'Singla@UDIN2026#',
        mobile: '98140-56789',
        email: 'mohit.singla@carg.in'
      }
    };
  });

  // MSME Office defaults
  const [msmeDefaults, setMsmeDefaults] = useState<MSMEFixedDefaults>(() => {
    const saved = localStorage.getItem('ca_office_msme_defaults');
    if (saved) {
      try { return JSON.parse(saved); } catch (e) {}
    }
    return {
      enterpriseType: 'Micro',
      organizationType: 'Proprietorship',
      majorActivity: 'Trading & Services',
      defaultNicCode: '47110 - Retail sale in non-specialised stores',
      officeDistrict: 'Jaitu, Faridkot',
      officeState: 'Punjab',
      defaultIfsc: 'HDFC0000123',
      depreciationMethod: 'Written Down Value (WDV) as per IT Act 1961'
    };
  });

  // Navigation tab
  const [currentTab, setCurrentTab] = useState<string>('tasks');

  // Firebase connection status & sync telemetry
  const [isFirebaseConnected, setIsFirebaseConnected] = useState<boolean>(false);
  const [lastSyncedAt, setLastSyncedAt] = useState<Date | null>(null);

  // Helper to cleanly parse and sort Firestore tasks
  const parseCloudTasks = (docs: any[]): Task[] => {
    const list: Task[] = docs.map(d => {
      const data = d.data();
      return {
        id: d.id,
        title: data.title || '',
        description: data.description || '',
        assignedTo: data.assignedTo || 'All Staff',
        deadline: data.deadline || undefined,
        isUrgent: !!data.isUrgent,
        completed: !!data.completed,
        completedAt: data.completedAt || undefined,
        completedBy: data.completedBy || undefined,
        attachments: data.attachments || [],
        createdAt: data.createdAt || new Date().toISOString().split('T')[0],
        updatedAt: data.updatedAt || undefined
      };
    });
    // Sort consistently by createdAt and ID so mobile and desktop render identical order
    list.sort((a, b) => {
      if (a.createdAt !== b.createdAt) {
        return (b.createdAt || '').localeCompare(a.createdAt || '');
      }
      return b.id.localeCompare(a.id);
    });
    return list;
  };

  // Direct server pull for zero-lag mobile verification
  const syncTasksNow = async () => {
    try {
      const snap = await getDocsFromServer(collection(db, 'tasks'));
      if (!snap.empty) {
        const cloudTasks = parseCloudTasks(snap.docs);
        setTasks(cloudTasks);
        try {
          localStorage.setItem('ca_office_tasks', JSON.stringify(cloudTasks));
        } catch (e) {}
        setIsFirebaseConnected(true);
        setLastSyncedAt(new Date());
      }
    } catch (e) {
      // In offline conditions, keep local tasks
    }
  };

  // Test Firebase connection & sync Firestore tasks and office settings in real-time across devices
  useEffect(() => {
    testConnection().then(connected => {
      setIsFirebaseConnected(connected);
    });

    const tasksCollection = collection(db, 'tasks');

    // 1. Instant real-time push listener
    const unsubscribeTasks = onSnapshot(
      tasksCollection,
      snapshot => {
        if (!snapshot.empty) {
          const cloudTasks = parseCloudTasks(snapshot.docs);
          setTasks(cloudTasks);
          try {
            localStorage.setItem('ca_office_tasks', JSON.stringify(cloudTasks));
          } catch (e) {}
          setIsFirebaseConnected(true);
          setLastSyncedAt(new Date());
        } else {
          // If remote collection is currently empty on initial run, seed once
          const hasSeeded = localStorage.getItem('ca_office_tasks_seeded');
          if (!hasSeeded) {
            localStorage.setItem('ca_office_tasks_seeded', 'true');
            INITIAL_TASKS.forEach(initTask => {
              const cleanInit = {
                id: initTask.id,
                title: initTask.title,
                description: initTask.description || '',
                assignedTo: initTask.assignedTo || 'All Staff',
                deadline: initTask.deadline || '',
                isUrgent: !!initTask.isUrgent,
                completed: !!initTask.completed,
                completedAt: initTask.completedAt || '',
                completedBy: initTask.completedBy || '',
                attachments: initTask.attachments || [],
                createdAt: initTask.createdAt || new Date().toISOString().split('T')[0]
              };
              setDoc(doc(db, 'tasks', initTask.id), cleanInit).catch(() => {});
            });
          }
        }
      },
      error => {
        console.warn('Real-time sync snapshot status:', error?.message);
      }
    );

    // 2. Real-time synchronization of security credentials across mobile and desktop
    const credsDocRef = doc(db, 'officeSettings', 'credentials');
    const unsubscribeCreds = onSnapshot(
      credsDocRef,
      snap => {
        if (snap.exists()) {
          const d = snap.data();
          if (d.adminPasswordHash !== undefined) {
            setAdminCredentials({
              username: 'ADMIN',
              passwordHash: d.adminPasswordHash || ''
            });
          }
          if (d.staffPasswordHash !== undefined) {
            setStaffCredentials({
              username: 'STAFF',
              passwordHash: d.staffPasswordHash || ''
            });
          }
        }
      },
      err => {
        console.warn('Credentials sync status:', err?.message);
      }
    );

    // 2b. Real-time synchronization of staff directory across mobile and desktop
    const staffDocRef = doc(db, 'officeSettings', 'staffDirectory');
    const unsubscribeStaff = onSnapshot(
      staffDocRef,
      snap => {
        if (snap.exists()) {
          const d = snap.data();
          if (Array.isArray(d.staffMembers)) {
            const cleanList = d.staffMembers.filter(
              (item: unknown): item is string => typeof item === 'string' && item.trim().length > 0 && item !== 'All Staff'
            );
            setStaffMembers(cleanList);
            try {
              localStorage.setItem('ca_office_staff_members', JSON.stringify(cleanList));
            } catch (e) {}
          }
        }
      },
      err => {
        console.warn('Staff directory sync status:', err?.message);
      }
    );

    // 3. Resilient background interval for mobile networks where WebSockets may sleep or throttle
    const syncInterval = setInterval(() => {
      syncTasksNow();
    }, 3500);

    // 4. Auto-reconnect when mobile screen wakes up, app tab regains focus, or network changes
    const handleForegroundWake = () => {
      testConnection().then(connected => {
        setIsFirebaseConnected(connected);
      });
      syncTasksNow();
    };

    document.addEventListener('visibilitychange', handleForegroundWake);
    window.addEventListener('focus', handleForegroundWake);
    window.addEventListener('online', handleForegroundWake);

    // Throttled touch refresh for mobile users interacting with the app
    let lastTouch = 0;
    const handleMobileTouch = () => {
      const now = Date.now();
      if (now - lastTouch > 4000) {
        lastTouch = now;
        syncTasksNow();
      }
    };
    window.addEventListener('touchstart', handleMobileTouch, { passive: true });

    return () => {
      unsubscribeTasks();
      unsubscribeCreds();
      unsubscribeStaff();
      clearInterval(syncInterval);
      document.removeEventListener('visibilitychange', handleForegroundWake);
      window.removeEventListener('focus', handleForegroundWake);
      window.removeEventListener('online', handleForegroundWake);
      window.removeEventListener('touchstart', handleMobileTouch);
    };
  }, []);

  // Clear any legacy persisted session so every fresh app open / shared link requires login
  useEffect(() => {
    try {
      localStorage.removeItem('ca_office_auth');
    } catch (e) {}
  }, []);

  useEffect(() => {
    localStorage.setItem('ca_office_admin_creds', JSON.stringify(adminCredentials));
  }, [adminCredentials]);

  useEffect(() => {
    localStorage.setItem('ca_office_staff_creds', JSON.stringify(staffCredentials));
  }, [staffCredentials]);

  useEffect(() => {
    localStorage.setItem('ca_office_tasks', JSON.stringify(tasks));
  }, [tasks]);

  useEffect(() => {
    localStorage.setItem('ca_office_events', JSON.stringify(calendarEvents));
  }, [calendarEvents]);

  useEffect(() => {
    localStorage.setItem('ca_office_udin_partners', JSON.stringify(udinPartners));
  }, [udinPartners]);

  useEffect(() => {
    localStorage.setItem('ca_office_msme_defaults', JSON.stringify(msmeDefaults));
  }, [msmeDefaults]);

  useEffect(() => {
    localStorage.setItem('ca_office_staff_members', JSON.stringify(staffMembers));
  }, [staffMembers]);

  // Auth methods (Fixed User IDs: ADMIN & STAFF; Password reset strictly via rishugarg006@gmail.com)
  const login = (role: UserRole, user: string, pass: string) => {
    const trimmedUser = user.trim().toUpperCase();
    const trimmedPass = pass.trim();

    if (role === 'admin') {
      if (trimmedUser !== 'ADMIN') {
        return { success: false, message: 'Invalid Admin User ID' };
      }
      if (!adminCredentials.passwordHash) {
        return {
          success: false,
          message: 'No password set yet. Please use the Reset Option to set your password via rishugarg006@gmail.com.'
        };
      }
      if (trimmedPass === adminCredentials.passwordHash) {
        setAuth({ role: 'admin', username: 'ADMIN' });
        return { success: true, message: 'Welcome ADMIN' };
      }
      return { success: false, message: 'Invalid password. You can reset it using the Reset Option.' };
    } else {
      if (trimmedUser !== 'STAFF') {
        return { success: false, message: 'Invalid Staff User ID' };
      }
      if (!staffCredentials.passwordHash) {
        return {
          success: false,
          message: 'No password set yet. Please use the Reset Option to set your password via rishugarg006@gmail.com.'
        };
      }
      if (trimmedPass === staffCredentials.passwordHash) {
        setAuth({ role: 'staff', username: 'STAFF' });
        return { success: true, message: 'Welcome STAFF' };
      }
      return { success: false, message: 'Invalid password. You can reset it using the Reset Option.' };
    }
  };

  const logout = () => {
    setAuth({ role: null, username: '' });
  };

  const updateCredentials = (targetRole: UserRole, _newUsername: string, newPass: string) => {
    if (auth.role !== 'admin') {
      return { success: false, message: 'Unauthorized: Only CA Admin can reset credentials.' };
    }
    if (!newPass.trim()) {
      return { success: false, message: 'Password cannot be empty.' };
    }

    if (targetRole === 'admin') {
      const updated = { username: 'ADMIN', passwordHash: newPass.trim() };
      setAdminCredentials(updated);
      localStorage.setItem('ca_office_admin_creds', JSON.stringify(updated));
      const credsDocRef = doc(db, 'officeSettings', 'credentials');
      setDoc(credsDocRef, {
        id: 'credentials',
        adminUsername: 'ADMIN',
        adminPasswordHash: updated.passwordHash,
        staffUsername: 'STAFF',
        staffPasswordHash: staffCredentials.passwordHash
      }, { merge: true }).catch(() => {});
      return { success: true, message: `Admin password updated successfully! User ID is fixed as ADMIN.` };
    } else {
      const updated = { username: 'STAFF', passwordHash: newPass.trim() };
      setStaffCredentials(updated);
      localStorage.setItem('ca_office_staff_creds', JSON.stringify(updated));
      const credsDocRef = doc(db, 'officeSettings', 'credentials');
      setDoc(credsDocRef, {
        id: 'credentials',
        adminUsername: 'ADMIN',
        adminPasswordHash: adminCredentials.passwordHash,
        staffUsername: 'STAFF',
        staffPasswordHash: updated.passwordHash
      }, { merge: true }).catch(() => {});
      return { success: true, message: `Staff password updated successfully! User ID is fixed as STAFF.` };
    }
  };

  // Helper to persist updated password across React state, localStorage, and Firestore
  const persistResetPassword = (targetRole: UserRole, newPass: string) => {
    const cleanPass = newPass.trim();
    const credsDocRef = doc(db, 'officeSettings', 'credentials');
    if (targetRole === 'admin') {
      const updated = { username: 'ADMIN', passwordHash: cleanPass };
      setAdminCredentials(updated);
      localStorage.setItem('ca_office_admin_creds', JSON.stringify(updated));
      setDoc(credsDocRef, {
        id: 'credentials',
        adminUsername: 'ADMIN',
        adminPasswordHash: updated.passwordHash,
        staffUsername: 'STAFF',
        staffPasswordHash: staffCredentials.passwordHash
      }, { merge: true }).catch(() => {});
    } else {
      const updated = { username: 'STAFF', passwordHash: cleanPass };
      setStaffCredentials(updated);
      localStorage.setItem('ca_office_staff_creds', JSON.stringify(updated));
      setDoc(credsDocRef, {
        id: 'credentials',
        adminUsername: 'ADMIN',
        adminPasswordHash: adminCredentials.passwordHash,
        staffUsername: 'STAFF',
        staffPasswordHash: updated.passwordHash
      }, { merge: true }).catch(() => {});
    }
  };

  // Password reset restricted strictly to rishugarg006@gmail.com for BOTH Admin and Staff
  // Never returns or displays any OTP on screen
  const requestResetEmail = async (email: string = 'rishugarg006@gmail.com', role: UserRole = 'admin') => {
    const raw = (email || 'rishugarg006@gmail.com').toString().trim().toLowerCase();
    const roleUpper = role === 'staff' ? 'STAFF' : 'ADMIN';

    try {
      const res = await fetch('/api/auth/reset-password-request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: raw, role: roleUpper })
      });
      const data = await res.json();
      return {
        success: !!data.success,
        code: data.code,
        message: data.message || (data.success
          ? 'Verification OTP has been sent to rishugarg006@gmail.com. Please check your inbox.'
          : 'Failed to send reset email.')
      };
    } catch (err: any) {
      return {
        success: false,
        code: 'NETWORK_ERROR',
        message: 'Could not reach email server. Please try again or use Google Account verification below.'
      };
    }
  };

  const requestResetMobile = (mobileOrEmail?: string, role?: UserRole) => requestResetEmail(mobileOrEmail || 'rishugarg006@gmail.com', role);
  const requestAdminResetMobile = (mobile?: string) => requestResetEmail(mobile || 'rishugarg006@gmail.com', 'admin');
  const requestAdminResetEmail = (mobileOrEmail?: string) => requestResetEmail(mobileOrEmail || 'rishugarg006@gmail.com', 'admin');

  // Verify OTP strictly on the server and reset password (persists until next reset)
  const verifyAndResetPassword = async (targetRole: UserRole, otp: string, newPass: string) => {
    const cleanOtp = otp.trim();
    const roleUpper = targetRole === 'staff' ? 'STAFF' : 'ADMIN';

    try {
      const res = await fetch('/api/auth/verify-reset-otp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: roleUpper, otp: cleanOtp })
      });
      const data = await res.json();
      if (!data.success) {
        return {
          success: false,
          message: data.message || 'Invalid verification OTP. Please check the 6-digit code sent to rishugarg006@gmail.com.'
        };
      }

      persistResetPassword(targetRole, newPass);
      return {
        success: true,
        message: `${roleUpper} password successfully updated! It will remain fixed until your next reset.`
      };
    } catch (err: any) {
      return {
        success: false,
        message: 'Could not verify OTP with server. Please try again.'
      };
    }
  };

  // Verified Google Account password reset for owner email rishugarg006@gmail.com
  const verifyGoogleAndResetPassword = async (targetRole: UserRole, newPass: string) => {
    const cleanPass = newPass.trim();
    if (!cleanPass || cleanPass.length < 4) {
      return { success: false, message: 'Password must be at least 4 characters.' };
    }
    try {
      const provider = new GoogleAuthProvider();
      provider.setCustomParameters({ prompt: 'select_account', login_hint: 'rishugarg006@gmail.com' });
      const result = await signInWithPopup(firebaseAuth, provider);
      const signedEmail = (result.user.email || '').trim().toLowerCase();

      if (signedEmail !== 'rishugarg006@gmail.com' || !result.user.emailVerified) {
        await signOut(firebaseAuth).catch(() => {});
        return {
          success: false,
          message: `Verification denied: Signed in as ${result.user.email || 'unknown'}. Only rishugarg006@gmail.com is authorized to reset passwords.`
        };
      }

      persistResetPassword(targetRole, cleanPass);
      return {
        success: true,
        message: `Verified via Google (rishugarg006@gmail.com)! ${targetRole === 'admin' ? 'ADMIN' : 'STAFF'} password updated and fixed until next reset.`
      };
    } catch (err: any) {
      return {
        success: false,
        message: err?.message || 'Google verification was cancelled or failed.'
      };
    }
  };

  const verifyAndResetAdminPass = (otp: string, newPass: string) => {
    return verifyAndResetPassword('admin', otp, newPass);
  };

  // Staff Directory CRUD (Strictly Admin Only)
  const syncStaffDirectory = (list: string[]) => {
    setStaffMembers(list);
    try {
      localStorage.setItem('ca_office_staff_members', JSON.stringify(list));
    } catch (e) {}
    const staffDocRef = doc(db, 'officeSettings', 'staffDirectory');
    setDoc(staffDocRef, {
      id: 'staffDirectory',
      staffMembers: list,
      updatedAt: new Date().toISOString()
    }, { merge: true }).catch(err => {
      handleFirestoreError(err, OperationType.WRITE, 'officeSettings/staffDirectory');
    });
  };

  const addStaffMember = (name: string) => {
    if (auth.role !== 'admin') {
      return { success: false, message: 'Unauthorized: Only Admin can add staff members.' };
    }
    const cleanName = name.trim();
    if (!cleanName) {
      return { success: false, message: 'Staff name cannot be empty.' };
    }
    if (cleanName.toLowerCase() === 'all staff') {
      return { success: false, message: '"All Staff" is a reserved group label.' };
    }
    if (staffMembers.some(s => s.toLowerCase() === cleanName.toLowerCase())) {
      return { success: false, message: `"${cleanName}" already exists in the staff list.` };
    }
    const updated = [...staffMembers, cleanName];
    syncStaffDirectory(updated);
    return { success: true, message: `Added "${cleanName}" to office staff.` };
  };

  const editStaffMember = (oldName: string, newName: string) => {
    if (auth.role !== 'admin') {
      return { success: false, message: 'Unauthorized: Only Admin can edit staff names.' };
    }
    const cleanNew = newName.trim();
    if (!cleanNew) {
      return { success: false, message: 'Staff name cannot be empty.' };
    }
    if (cleanNew.toLowerCase() === 'all staff') {
      return { success: false, message: '"All Staff" is a reserved group label.' };
    }
    if (oldName !== cleanNew && staffMembers.some(s => s !== oldName && s.toLowerCase() === cleanNew.toLowerCase())) {
      return { success: false, message: `"${cleanNew}" already exists in the staff list.` };
    }

    const updatedList = staffMembers.map(s => (s === oldName ? cleanNew : s));
    syncStaffDirectory(updatedList);

    // Also update tasks assigned to oldName so assignments remain consistent
    const affectedTasks = tasks.filter(t => t.assignedTo === oldName);
    if (affectedTasks.length > 0) {
      const updatedTasks = tasks.map(t => (t.assignedTo === oldName ? { ...t, assignedTo: cleanNew } : t));
      setTasks(updatedTasks);
      try {
        localStorage.setItem('ca_office_tasks', JSON.stringify(updatedTasks));
      } catch (e) {}
      affectedTasks.forEach(t => {
        const taskRef = doc(db, 'tasks', t.id);
        setDoc(taskRef, { ...t, assignedTo: cleanNew }, { merge: true }).catch(() => {});
      });
    }

    return { success: true, message: `Updated staff name from "${oldName}" to "${cleanNew}".` };
  };

  const deleteStaffMember = (name: string) => {
    if (auth.role !== 'admin') {
      return { success: false, message: 'Unauthorized: Only Admin can delete staff members.' };
    }
    const updated = staffMembers.filter(s => s !== name);
    syncStaffDirectory(updated);
    return { success: true, message: `Removed "${name}" from office staff.` };
  };

  // Task actions
  const addTask = (data: { title: string; description?: string; deadline?: string; isUrgent?: boolean; assignedTo?: string; attachments?: TaskAttachment[] }) => {
    const cleanTask: Task = {
      id: `task-${Date.now()}`,
      title: data.title.trim(),
      description: data.description?.trim() || '',
      deadline: data.deadline || '',
      isUrgent: !!data.isUrgent,
      assignedTo: data.assignedTo || 'All Staff',
      completed: false,
      completedAt: '',
      completedBy: '',
      attachments: data.attachments || [],
      createdAt: new Date().toISOString().split('T')[0]
    };
    // Immediate optimistic local update
    setTasks(prev => {
      const next = [cleanTask, ...prev];
      try {
        localStorage.setItem('ca_office_tasks', JSON.stringify(next));
      } catch (e) {}
      return next;
    });

    // Firestore cloud synchronization
    const taskRef = doc(db, 'tasks', cleanTask.id);
    setDoc(taskRef, cleanTask).catch(err => {
      handleFirestoreError(err, OperationType.CREATE, `tasks/${cleanTask.id}`);
    });
  };

  // Edit Task (Allowed for BOTH Admin and Staff)
  const editTask = (taskId: string, data: { title: string; description?: string; deadline?: string; isUrgent?: boolean; assignedTo?: string; attachments?: TaskAttachment[] }) => {
    const existing = tasks.find(t => t.id === taskId);
    if (!existing) return;

    const updatedTask: Task = {
      id: existing.id,
      title: data.title.trim(),
      description: data.description?.trim() || '',
      deadline: data.deadline || '',
      isUrgent: !!data.isUrgent,
      assignedTo: data.assignedTo || 'All Staff',
      completed: existing.completed,
      completedAt: existing.completedAt || '',
      completedBy: existing.completedBy || '',
      attachments: data.attachments !== undefined ? data.attachments : (existing.attachments || []),
      createdAt: existing.createdAt || new Date().toISOString().split('T')[0],
      updatedAt: new Date().toISOString()
    };

    setTasks(prev => {
      const next = prev.map(t => (t.id === taskId ? updatedTask : t));
      try {
        localStorage.setItem('ca_office_tasks', JSON.stringify(next));
      } catch (e) {}
      return next;
    });

    const taskRef = doc(db, 'tasks', taskId);
    setDoc(taskRef, updatedTask).catch(err => {
      handleFirestoreError(err, OperationType.UPDATE, `tasks/${taskId}`);
    });
  };

  // Single-click Truncate / Untruncate with zero-glitch synchronous calculation
  const toggleTaskComplete = (taskId: string) => {
    const current = tasks.find(t => t.id === taskId);
    if (!current) return;

    const nextCompleted = !current.completed;
    const completedAtStr = nextCompleted
      ? new Date().toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })
      : '';
    const completedByStr = nextCompleted
      ? (auth.username || (auth.role === 'admin' ? 'CA Rishu Garg' : 'Staff'))
      : '';

    const cleanTask: Task = {
      id: current.id,
      title: current.title,
      description: current.description || '',
      assignedTo: current.assignedTo || 'All Staff',
      deadline: current.deadline || '',
      isUrgent: !!current.isUrgent,
      completed: nextCompleted,
      completedAt: completedAtStr,
      completedBy: completedByStr,
      attachments: current.attachments || [],
      createdAt: current.createdAt || new Date().toISOString().split('T')[0]
    };

    // 1. Synchronously update local tasks state immediately (guarantees single-click response)
    const updatedTasks = tasks.map(t => (t.id === taskId ? cleanTask : t));
    setTasks(updatedTasks);
    try {
      localStorage.setItem('ca_office_tasks', JSON.stringify(updatedTasks));
    } catch (e) {}

    // 2. Firestore cloud synchronization with full document rewrite
    try {
      const taskRef = doc(db, 'tasks', taskId);
      setDoc(taskRef, cleanTask).catch(err => {
        handleFirestoreError(err, OperationType.WRITE, `tasks/${taskId}`);
      });
    } catch (err) {}
  };

  // Explicit option for both Admin and Staff to set or remove truncated state
  const setTaskTruncated = (taskId: string, truncated: boolean) => {
    const current = tasks.find(t => t.id === taskId);
    if (!current) return;
    if (current.completed === truncated) return;

    const completedAtStr = truncated
      ? new Date().toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })
      : '';
    const completedByStr = truncated
      ? (auth.username || (auth.role === 'admin' ? 'CA Rishu Garg' : 'Staff'))
      : '';

    const cleanTask: Task = {
      id: current.id,
      title: current.title,
      description: current.description || '',
      assignedTo: current.assignedTo || 'All Staff',
      deadline: current.deadline || '',
      isUrgent: !!current.isUrgent,
      completed: truncated,
      completedAt: completedAtStr,
      completedBy: completedByStr,
      attachments: current.attachments || [],
      createdAt: current.createdAt || new Date().toISOString().split('T')[0]
    };

    const updatedTasks = tasks.map(t => (t.id === taskId ? cleanTask : t));
    setTasks(updatedTasks);
    try {
      localStorage.setItem('ca_office_tasks', JSON.stringify(updatedTasks));
    } catch (e) {}

    try {
      const taskRef = doc(db, 'tasks', taskId);
      setDoc(taskRef, cleanTask).catch(err => {
        handleFirestoreError(err, OperationType.WRITE, `tasks/${taskId}`);
      });
    } catch (err) {}
  };

  const deleteTask = (taskId: string) => {
    if (auth.role !== 'admin') {
      return {
        success: false,
        message: 'Permission Denied: Staff cannot delete tasks. Only CA Admin has permission to delete tasks.'
      };
    }
    // Optimistic local update
    setTasks(prev => prev.filter(t => t.id !== taskId));

    // Firestore cloud deletion
    const taskRef = doc(db, 'tasks', taskId);
    deleteDoc(taskRef).catch(err => {
      handleFirestoreError(err, OperationType.DELETE, `tasks/${taskId}`);
    });

    return { success: true };
  };

  const addAttachmentToTask = (taskId: string, attachment: TaskAttachment) => {
    let updatedAttachments: TaskAttachment[] = [];
    setTasks(prev =>
      prev.map(t => {
        if (t.id === taskId) {
          updatedAttachments = [...t.attachments, attachment];
          return {
            ...t,
            attachments: updatedAttachments
          };
        }
        return t;
      })
    );

    // Sync attachments to Firestore
    if (updatedAttachments.length > 0) {
      const taskRef = doc(db, 'tasks', taskId);
      updateDoc(taskRef, {
        attachments: updatedAttachments
      }).catch(err => {
        handleFirestoreError(err, OperationType.UPDATE, `tasks/${taskId}`);
      });
    }
  };

  // Calendar actions
  const refreshCalendarWithAI = async (year = new Date().getFullYear(), month = new Date().getMonth() + 1) => {
    try {
      const res = await fetch('/api/calendar/enrich', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ year, month })
      });
      const data = await res.json();
      if (!data.success) {
        return { success: false, count: 0, message: data.error || 'Gemini AI sync returned an error.' };
      }
      if (Array.isArray(data.events) && data.events.length > 0) {
        // Merge without duplicates
        setCalendarEvents(prev => {
          const existingTitles = new Set(prev.map(e => e.title.toLowerCase()));
          const newOnes: StatutoryEvent[] = data.events
            .filter((e: any) => !existingTitles.has(e.title?.toLowerCase()))
            .map((e: any, idx: number) => ({
              id: `ai-${Date.now()}-${idx}`,
              title: e.title,
              date: e.date,
              category: e.category || 'STATUTORY',
              description: e.description || 'Statutory date verified by Gemini AI',
              urgency: e.urgency || 'MEDIUM',
              portalLink: e.portalLink
            }));
          return [...prev, ...newOnes];
        });
        return { success: true, count: data.events.length, message: `Successfully refreshed ${data.events.length} statutory dates & National/Punjab holidays via Gemini AI!` };
      }
      return { success: true, count: 0, message: data.message || 'Statutory calendar is already fully synchronized with latest notifications.' };
    } catch (e: any) {
      return { success: false, count: 0, message: 'Could not connect to AI service. Using cached statutory calendar.' };
    }
  };

  // UDIN partners update
  const updateUdinCredentials = (partnerKey: 'partner1' | 'partner2', data: Partial<PartnerCredentials>) => {
    setUdinPartners(prev => ({
      ...prev,
      [partnerKey]: {
        ...prev[partnerKey],
        ...data
      }
    }));
  };

  const updateMsmeDefaults = (data: Partial<MSMEFixedDefaults>) => {
    setMsmeDefaults(prev => {
      const updated = { ...prev, ...data };
      // Sync to Firestore
      const settingsRef = doc(db, 'officeSettings', 'default');
      setDoc(settingsRef, { id: 'default', ...updated }, { merge: true }).catch(err => {
        handleFirestoreError(err, OperationType.WRITE, 'officeSettings/default');
      });
      return updated;
    });
  };

  return (
    <AppContext.Provider
      value={{
        auth,
        login,
        logout,
        adminCredentials,
        staffCredentials,
        updateCredentials,
        requestResetEmail,
        requestResetMobile,
        requestAdminResetEmail,
        requestAdminResetMobile,
        verifyAndResetPassword,
        verifyGoogleAndResetPassword,
        verifyAndResetAdminPass,
        staffMembers,
        addStaffMember,
        editStaffMember,
        deleteStaffMember,
        tasks,
        addTask,
        editTask,
        toggleTaskComplete,
        setTaskTruncated,
        deleteTask,
        addAttachmentToTask,
        calendarEvents,
        refreshCalendarWithAI,
        udinPartners,
        updateUdinCredentials,
        msmeDefaults,
        updateMsmeDefaults,
        currentTab,
        setCurrentTab,
        isFirebaseConnected,
        syncTasksNow,
        lastSyncedAt
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};
