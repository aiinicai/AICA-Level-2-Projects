import { initializeApp } from "firebase/app";
import { getFirestore, collection, getDocs, doc, deleteDoc } from "firebase/firestore";
import firebaseConfig from "../firebase-applet-config.json" with { type: "json" };

const app = initializeApp(firebaseConfig);
const db = getFirestore(app, firebaseConfig.firestoreDatabaseId);

async function cleanEngagements() {
  console.log("=== CLEANING UNREQUESTED SEED ENGAGEMENTS ===");
  const snap = await getDocs(collection(db, "engagements"));
  for (const d of snap.docs) {
    console.log(`Deleting engagement: ${d.id}`);
    // Delete documents subcollection if any
    const subSnap = await getDocs(collection(db, "engagements", d.id, "documents"));
    for (const subDoc of subSnap.docs) {
      await deleteDoc(doc(db, "engagements", d.id, "documents", subDoc.id));
    }
    await deleteDoc(doc(db, "engagements", d.id));
  }
  console.log("All unrequested engagements deleted successfully.");
}

cleanEngagements().then(() => process.exit(0)).catch((err) => {
  console.error(err);
  process.exit(1);
});
