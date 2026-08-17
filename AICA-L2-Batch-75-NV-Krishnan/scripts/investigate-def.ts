import { initializeApp } from "firebase/app";
import { getFirestore, collection, getDocs, doc, getDoc } from "firebase/firestore";
import { getAuth, signInWithEmailAndPassword } from "firebase/auth";
import firebaseConfig from "../firebase-applet-config.json" with { type: "json" };

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const db = getFirestore(app, firebaseConfig.firestoreDatabaseId);

async function investigate() {
  console.log("=== CLIENTS ===");
  const clientSnap = await getDocs(collection(db, "clients"));
  clientSnap.forEach(d => console.log(d.id, "=>", d.data()));

  console.log("\n=== ENGAGEMENTS ===");
  const engSnap = await getDocs(collection(db, "engagements"));
  engSnap.forEach(d => console.log(d.id, "=>", d.data()));

  console.log("\n=== USERS ===");
  const userSnap = await getDocs(collection(db, "users"));
  userSnap.forEach(d => console.log(d.id, "=>", d.data()));

  console.log("\n=== CONSENT LOG ===");
  const logSnap = await getDocs(collection(db, "consentLog"));
  logSnap.forEach(d => console.log(d.id, "=>", d.data()));
}

investigate().then(() => process.exit(0)).catch(e => { console.error(e); process.exit(1); });
