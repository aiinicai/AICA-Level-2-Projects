/**
 * Single import point for Firestore functions. In normal use every call goes to
 * the real Cloud Firestore SDK. In "Try Demo" mode (sessionStorage flag) the same
 * calls are routed to the in-memory demo store instead, so demo visitors never
 * read or write the live database.
 */
import * as real from 'firebase/firestore';
import * as demo from './demoStore';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function pick<T extends (...args: any[]) => any>(realFn: T, demoFn: unknown): T {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return ((...args: any[]) =>
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    demo.isDemoMode() ? (demoFn as any)(...args) : (realFn as any)(...args)) as T;
}

export const collection = pick(real.collection, demo.collection);
export const doc = pick(real.doc, demo.doc);
export const query = pick(real.query, demo.query);
export const where = pick(real.where, demo.where);
export const onSnapshot = pick(real.onSnapshot, demo.onSnapshot);
export const getDocs = pick(real.getDocs, demo.getDocs);
export const setDoc = pick(real.setDoc, demo.setDoc);
export const addDoc = pick(real.addDoc, demo.addDoc);
export const updateDoc = pick(real.updateDoc, demo.updateDoc);
export const deleteDoc = pick(real.deleteDoc, demo.deleteDoc);
export const writeBatch = pick(real.writeBatch, demo.writeBatch);
export const runTransaction = pick(real.runTransaction, demo.runTransaction);
export const serverTimestamp = pick(real.serverTimestamp, demo.serverTimestamp);
