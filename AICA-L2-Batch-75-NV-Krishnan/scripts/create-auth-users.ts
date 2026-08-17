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
  getDoc,
  serverTimestamp 
} from "firebase/firestore";
import firebaseConfig from "../firebase-applet-config.json" with { type: "json" };

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const db = getFirestore(app, firebaseConfig.firestoreDatabaseId);

async function ensureUser(email: string, pass: string, role: string, displayName: string) {
  let uid = "";
  console.log(`\nChecking / Creating Firebase Auth user for: ${email}`);
  
  try {
    const cred = await signInWithEmailAndPassword(auth, email, pass);
    uid = cred.user.uid;
    console.log(`User already exists in Firebase Auth! UID: ${uid}`);
  } catch (err: any) {
    if (err.code === "auth/user-not-found" || err.code === "auth/invalid-credential" || err.code === "auth/invalid-login-credentials") {
      try {
        console.log(`Creating new Firebase Auth account for ${email}...`);
        const newCred = await createUserWithEmailAndPassword(auth, email, pass);
        uid = newCred.user.uid;
        console.log(`Created Firebase Auth user successfully! Real UID: ${uid}`);
      } catch (createErr: any) {
        console.error(`Failed to create user ${email}:`, createErr.code, createErr.message);
        throw createErr;
      }
    } else {
      console.error(`Unexpected auth error for ${email}:`, err.code, err.message);
      throw err;
    }
  }

  // Now create/update the Firestore /users/{uid} document with the REAL Firebase Auth UID
  console.log(`Updating Firestore /users/${uid} document...`);
  await setDoc(doc(db, "users", uid), {
    uid: uid,
    email: email,
    role: role,
    isActive: true,
    displayName: displayName,
    updatedAt: serverTimestamp()
  }, { merge: true });

  console.log(`Firestore /users/${uid} updated with role="${role}".`);
  return uid;
}

async function run() {
  console.log("=== CREATING REAL FIREBASE AUTH ACCOUNTS AND LINKING FIRESTORE DOCS ===");
  
  const adminUid = await ensureUser(
    "admin@abc-associates.com",
    "Admin@123456",
    "full_admin",
    "Senior Partner (Admin)"
  );

  const auditorUid = await ensureUser(
    "auditor@abc-associates.com",
    "Audit@123456",
    "team_member",
    "Audit Manager (Staff)"
  );

  console.log("\n=== VERIFYING SIGN-IN FOR BOTH ACCOUNTS ===");
  
  // Test Admin sign in
  const adminSignIn = await signInWithEmailAndPassword(auth, "admin@abc-associates.com", "Admin@123456");
  console.log(`Admin Sign-in SUCCESS! UID: ${adminSignIn.user.uid}`);
  const adminDoc = await getDoc(doc(db, "users", adminSignIn.user.uid));
  console.log(`Admin Firestore Profile:`, adminDoc.data());

  // Test Auditor sign in
  const auditorSignIn = await signInWithEmailAndPassword(auth, "auditor@abc-associates.com", "Audit@123456");
  console.log(`Auditor Sign-in SUCCESS! UID: ${auditorSignIn.user.uid}`);
  const auditorDoc = await getDoc(doc(db, "users", auditorSignIn.user.uid));
  console.log(`Auditor Firestore Profile:`, auditorDoc.data());

  console.log("\nALL VERIFICATIONS PASSED SUCCESSFULLY!");
}

run()
  .then(() => process.exit(0))
  .catch((err) => {
    console.error("Execution failed:", err);
    process.exit(1);
  });
