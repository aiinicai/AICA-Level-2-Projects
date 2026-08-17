import { initializeApp } from "firebase/app";
import { getFirestore, collection, getDocs, doc, deleteDoc } from "firebase/firestore";
import firebaseConfig from "../firebase-applet-config.json" with { type: "json" };

const app = initializeApp(firebaseConfig);
const db = getFirestore(app, firebaseConfig.firestoreDatabaseId);

async function listEngagements() {
  console.log("=== CHECKING ALL ENGAGEMENTS IN FIRESTORE ===");
  const snap = await getDocs(collection(db, "engagements"));
  console.log(`Found ${snap.size} engagement(s):`);
  snap.forEach((d) => {
    console.log(`- ID: ${d.id}`, d.data());
  });
}

listEngagements()
  .then(() => process.exit(0))
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });
