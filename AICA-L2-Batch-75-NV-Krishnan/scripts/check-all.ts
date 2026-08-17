import { initializeApp } from "firebase/app";
import { getFirestore, collection, getDocs } from "firebase/firestore";
import firebaseConfig from "../firebase-applet-config.json" with { type: "json" };

const app = initializeApp(firebaseConfig);
const db = getFirestore(app, firebaseConfig.firestoreDatabaseId);

async function checkAll() {
  console.log("=== CLIENTS ===");
  const clientsSnap = await getDocs(collection(db, "clients"));
  clientsSnap.forEach((d) => console.log(d.id, d.data()));

  console.log("\n=== USERS ===");
  const usersSnap = await getDocs(collection(db, "users"));
  usersSnap.forEach((d) => console.log(d.id, d.data()));
}

checkAll().then(() => process.exit(0));
