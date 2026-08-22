import { initializeApp, getApps } from 'firebase/app';
import {
  getAuth,
  signInWithPopup,
  signOut,
  GoogleAuthProvider,
  onAuthStateChanged,
  User,
} from 'firebase/auth';
import firebaseConfig from '../../firebase-applet-config.json';

// Initialize Firebase App
const app = getApps().length === 0 ? initializeApp(firebaseConfig) : getApps()[0];
export const auth = getAuth(app);

const provider = new GoogleAuthProvider();
// Add mandatory Gmail readonly scope for searching & reading Daily Professional Briefings
provider.addScope('https://www.googleapis.com/auth/gmail.readonly');

let cachedAccessToken: string | null = null;
let lastSyncTime: string | null = null;

export interface GmailConnectionState {
  isConnected: boolean; // MUST BE TRUE ONLY IF GMAIL PROFILE API VERIFICATION PASSED
  userEmail: string | null;
  userName: string | null;
  status: 'Connected' | 'Not Connected' | 'Configuration Required' | 'Authentication Expired' | 'Connection Error' | 'Reauthorization Required';
  lastSyncTime: string | null;
  errorMessage?: string;

  // Safe OAuth Diagnostic Matrix
  firebaseAuthStatus: 'PASS' | 'FAIL' | 'Connected' | 'Not Connected';
  googleUserReturned: 'PASS' | 'FAIL' | 'Not Executed';
  oauthCredentialReturned: 'PASS' | 'FAIL' | 'Not Executed';
  googleAccessTokenPresent: 'PASS' | 'FAIL' | 'Missing';
  gmailReadonlyScopeRequested: 'YES' | 'NO';
  gmailApiProfileStatus: 'PASS' | 'FAIL' | 'Pending' | 'Not Executed';
  connectedGmailAddress: string | null;
  lastError: string | null;
  lastTestTime: string | null;
}

// Function to store token safely in session memory
export const storeAccessToken = (token: string | null) => {
  cachedAccessToken = token;
  if (token) {
    sessionStorage.setItem('gmail_oauth_access_token', token);
  } else {
    sessionStorage.removeItem('gmail_oauth_access_token');
  }
};

// Retrieve token from memory or sessionStorage
export const getGmailAccessToken = (): string | null => {
  if (cachedAccessToken) return cachedAccessToken;
  const stored = sessionStorage.getItem('gmail_oauth_access_token');
  if (stored) {
    cachedAccessToken = stored;
    return stored;
  }
  return null;
};

// Call backend /api/gmail/verify-profile to verify https://www.googleapis.com/gmail/v1/users/me/profile
export const verifyGmailProfileAPI = async (
  token: string
): Promise<{ success: boolean; emailAddress?: string; error?: string }> => {
  try {
    const res = await fetch('/api/gmail/verify-profile', {
      headers: { Authorization: `Bearer ${token}` },
    });
    const data = await res.json();
    if (res.ok && data.success && data.profile?.emailAddress) {
      return { success: true, emailAddress: data.profile.emailAddress };
    } else {
      return {
        success: false,
        error: data.error || `Gmail API returned HTTP ${res.status}: ${res.statusText}`,
      };
    }
  } catch (err: any) {
    return {
      success: false,
      error: err.message || 'Failed to reach Gmail API endpoint.',
    };
  }
};

export const initAuth = (
  onAuthChange?: (state: GmailConnectionState) => void
) => {
  return onAuthStateChanged(auth, async (user: User | null) => {
    const firebaseStatus = user ? 'PASS' : 'FAIL';
    const token = getGmailAccessToken();

    if (user && token) {
      // Verify token with real Gmail API profile call
      const verifyResult = await verifyGmailProfileAPI(token);
      const testTimestamp = new Date().toLocaleString();
      if (verifyResult.success) {
        if (!lastSyncTime) {
          lastSyncTime = testTimestamp;
        }
        if (onAuthChange) {
          onAuthChange({
            isConnected: true,
            userEmail: verifyResult.emailAddress || user.email,
            userName: user.displayName,
            status: 'Connected',
            lastSyncTime,
            firebaseAuthStatus: firebaseStatus,
            googleUserReturned: 'PASS',
            oauthCredentialReturned: 'PASS',
            googleAccessTokenPresent: 'PASS',
            gmailReadonlyScopeRequested: 'YES',
            gmailApiProfileStatus: 'PASS',
            connectedGmailAddress: verifyResult.emailAddress || user.email,
            lastError: null,
            lastTestTime: testTimestamp,
          });
        }
      } else {
        // Token exists but failed profile check
        storeAccessToken(null);
        if (onAuthChange) {
          onAuthChange({
            isConnected: false,
            userEmail: user.email,
            userName: user.displayName,
            status: 'Reauthorization Required',
            lastSyncTime,
            errorMessage: verifyResult.error || 'Gmail OAuth token expired or invalid.',
            firebaseAuthStatus: firebaseStatus,
            googleUserReturned: 'PASS',
            oauthCredentialReturned: 'PASS',
            googleAccessTokenPresent: 'FAIL',
            gmailReadonlyScopeRequested: 'YES',
            gmailApiProfileStatus: 'FAIL',
            connectedGmailAddress: null,
            lastError: verifyResult.error || 'Gmail API profile verification failed',
            lastTestTime: testTimestamp,
          });
        }
      }
    } else if (user && !token) {
      // Firebase User authenticated, but no OAuth Bearer access token for Gmail API
      if (onAuthChange) {
        onAuthChange({
          isConnected: false,
          userEmail: user.email,
          userName: user.displayName,
          status: 'Reauthorization Required',
          lastSyncTime,
          errorMessage: 'Firebase authenticated, but Gmail OAuth access token is missing in session. Click Connect Gmail.',
          firebaseAuthStatus: firebaseStatus,
          googleUserReturned: 'PASS',
          oauthCredentialReturned: 'FAIL',
          googleAccessTokenPresent: 'FAIL',
          gmailReadonlyScopeRequested: 'YES',
          gmailApiProfileStatus: 'Not Executed',
          connectedGmailAddress: null,
          lastError: 'No OAuth Bearer access token found in session storage.',
          lastTestTime: new Date().toLocaleString(),
        });
      }
    } else {
      storeAccessToken(null);
      if (onAuthChange) {
        onAuthChange({
          isConnected: false,
          userEmail: null,
          userName: null,
          status: 'Not Connected',
          lastSyncTime,
          firebaseAuthStatus: 'FAIL',
          googleUserReturned: 'FAIL',
          oauthCredentialReturned: 'FAIL',
          googleAccessTokenPresent: 'Missing',
          gmailReadonlyScopeRequested: 'YES',
          gmailApiProfileStatus: 'Not Executed',
          connectedGmailAddress: null,
          lastError: null,
          lastTestTime: new Date().toLocaleString(),
        });
      }
    }
  });
};

export const connectGmailOAuth = async (): Promise<{
  state: GmailConnectionState;
  accessToken: string;
}> => {
  const testTimestamp = new Date().toLocaleString();
  try {
    const result = await signInWithPopup(auth, provider);
    const credential = GoogleAuthProvider.credentialFromResult(result);

    if (!credential?.accessToken) {
      throw new Error('Google OAuth succeeded, but failed to return a Bearer access token.');
    }

    const accessToken = credential.accessToken;
    // Store token immediately to prevent race conditions with onAuthStateChanged
    storeAccessToken(accessToken);

    // Immediately test Gmail API Profile call (https://www.googleapis.com/gmail/v1/users/me/profile)
    const verification = await verifyGmailProfileAPI(accessToken);

    if (!verification.success) {
      storeAccessToken(null);
      const failedState: GmailConnectionState = {
        isConnected: false,
        userEmail: result.user.email,
        userName: result.user.displayName,
        status: 'Connection Error',
        lastSyncTime: null,
        errorMessage: verification.error || 'Gmail API profile request failed.',
        firebaseAuthStatus: 'PASS',
        googleUserReturned: 'PASS',
        oauthCredentialReturned: 'PASS',
        googleAccessTokenPresent: 'PASS',
        gmailReadonlyScopeRequested: 'YES',
        gmailApiProfileStatus: 'FAIL',
        connectedGmailAddress: null,
        lastError: verification.error || 'Gmail API profile check failed.',
        lastTestTime: testTimestamp,
      };
      return { state: failedState, accessToken: '' };
    }

    // Success! Save token and sync time
    lastSyncTime = testTimestamp;

    const successState: GmailConnectionState = {
      isConnected: true,
      userEmail: verification.emailAddress || result.user.email,
      userName: result.user.displayName,
      status: 'Connected',
      lastSyncTime,
      firebaseAuthStatus: 'PASS',
      googleUserReturned: 'PASS',
      oauthCredentialReturned: 'PASS',
      googleAccessTokenPresent: 'PASS',
      gmailReadonlyScopeRequested: 'YES',
      gmailApiProfileStatus: 'PASS',
      connectedGmailAddress: verification.emailAddress || result.user.email,
      lastError: null,
      lastTestTime: testTimestamp,
    };

    return { state: successState, accessToken };
  } catch (error: any) {
    console.error('Gmail OAuth Sign In Error:', error);
    storeAccessToken(null);
    const isPopupClosed = error?.code === 'auth/popup-closed-by-user';
    const failedState: GmailConnectionState = {
      isConnected: false,
      userEmail: null,
      userName: null,
      status: isPopupClosed ? 'Not Connected' : 'Connection Error',
      lastSyncTime: null,
      errorMessage: isPopupClosed
        ? 'Sign in popup was closed before completing Google OAuth.'
        : error.message || 'OAuth authentication failed.',
      firebaseAuthStatus: auth.currentUser ? 'PASS' : 'FAIL',
      googleUserReturned: 'FAIL',
      oauthCredentialReturned: 'FAIL',
      googleAccessTokenPresent: 'Missing',
      gmailReadonlyScopeRequested: 'YES',
      gmailApiProfileStatus: 'FAIL',
      connectedGmailAddress: null,
      lastError: error.message || 'OAuth popup error',
      lastTestTime: testTimestamp,
    };
    return { state: failedState, accessToken: '' };
  }
};

export const disconnectGmail = async (): Promise<void> => {
  await signOut(auth);
  storeAccessToken(null);
  lastSyncTime = null;
};

export const setLastSyncTime = (timestamp: string) => {
  lastSyncTime = timestamp;
};
