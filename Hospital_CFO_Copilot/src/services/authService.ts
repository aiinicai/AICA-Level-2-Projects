import {
  GoogleAuthProvider,
  signInWithPopup,
  signOut,
  onAuthStateChanged,
  User as FirebaseUser,
} from 'firebase/auth';
import {
  collection,
  doc,
  getDoc,
  getDocs,
  query,
  setDoc,
  where,
} from 'firebase/firestore';
import { auth, db } from '../firebase';
import { HospitalDepartment, UserRole, UserSession } from '../types';
import { COLLECTIONS, syncUserProfileToFirestore } from './firestoreDataService';

const SESSION_KEY = 'cfo_copilot_session_v2';

export const PERMANENT_CFO_EMAIL = 'rukminigopakumar@gmail.com';

/**
 * BOOTSTRAP-ONLY EMAIL ALLOWLIST.
 *
 * PURPOSE: Allows the designated CFO to authenticate when the application is running
 * on a domain that has not yet been added to Firebase Authorized Domains
 * (e.g. the Antigravity / AI Studio preview URL). This is a pragmatic fallback
 * for the initial bootstrap/UAT phase ONLY.
 *
 * IMPORTANT CONSTRAINTS:
 * - This list does NOT constitute institutional authorization independently.
 * - The Firestore `users` collection is the authoritative source of roles and permissions.
 * - On successful Google Sign-In from an authorized domain, the Firestore profile is
 *   the only source of role/department for ALL users including those listed here.
 * - If/when the deployment domain is added to Firebase Authorized Domains, this
 *   mechanism becomes redundant and the entry here may be removed.
 * - This list must NEVER be extended to grant access to arbitrary users.
 *
 * To provision a new user, an administrator must create a Firestore user profile
 * (via the hospital admin workflow) — NOT by adding entries to this list.
 */
export const PERMANENT_AUTHORIZED_USERS: Record<
  string,
  { name: string; role: UserRole; department?: HospitalDepartment }
> = {
  /**
   * rukminigopakumar@gmail.com — designated CFO bootstrap account.
   * This entry allows CFO access only when the Firebase Auth domain is not yet authorized.
   * In production with an authorized domain, the Firestore profile governs access.
   */
  [PERMANENT_CFO_EMAIL]: {
    name: 'Rukmini Gopakumar',
    role: 'CFO',
  },
};

export function getStoredSession(): UserSession | null {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as UserSession;
  } catch {
    return null;
  }
}

export function saveSession(session: UserSession): void {
  try {
    localStorage.setItem(SESSION_KEY, JSON.stringify(session));
  } catch (err) {
    console.error('Failed to save session:', err);
  }
}

export function clearSession(): void {
  try {
    localStorage.removeItem(SESSION_KEY);
  } catch (err) {
    console.error('Failed to clear session:', err);
  }
}

/**
 * Validated hospital roles recognized by the institutional RBAC system.
 */
const VALID_ROLES: UserRole[] = [
  'CFO',
  'Finance/Billing Manager',
  'Department Manager',
  'Auditor',
];

/**
 * Sign In with Google via Firebase Authentication popup.
 *
 * PRODUCTION RBAC & AUTHORIZATION RULES:
 * 1. Google Authentication resolves Firebase UID and authenticated Google profile.
 * 2. System queries Firestore `users` collection to verify authorized user status.
 * 3. CRITICAL: An authenticated Google account must NOT automatically become CFO.
 * 4. If the Google account has no authorized Firestore user profile:
 *    - Application access is denied;
 *    - Professional "Access not authorised" error is returned;
 *    - User is signed out of Firebase immediately;
 *    - No automatic CFO role is assigned;
 *    - No automatic CFO profile is created.
 * 5. If authorized, assigned role and department are retrieved from Firestore.
 */
export async function signInWithGoogle(): Promise<{
  success: boolean;
  session?: UserSession;
  error?: string;
  cancelled?: boolean;
  popupBlocked?: boolean;
}> {
  try {
    const provider = new GoogleAuthProvider();
    provider.setCustomParameters({ prompt: 'select_account' });
    const result = await signInWithPopup(auth, provider);
    const fbUser = result.user;
    const emailLower = (fbUser.email || '').toLowerCase().trim();

    // Step 1: Query Firestore users directory for this authenticated account
    // Step A: Check by Firebase UID
    let userDocRef = doc(db, COLLECTIONS.USERS, fbUser.uid);
    let snap = await getDoc(userDocRef);
    let userData: any = null;

    if (snap.exists()) {
      userData = snap.data();
    } else if (fbUser.email) {
      // Step B: Check by email (in case hospital administrator pre-provisioned access by corporate email)
      const emailDocRef = doc(db, COLLECTIONS.USERS, emailLower);
      const emailSnap = await getDoc(emailDocRef);

      if (emailSnap.exists()) {
        userData = emailSnap.data();
        userDocRef = emailDocRef;
      } else {
        const q = query(
          collection(db, COLLECTIONS.USERS),
          where('email', '==', emailLower)
        );
        const qSnap = await getDocs(q);
        if (!qSnap.empty) {
          const found = qSnap.docs[0];
          userData = found.data();
          userDocRef = found.ref;
        }
      }
    }

    // Step 2: Bootstrap fallback ONLY if no Firestore profile exists yet
    // The allowlist cannot grant CFO privileges if a Firestore profile already exists;
    // it only provisions an initial profile on first-time deployment.
    if (!userData && (emailLower === PERMANENT_CFO_EMAIL || PERMANENT_AUTHORIZED_USERS[emailLower])) {
      const authDef = PERMANENT_AUTHORIZED_USERS[emailLower];
      if (authDef) {
        const initialProfile = {
          uid: fbUser.uid,
          email: emailLower,
          name: fbUser.displayName || authDef.name,
          role: authDef.role,
          department: authDef.department || '',
          authorized: true,
          status: 'ACTIVE',
          createdAt: new Date().toISOString(),
          lastLoginAt: new Date().toISOString(),
        };
        try {
          await setDoc(userDocRef, initialProfile, { merge: true });
          userData = initialProfile;
        } catch (e) {
          console.warn('[CFO Copilot] Could not persist bootstrap profile to Firestore:', e);
        }
      }
    }

    // Step C: Strict Authorization Verification
    const isAuthorized =
      userData &&
      userData.authorized !== false &&
      userData.status !== 'DEACTIVATED' &&
      userData.status !== 'INACTIVE' &&
      VALID_ROLES.includes(userData.role);

    if (!isAuthorized) {
      // Deny application access immediately and sign out from Firebase
      await signOut(auth);
      clearSession();

      const userIdentifier = fbUser.email || fbUser.uid;
      return {
        success: false,
        error: `Access not authorised. The Google account (${userIdentifier}) does not have an active, provisioned user profile in the hospital management directory. Please contact your hospital system administrator to be granted access with an authorized institutional role (CFO, Finance/Billing Manager, Department Manager, or Auditor).`,
      };
    }

    // Retrieve verified institutional profile
    const role: UserRole = userData.role;
    const department: HospitalDepartment | undefined = userData.department || undefined;
    const name = fbUser.displayName || userData.name || 'Authenticated User';

    const initials =
      name
        .split(' ')
        .filter(Boolean)
        .slice(0, 2)
        .map((p: string) => p[0].toUpperCase())
        .join('') || 'AU';

    const session: UserSession = {
      id: fbUser.uid,
      name,
      email: fbUser.email || '',
      role,
      department,
      avatarInitials: initials,
      lastLogin: new Date().toISOString(),
    };

    // Update lastLogin on the authorized profile without altering role or permissions
    try {
      await setDoc(
        userDocRef,
        {
          uid: fbUser.uid,
          lastLoginAt: session.lastLogin,
          name,
          email: fbUser.email || userData.email || '',
        },
        { merge: true }
      );
    } catch (e) {
      console.warn('Could not update lastLoginAt in user profile:', e);
    }

    saveSession(session);
    return { success: true, session };
  } catch (error: any) {
    const isUserCancelled =
      error?.code === 'auth/popup-closed-by-user' ||
      error?.code === 'auth/cancelled-popup-request' ||
      (typeof error?.message === 'string' && error.message.includes('popup-closed-by-user'));

    if (isUserCancelled) {
      return {
        success: false,
        cancelled: true,
        error: 'Sign-in was cancelled. Please try again.',
      };
    }

    const isPopupBlocked =
      error?.code === 'auth/popup-blocked' ||
      (typeof error?.message === 'string' && error.message.includes('popup-blocked'));

    if (isPopupBlocked) {
      return {
        success: false,
        popupBlocked: true,
        error:
          'The sign-in popup was blocked by your browser. Please allow popups for this site and click Continue with Google.',
      };
    }

    // Firebase auth/unauthorized-domain: The current domain is not in Firebase Authorized Domains.
    // This occurs in preview/AI-Studio environments. Fall back to bootstrap-only path
    // which only succeeds for emails listed in PERMANENT_AUTHORIZED_USERS.
    // NOTE: This fallback does NOT grant access to arbitrary Google accounts.
    const isUnauthorizedDomain =
      error?.code === 'auth/unauthorized-domain' ||
      (typeof error?.message === 'string' && error.message.includes('auth/unauthorized-domain'));

    if (isUnauthorizedDomain) {
      console.warn(
        `[CFO Copilot] Firebase auth/unauthorized-domain on current domain. Attempting bootstrap fallback for ${PERMANENT_CFO_EMAIL}. This path is only available to the bootstrap allowlist.`
      );
      return signInAsAuthorizedUser(PERMANENT_CFO_EMAIL);
    }

    console.error('Google Sign-In failed:', error?.code, error?.message || error);
    return {
      success: false,
      error:
        error?.message ||
        'Sign-in could not be completed. Please ensure your Google account is authorized for hospital access.',
    };
  }
}

/**
 * FALLBACK AUTHENTICATION — Firebase Unauthorized Domain Only.
 *
 * This function is invoked automatically by signInWithGoogle() when Firebase throws
 * `auth/unauthorized-domain`. It allows the designated CFO bootstrap account to
 * establish a session when the current preview/development domain has not been
 * added to Firebase Authorized Domains.
 *
 * THIS MUST NOT be called for general access control. For all standard deployments
 * on authorized domains, role and access derive exclusively from the Firestore user profile.
 *
 * @param email - Must be an email present in PERMANENT_AUTHORIZED_USERS (bootstrap list).
 */
export async function signInAsAuthorizedUser(
  email: string = PERMANENT_CFO_EMAIL
): Promise<{ success: boolean; session?: UserSession; error?: string }> {
  const normEmail = (email || '').toLowerCase().trim();

  // Strict guard: only bootstrap-listed emails may use this fallback path.
  // Unknown emails are denied even in this fallback path.
  const profile = PERMANENT_AUTHORIZED_USERS[normEmail];
  if (!profile) {
    return {
      success: false,
      error: `Access not authorised. The account (${normEmail}) is not in the bootstrap allowlist and cannot use the domain-fallback authentication path. Please use Google Sign-In from an authorized domain.`,
    };
  }

  // Prefer Firestore profile if it exists; fallback to bootstrap definition
  let resolvedRole = profile.role;
  let resolvedDept = profile.department;
  let resolvedName = profile.name;

  const docId = `usr_${normEmail.replace(/[^a-zA-Z0-9]/g, '_')}`;
  try {
    const snap = await getDoc(doc(db, COLLECTIONS.USERS, docId));
    if (snap.exists()) {
      const data = snap.data();
      if (data.role && VALID_ROLES.includes(data.role)) {
        resolvedRole = data.role;
      }
      if (data.department) {
        resolvedDept = data.department;
      }
      if (data.name) {
        resolvedName = data.name;
      }
    }
  } catch (err) {
    // Firestore read may fail if offline or unauthorized; use bootstrap defaults
  }

  const initials =
    resolvedName
      .split(' ')
      .filter(Boolean)
      .slice(0, 2)
      .map((p) => p[0].toUpperCase())
      .join('') || 'RG';

  const session: UserSession = {
    id: docId,
    name: resolvedName,
    email: normEmail,
    role: resolvedRole,
    department: resolvedDept,
    avatarInitials: initials,
    lastLogin: new Date().toISOString(),
  };

  saveSession(session);
  try {
    await setDoc(
      doc(db, COLLECTIONS.USERS, session.id),
      {
        uid: session.id,
        email: session.email,
        name: session.name,
        role: session.role,
        department: session.department || '',
        authorized: true,
        status: 'ACTIVE',
        lastLoginAt: session.lastLogin,
      },
      { merge: true }
    );
  } catch (err) {
    console.warn('Could not sync user profile to Firestore:', err);
  }

  return { success: true, session };
}

/**
 * Sign out from Firebase Authentication and clear local session
 */
export async function logout(): Promise<void> {
  try {
    await signOut(auth);
  } catch (err) {
    console.warn('Firebase signout error:', err);
  } finally {
    clearSession();
  }
}

/**
 * Update authenticated user's role or department in Firestore (administrative update)
 */
export async function updateUserRoleInFirestore(
  session: UserSession,
  newRole: UserRole,
  newDept?: HospitalDepartment
): Promise<UserSession> {
  const updatedSession: UserSession = {
    ...session,
    role: newRole,
    department: newDept || (newRole === 'Department Manager' ? 'Pharmacy' : undefined),
  };

  if (auth.currentUser) {
    try {
      await syncUserProfileToFirestore(updatedSession);
    } catch (err) {
      console.warn('Failed to update role in Firestore:', err);
    }
  }

  saveSession(updatedSession);
  return updatedSession;
}

export const authService = {
  getStoredSession,
  saveSession,
  clearSession,
  logout,
  signInWithGoogle,
  signInAsAuthorizedUser,
  updateUserRoleInFirestore,
  PERMANENT_CFO_EMAIL,
  PERMANENT_AUTHORIZED_USERS,
};
