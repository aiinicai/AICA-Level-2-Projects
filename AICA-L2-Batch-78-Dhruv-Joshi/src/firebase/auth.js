import { 
  createUserWithEmailAndPassword, 
  signInWithEmailAndPassword, 
  signOut, 
  onAuthStateChanged,
  GoogleAuthProvider,
  signInWithPopup,
  updateProfile
} from "firebase/auth";
import { doc, setDoc, getDoc, updateDoc, increment, collection, addDoc } from "firebase/firestore";
import { auth, db } from "./config";

// Google Auth Provider
const googleProvider = new GoogleAuthProvider();

// Sign up with email and password
export const signUpWithEmail = async (email, password, displayName, phoneNumber) => {
  try {
    const userCredential = await createUserWithEmailAndPassword(auth, email, password);
    const user = userCredential.user;
    
    // Update user profile with display name
    if (displayName) {
      await updateProfile(user, { displayName });
    }
    
    // Store user data in Firestore
    await setDoc(doc(db, "users", user.uid), {
      uid: user.uid,
      email: user.email,
      displayName: displayName || user.email.split('@')[0],
      phoneNumber: phoneNumber || '',
      createdAt: new Date().toISOString(),
      provider: "email",
      usage_count: 0,
      is_paid: false,
      subscription_expiry: null,
      upi_txn_id: ""
    });
    
    return { user, error: null };
  } catch (error) {
    return { user: null, error: error.message };
  }
};

// Sign in with email and password
export const signInWithEmail = async (email, password) => {
  try {
    const userCredential = await signInWithEmailAndPassword(auth, email, password);
    return { user: userCredential.user, error: null };
  } catch (error) {
    return { user: null, error: error.message };
  }
};

// Sign in with Google
export const signInWithGoogle = async () => {
  try {
    const result = await signInWithPopup(auth, googleProvider);
    const user = result.user;
    
    // Check if user document exists, if not create it
    const userDoc = await getDoc(doc(db, "users", user.uid));
    const isNewUser = !userDoc.exists();
    if (isNewUser) {
      await setDoc(doc(db, "users", user.uid), {
        uid: user.uid,
        email: user.email,
        displayName: user.displayName,
        photoURL: user.photoURL,
        createdAt: new Date().toISOString(),
        provider: "google",
        usage_count: 0,
        is_paid: false,
        subscription_expiry: null,
        upi_txn_id: ""
      });
    }
    
    return { user, isNewUser, error: null };
  } catch (error) {
    return { user: null, isNewUser: false, error: error.message };
  }
};

// Sign out
export const signOutUser = async () => {
  try {
    await signOut(auth);
    return { error: null };
  } catch (error) {
    return { error: error.message };
  }
};

// Auth state observer
export const onAuthStateChange = (callback) => {
  return onAuthStateChanged(auth, callback);
};

// Get current user
export const getCurrentUser = () => {
  return auth.currentUser;
};

// Get user data from Firestore
export const getUserData = async (uid) => {
  try {
    const userDoc = await getDoc(doc(db, "users", uid));
    if (userDoc.exists()) {
      return { data: userDoc.data(), error: null };
    } else {
      return { data: null, error: "User not found" };
    }
  } catch (error) {
    return { data: null, error: error.message };
  }
};

// Check and increment user usage count
export const checkAndIncrementUsage = async (uid) => {
  console.log('DEBUG: checkAndIncrementUsage called with uid:', uid);
  if (!uid) {
    console.log('DEBUG: No UID provided, returning access denied');
    return { canAccess: false, message: "Please sign in to use the tool." };
  }

  const userDocRef = doc(db, "users", uid);

  try {
    console.log('DEBUG: Fetching user document for uid:', uid);
    const userDoc = await getDoc(userDocRef);
    let userData;

    if (!userDoc.exists()) {
      console.log('DEBUG: New user detected, creating user document.');
      const currentUser = auth.currentUser;
      if (!currentUser) {
        return { canAccess: false, message: "Please sign in again." };
      }
      const newUserData = {
        uid: uid,
        email: currentUser.email,
        displayName: currentUser.displayName || 'User',
        photoURL: currentUser.photoURL,
        createdAt: new Date().toISOString(),
        usage_count: 0,
        is_paid: false,
        subscription_expiry: null,
      };
      await setDoc(userDocRef, newUserData);
      userData = newUserData;
    } else {
      userData = userDoc.data();
    }

    console.log('DEBUG: Current user data:', userData);
    const count = userData.usage_count || 0;

    // --- MODIFIED LOGIC: Always grant access (Unlimited Free Usage) ---
    console.log(`DEBUG: Usage count: ${count}. Incrementing count but granting access.`);
    
    // Increment count in the background for analytics
    updateDoc(userDocRef, { usage_count: increment(1) }).catch(err => {
      console.error('DEBUG: Background usage count update failed:', err);
    });

    return { canAccess: true };

  } catch (error) {
    console.error("DEBUG: CRITICAL ERROR in checkAndIncrementUsage:", error);
    if (error.message?.includes('net::ERR_BLOCKED_BY_CLIENT') || error.code === 'unavailable') {
      return {
        canAccess: false,
        reason: 'ad_blocker_or_network',
        message: 'Connection to our database was blocked. Please disable your ad blocker for this site, check your network, and try again.'
      };
    }
    return { canAccess: false, reason: 'unexpected_error', message: 'An unexpected error occurred. Please try again.' };
  }
};

// Submit payment details for manual verification
export const submitPaymentDetails = async ({ uid, name, companyName, gstNumber, phoneNumber, upiTxnId }) => {
  if (!uid || !name || !companyName || !phoneNumber || !upiTxnId) {
    return { success: false, error: "Missing required fields." };
  }

  try {
    // Create a new document in the 'payment_submissions' collection
    await addDoc(collection(db, "payment_submissions"), {
      uid,
      name,
      companyName,
      gstNumber: gstNumber || '', // Store empty string if not provided
      phoneNumber,
      upi_txn_id: upiTxnId,
      submitted_at: new Date().toISOString(),
      status: 'pending_verification',
    });

    return { success: true };

  } catch (error) {
    console.error("Error submitting payment details:", error);
    return { success: false, error: "Failed to submit payment details. Please try again." };
  }
};
