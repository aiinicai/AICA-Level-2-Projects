import { db } from '../firebase/config';
import { doc, updateDoc, increment, addDoc, collection, serverTimestamp } from 'firebase/firestore';

/**
 * Logs a reconciliation usage event and increments the user's reconciliation count.
 * @param {string} userId - The user's UID.
 */
export async function logReconciliationUsage(userId) {
  // Log event in 'reconciliation' collection
  await addDoc(collection(db, 'reconciliation'), {
    userId,
    timestamp: serverTimestamp()
  });

  // Increment reconciliationCount in user's doc
  const userRef = doc(db, 'users', userId);
  await updateDoc(userRef, {
    usage_count: increment(1)
  });
}
