import { initializeApp } from 'firebase/app';
import {
  getAuth,
  GoogleAuthProvider,
  onAuthStateChanged,
  signInWithPopup,
  signOut,
  type User,
} from 'firebase/auth';
import { doc, getDocFromServer, getFirestore } from 'firebase/firestore';
import firebaseConfig from '../../firebase-applet-config.json';
import { getDemoRole, isDemoMode, setDemoRole, resetDemoStore, type DemoRole } from './demoStore';
import { DEMO_USERS, seedDemoData } from './demoData';

const app = initializeApp(firebaseConfig);
const databaseId =
  (firebaseConfig as { firestoreDatabaseId?: string }).firestoreDatabaseId ||
  'ai-studio-15249b72-fb53-40ef-becb-01f319935e29';

export const db = getFirestore(app, databaseId);
export const auth = getAuth(app);

export const SHEETS_SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly'];

const googleProvider = new GoogleAuthProvider();
googleProvider.setCustomParameters({
  prompt: 'select_account',
});

// In-memory only access token cache (never stored in localStorage or sessionStorage)
let cachedSheetsAccessToken: string | null = null;
let isSigningIn = false;

export const getSheetsAccessToken = (): string | null => cachedSheetsAccessToken;

export function formatFirebaseAuthError(err: unknown): string {
  const code = (err as { code?: string })?.code || '';
  const msg = err instanceof Error ? err.message : String(err);

  if (code === 'auth/popup-closed-by-user' || msg.includes('auth/popup-closed-by-user')) {
    return 'Google Sign-In window was closed before completing. Please click "Sign in with Google" again and finish selecting your account (or allow pop-ups in your browser if it closed automatically).';
  }
  if (code === 'auth/popup-blocked' || msg.includes('auth/popup-blocked')) {
    return 'Your browser blocked the Google Sign-In pop-up. Please allow pop-ups for this site and try again.';
  }
  if (code === 'auth/cancelled-popup-request' || msg.includes('auth/cancelled-popup-request')) {
    return 'Another sign-in window is already open. Please complete or close it and try again.';
  }
  if (code === 'auth/unauthorized-domain' || msg.includes('auth/unauthorized-domain')) {
    const host = typeof window !== 'undefined' ? window.location.hostname : 'this domain';
    return `Domain "${host}" is not yet authorized in Firebase Authentication. Add "${host}" under Firebase Console → Authentication → Settings → Authorized domains (and add its origin to Google Cloud Console → Credentials → Authorized JavaScript origins if using Google Sheets sync).`;
  }
  return msg || 'Google Sign-In failed.';
}

// ---- Demo ("Try Demo") session: a fake signed-in user backed by in-memory sample data ----
type AuthCallback = (user: User | null, hasSheetsToken: boolean) => void;
const demoAuthListeners = new Set<AuthCallback>();

const demoUserFor = (role: DemoRole): User =>
  ({
    uid: `demo-${role}`,
    email: DEMO_USERS[role].email,
    displayName: DEMO_USERS[role].name,
    photoURL: null,
    emailVerified: true,
    isAnonymous: false,
  }) as unknown as User;

const emitDemoAuth = () => {
  const role = getDemoRole();
  const user = role ? demoUserFor(role) : null;
  demoAuthListeners.forEach((cb) => cb(user, false));
};

/** Enter (or switch role inside) demo mode. No Google account or password involved. */
export const startDemoSession = (role: DemoRole): void => {
  seedDemoData();
  setDemoRole(role);
  emitDemoAuth();
};

export const exitDemoSession = (): void => {
  setDemoRole(null);
  resetDemoStore();
  emitDemoAuth();
};

export const initFirebaseAuth = (onUserChange: AuthCallback) => {
  demoAuthListeners.add(onUserChange);
  if (isDemoMode()) {
    // Page reloaded while in demo: re-seed the sample data and restore the same demo user
    seedDemoData();
    onUserChange(demoUserFor(getDemoRole() as DemoRole), false);
  }
  const unsub = onAuthStateChanged(auth, (user) => {
    if (isDemoMode()) return; // demo owns the session; ignore real auth events
    if (!user) {
      cachedSheetsAccessToken = null;
    }
    onUserChange(user, Boolean(cachedSheetsAccessToken));
  });
  return () => {
    demoAuthListeners.delete(onUserChange);
    unsub();
  };
};

export const signInWithGoogle = async (): Promise<{ user: User; accessToken: string | null }> => {
  try {
    isSigningIn = true;
    const result = await signInWithPopup(auth, googleProvider);
    const credential = GoogleAuthProvider.credentialFromResult(result);
    // The plain sign-in token carries no Sheets scope, so it is deliberately NOT cached;
    // Sheets access is requested on first use via requestSheetsPermission().
    void credential;
    return {
      user: result.user,
      accessToken: cachedSheetsAccessToken,
    };
  } catch (err) {
    throw new Error(formatFirebaseAuthError(err));
  } finally {
    isSigningIn = false;
  }
};

export const requestSheetsPermission = async (): Promise<string> => {
  if (isDemoMode()) {
    throw new Error('Google Sheets sync is turned off in demo mode.');
  }
  const sheetsProvider = new GoogleAuthProvider();
  for (const scope of SHEETS_SCOPES) {
    sheetsProvider.addScope(scope);
  }
  sheetsProvider.setCustomParameters({
    prompt: 'consent',
    ...(auth.currentUser?.email ? { login_hint: auth.currentUser.email } : {}),
  });
  try {
    const result = await signInWithPopup(auth, sheetsProvider);
    const credential = GoogleAuthProvider.credentialFromResult(result);
    if (!credential?.accessToken) {
      throw new Error('Google Sheets permission was not granted.');
    }
    cachedSheetsAccessToken = credential.accessToken;
    return credential.accessToken;
  } catch (err) {
    throw new Error(formatFirebaseAuthError(err));
  }
};

export const logoutUser = async (): Promise<void> => {
  if (isDemoMode()) {
    exitDemoSession();
    return;
  }
  cachedSheetsAccessToken = null;
  await signOut(auth);
};

export const getIsSigningIn = (): boolean => isSigningIn;

export enum OperationType {
  CREATE = 'create',
  UPDATE = 'update',
  DELETE = 'delete',
  LIST = 'list',
  GET = 'get',
  WRITE = 'write',
}

export interface FirestoreErrorInfo {
  error: string;
  operationType: OperationType;
  path: string | null;
  authInfo: {
    userId?: string | null;
    email?: string | null;
    emailVerified?: boolean | null;
    isAnonymous?: boolean | null;
    tenantId?: string | null;
    providerInfo?: {
      providerId?: string | null;
      email?: string | null;
    }[];
  };
}

export function handleFirestoreError(
  error: unknown,
  operationType: OperationType,
  path: string | null
): never {
  const errInfo: FirestoreErrorInfo = {
    error: error instanceof Error ? error.message : String(error),
    authInfo: {
      userId: auth.currentUser?.uid,
      email: auth.currentUser?.email,
      emailVerified: auth.currentUser?.emailVerified,
      isAnonymous: auth.currentUser?.isAnonymous,
      tenantId: auth.currentUser?.tenantId,
      providerInfo:
        auth.currentUser?.providerData?.map((provider) => ({
          providerId: provider.providerId,
          email: provider.email,
        })) || [],
    },
    operationType,
    path,
  };
  console.error('Firestore Error:', JSON.stringify(errInfo));
  throw new Error(JSON.stringify(errInfo));
}

export async function testFirestoreConnection(): Promise<boolean> {
  if (isDemoMode()) return true;
  try {
    await getDocFromServer(doc(db, 'test', 'connection'));
    return true;
  } catch (error) {
    if (error instanceof Error && error.message.includes('the client is offline')) {
      console.error('Firestore client is offline. Please verify Firebase configuration.');
      return false;
    }
    return true;
  }
}
