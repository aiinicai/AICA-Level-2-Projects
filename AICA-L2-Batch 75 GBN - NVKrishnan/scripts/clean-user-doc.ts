import { initializeApp } from "firebase/app";
import { getFirestore, doc, deleteDoc } from "firebase/firestore";
import firebaseConfig from "../firebase-applet-config.json" with { type: "json" };

const app = initializeApp(firebaseConfig);
const db = getFirestore(app, firebaseConfig.firestoreDatabaseId);

async function cleanDoc() {
  await deleteDoc(doc(db, "users", "user_1786702484410"));
  console.log("Deleted old user_1786702484410");
}

cleanDoc().then(() => process.exit(0)).catch(e => { console.error(e); process.exit(1); });
