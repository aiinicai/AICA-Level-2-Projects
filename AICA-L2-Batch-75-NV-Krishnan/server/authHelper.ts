import { initializeApp } from "firebase/app";
import { 
  getAuth, 
  signInWithEmailAndPassword, 
  createUserWithEmailAndPassword 
} from "firebase/auth";
import { 
  getFirestore, 
  doc, 
  setDoc, 
  deleteDoc,
  collection,
  query,
  where,
  getDocs,
  serverTimestamp 
} from "firebase/firestore";
import firebaseConfig from "../firebase-applet-config.json" with { type: "json" };

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const db = getFirestore(app, firebaseConfig.firestoreDatabaseId);

export interface AuthEnsureResult {
  uid: string;
  isExistingAccount: boolean;
}

export async function ensureAuthUserAndProfile(
  email: string,
  pass: string,
  role: string,
  displayName: string,
  linkedClientId?: string
): Promise<AuthEnsureResult> {
  let uid = "";
  let isExistingAccount = false;
  const normalizedEmail = email.trim().toLowerCase();

  try {
    const cred = await signInWithEmailAndPassword(auth, normalizedEmail, pass);
    uid = cred.user.uid;
    console.log(`[AuthHelper] Authenticated ${normalizedEmail} (UID: ${uid})`);
  } catch (signInErr: any) {
    console.log(`[AuthHelper] Sign-in for ${normalizedEmail} produced: ${signInErr.code}`);

    try {
      const newCred = await createUserWithEmailAndPassword(auth, normalizedEmail, pass);
      uid = newCred.user.uid;
      console.log(`[AuthHelper] Created new Firebase Auth account for ${normalizedEmail} (UID: ${uid})`);
    } catch (createErr: any) {
      if (createErr.code === "auth/email-already-in-use") {
        console.log(`[AuthHelper] Account for ${normalizedEmail} already exists in Firebase Auth. Querying existing profile...`);
        isExistingAccount = true;

        const userQuery = query(collection(db, "users"), where("email", "==", normalizedEmail));
        const userSnap = await getDocs(userQuery);

        if (!userSnap.empty) {
          uid = userSnap.docs[0].id;
          console.log(`[AuthHelper] Found existing user doc for ${normalizedEmail}: UID ${uid}`);
        } else {
          // Check all user docs if where query misses
          const allSnap = await getDocs(collection(db, "users"));
          let foundDocId = "";
          allSnap.forEach((d) => {
            if (d.data().email?.toLowerCase() === normalizedEmail) {
              foundDocId = d.id;
            }
          });

          if (foundDocId) {
            uid = foundDocId;
            console.log(`[AuthHelper] Matched existing user doc in full scan: UID ${uid}`);
          } else {
            uid = `user_${Date.now()}`;
            console.log(`[AuthHelper] Provisioning new profile doc ID for existing auth user: ${uid}`);
          }
        }
      } else {
        console.error(`[AuthHelper] Critical error creating user for ${normalizedEmail}:`, createErr);
        throw createErr;
      }
    }
  }

  if (!uid) {
    throw new Error(`Failed to resolve a valid UID for user ${normalizedEmail}`);
  }

  const profileData: Record<string, any> = {
    uid: uid,
    email: normalizedEmail,
    role: role,
    isActive: true,
    displayName: displayName || normalizedEmail.split("@")[0],
    updatedAt: serverTimestamp(),
  };

  if (linkedClientId) {
    profileData.linkedClientId = linkedClientId;
  }

  await setDoc(doc(db, "users", uid), profileData, { merge: true });
  console.log(`[AuthHelper] Profile synchronized for UID ${uid} in /users`);

  return { uid, isExistingAccount };
}

export async function cleanupPlaceholderUsers() {
  const placeholders = ["admin_user_seed", "auditor_user_seed", "client_user_seed"];
  for (const id of placeholders) {
    try {
      await deleteDoc(doc(db, "users", id));
    } catch (e) {}
  }
}
